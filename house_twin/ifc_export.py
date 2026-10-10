"""Exporta `house.facts.json` a IFC4 con IfcOpenShell: muros, vanos con puerta/ventana, espacios y acabados de piso.

El IFC necesita alturas que el plano no da. Se usan los supuestos de ASSUMED_DEFAULTS,
y cada elemento lleva en el Pset `HDT_Provenance` qué dato es hecho y cuál es supuesto,
para que nadie confunda un supuesto con una medida.
"""
import math
import uuid

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import ifcopenshell.guid
from ifcopenshell.util.shape_builder import ShapeBuilder
from shapely.geometry import Polygon
from shapely.ops import unary_union

from house_twin.electrical import device_height, device_mesh
from house_twin.finishes import Finishes
from house_twin.closet_interior import interior_parts, leaf_parts
from house_twin.furniture import closet_meshes
from house_twin.hardware import for_leaf, knob_mesh, placements
from house_twin.kitchen import kitchen_parts
from house_twin.living import living_parts
from house_twin.bedroom import bedroom_parts
from house_twin.laundry import laundry_parts
from house_twin.lighting import luminaire_meshes
from house_twin.plumbing import (faucet_mesh, lever_mesh, material_of, sanitary_mesh, shower_mesh, spec_for,
                                 valve_meshes)

ASSUMED_DEFAULTS = {'storey_height': 2.40, 'door_height': 2.10, 'window_sill': 0.90, 'window_height': 1.20,
                    'slab_thickness': 0.10}  # losa: U02 sin respuesta; 10 cm es común en losa maciza de casa
CEILING_FINISH_M = 0.01  # capa de tirol bajo la losa
PANEL_THICKNESS = 0.05
FLOOR_FINISH_THICKNESS = 0.01  # la loseta o el firme: su cara de arriba es el nivel 0 de piso terminado
PART_NAMES = {'leaf': 'Hoja', 'frame': 'Marco', 'glass': 'Vidrio'}
OPENING_OVERCUT = 0.01  # el vano sobresale del muro para que el corte booleano sea limpio
GUID_NAMESPACE = uuid.UUID('6f2b8c1e-3d4a-5b6c-8d7e-9f0a1b2c3d4e')  # fijo: cambiarlo cambia todos los GlobalId


class _IfcContext:
    def __init__(self, name: str):
        self.model = ifcopenshell.api.project.create_file(version='IFC4')
        self.project = self._create('IfcProject', name)
        # Sin argumentos IfcOpenShell asigna milímetros; los hechos están en metros.
        ifcopenshell.api.unit.assign_unit(self.model, units=[
            ifcopenshell.api.unit.add_si_unit(self.model, unit_type=kind)
            for kind in ('LENGTHUNIT', 'AREAUNIT', 'VOLUMEUNIT')])
        model_ctx = ifcopenshell.api.context.add_context(self.model, context_type='Model')
        self.body = ifcopenshell.api.context.add_context(self.model, context_type='Model', context_identifier='Body',
                                                         target_view='MODEL_VIEW', parent=model_ctx)
        self.builder = ShapeBuilder(self.model)

    def _create(self, ifc_class, name=None, predefined_type=None):
        return ifcopenshell.api.root.create_entity(self.model, ifc_class=ifc_class, name=name, predefined_type=predefined_type)

    def element(self, ifc_class, name, predefined_type=None):
        entity = self._create(ifc_class, name, predefined_type)
        ifcopenshell.api.geometry.edit_object_placement(self.model, product=entity)
        return entity

    def extrude_polygon(self, product, points, height, base_z=0.0):
        curve = self.builder.polyline([tuple(p) for p in points], closed=True)
        solid = self.builder.extrude(self.builder.profile(curve), magnitude=height, position=(0.0, 0.0, base_z))
        rep = self.builder.get_representation(self.body, [solid])
        ifcopenshell.api.geometry.assign_representation(self.model, product=product, representation=rep)

    def material(self, name):
        """Un IfcMaterial por textura, compartido: su nombre es el de `assets/textures/<nombre>/`."""
        found = next((m for m in self.model.by_type('IfcMaterial') if m.Name == name), None)
        return found or ifcopenshell.api.material.add_material(self.model, name=name, category='acabado')

    def assign_parts(self, product, parts: dict[str, str]):
        if len(parts) == 1:
            ifcopenshell.api.material.assign_material(self.model, products=[product], material=self.material(*parts.values()))
            return
        constituents = ifcopenshell.api.material.add_material_set(self.model, name=product.Name, set_type='IfcMaterialConstituentSet')
        for part, name in sorted(parts.items()):
            ifcopenshell.api.material.add_constituent(self.model, constituent_set=constituents, material=self.material(name),
                                                      name=PART_NAMES[part])
        ifcopenshell.api.material.assign_material(self.model, products=[product], type='IfcMaterialConstituentSet',
                                                  material=constituents)

    def pset(self, product, name, properties):
        known = {k: v for k, v in properties.items() if v is not None}
        if not known:
            return  # IFC no admite property sets vacíos
        pset = ifcopenshell.api.pset.add_pset(self.model, product=product, name=name)
        ifcopenshell.api.pset.edit_pset(self.model, pset=pset, properties=known)


