"""Exporta `house.facts.json` a IFC4 con IfcOpenShell: muros, vanos con puerta/ventana y espacios.

El IFC necesita alturas que el plano no da. Se usan los supuestos de ASSUMED_DEFAULTS,
y cada elemento lleva en el Pset `HDT_Provenance` qué dato es hecho y cuál es supuesto,
para que nadie confunda un supuesto con una medida.
"""
import math

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
from ifcopenshell.util.shape_builder import ShapeBuilder

ASSUMED_DEFAULTS = {'storey_height': 2.40, 'door_height': 2.10, 'window_sill': 0.90, 'window_height': 1.20}
PANEL_THICKNESS = 0.05
OPENING_OVERCUT = 0.01  # el vano sobresale del muro para que el corte booleano sea limpio


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
    xs = [p[0] for p in footprint]; ys = [p[1] for p in footprint]
    cx, cy = sum(xs)/4, sum(ys)/4
    return [(x + math.copysign(margin, x-cx), y + math.copysign(margin, y-cy)) for x, y in footprint]


def _add_walls(ctx: _IfcContext, facts, storey, height):
    walls = {}
    for w in facts['walls']:
        wall = ctx.element('IfcWall', w['id'], 'SOLIDWALL')
        ctx.extrude_polygon(wall, w['footprint'], height)
        ctx.pset(wall, 'Pset_WallCommon', {'IsExternal': w['faces_exterior']})
        ctx.pset(wall, 'HDT_Provenance', {'FactId': w['id'], 'Source': w['source'], 'Thickness': w['thickness'],
                                          'OnPropertyLine': w['on_property_line'], 'HeightAssumed': True,
                                          'LoadBearingKnown': w['load_bearing']['value'] is not None})
        walls[w['id']] = wall
    ifcopenshell.api.spatial.assign_container(ctx.model, products=list(walls.values()), relating_structure=storey)
    return walls


def _add_declared_opening(ctx: _IfcContext, o, walls):
    """Vano que el dueño declaró pero el plano no dibuja: queda como dato del muro, sin geometría inventada."""
    host = walls.get(o['host_wall'])
    if host:
        ctx.pset(host, 'HDT_DeclaredOpenings', {o['id']: f"{o['kind']} sin medidas; conecta {','.join(o['connects'])}"})


def _add_opening(ctx: _IfcContext, o, walls, storey):
    if o['footprint'] is None:
        _add_declared_opening(ctx, o, walls)
        return
    is_door = o['kind'] == 'door'
    sill, sill_assumed = (0.0, False) if is_door else _value_or_assumed(o['sill_height'], 'window_sill')
    height, height_assumed = _value_or_assumed(o['height'], 'door_height' if is_door else 'window_height')
    void = ctx.element('IfcOpeningElement', f"{o['id']}-vano", 'OPENING')
    ctx.extrude_polygon(void, _grown(o['footprint'], OPENING_OVERCUT), height, sill)
    filler = ctx.element('IfcDoor' if is_door else 'IfcWindow', o['id'], 'DOOR' if is_door else 'WINDOW')
    ctx.extrude_polygon(filler, _panel(o['footprint'], PANEL_THICKNESS), height, sill)
    filler.OverallWidth, filler.OverallHeight = o['width'], height
    host = walls.get(o['host_wall'])
    if host:
        ifcopenshell.api.feature.add_feature(ctx.model, feature=void, element=host)
    ifcopenshell.api.feature.add_filling(ctx.model, opening=void, element=filler)
    ifcopenshell.api.spatial.assign_container(ctx.model, products=[filler], relating_structure=storey)
    ctx.pset(filler, 'HDT_Provenance', {'FactId': o['id'], 'Width': o['width'], 'SillHeight': sill, 'SillAssumed': sill_assumed,
                                        'Height': height, 'HeightAssumed': height_assumed, 'HostWall': o['host_wall'],
                                        'Connects': ','.join(o['connects'])})


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


def build_ifc(facts: dict) -> ifcopenshell.file:
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
        _add_opening(ctx, o, walls, storey)
    _add_spaces(ctx, facts, storey, height)
    return ctx.model
