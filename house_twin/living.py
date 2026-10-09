"""Sala: sofá en L y televisión, descritos en `sources/sala/sala.json`. Aquí se arman las mallas en coordenadas
del mundo (mismas piezas que la cocineta: id, clase IFC, material y malla); `ifc_export` las guarda.
Solo biblioteca estándar.
"""
import json
import math
from pathlib import Path

from house_twin.hardware import merge
from house_twin.kitchen import _Run

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / 'sources' / 'sala' / 'sala.json'


def load_living(path: Path = SPEC_PATH) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _sofa(s):
    """Dos lados en L desde la esquina: el lado A ocupa el rincón; el B empieza donde termina la profundidad de A.
    Cada lado: base, cojines de asiento separados, respaldo y brazo en la punta libre."""
    length = s['size_m'][0]
    d, seat, back, bd = s['depth_m'], s['seat_m'], s['back_top_m'], s['back_depth_m']
    arm, feet, seam = s['arm'], s['feet_m'], s['seam_m']
    body, feet_parts = [], []
    for leg, (start, end) in (('leg_a', (0.0, length)), ('leg_b', (d, s['size_m'][1]))):
        frame = _Run({'origin': s['corner'], 'along': s[leg]['along'], 'into_room': s[leg]['into_room']})
        seats_end = end - arm['width_m']
        body.append(frame.box((start, seats_end), (feet, seat - 0.12), (0, d)))  # base
        back_start = 0.0 if leg == 'leg_a' else bd  # el respaldo de B arranca en el de A
        body.append(frame.box((back_start, seats_end), (feet, back), (0, bd)))
        n = s['seats_per_leg'] + (1 if leg == 'leg_a' else 0)  # A lleva además la cuña del rincón
        first = bd if leg == 'leg_a' else start
        width = (seats_end - first) / n
        for k in range(n):  # cojines de asiento con su junta
            a, b = first + k * width + seam / 2, first + (k + 1) * width - seam / 2
            body.append(frame.box((a, b), (seat - 0.12, seat), (bd, d - 0.02)))
        body.append(frame.box((seats_end, end), (feet, arm['top_m']), (0, d)))  # brazo
        for u in (start + 0.08, end - 0.08):
            feet_parts.append(frame.box((u - 0.03, u + 0.03), (0, feet), (0.08, 0.14)))
            feet_parts.append(frame.box((u - 0.03, u + 0.03), (0, feet), (d - 0.14, d - 0.08)))
    return merge(body), merge(feet_parts)


def _tv(t):
    diag = t['diagonal_in'] * 0.0254
    w = diag * t['aspect'][0] / math.hypot(*t['aspect'])
    h = diag * t['aspect'][1] / math.hypot(*t['aspect'])
    frame = _Run(t['wall'])
    u0, z0, b = t['u_centre'] - w / 2, t['z_bottom'], t['bezel_m']
    body = merge([frame.box((u0 - b, u0 + w + b), (z0 - b, z0 + h + b), (0.03, 0.03 + t['depth_m'])),
                  frame.box((u0 + w / 2 - 0.2, u0 + w / 2 + 0.2), (z0 + h / 2 - 0.2, z0 + h / 2 + 0.2), (0.0, 0.03))])
    screen = frame.box((u0, u0 + w), (z0, z0 + h), (0.03 + t['depth_m'], 0.03 + t['depth_m'] + 0.002))
    return body, screen, (w, h)


