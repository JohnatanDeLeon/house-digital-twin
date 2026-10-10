"""Recámaras amuebladas: closet abierto, cama de latón, buros, escritorio y televisión, descritos en
`sources/recamaras/<nombre>.json`. Arma las mallas en coordenadas del mundo con el mismo formato de piezas que la
cocineta y la sala; `ifc_export` las guarda. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import cylinder, lathe, merge
from house_twin.kitchen import _Run
from house_twin.living import _tv
from house_twin.office import office_parts

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


def _upholstered_bed(bd):
    """Cama con base tapizada, cabecera acolchada por tableros y cobija encima."""
    frame = _Run(bd['headboard_wall'])
    w, length = bd['size_m']
    b0, b1 = bd['base_m']
    hb, m = bd['headboard'], bd['materials']
    cols, rows = hb['panels']
    pw, ph = hb['width_m'] / cols, (hb['height_m'] - b1) / rows
    head = [frame.box((-hb['width_m'] / 2 + c * pw + 0.004, -hb['width_m'] / 2 + (c + 1) * pw - 0.004),
                      (b1 + r * ph + 0.004, b1 + (r + 1) * ph - 0.004), (0.0, hb['thickness_m']))
            for c in range(cols) for r in range(rows)]
    head.append(frame.box((-hb['width_m'] / 2, hb['width_m'] / 2), (0.0, b1), (0.0, hb['thickness_m'] - 0.01)))
    t = hb['thickness_m']
    base = [frame.box((-w / 2, w / 2), (b0, b1), (t, t + length)),
            *[frame.box((u - 0.04, u + 0.04), (0, b0), (n - 0.04, n + 0.04)) for u in (-w / 2 + 0.08, w / 2 - 0.08)
              for n in (t + 0.1, t + length - 0.1)]]
    cover = frame.box((-w / 2 - 0.03, w / 2 + 0.03), (b1, bd['mattress_top_m']), (t + 0.02, t + length + 0.03))
    src = bd['source']
    return [{'id': bd['id'], 'ifc': 'IfcFurniture', 'type': 'BED', 'material': m['cover'], 'mesh': cover, 'source': src},
            {'id': f"{bd['id']}-base", 'ifc': 'IfcFurniture', 'type': 'BED', 'material': m['base'], 'mesh': merge(base), 'source': src},
            {'id': f"{bd['id']}-cabecera", 'ifc': 'IfcFurniture', 'type': 'BED', 'material': m['headboard'], 'mesh': merge(head), 'source': src}]


def _framed_nightstands(ns, bd):
    """Buros de cajones de laminado dentro de un marco metálico, uno a cada lado de la cama."""
    frame = _Run(bd['headboard_wall'])
    w, d, h = ns['size_m']
    off = bd['size_m'][0] / 2 + ns['gap_m'] + w / 2
    wood, metal = [], []
    for side in (-1, 1):
        u = side * off
        wood.append(frame.box((u - w / 2 + 0.03, u + w / 2 - 0.03), (h - 0.04, h), (0.0, d)))  # cubierta
        for k in range(ns['drawers']):
            z0 = h - 0.04 - (k + 1) * 0.12
            wood.append(frame.box((u - w / 2 + 0.03, u + w / 2 - 0.03), (z0 + 0.004, z0 + 0.12 - 0.004), (0.02, d)))
            metal.append(cylinder(frame.point(u - 0.06, d + 0.02, z0 + 0.06), frame.point(u + 0.06, d + 0.02, z0 + 0.06), 0.006, 8))
        wood.append(frame.box((u - w / 2 + 0.03, u + w / 2 - 0.03), (0.04, 0.06), (0.02, d - 0.02)))  # repisa de abajo
        for du in (-w / 2, w / 2 - 0.03):  # costados del marco
            metal.append(frame.box((u + du, u + du + 0.03), (0.0, h), (0.0, d)))
    return [{'id': ns['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'buros', 'material': ns['material'],
             'mesh': merge(wood), 'source': ns['source']},
            {'id': f"{ns['id']}-marco", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'marco de los buros',
             'material': ns['frame_material'], 'mesh': merge(metal), 'source': ns['source']}]


def _ottoman(ot, bd):
    frame = _Run(bd['headboard_wall'])
    w, d, h = ot['size_m']
    n0 = bd['headboard']['thickness_m'] + bd['size_m'][1] + ot['from_foot_m']
    return [{'id': ot['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'baúl', 'material': ot['material'],
             'mesh': frame.box((-w / 2, w / 2), (0.0, h), (n0, n0 + d)), 'source': ot['source']}]


def _mirror(mi):
    frame = _Run(mi['wall'])
    (u0, u1), (z0, z1), lean = mi['u'], mi['z'], mi['lean_m']
    border = 0.03
    frame_parts = [frame.box((u0, u1), (z0, z0 + border), (lean, lean + 0.025)), frame.box((u0, u1), (z1 - border, z1), (0.0, 0.025)),
                   frame.box((u0, u0 + border), (z0, z1), (lean / 2 - 0.0, lean / 2 + 0.025)),
                   frame.box((u1 - border, u1), (z0, z1), (lean / 2, lean / 2 + 0.025))]
    glass = frame.box((u0 + border, u1 - border), (z0 + border, z1 - border), (lean / 2 + 0.012, lean / 2 + 0.016))
    if z0 < 0.3:  # parado en el piso: base hasta el suelo (si está sobre un mueble, no)
        frame_parts.append(frame.box((u0, u1), (0.0, z0), (lean, lean + 0.02)))
    return [{'id': mi['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'espejo', 'material': mi['material'],
             'mesh': glass, 'source': mi['source']},
            {'id': f"{mi['id']}-marco", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'marco del espejo',
             'material': mi['frame_material'], 'mesh': merge(frame_parts), 'source': mi['source']}]


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
    bd = spec.get('bed')
    if bd:
        upholstered = bd.get('style') == 'upholstered'
        parts += _upholstered_bed(bd) if upholstered else _bed(bd)
        ns = spec.get('nightstands')
        if ns:
            parts += _framed_nightstands(ns, bd) if ns.get('style') == 'framed' else _nightstands(ns, bd)
        if spec.get('ottoman'):
            parts += _ottoman(spec['ottoman'], bd)
    if spec.get('mirror'):
        parts += _mirror(spec['mirror'])
    if spec.get('desk'):
        parts += _desk(spec['desk'])
    if spec.get('office'):
        parts += office_parts(spec['office'])
    for art in spec.get('artworks', []):  # cuadro: tabla con canto de madera y la imagen de la foto al frente
        frame = _Run(art['wall'])
        t = art['thickness_m']
        parts += [{'id': f"{art['id']}-tabla", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'cuadro',
                   'material': art['edge_material'], 'mesh': frame.box(art['u'], art['z'], (0.0, t)), 'source': art['source']},
                  {'id': art['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'cuadro', 'material': art['material'],
                   'mesh': frame.box((art['u'][0] + 0.004, art['u'][1] - 0.004), (art['z'][0] + 0.004, art['z'][1] - 0.004), (t, t + 0.001)),
                   'source': art['source'], 'image_facing': list(art['wall']['into_room'])}]
    ac = spec.get('minisplit')
    if ac:  # unidad interior: cuerpo con el frente redondeado abajo (2 escalones) y la rejilla de salida
        frame = _Run(ac['wall'])
        (u0, u1), (z0, z1), d = ac['u'], ac['z'], ac['depth_m']
        body = merge([frame.box((u0, u1), (z0 + 0.06, z1), (0.0, d)), frame.box((u0, u1), (z0 + 0.02, z0 + 0.06), (0.0, d - 0.03)),
                      frame.box((u0, u1), (z0, z0 + 0.02), (0.0, d - 0.08))])
        louver = frame.box((u0 + 0.05, u1 - 0.05), (z0 + 0.025, z0 + 0.055), (d - 0.031, d - 0.029))
        parts += [{'id': ac['id'], 'ifc': 'IfcUnitaryEquipment', 'type': 'SPLITSYSTEM', 'material': ac['material'], 'mesh': body,
                   'source': ac['source']},
                  {'id': f"{ac['id']}-rejilla", 'ifc': 'IfcUnitaryEquipment', 'type': 'SPLITSYSTEM', 'material': ac['louver_material'],
                   'mesh': louver, 'source': ac['source']}]
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