def _value_or_assumed(fact: dict, default_key: str):
    value = (fact or {}).get('value')
    return (value, False) if value is not None else (ASSUMED_DEFAULTS[default_key], True)


def _panel(footprint, thickness):
    """Rectángulo delgado centrado en el vano, a lo largo del muro (hoja de puerta o vidrio)."""
    p0, p1, _, p3 = footprint
    a = (p1[0]-p0[0], p1[1]-p0[1])
    b = (p3[0]-p0[0], p3[1]-p0[1])
    long_side, short_side = (a, b) if math.hypot(*a) >= math.hypot(*b) else (b, a)
    centre = (p0[0] + (a[0]+b[0])/2, p0[1] + (a[1]+b[1])/2)
    ls, ss = math.hypot(*long_side), math.hypot(*short_side)
    u = (long_side[0]/ls, long_side[1]/ls)
    v = (short_side[0]/ss, short_side[1]/ss)
    h, t = ls / 2, thickness / 2
    return [(centre[0] + su*h*u[0] + sv*t*v[0], centre[1] + su*h*u[1] + sv*t*v[1]) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _grown(footprint, margin):
    """El rectángulo del vano, `margin` más grande por lado sobre sus propios ejes.

    Crecer sobre X e Y del mundo solo sirve a escuadra: en un muro diagonal estira el vano a lo largo y no lo hace
    salir del espesor, sus caras coinciden con las del muro y el corte booleano falla a medias.
    """
    p0, p1, _, p3 = footprint
    a = (p1[0]-p0[0], p1[1]-p0[1])
    b = (p3[0]-p0[0], p3[1]-p0[1])
    la, lb = math.hypot(*a), math.hypot(*b)
    ua, ub = (a[0]/la, a[1]/la), (b[0]/lb, b[1]/lb)
    centre = (p0[0] + (a[0]+b[0])/2, p0[1] + (a[1]+b[1])/2)
    ha, hb = la/2 + margin, lb/2 + margin
    return [(centre[0] + sa*ha*ua[0] + sb*hb*ub[0], centre[1] + sa*ha*ua[1] + sb*hb*ub[1])
            for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _add_walls(ctx: _IfcContext, facts, storey, height):
    walls = {}
    for w in facts['walls']:
        wall = ctx.element('IfcWall', w['id'], 'SOLIDWALL')
        known = w['height']['value']  # p. ej. el sardinel de la regadera; los demás llegan a la losa (supuesto)
        ctx.extrude_polygon(wall, w['footprint'], known if known is not None else height)
        ctx.pset(wall, 'Pset_WallCommon', {'IsExternal': w['faces_exterior']})
        ctx.pset(wall, 'HDT_Provenance', {'FactId': w['id'], 'Source': w['source'], 'Thickness': w['thickness'],
                                          'OnPropertyLine': w['on_property_line'], 'HeightAssumed': known is None,
                                          'HeightSource': w['height']['source'] if known is not None else None,
                                          'Role': w.get('role'),
                                          'LoadBearingKnown': w['load_bearing']['value'] is not None})
        walls[w['id']] = wall
    ifcopenshell.api.spatial.assign_container(ctx.model, products=list(walls.values()), relating_structure=storey)
    return walls


def _add_declared_opening(ctx: _IfcContext, o, walls):
    """Vano que el dueño declaró pero el plano no dibuja: queda como dato del muro, sin geometría inventada."""
    host = walls.get(o['host_wall'])
    if host:
        ctx.pset(host, 'HDT_DeclaredOpenings', {o['id']: f"{o['kind']} sin medidas; conecta {','.join(o['connects'])}"})


def _add_opening(ctx: _IfcContext, o, walls, storey, finishes: Finishes | None, hardware=None, spaces=()):
    if o['footprint'] is None:
        _add_declared_opening(ctx, o, walls)
        return
    is_door = o['kind'] == 'door'
    sill, sill_assumed = (0.0, False) if is_door else _value_or_assumed(o['sill_height'], 'window_sill')
    height, height_assumed = _value_or_assumed(o['height'], 'door_height' if is_door else 'window_height')
    filler = ctx.element('IfcDoor' if is_door else 'IfcWindow', o['id'], 'DOOR' if is_door else 'WINDOW')
    ctx.extrude_polygon(filler, _panel(o['footprint'], PANEL_THICKNESS), height, sill)
    filler.OverallWidth, filler.OverallHeight = o['width'], height
    host = walls.get(o['host_wall'])
    if host:  # sin muro (puerta de herrería entre dos muros) no hay hueco que cortar: la puerta va sola
        void = ctx.element('IfcOpeningElement', f"{o['id']}-vano", 'OPENING')
        ctx.extrude_polygon(void, _grown(o['footprint'], OPENING_OVERCUT), height, sill)
        ifcopenshell.api.feature.add_feature(ctx.model, feature=void, element=host)
        ifcopenshell.api.feature.add_filling(ctx.model, opening=void, element=filler)
    ifcopenshell.api.spatial.assign_container(ctx.model, products=[filler], relating_structure=storey)
    ctx.pset(filler, 'HDT_Provenance', {'FactId': o['id'], 'Width': o['width'], 'SillHeight': sill, 'SillAssumed': sill_assumed,
                                        'Height': height, 'HeightAssumed': height_assumed, 'HostWall': o['host_wall'],
                                        'Connects': ','.join(o['connects'])})
    parts = finishes.opening(o['id']) if finishes else {}
    if parts:
        ctx.assign_parts(filler, parts)
    if is_door and o.get('swing'):
        for spec in for_leaf(hardware or [], parts.get('leaf')):
            _add_hardware(ctx, filler, o, spec, height, spaces)


def _add_hardware(ctx: _IfcContext, door, o, spec, height, spaces):
    """Herraje de la puerta (chapa): IfcDiscreteAccessory con malla torneada, parte de la puerta (no del nivel)."""
    places = placements(spec, o, height, PANEL_THICKNESS, spaces)
    points, faces = knob_mesh(spec, places)
    item = ctx.builder.polygonal_face_set(points, faces)
    accessory = ctx.element('IfcDiscreteAccessory', f"{o['id']}-{spec['name']}")
    accessory.ObjectType = spec['name']
    ifcopenshell.api.geometry.assign_representation(ctx.model, product=accessory,
                                                    representation=ctx.builder.get_representation(ctx.body, [item]))
    ifcopenshell.api.aggregate.assign_object(ctx.model, products=[accessory], relating_object=door)
    ifcopenshell.api.material.assign_material(ctx.model, products=[accessory], material=ctx.material(spec['material']))
    ctx.pset(accessory, 'HDT_Provenance', {'FactId': o['id'], 'Source': spec['applies_to']['source'],
                                           'Position': spec['position']['source'], 'Swing': o['swing']['source'],
                                           'TurnButtonSide': next((o['swing']['opens_into'] for p in places if p['button']), '')})


def _add_furniture(ctx: _IfcContext, facts, storey, height, furniture):
    """Closets: el plano dice dónde (`fixtures`) y su especificación cómo es el frente. Sin especificación, nada:
    un closet sin datos de su frente (o sin puertas) no se inventa."""
    specs = {f['applies_to']['space']: f for f in furniture}
    for fixture in facts.get('fixtures', []):
        spec = specs.get(fixture['space'])
        if fixture['kind'] != 'closet' or spec is None:
            continue
        (points, faces), (hpoints, hfaces) = closet_meshes(fixture, spec, height)
        closet = ctx.element('IfcFurniture', f"{fixture['id']}-closet", 'USERDEFINED')
        closet.ObjectType = 'closet'
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=closet, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(points, faces)]))
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[closet], relating_structure=storey)
        ifcopenshell.api.material.assign_material(ctx.model, products=[closet], material=ctx.material(spec['materials']['body']))
        ctx.pset(closet, 'HDT_Provenance', {'FactId': fixture['id'], 'Space': fixture['space'], 'Footprint': fixture['source'],
                                            'Front': spec['applies_to']['source'], 'Width': fixture['width'], 'Depth': fixture['depth']})
        handles = ctx.element('IfcDiscreteAccessory', f"{fixture['id']}-jaladeras")
        handles.ObjectType = 'jaladeras'
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=handles, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(hpoints, hfaces)]))
        ifcopenshell.api.aggregate.assign_object(ctx.model, products=[handles], relating_object=closet)
        ifcopenshell.api.material.assign_material(ctx.model, products=[handles], material=ctx.material(spec['handles']['material']))
        if 'interior' in spec:  # cuerpo hueco, lo de adentro y las hojas de abajo sueltas (se abren en el recorrido)
            _add_parts(ctx, storey, spec, lambda s, fx=fixture: interior_parts(fx, s, height) + leaf_parts(fx, s, height)[0])


