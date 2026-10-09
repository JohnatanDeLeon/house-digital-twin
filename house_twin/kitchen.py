"""Cocineta: muebles bajos y altos, cubiertas, tarja, estufa y refrigerador, descritos en
`sources/cocina/cocineta.json` por tramos de muro. Aquí se arman las mallas en coordenadas del mundo, una por pieza
con su material; `ifc_export` las guarda como IfcFurniture, IfcElectricAppliance, IfcSanitaryTerminal e IfcValve.
Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import cylinder, merge, oriented_box

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / 'sources' / 'cocina' / 'cocineta.json'


def load_kitchen(path: Path = SPEC_PATH) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


class _Run:
    """Marco de un tramo: `u` a lo largo del muro desde la esquina, `n` del muro hacia el cuarto, `z` arriba."""

    def __init__(self, run):
        self.origin = (*run['origin'], 0.0)
        self.along, self.normal = tuple(run['along']), tuple(run['into_room'])

    def box(self, u, z, n):
        return oriented_box(self.origin, self.along, self.normal, tuple(u), tuple(z), tuple(n))

    def point(self, u, n, z):
        (ox, oy, _), (ax, ay), (nx, ny) = self.origin, self.along, self.normal
        return (ox + ax * u + nx * n, oy + ay * u + ny * n, z)


def _handle(spec, frame, u, z, n0, vertical):
    """Jaladera de barra con 2 postes, centrada en (u, z), saliendo del frente en `n0`."""
    h = spec['handle']
    half, out = h['length_m'] / 2, n0 + h['standoff_m']
    a, b = ((u, z - half), (u, z + half)) if vertical else ((u - half, z), (u + half, z))
    parts = [cylinder(frame.point(a[0], out, a[1]), frame.point(b[0], out, b[1]), h['radius_m'], 12)]
    for pu, pz in (a, b):
        parts.append(cylinder(frame.point(pu, n0, pz), frame.point(pu, out, pz), h['post_radius_m'], 8))
    return merge(parts)


def kitchen_parts(spec: dict) -> list[dict]:
    """Piezas de la cocineta: id, clase IFC, tipo, material y malla (puntos, caras)."""
    m, gap, t = spec['materials'], spec['gap_m'], spec['front_thickness_m']
    parts = []
    for run in spec['runs']:
        frame, rid = _Run(run), run['id']
        handles = []
        base = run.get('base')
        if base:
            depth = base['depth_m']
            for i, module in enumerate(base['modules']):
                pieces = [frame.box(module['u'], (base['plinth_m'], base['top_m']), (0, depth))]
                for front in module['fronts']:
                    (u0, u1), (z0, z1) = front['u'], front['z']
                    pieces.append(frame.box((u0 + gap / 2, u1 - gap / 2), (z0 + gap / 2, z1 - gap / 2), (depth, depth + t)))
                    if front['kind'] == 'door':
                        u = u1 - 0.04 if front['handle'] == 'right' else u0 + 0.04
                        handles.append(_handle(spec, frame, u, z1 - 0.11, depth + t, True))
                    elif front['kind'] == 'drawer':
                        handles.append(_handle(spec, frame, (u0 + u1) / 2, (z0 + z1) / 2, depth + t, False))
                parts.append({'id': f'cocina-{rid}-bajo-{i + 1}', 'ifc': 'IfcFurniture', 'type': 'USERDEFINED',
                              'material': m['body'], 'mesh': merge(pieces)})
            span = (min(mod['u'][0] for mod in base['modules']), max(mod['u'][1] for mod in base['modules']))
            plinths = [frame.box(mod['u'], (0, base['plinth_m']), (0, depth + t - base['plinth_setback_m'])) for mod in base['modules']]
            parts.append({'id': f'cocina-{rid}-zoclo', 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'material': m['plinth'],
                          'mesh': merge(plinths), 'span': span})
        c = run.get('counter')
        for i, counter in enumerate(run.get('counters', [])):
            pieces = [frame.box(counter['u'], c['z'], (0, c['depth_m']))]
            bh, bt = c['backsplash_m']
            if bh:
                pieces.append(frame.box(counter['u'], (c['z'][1], c['z'][1] + bh), (0, bt)))
            parts.append({'id': f'cocina-{rid}-cubierta-{i + 1}', 'ifc': 'IfcFurniture', 'type': 'USERDEFINED',
                          'material': m['counter'], 'mesh': merge(pieces)})
        sink = run.get('sink')
        if sink:
            w, d = sink['size_m']
            top = c['z'][1]
            u0, n0 = sink['u_centre'] - w / 2, sink['from_wall_m']
            parts.append({'id': f'cocina-{rid}-tarja', 'ifc': 'IfcSanitaryTerminal', 'type': 'SINK', 'material': 'granito-negro',
                          'mesh': frame.box((u0, u0 + w), (top, top + 0.004), (n0, n0 + d))})
            f = sink['faucet']
            base_pt = frame.point(sink['u_centre'], f['from_wall_m'], top)
            up = frame.point(sink['u_centre'], f['from_wall_m'], top + f['height_m'])
            out = frame.point(sink['u_centre'], f['from_wall_m'] + f['reach_m'], top + f['height_m'] - 0.03)
            spout = frame.point(sink['u_centre'], f['from_wall_m'] + f['reach_m'], top + f['height_m'] - 0.12)
            parts.append({'id': f'cocina-{rid}-llave', 'ifc': 'IfcValve', 'type': 'FAUCET', 'material': 'acero-negro',
                          'mesh': merge([cylinder(base_pt, up, f['radius_m'], 12), cylinder(up, out, f['radius_m'], 12),
                                         cylinder(out, spout, f['radius_m'] * 1.3, 12)])})
        uppers = run.get('uppers')
        if uppers:
            depth = uppers['depth_m']
            for i, module in enumerate(uppers['modules']):
                (u0, u1), (z0, z1) = module['u'], module['z']
                pieces = [frame.box((u0, u1), (z0, z1), (0, depth - t))]
                width = (u1 - u0) / module['doors']
                for k in range(module['doors']):
                    a, b = u0 + k * width, u0 + (k + 1) * width
                    pieces.append(frame.box((a + gap / 2, b - gap / 2), (z0 + gap / 2, z1 - gap / 2), (depth - t, depth)))
                    u = b - 0.04 if k == 0 and module['doors'] > 1 else a + 0.04
                    handles.append(_handle(spec, frame, u, z0 + 0.11, depth, True))
                parts.append({'id': f'cocina-{rid}-alto-{i + 1}', 'ifc': 'IfcFurniture', 'type': 'USERDEFINED',
                              'material': m['body'], 'mesh': merge(pieces)})
        for appliance in run.get('appliances', []):
            u0, u1 = appliance['u']
            d, h = appliance['depth_m'], appliance['height_m']
            if appliance['kind'] == 'stove':
                pieces = [frame.box((u0, u1), (0.02, h), (0, d)),
                          frame.box((u0 + 0.03, u1 - 0.03), (h, h + appliance['grates_m']), (0.08, d - 0.06))]
                for k in range(7):  # perillas al frente
                    uk = u0 + 0.1 + k * (u1 - u0 - 0.2) / 6
                    pieces.append(cylinder(frame.point(uk, d, h - 0.06), frame.point(uk, d + 0.03, h - 0.06), 0.02, 12))
                for uk in (u0 + 0.04, u1 - 0.04):  # patas
                    pieces.append(frame.box((uk - 0.03, uk + 0.03), (0, 0.02), (d - 0.08, d - 0.02)))
            else:
                pieces = [frame.box((u0, u1), (0, h * 0.72 - 0.004), (0, d)), frame.box((u0, u1), (h * 0.72 + 0.004, h), (0, d)),
                          frame.box((u0 + 0.01, u1 - 0.01), (h * 0.72 - 0.004, h * 0.72 + 0.004), (0, d - 0.01))]
            parts.append({'id': f"cocina-{appliance['id']}", 'ifc': 'IfcElectricAppliance',
                          'type': 'REFRIGERATOR' if appliance['kind'] == 'fridge' else 'USERDEFINED',
                          'object_type': None if appliance['kind'] == 'fridge' else 'estufa de gas',
                          'material': appliance['material'], 'mesh': merge(pieces), 'source': appliance['source']})
        if handles:
            parts.append({'id': f'cocina-{rid}-jaladeras', 'ifc': 'IfcDiscreteAccessory', 'type': None,
                          'material': m['handles'], 'mesh': merge(handles)})
    return parts
