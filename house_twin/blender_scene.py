"""Escena de Blender con los acabados aplicados. Corre DENTRO de Blender (con Bonsai), no con el Python del repo:

    blender --background --python house_twin/blender_scene.py -- <raíz> <ifc> <salida.blend> [--render DIR] [--glb ARCHIVO]

Abre el IFC con Bonsai, crea un material PBR por textura de `assets/textures/` y lo asigna según
`house_twin.finishes`: cada cara de muro según el espacio al que mira, cada piso según su espacio y cada
puerta o ventana según sus partes. Las coordenadas de textura se calculan en metros a partir de la
geometría, así que la escala de cada textura es la real (`size_m`). Se lanza con `python -m house_twin.cli scene`.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
ROOT = Path(ARGS[0])
sys.path.insert(0, str(ROOT))
from house_twin.finishes import Finishes, _inside, load_materials  # noqa: E402  (necesita la raíz en sys.path)
from house_twin.sunlight import sun_direction  # noqa: E402
from house_twin.variants import apply_variant, variant_materials  # noqa: E402

TEXTURES = ROOT / 'assets' / 'textures'
FACTS = ROOT / 'data' / 'facts' / 'existing.facts.json'
# Ventana corrediza de 2 hojas (foto 3): perfil perimetral y el traslape de las hojas al centro. Supuesto: no medido.
WINDOW_FRAME_M = 0.045
WINDOW_MEETING_M = 0.06
VIEW_PROBE_M = 0.3  # más que medio muro (0.17 m): el punto cae en el espacio de ese lado
LOW_WALL_MAX_M = 1.5  # un muro más bajo que esto no llega a la losa: su tope se ve y lleva acabado
CUT_COLOR = (0.18, 0.18, 0.18)       # cabeza de muro cortada: se ve porque el modelo aún no tiene techo
UNKNOWN_COLOR = (0.55, 0.52, 0.60)   # superficie sin acabado registrado: gris violáceo para que se note


def srgb_to_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _principled(nt, pbr):
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    if 'basecolor_srgb' in pbr:
        bsdf.inputs['Base Color'].default_value = (*[srgb_to_linear(c) for c in pbr['basecolor_srgb']], 1)
    bsdf.inputs['Roughness'].default_value = pbr.get('roughness', 0.5)
    bsdf.inputs['Metallic'].default_value = pbr.get('metallic', 0.0)
    if pbr.get('transmission'):
        bsdf.inputs['Transmission Weight'].default_value = pbr['transmission']
        bsdf.inputs['IOR'].default_value = pbr.get('ior', 1.5)
    if pbr.get('emission_srgb'):  # foco encendido
        bsdf.inputs['Emission Color'].default_value = (*[srgb_to_linear(c) for c in pbr['emission_srgb']], 1)
        bsdf.inputs['Emission Strength'].default_value = pbr.get('emission_strength', 1.0)
    return bsdf


def _new_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    return mat, nt


def plain_material(name, color):
    mat, nt = _new_material(name)
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = 0.9
    nt.links.new(bsdf.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return mat


def texture_material(name, spec, specs):
    """Material de una textura: constante (solo PBR) o con mapas; con `opacity`, mezcla su vidrio o deja ver a través."""
    mat, nt = _new_material(name)
    out = nt.nodes['Material Output']
    if spec.get('kind') == 'constant':
        nt.links.new(_principled(nt, spec['pbr']).outputs[0], out.inputs['Surface'])
        return mat
    folder = TEXTURES / name
    coords = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    if spec.get('tileable'):  # UV en metros → una repetición cada `size_m`
        scale = (1 / spec['size_m']['width'], 1 / spec['size_m']['height'])
        mapping.inputs['Scale'].default_value = (*scale, 1)
        # la textura empieza en una junta: se corre para que una junta caiga donde dice `grid.origin_m`
        origin = (spec.get('grid') or {}).get('origin_m') or {}
        mapping.inputs['Location'].default_value = (-(origin.get('x') or 0) * scale[0], -(origin.get('y') or 0) * scale[1], 0)
    nt.links.new(coords.outputs['UV'], mapping.inputs['Vector'])

    def image(file, colorspace):
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(folder / file), check_existing=True)
        node.image.colorspace_settings.name = colorspace
        node.extension = 'REPEAT' if spec.get('tileable') else 'EXTEND'
        nt.links.new(mapping.outputs[0], node.inputs['Vector'])
        return node

    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(image('basecolor.jpg', 'sRGB').outputs[0], bsdf.inputs['Base Color'])
    nt.links.new(image('roughness.png', 'Non-Color').outputs[0], bsdf.inputs['Roughness'])
    normal = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(image('normal.png', 'Non-Color').outputs[0], normal.inputs['Color'])
    nt.links.new(normal.outputs[0], bsdf.inputs['Normal'])
    if 'metallic' in spec['maps']:  # estampado de foil: metálico solo donde lo marca el mapa
        nt.links.new(image('metallic.png', 'Non-Color').outputs[0], bsdf.inputs['Metallic'])
    if spec.get('emissive'):  # pantalla encendida
        nt.links.new(image('basecolor.jpg', 'sRGB').outputs[0], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = spec['emissive']
    surface = bsdf
    if 'opacity' in spec['maps'] and spec.get('glass_material'):
        mix = nt.nodes.new('ShaderNodeMixShader')  # opacidad 0 = vidrio, 1 = hoja
        nt.links.new(image('opacity.png', 'Non-Color').outputs[0], mix.inputs['Fac'])
        nt.links.new(_principled(nt, specs[spec['glass_material']]['pbr']).outputs[0], mix.inputs[1])
        nt.links.new(bsdf.outputs[0], mix.inputs[2])
        surface = mix
    elif 'opacity' in spec['maps']:  # herrería: los huecos no tienen vidrio, se ve a través
        nt.links.new(image('opacity.png', 'Non-Color').outputs[0], bsdf.inputs['Alpha'])
    nt.links.new(surface.outputs[0], out.inputs['Surface'])
    return mat


def window_material(name, size, frame_spec, glass_spec, grid=None):
    """Ventana corrediza: marco perimetral y traslape central de aluminio; el resto, vidrio. UV en metros.

    Con `grid` (`cols` vidrios a lo ancho entre las dos hojas, `rows` a lo alto, perfil `bar_m`) lleva retícula.
    """
    mat, nt = _new_material(name)
    w, h = size
    uv = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(nt.nodes.new('ShaderNodeTexCoord').outputs['UV'], uv.inputs[0])

    def math_node(op, a, b=None):
        node = nt.nodes.new('ShaderNodeMath')
        node.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                node.inputs[i].default_value = v
            else:
                nt.links.new(v, node.inputs[i])
        return node.outputs[0]

    u, v = uv.outputs['X'], uv.outputs['Y']
    near_u = math_node('LESS_THAN', math_node('MINIMUM', u, math_node('SUBTRACT', w, u)), WINDOW_FRAME_M)
    near_v = math_node('LESS_THAN', math_node('MINIMUM', v, math_node('SUBTRACT', h, v)), WINDOW_FRAME_M)
    centre = math_node('LESS_THAN', math_node('ABSOLUTE', math_node('SUBTRACT', u, w / 2)), WINDOW_MEETING_M / 2)
    frame = math_node('MAXIMUM', math_node('MAXIMUM', near_u, near_v), centre)
    if grid:  # una línea cada `paso`: distancia al múltiplo más cercano menor que medio perfil
        for coord, step in ((u, w / grid['cols']), (v, h / grid['rows'])):
            offset = math_node('SUBTRACT', math_node('MODULO', math_node('ADD', coord, step / 2), step), step / 2)
            bars = math_node('LESS_THAN', math_node('ABSOLUTE', offset), grid['bar_m'] / 2)
            frame = math_node('MAXIMUM', frame, bars)
    mix = nt.nodes.new('ShaderNodeMixShader')  # 0 = vidrio, 1 = aluminio
    nt.links.new(frame, mix.inputs['Fac'])
    nt.links.new(_principled(nt, glass_spec['pbr']).outputs[0], mix.inputs[1])
    nt.links.new(_principled(nt, frame_spec['pbr']).outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return mat


def _face_axis(normal):
    """Dirección horizontal a lo largo de una cara vertical (U de la textura); la V es la altura."""
    return Vector((-normal.y, normal.x, 0)).normalized()


def _main_axis(obj, front=None):
    """Eje a lo ancho de una puerta o ventana: el de su cara vertical más grande.

    Con `front` (función de la normal), la U crece hacia la derecha visto desde el lado en que `front` es verdadera.
    """
    face = max((p for p in obj.data.polygons if abs(p.normal.z) < 0.3), key=lambda p: p.area)
    normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()
    if front is not None and not front(normal):
        normal = -normal
    return _face_axis(normal)


def write_uvs(obj, fit=None, front=None, axis=None):
    """UV en metros del mundo (muros y pisos). Con `fit`, relativas al objeto: 'unit' 0–1, 'metres' 0–ancho.

    `axis` fija hacia dónde crece la U (p. ej. desde el canto de la chapa hacia la bisagra).
    """
    mw, rot = obj.matrix_world, obj.matrix_world.to_3x3()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.loops.layers.uv.verify()
    if fit:
        axis = axis or _main_axis(obj, front)
        pts = [mw @ v.co for v in bm.verts]
        u0, u1 = min(p.dot(axis) for p in pts), max(p.dot(axis) for p in pts)
        z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
        su, sv = (1 / (u1 - u0), 1 / (z1 - z0)) if fit == 'unit' else (1, 1)
    for face in bm.faces:
        n = (rot @ face.normal).normalized()
        for loop in face.loops:
            p = mw @ loop.vert.co
            if fit:
                loop[layer].uv = ((p.dot(axis) - u0) * su, (p.z - z0) * sv)
            elif abs(n.z) > 0.7:
                loop[layer].uv = (p.x, p.y)
            else:
                loop[layer].uv = (p.dot(_face_axis(n)), p.z)
    bm.to_mesh(obj.data)
    bm.free()
    return (u1 - u0, z1 - z0) if fit else None


def write_plane_uvs(obj, right, up):
    """UV 0–1 de una imagen acostada: U a lo largo de `right` y V de `up`, ajustadas al objeto."""
    mw = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.loops.layers.uv.verify()
    pts = [mw @ v.co for v in bm.verts]
    u0, u1 = min(p.dot(right) for p in pts), max(p.dot(right) for p in pts)
    v0, v1 = min(p.dot(up) for p in pts), max(p.dot(up) for p in pts)
    for face in bm.faces:
        for loop in face.loops:
            p = mw @ loop.vert.co
            loop[layer].uv = ((p.dot(right) - u0) / (u1 - u0), (p.dot(up) - v0) / (v1 - v0))
    bm.to_mesh(obj.data)
    bm.free()


def split_at_boundaries(obj, boundaries, heights=()):
    """Corta la malla con planos verticales en cada X e Y de los vértices de los espacios, y con planos
    horizontales en las alturas donde cambia un acabado (lambrines)."""
    inv, to_local = obj.matrix_world.inverted(), obj.matrix_world.to_3x3().transposed()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for axis, values in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), (*boundaries, heights)):
        for v in values:
            point = Vector(axis) * v
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-4,
                                   plane_co=inv @ point, plane_no=(to_local @ Vector(axis)).normalized())
    bm.to_mesh(obj.data)
    bm.free()


class Scene:
    def __init__(self, finishes, specs, spaces, openings=None):
        self.finishes, self.specs = finishes, specs
        self.openings = openings or {}  # hechos de cada vano por id (retícula de las ventanas)
        # una cara de muro puede mirar a dos espacios (sale del baño y sigue en el pasillo): se corta en sus límites
        regions = [r for layers in finishes.wall_layers.values() for *_, r in layers if r]  # zonas de un acabado (azulejo del nicho)
        corners = [p for s in spaces for p in s['polygon']] + [p for r in regions for p in r]
        self.boundaries = (sorted({round(p[0], 3) for p in corners}), sorted({round(p[1], 3) for p in corners}))
        self.materials = {}
        self.unknown = set()

    def material(self, name):
        if name not in self.materials:
            if name == 'corte':
                self.materials[name] = plain_material('corte', CUT_COLOR)
            elif name == 'sin-dato':
                self.materials[name] = plain_material('sin-dato', UNKNOWN_COLOR)
            else:
                self.materials[name] = texture_material(name, self.specs[name], self.specs)
        return self.materials[name]

    def _set(self, obj, names):
        """Asigna un material por cara (`names[i]` para el polígono i)."""
        obj.data.materials.clear()
        slots = sorted(set(names))
        for n in slots:
            obj.data.materials.append(self.material(n))
        for poly, n in zip(obj.data.polygons, names):
            poly.material_index = slots.index(n)

    def wall(self, obj):
        split_at_boundaries(obj, self.boundaries, self.finishes.wall_split_heights())
        write_uvs(obj)
        rot, mw = obj.matrix_world.to_3x3(), obj.matrix_world
        names = []
        for poly in obj.data.polygons:
            n = (rot @ poly.normal).normalized()
            c = mw @ poly.center
            if n.z > 0.7 and c.z < LOW_WALL_MAX_M:  # tope de un muro bajo (sardinel): lleva el acabado de su espacio
                names.append(self.finishes.wall_finish(self.finishes.space_at((c.x, c.y)), c.z, (c.x, c.y)) or 'sin-dato')
                continue
            if abs(n.z) > 0.7:
                names.append('corte')
                continue
            finish, where = self.finishes.wall_face((c.x, c.y), Vector((n.x, n.y)).normalized(), c.z)
            names.append(finish or 'sin-dato')
            if finish is None and where not in (None, 'colindancia'):
                self.unknown.add(f'{obj.name}: cara hacia {where}')
        self._set(obj, names)

    def ceiling(self, obj, space_id):
        write_uvs(obj)
        self._set(obj, [self.finishes.ceiling(space_id) or 'sin-dato'] * len(obj.data.polygons))

    def floor(self, obj, space_id):
        write_uvs(obj)
        self._set(obj, [self.finishes.floor(space_id) or 'sin-dato'] * len(obj.data.polygons))

    def decal(self, obj):
        """Imagen sobre un muro (mural): la textura entera en la cara que mira al cuarto, sin espejar."""
        import bonsai.tool as tool
        import ifcopenshell.util.element as ue
        material = _ifc_material(obj)
        space = ue.get_psets(tool.Ifc.get_entity(obj)).get('HDT_Provenance', {}).get('Space')
        write_uvs(obj, fit='unit', front=self._front(obj, space))
        self._set(obj, [material if material in self.specs else 'sin-dato'] * len(obj.data.polygons))

    def shower_floor(self, obj, space_id):
        write_uvs(obj)
        self._set(obj, [self.finishes.shower_floor(space_id) or 'sin-dato'] * len(obj.data.polygons))

    def _latch_axis(self, oid, parts):
        """Si la textura de la hoja dice de qué lado tiene la chapa, la U arranca en el canto de la chapa del plano."""
        swing = self.openings.get(oid, {}).get('swing')
        side = self.specs.get(parts.get('leaf'), {}).get('latch_side')
        if not swing or side not in ('left', 'right'):
            return None
        (lx, ly), (hx, hy) = swing['latch_end'], swing['hinge_end']
        axis = Vector((hx - lx, hy - ly, 0)).normalized()
        return axis if side == 'left' else -axis

    def accessory(self, obj):
        """Herraje o mueble: el material que le da el IFC y sombreado suave salvo en los filos."""
        import bonsai.tool as tool
        import ifcopenshell.util.element as ue
        material = _ifc_material(obj)
        image = ue.get_psets(tool.Ifc.get_entity(obj)).get('HDT_Image')
        if image and 'UpX' in image:  # imagen acostada (una prenda extendida): U a la derecha y V hacia arriba de la foto
            write_plane_uvs(obj, Vector((image['RightX'], image['RightY'], 0)), Vector((image['UpX'], image['UpY'], 0)))
        elif image:  # pantalla: la foto entera en su cara, con la U hacia la derecha de quien la mira
            write_uvs(obj, fit='unit', axis=Vector((-image['FacingY'], image['FacingX'], 0)))
        else:
            write_uvs(obj)  # melamina: veta en metros del mundo, como los muros
        self._set(obj, [material if material in self.specs else 'sin-dato'] * len(obj.data.polygons))
        if material and self.specs.get(material, {}).get('pbr', {}).get('emission_srgb'):
            obj.visible_shadow = False  # el foco envuelve a su luz: si proyectara sombra, la apagaría
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(35))

    def _front(self, obj, space_id):
        """¿La normal mira hacia `space_id`? Se prueba un punto a VIEW_PROBE_M del centro del vano."""
        if space_id is None:
            return None
        c = obj.matrix_world @ (sum((v.co for v in obj.data.vertices), Vector()) / len(obj.data.vertices))
        return lambda n: self.finishes.space_at((c.x + n.x * VIEW_PROBE_M, c.y + n.y * VIEW_PROBE_M)) == space_id

    def opening(self, obj, oid):
        parts = self.finishes.opening(oid)
        if 'frame' in parts:  # ventana: marco procedural con las medidas del vano
            size = write_uvs(obj, fit='metres')
            obj['hdt_size'] = list(size)  # el visor web dibuja el marco con estas medidas
            grid = self.openings.get(oid, {}).get('grid')
            if grid:
                obj['hdt_grid'] = [grid['cols'], grid['rows'], grid['bar_m']]
            mat = window_material(f'ventana-{oid}', size, self.specs[parts['frame']], self.specs[parts['glass']], grid)
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            return
        if self.specs.get(parts.get('leaf'), {}).get('tileable'):  # hoja de un material continuo (paneles de un portón
            write_uvs(obj)                                            # seccional): en metros, como sus demás paneles
        else:
            write_uvs(obj, fit='unit', front=self._front(obj, self.finishes.viewed_from(oid)), axis=self._latch_axis(oid, parts))
        if 'leaf' not in parts:
            self.unknown.add(f'{obj.name}: sin textura de hoja')
        self._set(obj, [parts.get('leaf', 'sin-dato')] * len(obj.data.polygons))


LUMENS_PER_WATT = 683  # Blender: 1 W de luz equivale a 683 lm
LIGHT_REACH_M = 10.0


def add_point_light(fixture):
    """Luz puntual en el centro del foco, con el flujo y el color de su luminaria (Pset HDT_Light del IFC)."""
    import bonsai.tool as tool
    import ifcopenshell.util.element as ue
    data = ue.get_pset(tool.Ifc.get_entity(fixture), 'HDT_Light') or {}
    if not data:
        return None
    corners = [fixture.matrix_world @ Vector(c) for c in fixture.bound_box]
    centre = Vector((sum(c.x for c in corners) / 8, sum(c.y for c in corners) / 8, data['CentreZ']))
    light = bpy.data.lights.new(f"luz-{fixture.name.split('/')[-1]}", 'POINT')
    light.energy = data['Lumens'] / LUMENS_PER_WATT
    light.shadow_soft_size = 0.03
    # EEVEE corta cada luz donde su intensidad cae bajo un umbral: con el flujo real de un foco, a pocos cm
    light.use_custom_distance = True
    light.cutoff_distance = LIGHT_REACH_M
    light.color = _kelvin_rgb(data['ColorTemperature'])
    obj = bpy.data.objects.new(light.name, light)
    obj.location = centre
    collection = bpy.data.collections.get('Luces') or bpy.data.collections.new('Luces')
    if collection.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    return obj


def _kelvin_rgb(kelvin):
    """Color aproximado de una temperatura de color (Tanner Helland), en lineal 0–1."""
    t = kelvin / 100
    r = 255 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    return tuple(srgb_to_linear(max(0, min(255, c))) for c in (r, g, b))


def _ifc_material(obj):
    """Nombre del IfcMaterial del objeto (el de su textura en `assets/textures/`)."""
    import bonsai.tool as tool
    import ifcopenshell.util.element as ue
    entity = tool.Ifc.get_entity(obj)
    material = ue.get_material(entity) if entity else None
    return material.Name if material else None


def _ifc_name(obj):
    ifc_class, _, name = obj.name.partition('/')
    return ifc_class, name


def apply_finishes(ifc_path, facts, variant=None):
    for obj in list(bpy.data.objects):  # escena de inicio: cubo, cámara y luz
        bpy.data.objects.remove(obj)
    bpy.ops.bim.load_project(filepath=str(ifc_path))
    specs = load_materials(TEXTURES)
    finishes = Finishes(facts, variant_materials(specs, variant) if variant else specs)
    if variant:  # una remodelación: los acabados de sus vanos nuevos
        finishes = apply_variant(finishes, variant, specs)
    scene = Scene(finishes, specs, facts['spaces'], {o['id']: o for o in facts['openings']})
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        ifc_class, name = _ifc_name(obj)
        if obj.data.users > 1:
            obj.data = obj.data.copy()  # cada muro necesita sus propias UV y materiales por cara
        if ifc_class == 'IfcWall':
            scene.wall(obj)
        elif ifc_class == 'IfcCovering' and name.endswith('-techo'):
            scene.ceiling(obj, name.removesuffix('-techo'))
        elif ifc_class == 'IfcCovering' and name.startswith('cocina-'):
            scene.decal(obj)
        elif ifc_class == 'IfcCovering' and name.endswith('-regadera'):
            scene.shower_floor(obj, name.removesuffix('-regadera'))
        elif ifc_class == 'IfcCovering':
            scene.floor(obj, name.removesuffix('-piso'))
        elif ifc_class == 'IfcSlab':
            scene._set(obj, ['sin-dato'] * len(obj.data.polygons))  # acabado de la azotea: sin dato
        elif ifc_class == 'IfcLightFixture':
            scene.accessory(obj)
            add_point_light(obj)
        elif ifc_class in ('IfcDoor', 'IfcWindow'):
            scene.opening(obj, name)
        elif ifc_class in ('IfcDiscreteAccessory', 'IfcFurniture', 'IfcOutlet', 'IfcSwitchingDevice', 'IfcValve',
                           'IfcSanitaryTerminal', 'IfcElectricAppliance', 'IfcAudioVisualAppliance',
                           'IfcUnitaryEquipment', 'IfcFlowStorageDevice', 'IfcPlate', 'IfcMember', 'IfcColumn', 'IfcBeam',
                           'IfcRoof', 'IfcBuildingElementProxy'):
            scene.accessory(obj)
        elif ifc_class in ('IfcSpace', 'IfcOpeningElement'):
            obj.hide_render = obj.hide_viewport = True
    return scene


def light_scene():
    sc = bpy.context.scene
    sun = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN'))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(0.53)
    sun.rotation_euler = (-Vector(sun_direction())).to_track_quat('-Z', 'Y').to_euler()
    sc.collection.objects.link(sun)
    world = bpy.data.worlds.new('cielo')
    world.use_nodes = True
    # cielo ≈ 1/4 de la luz del sol, como en un día despejado; más fuerte tiñe todo de azul
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.68, 0.9, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3
    sc.world = world
    sc.view_settings.view_transform = 'AgX'


CAMERAS = {  # nombre: (posición, a dónde mira, lente mm)
    'aerea': ((-5.5, -7.0, 15.0), (5.0, 9.0, 0.0), 30),
    'fachada': ((5.0, -7.5, 1.6), (5.0, 2.0, 1.6), 24),
    'sala-cocina': ((7.8, 4.2, 1.6), (2.0, 8.8, 1.2), 18),
    'pasillo': ((5.0, 9.4, 1.6), (5.0, 13.5, 1.1), 16),
    'bano': ((4.05, 10.4, 1.6), (3.0, 12.4, 1.0), 12),
}


EYE_HEIGHT_M = 1.6
ROOM_CORNER_INSET_M = 0.35
ROOM_LENS_MM = 14  # gran angular, como las fotos del celular


def _camera(name, location, target, lens, collection):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    collection.objects.link(cam)
    return cam


def room_viewpoint(polygon):
    """Desde una esquina hacia la esquina más lejana: así se ve casi todo el cuarto de un vistazo."""
    cx, cy = sum(p[0] for p in polygon) / len(polygon), sum(p[1] for p in polygon) / len(polygon)
    best = None
    for x, y in polygon:
        d = math.hypot(cx - x, cy - y) or 1
        eye = (x + (cx - x) / d * ROOM_CORNER_INSET_M, y + (cy - y) / d * ROOM_CORNER_INSET_M)
        if not _inside(eye, polygon):
            continue  # esquina entrante de un cuarto en L
        far = max(polygon, key=lambda q: math.hypot(q[0] - x, q[1] - y))
        reach = math.hypot(far[0] - x, far[1] - y)
        if best is None or reach > best[0]:
            best = (reach, eye, far)
    return best[1], best[2]


def add_cameras(spaces):
    fixed = {name: _camera(f'camara-{name}', location, target, lens, bpy.context.scene.collection)
             for name, (location, target, lens) in CAMERAS.items()}
    tour = bpy.data.collections.new('Recorrido')  # una cámara por espacio, a la altura de los ojos
    bpy.context.scene.collection.children.link(tour)
    cameras = [fixed['aerea']]
    for space in spaces:
        eye, far = room_viewpoint(space['polygon'])
        cameras.append(_camera(f"{space['id']} {space['name'] or 'sin rótulo'}", (*eye, EYE_HEIGHT_M), (*far, 1.0),
                               ROOM_LENS_MM, tour))
    bind_to_frames(cameras)


def bind_to_frames(cameras):
    """Un fotograma por cámara (marcador ligado): con ← y → se pasa de un cuarto al siguiente."""
    sc = bpy.context.scene
    for frame, cam in enumerate(cameras, start=1):
        marker = sc.timeline_markers.new(cam.name, frame=frame)
        marker.camera = cam
    sc.frame_start, sc.frame_end = 1, len(cameras)
    sc.frame_set(1)
    sc.camera = cameras[0]


def render_all(folder: Path, samples=64):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'  # la Iris Xe no sirve para Cycles
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 900
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 88
    folder.mkdir(parents=True, exist_ok=True)
    for marker in sc.timeline_markers:  # el .blend ya se guardó: aquí los marcadores cambiarían la cámara del render
        marker.camera = None
    for name in CAMERAS:
        sc.camera = bpy.data.objects[f'camara-{name}']
        sc.render.filepath = str(folder / f'{name}.jpg')
        bpy.ops.render.render(write_still=True)


def show_materials():
    """La vista 3D abre en modo Material Preview: en modo sólido (el de fábrica) no se ven las texturas."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'