def _roofed(facts):
    return [s for s in facts['spaces'] if (s.get('roofed') or {}).get('value') is True]


def _add_roof(ctx: _IfcContext, facts, storey, height):
    """Losa sobre los espacios techados y los muros que los rodean; deja abierto lo que no está techado (tragaluz).

    El espesor es un supuesto (U02 sin respuesta) y queda marcado en HDT_Provenance.
    """
    roofed = _roofed(facts)
    if not roofed:
        return
    rooms = unary_union([Polygon(s['polygon']) for s in roofed])
    walls = unary_union([Polygon(w['footprint']) for w in facts['walls']])
    reach = max(w['thickness'] for w in facts['walls']) + 0.02
    footprint = rooms.union(rooms.buffer(reach, join_style='mitre').intersection(walls)).buffer(0.005).buffer(-0.005)
    thickness = ASSUMED_DEFAULTS['slab_thickness']
    solids = []
    for poly in getattr(footprint, 'geoms', [footprint]):
        outer = ctx.builder.polyline([tuple(p) for p in poly.exterior.coords[:-1]], closed=True)
        inner = [ctx.builder.polyline([tuple(p) for p in ring.coords[:-1]], closed=True) for ring in poly.interiors]
        solids.append(ctx.builder.extrude(ctx.builder.profile(outer, inner_curves=inner), magnitude=thickness,
                                          position=(0.0, 0.0, height)))
    slab = ctx.element('IfcSlab', 'losa', 'ROOF')
    ifcopenshell.api.geometry.assign_representation(ctx.model, product=slab, representation=ctx.builder.get_representation(ctx.body, solids))
    ifcopenshell.api.spatial.assign_container(ctx.model, products=[slab], relating_structure=storey)
    ctx.pset(slab, 'HDT_Provenance', {'Spaces': ','.join(s['id'] for s in roofed), 'Thickness': thickness, 'ThicknessAssumed': True,
                                      'Unknown': 'U02', 'Roofed': 'dueño: espacios interiores y pórtico techados'})


