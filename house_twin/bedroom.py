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
    if spec.get('desk_l'):
        parts += _desk_l(spec['desk_l'])
        if spec.get('monitors'):
            parts += _monitors(spec['monitors'], spec['desk_l'])
    for ex in spec.get('extras', []):
        parts += _extra(ex)
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


def _desk_l(dk):
    """Escritorio en L: lado largo y lado corto desde la esquina de 2 muros, con patas en T."""
    cx, cy = dk['corner']
    m, r, h, t = dk['main'], dk['return'], dk['height_m'], dk['top_m']
    main = _Run({'origin': [cx, cy], 'along': m['along'], 'into_room': m['into_room']})
    side = _Run({'origin': [cx, cy], 'along': r['along'], 'into_room': r['into_room']})
    top = [main.box((0.0, m['length_m']), (h - t, h), (0.0, m['depth_m'])),
           side.box((m['depth_m'], r['length_m']), (h - t, h), (0.0, r['depth_m']))]
    legs = []
    for u in (0.12, m['length_m'] - 0.12):
        legs += [main.box((u - 0.035, u + 0.035), (0.03, h - t), (m['depth_m'] / 2 - 0.035, m['depth_m'] / 2 + 0.035)),
                 main.box((u - 0.035, u + 0.035), (0.0, 0.03), (0.04, m['depth_m'] - 0.04))]
    src = f"{dk['size_source']}; {dk['position_source']}; {dk['assumptions']}"
    return [{'id': dk['id'], 'ifc': 'IfcFurniture', 'type': 'DESK', 'material': dk['material'], 'mesh': merge(top), 'source': src},
            {'id': f"{dk['id']}-patas", 'ifc': 'IfcFurniture', 'type': 'DESK', 'material': dk['legs_material'], 'mesh': merge(legs), 'source': src}]


def _monitors(mo, dk):
    """Brazo de 3 posiciones al fondo del lado largo: 2 monitores arriba (un poco girados hacia el centro) y la
    charola de la laptop abajo, al centro."""
    import math
    cx, cy = dk['corner']
    m = dk['main']
    ax, ay = m['along']
    nx, ny = m['into_room']  # los monitores miran hacia el cuarto
    mid = (cx + ax * m['length_m'] / 2, cy + ay * m['length_m'] / 2)
    px, py = mid[0] + nx * 0.08, mid[1] + ny * 0.08
    h = dk['height_m']
    diag = mo['diagonal_in'] * 0.0254
    w, hh = diag * mo['aspect'][0] / math.hypot(*mo['aspect']), diag * mo['aspect'][1] / math.hypot(*mo['aspect'])
    body, screens = [cylinder((px, py, h), (px, py, h + mo['pole_height_m']), mo['pole_radius_m'], 12)], []
    for side in (-1, 1):
        u = side * (w / 2 + mo['gap_m'] / 2)
        ang = math.radians(mo['toe_in_deg']) * side
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = ax * ca - nx * sa, ay * ca - ny * sa  # a lo ancho del monitor, girado
        fx, fy = nx * ca + ax * sa, ny * ca + ay * sa  # hacia donde mira
        ox, oy = px + ax * u + nx * 0.05, py + ay * u + ny * 0.05
        frame = _Run({'origin': [ox, oy], 'along': [bx, by], 'into_room': [fx, fy]})
        z0 = mo['centre_z'] - hh / 2
        body.append(frame.box((-w / 2 - 0.008, w / 2 + 0.008), (z0 - 0.008, z0 + hh + 0.008), (0.0, 0.03)))
        screens.append(frame.box((-w / 2, w / 2), (z0, z0 + hh), (0.03, 0.032)))
        body.append(cylinder((px, py, mo['centre_z']), (ox, oy, mo['centre_z']), 0.012, 8))
    tw, td = mo['tray']['size_m']
    tz = h + mo['tray']['z_above_desk_m']
    tray = _Run({'origin': [px, py], 'along': [ax, ay], 'into_room': [nx, ny]})
    body += [tray.box((-tw / 2, tw / 2), (tz, tz + 0.01), (0.02, 0.02 + td)),
             tray.box((-0.16, 0.16), (tz + 0.01, tz + 0.025), (0.04, 0.26)),
             tray.box((-0.16, 0.16), (tz + 0.025, tz + 0.235), (0.04, 0.052))]  # laptop abierta
    return [{'id': mo['id'], 'ifc': 'IfcAudioVisualAppliance', 'type': 'DISPLAY', 'material': mo['body_material'], 'mesh': merge(body), 'source': mo['source']},
            {'id': f"{mo['id']}-pantallas", 'ifc': 'IfcAudioVisualAppliance', 'type': 'DISPLAY', 'material': mo['screen_material'],
             'mesh': merge(screens), 'source': mo['source']}]


def _extra(ex):
    if 'chair' in ex:  # silla gamer: base de 5 ruedas simplificada, asiento y respaldo alto
        (cx, cy), (fx, fy) = ex['chair']['centre'], ex['chair']['facing']
        f = _Run({'origin': [cx, cy], 'along': [-fy, fx], 'into_room': [fx, fy]})
        mesh = merge([cylinder((cx, cy, 0.05), (cx, cy, 0.42), 0.03, 10), f.box((-0.33, 0.33), (0.0, 0.05), (-0.33, 0.33)),
                      f.box((-0.27, 0.27), (0.42, 0.52), (-0.25, 0.27)), f.box((-0.26, 0.26), (0.52, 1.32), (-0.3, -0.2)),
                      *[f.box((s * 0.3 - 0.04, s * 0.3 + 0.04), (0.6, 0.66), (-0.2, 0.2)) for s in (-1, 1)]])
    else:
        (x0, x1), (y0, y1), (z0, z1) = ex['box']
        from house_twin.hardware import _box
        mesh = _box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0))
    return [{'id': ex['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': ex['object_type'], 'material': ex['material'],
             'mesh': mesh, 'source': ex['source']}]
