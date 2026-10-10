"""Lavandería: lavadora, secadora, boiler, cilindro de gas, repisa y placas, descritos en
`sources/lavanderia/lavanderia.json`. Arma las mallas en coordenadas del mundo con el mismo formato de piezas que
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


def laundry_parts(spec: dict, plate: dict | None = None) -> list[dict]:
    xw, parts = spec['back_wall_x'], []
    w = spec['washer']
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
                  'source': g['source']})
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
    for p in parts:
        p.setdefault('space', spec['applies_to']['space'])
    return parts