def _add_ceilings(ctx: _IfcContext, facts, storey, height, finishes: Finishes | None):
    """Plafón (capa de tirol) de cada espacio techado, justo bajo la losa."""
    for s in _roofed(facts):
        ceiling = ctx.element('IfcCovering', f"{s['id']}-techo", 'CEILING')
        ctx.extrude_polygon(ceiling, s['polygon'], CEILING_FINISH_M, height - CEILING_FINISH_M)
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[ceiling], relating_structure=storey)
        finish = finishes.ceiling(s['id']) if finishes else None
        if finish:
            ifcopenshell.api.material.assign_material(ctx.model, products=[ceiling], material=ctx.material(finish))
        ctx.pset(ceiling, 'HDT_Provenance', {'Space': s['id'], 'Finish': finish or 'sin dato', 'Roofed': s['roofed']['source']})


def _add_lights(ctx: _IfcContext, facts, storey, height, luminaires):
    """Portalámparas con su foco en cada salida del plano que cae en un espacio techado."""
    if not luminaires:
        return
    spec = luminaires[0]
    roofed = {s['id'] for s in _roofed(facts)}
    for light in facts.get('lights', []):
        if light['space'] not in roofed:
            continue
        (sp, sf), (bp, bf), centre = luminaire_meshes(spec, light['position'], height - CEILING_FINISH_M)
        fixture = ctx.element('IfcLightFixture', light['id'], 'POINTSOURCE')
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=fixture, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(sp, sf)]))
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[fixture], relating_structure=storey)
        ifcopenshell.api.material.assign_material(ctx.model, products=[fixture], material=ctx.material(spec['materials']['socket']))
        bulb = ctx.element('IfcDiscreteAccessory', f"{light['id']}-foco")
        bulb.ObjectType = 'foco'
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=bulb, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(bp, bf)]))
        ifcopenshell.api.aggregate.assign_object(ctx.model, products=[bulb], relating_object=fixture)
        ifcopenshell.api.material.assign_material(ctx.model, products=[bulb], material=ctx.material(spec['materials']['bulb']))
        lit = spec['light']
        ctx.pset(fixture, 'HDT_Provenance', {'FactId': light['id'], 'Space': light['space'], 'Position': light['source'],
                                             'Fixture': spec['applies_to']['source']})
        ctx.pset(fixture, 'HDT_Light', {'Lumens': lit['lumens'], 'ColorTemperature': lit['color_temperature_k'], 'PowerW': lit['power_w'],
                                        'CentreZ': round(centre[2], 3), 'Source': lit['source']})


