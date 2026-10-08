"""Escena de Blender con los acabados aplicados. Corre DENTRO de Blender (con Bonsai), no con el Python del repo:

    blender --background --python house_twin/blender_scene.py -- <raíz> <ifc> <salida.blend> [<carpeta de renders>]

Abre el IFC con Bonsai, crea un material PBR por textura de `assets/textures/` y lo asigna según
`house_twin.finishes`: cada cara de muro según el espacio al que mira, cada piso según su espacio y cada
puerta o ventana según sus partes. Las coordenadas de textura se calculan en metros a partir de la
geometría, así que la escala de cada textura es la real (`size_m`). Se lanza con `python -m house_twin.cli scene`.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
ROOT = Path(ARGS[0])
sys.path.insert(0, str(ROOT))
from house_twin.finishes import Finishes, load_materials  # noqa: E402  (necesita la raíz en sys.path)

TEXTURES = ROOT / 'assets' / 'textures'
FACTS = ROOT / 'data' / 'facts' / 'existing.facts.json'
# Ventana corrediza de 2 hojas (foto 3): perfil perimetral y el traslape de las hojas al centro. Supuesto: no medido.
WINDOW_FRAME_M = 0.045
WINDOW_MEETING_M = 0.06
CUT_COLOR = (0.18, 0.18, 0.18)       # cabeza de muro cortada: se ve porque el modelo aún no tiene techo
UNKNOWN_COLOR = (0.55, 0.52, 0.60)   # superficie sin acabado registrado: gris violáceo para que se note
# Orientación medida por el dueño con brújula: la fachada mira a 27° (el fondo, +Y, a 207°). Sin saber si es
# norte magnético o verdadero (en Saltillo difieren ≈ 4°), basta para la vista previa.
BACK_AZIMUTH_DEG = 207
SUN_AZIMUTH_DEG, SUN_ELEVATION_DEG = 150, 50  # media mañana de octubre en Saltillo, aproximado


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
    """Material de una textura: constante (solo PBR) o con mapas; con `opacity`, mezcla su vidrio."""
    mat, nt = _new_material(name)
    out = nt.nodes['Material Output']
    if spec.get('kind') == 'constant':
        nt.links.new(_principled(nt, spec['pbr']).outputs[0], out.inputs['Surface'])
        return mat
    folder = TEXTURES / name
    coords = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    if spec.get('tileable'):  # UV en metros → una repetición cada `size_m`
        mapping.inputs['Scale'].default_value = (1 / spec['size_m']['width'], 1 / spec['size_m']['height'], 1)
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
    surface = bsdf
    if 'opacity' in spec['maps'] and spec.get('glass_material'):
        mix = nt.nodes.new('ShaderNodeMixShader')  # opacidad 0 = vidrio, 1 = hoja
        nt.links.new(image('opacity.png', 'Non-Color').outputs[0], mix.inputs['Fac'])
        nt.links.new(_principled(nt, specs[spec['glass_material']]['pbr']).outputs[0], mix.inputs[1])
        nt.links.new(bsdf.outputs[0], mix.inputs[2])
        surface = mix
    nt.links.new(surface.outputs[0], out.inputs['Surface'])
    return mat


def window_material(name, size, frame_spec, glass_spec):
    """Ventana corrediza: marco perimetral y traslape central de aluminio; el resto, vidrio. UV en metros."""
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
    mix = nt.nodes.new('ShaderNodeMixShader')  # 0 = vidrio, 1 = aluminio
    nt.links.new(frame, mix.inputs['Fac'])
    nt.links.new(_principled(nt, glass_spec['pbr']).outputs[0], mix.inputs[1])
    nt.links.new(_principled(nt, frame_spec['pbr']).outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return mat


def _face_axis(normal):
    """Dirección horizontal a lo largo de una cara vertical (U de la textura); la V es la altura."""
    return Vector((-normal.y, normal.x, 0)).normalized()


def _main_axis(obj):
    """Eje a lo ancho de una puerta o ventana: el de su cara vertical más grande."""
    face = max((p for p in obj.data.polygons if abs(p.normal.z) < 0.3), key=lambda p: p.area)
    return _face_axis(obj.matrix_world.to_3x3() @ face.normal)


def write_uvs(obj, fit=None):
    """UV en metros del mundo (muros y pisos). Con `fit`, relativas al objeto: 'unit' 0–1, 'metres' 0–ancho."""
    mw, rot = obj.matrix_world, obj.matrix_world.to_3x3()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.loops.layers.uv.verify()
    if fit:
        axis = _main_axis(obj)
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


def split_at_boundaries(obj, boundaries):
    """Corta la malla con planos verticales en cada X e Y de los vértices de los espacios."""
    inv, to_local = obj.matrix_world.inverted(), obj.matrix_world.to_3x3().transposed()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for axis, values in zip(((1, 0, 0), (0, 1, 0)), boundaries):
        for v in values:
            point = Vector(axis) * v
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-4,
                                   plane_co=inv @ point, plane_no=(to_local @ Vector(axis)).normalized())
    bm.to_mesh(obj.data)
    bm.free()


class Scene:
    def __init__(self, finishes, specs, spaces):
        self.finishes, self.specs = finishes, specs
        # una cara de muro puede mirar a dos espacios (sale del baño y sigue en el pasillo): se corta en sus límites
        self.boundaries = (sorted({round(p[0], 3) for s in spaces for p in s['polygon']}),
                           sorted({round(p[1], 3) for s in spaces for p in s['polygon']}))
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
        split_at_boundaries(obj, self.boundaries)
        write_uvs(obj)
        rot, mw = obj.matrix_world.to_3x3(), obj.matrix_world
        names = []
        for poly in obj.data.polygons:
            n = (rot @ poly.normal).normalized()
            if abs(n.z) > 0.7:
                names.append('corte')
                continue
            c = mw @ poly.center
            finish, where = self.finishes.wall_face((c.x, c.y), Vector((n.x, n.y)).normalized())
            names.append(finish or 'sin-dato')
            if finish is None and where not in (None, 'colindancia'):
                self.unknown.add(f'{obj.name}: cara hacia {where}')
        self._set(obj, names)

    def floor(self, obj, space_id):
        write_uvs(obj)
        self._set(obj, [self.finishes.floor(space_id) or 'sin-dato'] * len(obj.data.polygons))

    def opening(self, obj, oid):
        parts = self.finishes.opening(oid)
        if 'frame' in parts:  # ventana: marco procedural con las medidas del vano
            size = write_uvs(obj, fit='metres')
            mat = window_material(f'ventana-{oid}', size, self.specs[parts['frame']], self.specs[parts['glass']])
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            return
        write_uvs(obj, fit='unit')
        if 'leaf' not in parts:
            self.unknown.add(f'{obj.name}: sin textura de hoja')
        self._set(obj, [parts.get('leaf', 'sin-dato')] * len(obj.data.polygons))


def _ifc_name(obj):
    ifc_class, _, name = obj.name.partition('/')
    return ifc_class, name


def apply_finishes(ifc_path):
    for obj in list(bpy.data.objects):  # escena de inicio: cubo, cámara y luz
        bpy.data.objects.remove(obj)
    bpy.ops.bim.load_project(filepath=str(ifc_path))
    import json
    facts = json.loads(FACTS.read_text())
    specs = load_materials(TEXTURES)
    scene = Scene(Finishes(facts, specs), specs, facts['spaces'])
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        ifc_class, name = _ifc_name(obj)
        if obj.data.users > 1:
            obj.data = obj.data.copy()  # cada muro necesita sus propias UV y materiales por cara
        if ifc_class == 'IfcWall':
            scene.wall(obj)
        elif ifc_class == 'IfcCovering':
            scene.floor(obj, name.removesuffix('-piso'))
        elif ifc_class in ('IfcDoor', 'IfcWindow'):
            scene.opening(obj, name)
        elif ifc_class in ('IfcSpace', 'IfcOpeningElement'):
            obj.hide_render = obj.hide_viewport = True
    return scene


def _direction(azimuth_deg, elevation_deg=0.0):
    """Rumbo de brújula → vector de la escena (+Y apunta a BACK_AZIMUTH_DEG, +X a 90° a su derecha)."""
    a, e = math.radians(azimuth_deg - BACK_AZIMUTH_DEG), math.radians(elevation_deg)
    return Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))


def light_scene():
    sc = bpy.context.scene
    sun = bpy.data.objects.new('sol', bpy.data.lights.new('sol', 'SUN'))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(0.53)
    sun.rotation_euler = (-_direction(SUN_AZIMUTH_DEG, SUN_ELEVATION_DEG)).to_track_quat('-Z', 'Y').to_euler()
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


def add_cameras():
    for name, (location, target, lens) in CAMERAS.items():
        cam = bpy.data.objects.new(f'camara-{name}', bpy.data.cameras.new(name))
        cam.location = location
        cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        bpy.context.scene.collection.objects.link(cam)


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
    for name in CAMERAS:
        sc.camera = bpy.data.objects[f'camara-{name}']
        sc.render.filepath = str(folder / f'{name}.jpg')
        bpy.ops.render.render(write_still=True)


def main():
    ifc_path, blend_path = Path(ARGS[1]), Path(ARGS[2])
    scene = apply_finishes(ifc_path)
    light_scene()
    add_cameras()
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), relative_remap=True)
    print(f'materiales: {sorted(scene.materials)}')
    for line in sorted(scene.unknown):
        print(f'sin acabado: {line}')
    if len(ARGS) > 3:
        render_all(Path(ARGS[3]))


main()