def leaf_copies(obj, leaves):
    """Una copia del objeto por hoja (portón de 2 hojas): cada una conserva su mitad, cortada donde se juntan las
    hojas, con la cara del corte tapada. Las UV se interpolan en el corte, así la textura sigue entera."""
    copies = []
    for i, leaf in enumerate(leaves):
        (hx, hy), (lx, ly) = leaf['hinge_end'], leaf['latch_end']
        to_hinge = Vector((hx - lx, hy - ly, 0)).normalized()
        copy = obj.copy()
        copy.data = obj.data.copy()
        bpy.context.scene.collection.objects.link(copy)
        inv, to_local = copy.matrix_world.inverted(), copy.matrix_world.to_3x3().transposed()
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5, clear_inner=True,
                               plane_co=inv @ Vector((lx, ly, 0)), plane_no=(to_local @ to_hinge).normalized())
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        bm.to_mesh(copy.data)
        bm.free()
        copy['hdt_leaf'] = i
        copies.append(copy)
    return copies


def export_glb(path: Path, openings: dict | None = None):
    """Geometría, UV y nombres de material para el recorrido web; las imágenes las pone el visor (versión ligera).

    Una puerta de varias hojas sale partida en una malla por hoja (con `hdt_leaf`), para que el visor las abra
    por separado; las copias se borran después de exportar, así la escena de Blender no cambia."""
    bpy.ops.object.select_all(action='DESELECT')
    temporary = []
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH' and not obj.hide_render:
            kind, name = _ifc_name(obj)
            leaves = (openings or {}).get(name, {}).get('leaves') or []
            parts = leaf_copies(obj, leaves) if kind == 'IfcDoor' and len(leaves) > 1 else [obj]
            if parts[0] is not obj:
                temporary += parts
            for part in parts:
                part['hdt_kind'], part['hdt_id'] = kind, name  # el glTF limpia los nombres: el id viaja en extras
                part.select_set(True)
    for cam in bpy.data.collections['Recorrido'].objects:
        cam['hdt_kind'], cam['hdt_id'] = 'camera', cam.name
        cam.select_set(True)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_extras=True,
                              export_cameras=True, export_lights=False, export_materials='EXPORT',
                              export_image_format='NONE', export_apply=False)
    for obj in temporary:
        bpy.data.objects.remove(obj)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('root')
    parser.add_argument('ifc', type=Path)
    parser.add_argument('blend', type=Path)
    parser.add_argument('--render', type=Path)
    parser.add_argument('--glb', type=Path)
    parser.add_argument('--facts', type=Path, default=FACTS, help='hechos del IFC (los propuestos, en una variante)')
    parser.add_argument('--variant', type=Path, help='variante cuyos acabados van encima (una remodelación)')
    args = parser.parse_args(ARGS)
    ifc_path, blend_path = args.ifc, args.blend
    facts = json.loads(args.facts.read_text())
    scene = apply_finishes(ifc_path, facts, json.loads(args.variant.read_text()) if args.variant else None)
    light_scene()
    add_cameras(facts['spaces'])
    show_materials()
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), relative_remap=True)
    print(f'materiales: {sorted(scene.materials)}')
    for line in sorted(scene.unknown):
        print(f'sin acabado: {line}')
    if args.glb:
        export_glb(args.glb, {o['id']: o for o in facts['openings']})
    if args.render:
        render_all(args.render)


main()