def _add_devices(ctx: _IfcContext, facts, storey, spec):
    """Contactos (IfcOutlet) y apagadores (IfcSwitchingDevice) en la cara del muro."""
    if not spec:
        return
    for device in facts.get('devices', []):
        if device.get('exists', {}).get('value') is False:  # el plano lo dibuja, pero el dueño dice que no está
            continue
        points, faces = device_mesh(spec, device)
        ifc_class, kind = ('IfcOutlet', 'POWEROUTLET') if device['kind'] == 'outlet' else ('IfcSwitchingDevice', 'TOGGLESWITCH')
        element = ctx.element(ifc_class, device['id'], kind)
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=element, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(points, faces)]))
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[element], relating_structure=storey)
        plate = device.get('plate') or {}
        ifcopenshell.api.material.assign_material(ctx.model, products=[element], material=ctx.material(plate.get('material') or spec['material']))
        z, z_source = device_height(spec, device)
        ctx.pset(element, 'HDT_Provenance', {'FactId': device['id'], 'Space': device['space'], 'Position': device['source'],
                                             'Height': z, 'HeightSource': z_source,
                                             'Finish': plate.get('source') or spec['applies_to']['source'],
                                             'SharedPlate': plate.get('id'), 'PlateWith': ','.join(plate.get('with', [])) or None})


