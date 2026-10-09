"""Recámaras amuebladas: closet abierto, cama de latón, buros, escritorio y televisión, descritos en
`sources/recamaras/<nombre>.json`. Arma las mallas en coordenadas del mundo con el mismo formato de piezas que la
cocineta y la sala; `ifc_export` las guarda. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import cylinder, lathe, merge
from house_twin.kitchen import _Run
from house_twin.living import _tv

ROOT = Path(__file__).resolve().parent.parent
BEDROOMS_DIR = ROOT / 'sources' / 'recamaras'


def load_bedrooms(folder: Path = BEDROOMS_DIR) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))]


def _ball(frame, u, n, z, radius):
    """Perilla esférica (torneada) con el centro en (u, n, z)."""
    profile = [(0, 0)] + [(radius * s, radius * (1 - c)) for s, c in ((0.6, 0.8), (0.95, 0.31), (0.95, -0.31), (0.6, -0.8))] \
        + [(0, 2 * radius)]
    points, faces = lathe(profile, 16)
    x, y, _ = frame.point(u, n, 0)
    return [(x + px, y + py, z - radius + pz) for px, py, pz in points], faces


def _closet(c):
    frame = _Run(c['wall'])
    d, b = c['depth_m'], c['board_m']
    wood, rods = [], []
    for s in c['sections']:
        u0, u1 = s['u']
        if s['kind'] == 'drawers':
            wood += [frame.box((u0, u0 + b), (0, c['top_shelf']['z']), (0, d)), frame.box((u1 - b, u1), (0, c['top_shelf']['z']), (0, d))]
            h = (s['drawers_top_m'] - 0.04) / s['drawers']
            for k in range(s['drawers']):  # frentes de los cajones, con su junta
                wood.append(frame.box((u0 + 0.004, u1 - 0.004), (0.04 + k * h + 0.003, 0.04 + (k + 1) * h - 0.003), (d - 0.02, d)))
            wood.append(frame.box((u0, u1), (0.02, 0.04), (0, d - 0.02)))
            wood.append(frame.box((u0, u1), (0.04, s['drawers_top_m']), (0, d - 0.02)))  # cuerpo de la cajonera
            for z in [s['drawers_top_m']] + s['shelves_m']:
                wood.append(frame.box((u0 + b, u1 - b), (z, z + b), (0, d)))
        elif s['kind'] == 'shelves':
            wood += [frame.box((u0, u0 + b), (0, c['top_shelf']['z']), (0, d)), frame.box((u1 - b, u1), (0, c['top_shelf']['z']), (0, d))]
            for z in s['shelves_m']:
                wood.append(frame.box((u0 + b, u1 - b), (z, z + b), (0, d)))
        else:  # colgador: tubos de lado a lado, a media profundidad
            for z in s['rods_m']:
                rods.append(cylinder(frame.point(u0, d / 2, z), frame.point(u1, d / 2, z), 0.012, 12))
    span = (min(s['u'][0] for s in c['sections']), max(s['u'][1] for s in c['sections']))
    t = c['top_shelf']
    wood.append(frame.box(span, (t['z'], t['z'] + b), (0, t['depth_m'] + 0.1)))
    src = c['source']
    return [{'id': c['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'closet abierto', 'material': c['material'],
             'mesh': merge(wood), 'source': src},
            {'id': f"{c['id']}-tubos", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'tubos del closet',
             'material': c['rod_material'], 'mesh': merge(rods), 'source': src}]


def _bed(bd):
    frame = _Run(bd['headboard_wall'])
    w, length = bd['size_m']
    r, br = bd['post_radius_m'], bd['bar_radius_m']
    m0, m1 = bd['mattress_m']
    iron, brass = [], []
    ends = ((0.06, bd["head_top_m"]), (length - 0.04, bd["foot_top_m"]))  # la perilla de la cabecera no toca el muro
    for n, top in ends:
        for u in (-w / 2, w / 2):  # postes negros con perilla de latón
            iron.append(cylinder(frame.point(u, n, 0), frame.point(u, n, top - 0.05), r, 12))
            brass.append(_ball(frame, u, n, top, 0.045))
            for z in (top * 0.35, top * 0.7):  # anillos de latón en el poste
                brass.append(cylinder(frame.point(u, n, z - 0.03), frame.point(u, n, z + 0.03), r * 1.5, 12))
        low, high, upper = (m1 - 0.05, top - 0.12, top - 0.24)
        for z in (low, upper, high):  # travesaños de latón
            brass.append(cylinder(frame.point(-w / 2, n, z), frame.point(w / 2, n, z), br * 1.3, 10))
        for k in range(1, 6):  # barrotes
            u = -w / 2 + w * k / 6
            brass.append(cylinder(frame.point(u, n, low), frame.point(u, n, upper), br, 8))
        for u in (-w / 6 * 1.5, w / 6 * 1.5):  # arillos (como 2 tramos cortos)
            brass.append(cylinder(frame.point(u, n - 0.012, (upper + high) / 2), frame.point(u, n + 0.012, (upper + high) / 2), 0.05, 16))
    iron += [frame.box((-w / 2, w / 2), (m0 - 0.06, m0), (0.04, length - 0.04))]  # bastidor
    mattress = frame.box((-w / 2 + 0.02, w / 2 - 0.02), (m0, m1), (0.06, length - 0.06))
    src = bd['source']
    return [{'id': bd['id'], 'ifc': 'IfcFurniture', 'type': 'BED', 'material': 'sabana-gris', 'mesh': mattress, 'source': src},
            {'id': f"{bd['id']}-postes", 'ifc': 'IfcFurniture', 'type': 'BED', 'material': 'hierro-negro', 'mesh': merge(iron), 'source': src},
            {'id': f"{bd['id']}-laton", 'ifc': 'IfcFurniture', 'type': 'BED', 'material': 'laton-pulido', 'mesh': merge(brass), 'source': src}]


def _nightstands(ns, bd):
    frame = _Run(bd['headboard_wall'])
    w, d, h = ns['size_m']
    off = bd['size_m'][0] / 2 + ns['gap_m'] + w / 2
    body, handles = [], []
    for side in (-1, 1):
        u = side * off
        body.append(frame.box((u - w / 2, u + w / 2), (0.05, h), (0.0, d)))
        for k in range(ns['drawers']):
            z = 0.05 + (h - 0.05) * (k + 0.5) / ns['drawers']
            handles.append(cylinder(frame.point(u - 0.06, d + 0.02, z), frame.point(u + 0.06, d + 0.02, z), 0.007, 8))
        for du in (-w / 2 + 0.04, w / 2 - 0.04):
            body.append(frame.box((u + du - 0.02, u + du + 0.02), (0, 0.05), (0.04, d - 0.04)))
    return [{'id': ns['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'buros', 'material': ns['material'],
             'mesh': merge(body), 'source': ns['source']},
            {'id': f"{ns['id']}-jaladeras", 'ifc': 'IfcDiscreteAccessory', 'type': None, 'material': ns['handles'],
             'mesh': merge(handles), 'source': ns['source']}]


def _desk(dk):
    frame = _Run(dk['wall'])
    (u0, u1), d, h = dk['u'], dk['depth_m'], dk['height_m']
    p = dk['pedestal_m']
    parts = [frame.box((u0, u1), (h - 0.03, h), (0, d)), frame.box((u0, u0 + p), (0, h - 0.03), (0.02, d - 0.02))]
    for n in (0.04, d - 0.06):
        parts.append(frame.box((u1 - 0.05, u1 - 0.02), (0, h - 0.03), (n, n + 0.02)))
    return [{'id': dk['id'], 'ifc': 'IfcFurniture', 'type': 'DESK', 'material': dk['material'], 'mesh': merge(parts), 'source': dk['source']}]


def bedroom_parts(spec: dict) -> list[dict]:
    parts = []
    if spec.get('closet'):
        parts += _closet(spec['closet'])
    if spec.get('bed'):
        parts += _bed(spec['bed'])
        if spec.get('nightstands'):
            parts += _nightstands(spec['nightstands'], spec['bed'])
    if spec.get('desk'):
        parts += _desk(spec['desk'])
    t = spec.get('tv')
    if t:
        body, screen, _ = _tv(t)
        parts += [{'id': t['id'], 'ifc': 'IfcAudioVisualAppliance', 'type': 'TV', 'material': t['body_material'], 'mesh': body,
                   'source': f"{t['size_source']}; {t['position_source']}"},
                  {'id': f"{t['id']}-pantalla", 'ifc': 'IfcAudioVisualAppliance', 'type': 'DISPLAY', 'material': t['screen_material'],
                   'mesh': screen, 'source': t['size_source']}]
    for p in parts:
        p.setdefault('space', spec['applies_to']['space'])
    return parts
