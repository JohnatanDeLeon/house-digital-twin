"""Lavandería: lavadora y secadora (o una lavasecadora, `combo`), boiler (o calentador de paso, `heater`), cilindro
de gas, repisa y placas, descritos en `sources/lavanderia/lavanderia.json`. Una propuesta puede agregar lavadero
(`sink`), cubierta (`counter`), gabinete alto (`cabinet`), tendedero (`line`) y techo (`roof`). Arma las mallas en coordenadas del mundo con el mismo formato de piezas que
la cocineta; `ifc_export` las guarda. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.electrical import device_mesh
from house_twin.hardware import _box, cylinder, merge

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / 'sources' / 'lavanderia' / 'lavanderia.json'


def load_laundry(path: Path = SPEC_PATH) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _against_back(x_wall, depth, y, z):
    """Caja contra el muro del fondo (x = x_wall), de `depth` hacia el cuarto (−x)."""
    (y0, y1), (z0, z1) = y, z
    return _box(((2 * x_wall - depth) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (depth, y1 - y0, z1 - z0))


def _washer_dryer_parts(xw, spec):
    """Lavadora de 2 tinas (tapa arriba) y secadora, lado a lado contra el muro del fondo."""
    w, parts = spec['washer'], []
    body = _against_back(xw, w['depth_m'], w['y'], (0.0, w['body_m'] - 0.02))
    lid = merge([_against_back(xw, w['depth_m'] - 0.02, (w['y'][0] + 0.01, w['y'][1] - 0.01), (w['body_m'] - 0.02, w['body_m'])),
                 _against_back(xw, 0.08, w['y'], (w['body_m'], w['panel_m']))])
    src = f"{w['size_source']}; {w['position_source']}; {w['height_source']}"
    parts += [{'id': w['id'], 'ifc': 'IfcElectricAppliance', 'type': 'WASHINGMACHINE', 'material': w['materials']['body'], 'mesh': body, 'source': src},
              {'id': f"{w['id']}-tapa", 'ifc': 'IfcElectricAppliance', 'type': 'WASHINGMACHINE', 'material': w['materials']['lid'], 'mesh': lid, 'source': src}]
    d = spec['dryer']
    dryer = merge([_against_back(xw, d['depth_m'], d['y'], (0.0, d['body_m'])),
                   _against_back(xw, 0.12, (d['y'][0] + 0.02, d['y'][1] - 0.02), (d['body_m'], d['console_m']))])
    parts.append({'id': d['id'], 'ifc': 'IfcElectricAppliance', 'type': 'TUMBLEDRYER', 'material': d['material'], 'mesh': dryer,
                  'source': f"{d['size_source']}; {d['position_source']}; {d['height_source']}"})
    return parts


def _combo_parts(xw, c):
    """Lavasecadora de carga frontal: gabinete separado del muro (mangueras), puerta redonda con aro y tablero arriba."""
    back = xw - c['rear_gap_m']
    front = back - c['depth_m']
    (y0, y1), h = c['y'], c['height_m']
    yc, door = (y0 + y1) / 2, c['door']
    src = f"{c['size_source']}; {c['position_source']}"
    glass = cylinder((front, yc, door['z']), (front - door['thickness_m'], yc, door['z']), door['diameter_m'] / 2, 32)
    ring = cylinder((front, yc, door['z']), (front - door['thickness_m'] / 2, yc, door['z']), door['diameter_m'] / 2 + door['ring_m'], 32)
    (pw, ph) = c['panel_m']
    panel = _box((front - 0.003, yc, h - 0.04 - ph / 2), (0.006, pw, ph))
    kind = {'ifc': 'IfcElectricAppliance', 'type': 'USERDEFINED', 'object_type': 'lavasecadora', 'source': src}
    return [{'id': c['id'], 'material': c['materials']['body'], 'mesh': _against_back(back, c['depth_m'], c['y'], (0.0, h)), **kind},
            {'id': f"{c['id']}-aro", 'material': c['materials']['ring'], 'mesh': ring, **kind},
            {'id': f"{c['id']}-puerta", 'material': c['materials']['door'], 'mesh': glass, **kind},
            {'id': f"{c['id']}-tablero", 'material': c['materials']['panel'], 'mesh': panel, **kind}]


def _sink_parts(xw, k):
    """Lavadero: pedestal, pila abierta arriba (orilla de `rim_m`) y llave que sale del muro."""
    (y0, y1), d, top, bottom, rim = k['y'], k['depth_m'], k['top_m'], k['basin_floor_m'], k['rim_m']
    x0 = xw - d
    basin = [_against_back(xw, d, (y0, y1), (0.0, bottom)),
             _against_back(x0 + rim, rim, (y0, y1), (bottom, top)),  # frente
             _against_back(xw, rim, (y0, y1), (bottom, top)),  # contra el muro
             _against_back(xw - rim, d - 2 * rim, (y0, y0 + rim), (bottom, top)),
             _against_back(xw - rim, d - 2 * rim, (y1 - rim, y1), (bottom, top))]
    f, yc = k['faucet'], (y0 + y1) / 2
    faucet = merge([cylinder((xw, yc, f['z']), (xw - f['reach_m'], yc, f['z']), f['radius_m'], 12),
                    cylinder((xw - f['reach_m'], yc, f['z']), (xw - f['reach_m'], yc, f['z'] - 0.08), f['radius_m'], 12)])
    return [{'id': k['id'], 'ifc': 'IfcSanitaryTerminal', 'type': 'SINK', 'material': k['material'], 'mesh': merge(basin),
             'source': k['source']},
            {'id': f"{k['id']}-llave", 'ifc': 'IfcValve', 'type': 'FAUCET', 'material': f['material'], 'mesh': faucet,
             'source': k['source']}]


def _cabinet_parts(xw, c):
    """Gabinete alto: cuerpo, 2 puertas (rendija al centro) y una jaladera vertical en cada una."""
    (y0, y1), d, h = c['y'], c['depth_m'], c['height_m']
    yc, front = (y0 + y1) / 2, xw - d
    doors = [_box((front - 0.01, (a + b) / 2, h / 2 + 0.05), (0.02, b - a, h - 0.12)) for a, b in ((y0 + 0.003, yc - 0.002), (yc + 0.002, y1 - 0.003))]
    handles = [cylinder((front - 0.045, yy, 1.0), (front - 0.045, yy, 1.25), 0.008, 10) for yy in (yc - 0.04, yc + 0.04)]
    return [{'id': c['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'gabinete alto', 'material': c['material'],
             'mesh': merge([_against_back(xw, d - 0.02, (y0, y1), (0.0, h))] + doors), 'source': c['source']},
            {'id': f"{c['id']}-jaladeras", 'ifc': 'IfcDiscreteAccessory', 'type': None, 'material': c['handle_material'],
             'mesh': merge(handles), 'source': c['source']}]


def _heater_parts(xw, h):
    """Calentador de paso colgado del muro, con su chimenea hasta arriba del techo."""
    (y0, y1), (z0, z1), d = h['y'], h['z'], h['depth_m']
    yc, f = (y0 + y1) / 2, h['flue']
    flue = cylinder((xw - d / 2, yc, z1), (xw - d / 2, yc, f['top_m']), f['diameter_m'] / 2, 16)
    return [{'id': h['id'], 'ifc': 'IfcFlowStorageDevice', 'type': 'USERDEFINED', 'object_type': 'calentador de paso',
             'material': h['material'], 'mesh': merge([_against_back(xw, d, (y0, y1), (z0, z1)), flue]), 'source': h['source']}]


def _line_parts(xw, t):
    """Tendedero retráctil: caja en el muro del pasillo (`from_x`) e hilos tendidos hasta el muro del fondo."""
    x0, y, z = t['from_x'], t['y'], t['z']
    box = _box((x0 + 0.04, y, z), (0.08, 0.3, 0.1))
    lines = [cylinder((x0 + 0.08, y + dy, z), (xw, y + dy, z), 0.003, 6) for dy in (-0.1, 0.0, 0.1)]
    return [{'id': t['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'tendedero', 'material': t['material'],
             'mesh': merge([box] + lines), 'source': t['source']}]


def _roof_parts(r):
    """Techo inclinado: lámina (sube de `x[0]` a `x[1]`) sobre 4 postes y 2 largueros, con la ventila abierta abajo."""
    (x0, x1), (y0, y1), (zlo, zhi), wall, t = r['x'], r['y'], r['z'], r['wall_top_m'], r['thickness_m']
    slope = (zhi - zlo) / (x1 - x0)
    points, faces = _box(((x0 + x1) / 2, (y0 + y1) / 2, zlo + t / 2), (x1 - x0, y1 - y0, t))
    sheet = ([(x, y, z + (x - x0) * slope) for x, y, z in points], faces)
    p = r['post_m']
    frame = [_box((x, y, (wall + zlo + (x - x0) * slope) / 2), (p, p, zlo + (x - x0) * slope - wall))
             for x in (x0 + p / 2, x1 - p / 2) for y in (y0 + p / 2, y1 - p / 2)]
    for x in (x0 + p / 2, x1 - p / 2):
        z = zlo + (x - x0) * slope - p / 2
        frame.append(_box((x, (y0 + y1) / 2, z), (p, y1 - y0, p)))
    return [{'id': r['id'], 'ifc': 'IfcPlate', 'type': 'USERDEFINED', 'object_type': 'lámina de techo', 'material': r['material'],
             'mesh': sheet, 'source': r['source']},
            {'id': f"{r['id']}-estructura", 'ifc': 'IfcMember', 'type': 'USERDEFINED', 'object_type': 'estructura del techo',
             'material': r['frame_material'], 'mesh': merge(frame), 'source': r['source']}]


def laundry_parts(spec: dict, plate: dict | None = None) -> list[dict]:
    xw, parts = spec['back_wall_x'], []
    if 'combo' in spec:
        parts += _combo_parts(xw, spec['combo'])
    if 'washer' in spec:
        parts += _washer_dryer_parts(xw, spec)
    if 'boiler' in spec:
        b = spec['boiler']
        (cx, cy), r, z0 = b['centre'], b['diameter_m'] / 2, b['stand_m']
        sw, sd = b['stand_size_m']
        stand = [_box((cx + dx * (sw / 2 - 0.015), cy + dy * (sd / 2 - 0.015), z0 / 2), (0.03, 0.03, z0)) for dx in (-1, 1) for dy in (-1, 1)]
        stand.append(_box((cx, cy, z0 - 0.015), (sw, sd, 0.03)))
        tank = merge([cylinder((cx, cy, z0), (cx, cy, z0 + b['height_m']), r, 24),
                      cylinder((cx, cy, z0 + b['height_m']), (cx, cy, z0 + b['height_m'] + b['flue_m']), 0.05, 12)])
        bsrc = f"{b['size_source']}; {b['position_source']}"
        parts += [{'id': b['id'], 'ifc': 'IfcFlowStorageDevice', 'type': 'USERDEFINED', 'object_type': 'calentador de agua (boiler)',
                   'material': b['material'], 'mesh': tank, 'source': bsrc},
                  {'id': f"{b['id']}-base", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'base del boiler',
                   'material': b['stand_material'], 'mesh': merge(stand), 'source': bsrc}]
    g = spec['gas']
    (gx, gy), gr = g['centre'], g['diameter_m'] / 2
    parts.append({'id': g['id'], 'ifc': 'IfcFlowStorageDevice', 'type': 'USERDEFINED', 'object_type': 'cilindro de gas',
                  'material': g['material'], 'mesh': merge([cylinder((gx, gy, 0.0), (gx, gy, g['height_m'] - 0.1), gr, 20),
                                                            cylinder((gx, gy, g['height_m'] - 0.1), (gx, gy, g['height_m']), gr * 0.45, 16)]),
                  'source': g['source'], **({'space': g['space']} if 'space' in g else {})})  # puede quedar fuera (pasillo)
    s = spec['shelf']
    (x0, x1), y, z, t = s['x'], s['y_wall'], s['z'], s['thickness_m']
    shelf = [_box(((x0 + x1) / 2, y + s['depth_m'] / 2, z + t / 2), (x1 - x0, s['depth_m'], t))]
    shelf += [_box((xb, y + 0.01, z - 0.1), (0.03, 0.02, 0.2)) for xb in (x0 + 0.15, x1 - 0.15)]  # ménsulas
    parts.append({'id': s['id'], 'ifc': 'IfcFurniture', 'type': 'SHELF', 'material': s['material'], 'mesh': merge(shelf), 'source': s['source']})
    if plate:
        for dv in spec['devices']:
            device = {'kind': dv['kind'], 'position': [xw, dv['y']], 'faces_toward': [-1.0, 0.0],
                      'height': {'value': dv['z'], 'source': spec['devices_source']}}
            parts.append({'id': dv['id'], 'ifc': 'IfcOutlet' if dv['kind'] == 'outlet' else 'IfcSwitchingDevice',
                          'type': 'POWEROUTLET' if dv['kind'] == 'outlet' else 'TOGGLESWITCH', 'material': 'placa-beige',
                          'mesh': device_mesh(plate, device), 'source': spec['devices_source']})
    parts += _sink_parts(xw, spec['sink']) if 'sink' in spec else []
    parts += _cabinet_parts(xw, spec['cabinet']) if 'cabinet' in spec else []
    parts += _heater_parts(xw, spec['heater']) if 'heater' in spec else []
    parts += _line_parts(xw, spec['line']) if 'line' in spec else []
    parts += _roof_parts(spec['roof']) if 'roof' in spec else []
    if 'counter' in spec:
        c = spec['counter']
        parts.append({'id': c['id'], 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'cubierta', 'material': c['material'],
                      'mesh': _against_back(xw, c['depth_m'], c['y'], c['z']), 'source': c['source']})
    for p in parts:
        p.setdefault('space', spec['applies_to']['space'])
    return parts