def _add_shower_fittings(ctx: _IfcContext, facts, storey, spec):
    """Llaves (IfcValve) y brazo con regadera (IfcSanitaryTerminal) en el muro de la regadera."""
    shower = next((f for f in facts.get('fixtures', []) if f['kind'] == 'shower' and spec and f['space'] == spec['applies_to']['space']), None)
    if shower is None:
        return
    parts = [(f"{shower['id']}-llave-{i + 1}", 'IfcValve', 'MIXING', mesh, spec['valves']['source'])
             for i, mesh in enumerate(valve_meshes(spec))]
    parts.append((f"{shower['id']}-regadera", 'IfcSanitaryTerminal', 'SHOWER', shower_mesh(spec), spec['shower']['outlet_source']))
    for name, ifc_class, kind, (points, faces), source in parts:
        element = ctx.element(ifc_class, name, kind)
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=element, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(points, faces)]))
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[element], relating_structure=storey)
        ifcopenshell.api.material.assign_material(ctx.model, products=[element], material=ctx.material(spec['material']))
        ctx.pset(element, 'HDT_Provenance', {'FactId': shower['id'], 'Space': shower['space'], 'Height': source,
                                             'Position': spec['mount']['source']})


def _add_sanitary(ctx: _IfcContext, facts, storey, specs):
    """Inodoros y lavabos (IfcSanitaryTerminal) donde el plano los dibuja, en los baños que tienen especificación;
    la mezcladora del lavabo va como IfcValve y la palanca del tanque como IfcDiscreteAccessory."""
    for fixture in facts.get('fixtures', []):
        spec = spec_for(specs or [], fixture['space']) if fixture['kind'] in ('toilet', 'basin') else None
        if spec is None:
            continue
        kind = 'TOILETPAN' if fixture['kind'] == 'toilet' else 'WASHHANDBASIN'
        parts = [(fixture['id'], 'IfcSanitaryTerminal', kind, sanitary_mesh(spec, fixture), material_of(spec, fixture['kind']),
                  spec[fixture['kind']]['source'])]
        if fixture['kind'] == 'basin':
            faucet = spec['basin']['faucet']
            parts.append((f"{fixture['id']}-mezcladora", 'IfcValve', 'FAUCET', faucet_mesh(spec, fixture), faucet['material'],
                          faucet['note']))
        lever = lever_mesh(spec, fixture) if fixture['kind'] == 'toilet' else None
        if lever:
            parts.append((f"{fixture['id']}-palanca", 'IfcDiscreteAccessory', None, lever, spec['toilet']['lever']['material'],
                          spec['toilet']['lever']['note']))
        for name, ifc_class, predefined, (points, faces), material, source in parts:
            element = ctx.element(ifc_class, name, predefined)
            ifcopenshell.api.geometry.assign_representation(
                ctx.model, product=element, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(points, faces)]))
            ifcopenshell.api.spatial.assign_container(ctx.model, products=[element], relating_structure=storey)
            ifcopenshell.api.material.assign_material(ctx.model, products=[element], material=ctx.material(material))
            ctx.pset(element, 'HDT_Provenance', {'FactId': fixture['id'], 'Space': fixture['space'],
                                                 'Position': fixture['source'], 'Shape': source})


