"""Llaves y regadera: el área de la regadera sale de los hechos (`fixtures` de tipo `shower`) y
`sources/sanitarios/regadera.json` dice cómo son las piezas y dónde van en el muro. Aquí se arma la malla en
coordenadas del mundo; `ifc_export` la guarda como IfcValve e IfcSanitaryTerminal. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import cylinder, lathe, merge, oriented_box

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / 'sources' / 'sanitarios' / 'regadera.json'


def load_shower_spec(path: Path = SPEC_PATH) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _on_wall(spec, along_m, height_m, out_m=0.0):
    (cx, cy), (ax, ay), (nx, ny) = spec['mount']['corner'], spec['mount']['along'], spec['mount']['into_room']
    return (cx + ax * along_m + nx * out_m, cy + ay * along_m + ny * out_m, height_m)


def valve_meshes(spec: dict) -> list:
    """Una malla por llave: perfil torneado con su eje hacia el cuarto, normales hacia afuera."""
    v = spec['valves']
    local, faces = lathe([(r / 1000, z / 1000) for r, z in v['profile_mm']], v['segments'])
    (ax, ay), (nx, ny) = spec['mount']['along'], spec['mount']['into_room']
    if ay * nx - ax * ny < 0:  # el triedro (a lo largo, arriba, hacia el cuarto) debe ser derecho
        ax, ay = -ax, -ay
    meshes = []
    for offset in (-v['spacing_m'] / 2, v['spacing_m'] / 2):
        ox, oy, oz = _on_wall(spec, v['centre_from_corner_m'] + offset, v['height_m'])
        meshes.append(([(ox + x * ax + z * nx, oy + x * ay + z * ny, oz + y) for x, y, z in local], faces))
    return meshes


def shower_mesh(spec: dict):
    """Brazo que sale del muro, codo hacia abajo y regadera cuadrada."""
    s = spec['shower']
    along = spec['valves']['centre_from_corner_m']
    start = _on_wall(spec, along, s['outlet_height_m'])
    elbow = _on_wall(spec, along, s['outlet_height_m'], s['arm_length_m'])
    end = (elbow[0], elbow[1], elbow[2] - s['drop_m'])
    w, d, t = s['head_size_m']
    head = oriented_box(end, spec['mount']['along'], spec['mount']['into_room'], (-w / 2, w / 2), (-t, 0), (-d / 2, d / 2))
    return merge([cylinder(start, elbow, s['pipe_radius_m'], s['segments']),
                  cylinder(elbow, end, s['pipe_radius_m'], s['segments']), head])


SANITARY_DIR = ROOT / 'sources' / 'sanitarios'


def load_sanitary_specs(folder: Path = SANITARY_DIR) -> list[dict]:
    """Una especificación de muebles por baño (`muebles-*.json`): cada una dice a qué espacios aplica."""
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('muebles-*.json'))]


def spec_for(specs: list[dict], space_id: str) -> dict | None:
    return next((s for s in specs if space_id in s['applies_to']['spaces']), None)


def material_of(spec: dict, kind: str) -> str:
    """El material de la pieza si lo declara (un baño puede tener inodoro blanco y lavabo beige); si no, el común."""
    return spec[kind].get('material') or spec['material']


def _frame(fixture):
    """Marco del mueble: `x` a lo ancho, `y` del muro hacia el cuarto, `z` arriba (triedro derecho)."""
    fx, fy = fixture['facing']
    return fixture['back_centre'], (fy, -fx), (fx, fy)


def _to_world(fixture, points):
    (ox, oy), (ax, ay), (fx, fy) = _frame(fixture)
    return [(ox + x * ax + y * fx, oy + x * ay + y * fy, z) for x, y, z in points]


def _oval(part):
    """Sólido torneado y vuelto óvalo (radio x, radio y), centrado en `centre_y`."""
    points, faces = lathe(part['profile'], part['segments'])
    rx, ry = part['radius']
    return [(x * rx, part['centre_y'] + y * ry, z) for x, y, z in points], faces


def _box(b):
    return oriented_box((0.0, 0.0, 0.0), (1.0, 0.0), (0.0, 1.0), b['x'], b['z'], b['y'])


def sanitary_mesh(spec: dict, fixture: dict):
    """Malla de porcelana del inodoro o del lavabo, en coordenadas del mundo."""
    if fixture['kind'] == 'toilet':
        t = spec['toilet']
        parts = [_oval(t['bowl']), _oval(t['seat']), _box(t['tank']), _box(t['tank_lid']), _box(t['neck'])]
    else:
        b = spec['basin']
        parts = [_oval(b['pedestal']), _oval(b['bowl'])]
    points, faces = merge(parts)
    return _to_world(fixture, points), faces


def lever_mesh(spec: dict, fixture: dict):
    """Palanca del tanque del inodoro, si la especificación la trae."""
    lever = spec['toilet'].get('lever')
    if lever is None:
        return None
    points, faces = _box(lever)
    return _to_world(fixture, points), faces


def faucet_mesh(spec: dict, fixture: dict):
    """Mezcladora del lavabo: base, cuello y 2 manijas."""
    f = spec['basin']['faucet']
    h = f['handles']
    parts = [_box(f['base']), cylinder(*f['spout'], f['spout_radius'], 16)]
    parts += [cylinder((x, h['y'], h['z'][0]), (x, h['y'], h['z'][1]), h['radius'], 16) for x in h['x']]
    points, faces = merge(parts)
    return _to_world(fixture, points), faces