def living_parts(spec: dict) -> list[dict]:
    parts = []
    s = spec.get('sofa')
    if s:
        body, feet = _sofa(s)
        parts.append({'id': s['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'sofá en L',
                      'material': s['material'], 'mesh': body, 'source': f"{s['size_source']}; {s['position_source']}"})
        parts.append({'id': f"{s['id']}-patas", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'patas del sofá',
                      'material': s['feet_material'], 'mesh': feet, 'source': s['source']})
    t = spec.get('tv')
    if t:
        body, screen, _ = _tv(t)
        parts.append({'id': t['id'], 'ifc': 'IfcAudioVisualAppliance', 'type': 'TV', 'material': t['body_material'],
                      'mesh': body, 'source': f"{t['size_source']}; {t['position_source']}"})
        parts.append({'id': f"{t['id']}-pantalla", 'ifc': 'IfcAudioVisualAppliance', 'type': 'DISPLAY',
                      'material': t['screen_material'], 'mesh': screen, 'source': t['size_source']})
    if spec.get('dining'):
        parts += dining_parts(spec['dining'])
    return parts


def _chair(frame, u, n, facing, c):
    """Silla en (u, n) del marco de la mesa, mirando hacia `facing` (vector unitario en ese marco)."""
    sw, sd = c['seat_m']
    h, top = c['seat_height_m'], c['back_height_m']
    fu, fn = facing
    pu, pn = -fn, fu  # a lo ancho de la silla
    def box(a0, a1, d0, d1, z0, z1):  # a: a lo ancho, d: hacia el frente de la silla (desde el respaldo)
        corners = [(u + pu * a + fu * dd, n + pn * a + fn * dd) for a in (a0, a1) for dd in (d0, d1)]
        us, ns = [p[0] for p in corners], [p[1] for p in corners]
        return frame.box((min(us), max(us)), (z0, z1), (min(ns), max(ns)))
    wood = [box(-sw / 2 + k * (sw - 0.045), -sw / 2 + k * (sw - 0.045) + 0.045, d, d + 0.045, 0, h - 0.06)
            for k in (0, 1) for d in (-sd / 2, sd / 2 - 0.045)]
    wood.append(box(-sw / 2, sw / 2, -sd / 2, sd / 2, h - 0.06, h - 0.03))  # bastidor del asiento
    for a in (-sw / 2, sw / 2 - 0.045):  # postes del respaldo
        wood.append(box(a, a + 0.045, -sd / 2, -sd / 2 + 0.045, h - 0.03, top))
    wood.append(box(-sw / 2, sw / 2, -sd / 2, -sd / 2 + 0.05, top - 0.09, top))  # travesaño de arriba
    wood.append(box(-0.06, 0.06, -sd / 2 + 0.01, -sd / 2 + 0.035, h, top - 0.09))  # tablilla
    seat = box(-sw / 2 + 0.01, sw / 2 - 0.01, -sd / 2 + 0.05, sd / 2 - 0.01, h - 0.03, h + 0.03)
    return wood, seat


def dining_parts(d):
    """Mesa rectangular con 2 pedestales y 6 sillas (2 por lado y las cabeceras)."""
    (cx, cy), (ax, ay) = d['centre'], d['long_axis']
    length, width = d['size_m']
    frame = _Run({'origin': [cx, cy], 'along': [ax, ay], 'into_room': [-ay, ax]})
    t, c = d['table'], d['chairs']
    h = t['height_m']
    table = [frame.box((-length / 2, length / 2), (h - t['top_m'], h), (-width / 2, width / 2)),
             frame.box((-length / 2 + 0.06, length / 2 - 0.06), (h - t['top_m'] - t['apron_m'], h - t['top_m']),
                       (-width / 2 + 0.06, width / 2 - 0.06))]
    pw, pd = t['pedestal_size_m']
    for k in range(t['pedestals']):
        u = -length / 2 + length * (k + 1) / (t['pedestals'] + 1)
        table.append(frame.box((u - pw / 2, u + pw / 2), (0.05, h - t['top_m'] - t['apron_m']), (-pw / 2, pw / 2)))
        table.append(frame.box((u - 0.08, u + 0.08), (0, 0.05), (-pd / 2, pd / 2)))  # pie
    woods, seats = [], []
    out = c['seat_m'][1] / 2 - c['tuck_m']  # el asiento entra un poco bajo la mesa
    places = [(-length / 2 + length * (k + 1) / (c['count_per_side'] + 1), side * (width / 2 + out), (0, -side))
              for k in range(c['count_per_side']) for side in (1, -1)]
    if c['heads']:
        places += [(side * (length / 2 + out), 0.0, (-side, 0)) for side in (1, -1)]
    for u, n, facing in places:
        w, s = _chair(frame, u, n, facing, c)
        woods += w
        seats.append(s)
    src = f"{d['size_source']}; {d['position_source']}"
    return [{'id': f"{d['id']}-mesa", 'ifc': 'IfcFurniture', 'type': 'TABLE', 'material': t['material'], 'mesh': merge(table), 'source': src},
            {'id': f"{d['id']}-sillas", 'ifc': 'IfcFurniture', 'type': 'CHAIR', 'material': c['material'], 'mesh': merge(woods), 'source': c['source']},
            {'id': f"{d['id']}-asientos", 'ifc': 'IfcFurniture', 'type': 'CHAIR', 'material': c['seat_material'], 'mesh': merge(seats), 'source': c['source']}]