def _add_parts(ctx: _IfcContext, storey, spec, parts):
    """Piezas armadas por módulo (cocineta, sala): cada una con su clase IFC, material y la fuente de sus medidas.

    Cocineta: muebles (IfcFurniture), estufa y refrigerador (IfcElectricAppliance), tarja (IfcSanitaryTerminal),
    llave (IfcValve) y jaladeras (IfcDiscreteAccessory). Sala: sofá (IfcFurniture) y TV (IfcAudioVisualAppliance)."""
    if not spec:
        return
    for part in parts(spec):
        element = ctx.element(part['ifc'], part['id'], part['type'])
        if part['type'] == 'USERDEFINED' or part['ifc'] == 'IfcCovering':
            element.ObjectType = part.get('object_type') or 'mueble'
        points, faces = part['mesh']
        ifcopenshell.api.geometry.assign_representation(
            ctx.model, product=element, representation=ctx.builder.get_representation(ctx.body, [ctx.builder.polygonal_face_set(points, faces)]))
        ifcopenshell.api.spatial.assign_container(ctx.model, products=[element], relating_structure=storey)
        ifcopenshell.api.material.assign_material(ctx.model, products=[element], material=ctx.material(part['material']))
        if part.get('image_facing'):  # imagen (pantalla): Blender encuadra la textura en la cara que mira hacia allá
            ctx.pset(element, 'HDT_Image', {'FacingX': part['image_facing'][0], 'FacingY': part['image_facing'][1]})
        ctx.pset(element, 'HDT_Provenance', {'Space': spec['applies_to']['space'], 'Source': spec['applies_to']['source'],
                                             'Measures': part.get('source') or spec['measure_source']})


def _add_spaces(ctx: _IfcContext, facts, storey, height):
    spaces = []
    for s in facts['spaces']:
        space = ctx.element('IfcSpace', s['id'], 'EXTERNAL' if s['is_exterior'] else 'INTERNAL')
        space.LongName = s['name'] or 'Sin rótulo'
        ctx.extrude_polygon(space, s['polygon'], height)
        ctx.pset(space, 'HDT_Provenance', {'FactId': s['id'], 'Area': s['area'], 'Labels': ', '.join(s['labels']) or None,
                                           'FloorLevel': s['floor_level']['value'], 'IsExterior': s['is_exterior']})
        spaces.append(space)
    ifcopenshell.api.aggregate.assign_object(ctx.model, products=spaces, relating_object=storey)


def _add_floor_finishes(ctx: _IfcContext, facts, storey, finishes: Finishes):
    """Acabado de piso de cada espacio que lo tiene registrado: un IfcCovering delgado bajo el nivel 0."""
    coverings = []
    showers = {}
    for f in facts.get('fixtures', []):
        if f['kind'] == 'shower' and finishes.shower_floor(f['space']):
            showers.setdefault(f['space'], []).append(f)
    for s in facts['spaces']:
        name = finishes.floor(s['id'])
        if name is None:
            continue
        floor = Polygon(s['polygon']).difference(unary_union([Polygon(f['polygon']) for f in showers.get(s['id'], [])]))
        covering = ctx.element('IfcCovering', f"{s['id']}-piso", 'FLOORING')
        ctx.extrude_polygon(covering, [list(p) for p in floor.exterior.coords[:-1]], FLOOR_FINISH_THICKNESS, -FLOOR_FINISH_THICKNESS)
        ctx.assign_parts(covering, {'leaf': name})
        ctx.pset(covering, 'HDT_Provenance', {'Space': s['id'], 'Finish': name, 'ThicknessAssumed': True})
        coverings.append(covering)
        for f in showers.get(s['id'], []):  # su propio piso: el antiderrapante
            shower_name = finishes.shower_floor(s['id'])
            covering = ctx.element('IfcCovering', f"{s['id']}-regadera", 'FLOORING')
            ctx.extrude_polygon(covering, f['polygon'], FLOOR_FINISH_THICKNESS, -FLOOR_FINISH_THICKNESS)
            ctx.assign_parts(covering, {'leaf': shower_name})
            ctx.pset(covering, 'HDT_Provenance', {'Space': s['id'], 'FactId': f['id'], 'Finish': shower_name,
                                                  'Area': f['source'], 'ThicknessAssumed': True})
            coverings.append(covering)
    if coverings:
        ifcopenshell.api.spatial.assign_container(ctx.model, products=coverings, relating_structure=storey)


