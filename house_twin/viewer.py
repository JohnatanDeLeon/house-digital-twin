"""Visor 3D web (three.js) generado desde los hechos: un solo HTML que se abre en el celular.

La geometría se resuelve aquí, no en el navegador: cada muro se parte en prismas
(tramos llenos, antepechos bajo ventanas y dinteles sobre vanos) para que el visor
solo tenga que extruir polígonos. Las alturas no conocidas usan ASSUMED_DEFAULTS
y la página lo dice.
"""
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import polylabel, unary_union

from house_twin.ifc_export import ASSUMED_DEFAULTS
from house_twin.model import HouseModel

TEMPLATE = Path(__file__).with_name('viewer_template.html')
DATA_MARKER = '/*__SCENE_DATA__*/null'


def _rings(geom):
    """Polígonos como [exterior, *huecos] en listas de puntos."""
    for poly in getattr(geom, 'geoms', [geom]):
        if poly.geom_type == 'Polygon' and poly.area > 1e-6:
            yield [[[round(x, 3), round(y, 3)] for x, y in ring.coords[:-1]]
                   for ring in [poly.exterior, *poly.interiors]]


def _opening_heights(o, storey_height):
    if o['kind'] == 'door':
        height = o['height']['value'] or ASSUMED_DEFAULTS['door_height']
        return 0.0, min(height, storey_height)
    sill = o['sill_height']['value'] if o['sill_height']['value'] is not None else ASSUMED_DEFAULTS['window_sill']
    height = o['height']['value'] or ASSUMED_DEFAULTS['window_height']
    return sill, min(sill + height, storey_height)


def _wall_prisms(facts, storey_height):
    drawn = [o for o in facts['openings'] if o['footprint']]
    voids = unary_union([Polygon(o['footprint']) for o in drawn])
    prisms = []
    for w in facts['walls']:
        solid = Polygon(w['footprint']).difference(voids)
        prisms += [{'rings': r, 'z0': 0.0, 'z1': storey_height, 'wall': w['id']} for r in _rings(solid)]
    for o in drawn:
        sill, head = _opening_heights(o, storey_height)
        rect = Polygon(o['footprint'])
        if sill > 0:
            prisms += [{'rings': r, 'z0': 0.0, 'z1': sill, 'wall': o['host_wall']} for r in _rings(rect)]
        if head < storey_height:
            prisms += [{'rings': r, 'z0': head, 'z1': storey_height, 'wall': o['host_wall']} for r in _rings(rect)]
    return prisms


def _glass(facts, storey_height):
    panes = []
    for o in facts['openings']:
        if o['kind'] != 'window' or not o['footprint']:
            continue
        sill, head = _opening_heights(o, storey_height)
        rect = Polygon(o['footprint'])
        # vidrio: franja central de 2 cm a lo largo del vano
        minx, miny, maxx, maxy = rect.bounds
        along_x = (maxx - minx) >= (maxy - miny)
        if along_x:
            cy = (miny + maxy) / 2
            pane = [[minx, cy - 0.01], [maxx, cy - 0.01], [maxx, cy + 0.01], [minx, cy + 0.01]]
        else:
            cx = (minx + maxx) / 2
            pane = [[cx - 0.01, miny], [cx + 0.01, miny], [cx + 0.01, maxy], [cx - 0.01, maxy]]
        panes.append({'rings': [pane], 'z0': sill, 'z1': head, 'id': o['id']})
    return panes


def _space_info(house: HouseModel, s: dict) -> dict:
    room = house.get_room(s['id'])
    pole = polylabel(Polygon(s['polygon']), tolerance=0.05)
    return {
        'id': s['id'], 'name': room['name'], 'area': s['area'], 'perimeter': s['perimeter'],
        'exterior': s['is_exterior'], 'rings': [s['polygon']], 'label': [round(pole.x, 3), round(pole.y, 3)],
        'floor': s['floor_level']['value'], 'roofed': s['roofed']['value'],
        'note': s.get('owner_note'), 'name_source': s.get('name_source'),
        'openings': room['openings'],
        'neighbors': [{'name': n['name'], 'via': n['connection']} for n in room['neighbors']],
    }


def build_scene(facts: dict) -> dict:
    house = HouseModel(facts)
    storey = facts['levels'][0]['storey_height']['value'] or ASSUMED_DEFAULTS['storey_height']
    declared = [o for o in facts['openings'] if not o['footprint']]
    door_heights = {o['height']['value'] for o in facts['openings'] if o['kind'] == 'door'}
    return {
        'name': facts['name'], 'site': facts['site'], 'storey_height': storey,
        'storey_height_assumed': facts['levels'][0]['storey_height']['value'] is None,
        'assumed': ASSUMED_DEFAULTS,
        'door_height_assumed': None in door_heights,
        'door_height': door_heights.pop() if len(door_heights) == 1 and None not in door_heights else None,
        'walls': _wall_prisms(facts, storey), 'glass': _glass(facts, storey),
        'doors': [{'id': o['id'], 'rings': [o['footprint']]} for o in facts['openings'] if o['kind'] == 'door' and o['footprint']],
        'declared_openings': [{'id': o['id'], 'kind': o['kind'], 'wall': o['host_wall'], 'note': o.get('owner_note')} for o in declared],
        'spaces': [_space_info(house, s) for s in facts['spaces']],
        'pending': len(facts['unknowns']), 'built_on': facts['provenance']['built_on'],
    }


def render_viewer(facts: dict, out_path: Path):
    scene = json.dumps(build_scene(facts), ensure_ascii=False, separators=(',', ':'))
    html = TEMPLATE.read_text()
    if DATA_MARKER not in html:
        raise ValueError(f'La plantilla del visor no tiene el marcador {DATA_MARKER}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html.replace(DATA_MARKER, scene))
