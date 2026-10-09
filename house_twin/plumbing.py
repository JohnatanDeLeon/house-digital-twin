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