def _identity(entity) -> str:
    """Identidad de una entidad por lo que es, no por el orden en que se creó.

    Los productos se reconocen por su nombre (el id del hecho: W01, D03-vano, S05…); las relaciones y los
    Psets, por su nombre y los productos a los que se refieren.
    """
    refs = [v for v in entity if isinstance(v, ifcopenshell.entity_instance) or isinstance(v, tuple)]
    related = []
    for v in refs:
        for item in (v if isinstance(v, tuple) else (v,)):
            if isinstance(item, ifcopenshell.entity_instance) and item.is_a('IfcRoot'):
                related.append(f"{item.is_a()}:{item.Name or ''}")
    if entity.is_a('IfcPropertySetDefinition'):
        related += [f"{o.is_a()}:{o.Name or ''}" for rel in entity.DefinesOccurrence for o in rel.RelatedObjects]
    return f"{entity.is_a()}|{entity.Name or ''}|{','.join(sorted(related))}"


def _stabilize_guids(model: ifcopenshell.file):
    """GlobalId deterministas: el mismo hecho tiene el mismo GUID en cada `build`.

    Así Bonsai puede recargar el IFC por cambios (los compara por GlobalId) y cualquier referencia externa
    a un elemento sigue valiendo. El GUID sigue al id del hecho: si un cambio del plano renumera los muros,
    el GUID se va con el id.
    """
    seen: dict[str, int] = {}
    for entity in model.by_type('IfcRoot'):
        key = _identity(entity)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            key = f"{key}#{seen[key]}"
        entity.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(GUID_NAMESPACE, key).hex)


def build_ifc(facts: dict, finishes: Finishes | None = None, hardware: list[dict] | None = None,
              furniture: list[dict] | None = None, luminaires: list[dict] | None = None,
              devices: dict | None = None, shower: dict | None = None, sanitary: list[dict] | None = None,
              kitchen: dict | None = None, living: dict | None = None,
              bedrooms: list[dict] | None = None, laundry: dict | None = None) -> ifcopenshell.file:
    ctx = _IfcContext(facts['name'])
    site = ctx.element('IfcSite', 'Terreno')
    building = ctx.element('IfcBuilding', 'Casa')
    storey = ctx.element('IfcBuildingStorey', facts['levels'][0]['name'])
    ifcopenshell.api.aggregate.assign_object(ctx.model, products=[site], relating_object=ctx.project)
    ifcopenshell.api.aggregate.assign_object(ctx.model, products=[building], relating_object=site)
    ifcopenshell.api.aggregate.assign_object(ctx.model, products=[storey], relating_object=building)
    ctx.pset(site, 'HDT_Provenance', {'Area': facts['site']['area'], 'Width': facts['site']['width'], 'Depth': facts['site']['depth']})
    height, _ = _value_or_assumed(facts['levels'][0]['storey_height'], 'storey_height')
    walls = _add_walls(ctx, facts, storey, height)
    for o in facts['openings']:
        _add_opening(ctx, o, walls, storey, finishes, hardware, facts['spaces'])
    _add_furniture(ctx, facts, storey, height, furniture or [])
    _add_roof(ctx, facts, storey, height)
    _add_ceilings(ctx, facts, storey, height, finishes)
    _add_lights(ctx, facts, storey, height, luminaires or [])
    _add_devices(ctx, facts, storey, devices)
    _add_shower_fittings(ctx, facts, storey, shower)
    _add_sanitary(ctx, facts, storey, sanitary)
    _add_parts(ctx, storey, kitchen, kitchen_parts)
    _add_parts(ctx, storey, living, living_parts)
    for bedroom in bedrooms or []:
        _add_parts(ctx, storey, bedroom, bedroom_parts)
    _add_parts(ctx, storey, laundry, lambda spec: laundry_parts(spec, devices))
    _add_spaces(ctx, facts, storey, height)
    if finishes:
        _add_floor_finishes(ctx, facts, storey, finishes)
    _stabilize_guids(ctx.model)
    return ctx.model
