"""Herrajes: piezas chicas de las puertas (chapas) que no caben en una textura y van como objetos 3D.

Cada herraje se describe en `sources/herrajes/<nombre>.json`: a qué hojas va (`applies_to.leaf_material`), dónde
(fracciones de la hoja, como en la foto de su textura), su perfil torneado y su material. Aquí se calcula la
malla en coordenadas del mundo; `ifc_export` la guarda como `IfcDiscreteAccessory`, parte de su puerta.
Solo biblioteca estándar, como `finishes.py`.
"""
import json
import math
from pathlib import Path

from house_twin.finishes import _inside

ROOT = Path(__file__).resolve().parent.parent
HARDWARE_DIR = ROOT / 'sources' / 'herrajes'
SIDE_PROBE_M = 0.3  # más que medio muro: el punto cae en el espacio de ese lado de la puerta


def load_hardware(folder: Path = HARDWARE_DIR) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))]


def for_leaf(hardware: list[dict], leaf_material: str | None) -> list[dict]:
    return [h for h in hardware if leaf_material and h['applies_to'].get('leaf_material') == leaf_material]


def lathe(profile: list[tuple[float, float]], segments: int):
    """Sólido de revolución alrededor de +Z: `profile` va de (0, 0) en la cara de la hoja hasta la punta en el eje.

    Devuelve puntos locales y caras (índices desde 0) con las normales hacia afuera.
    """
    points, rings = [], []
    for r, z in profile:
        if r == 0:
            rings.append([len(points)])
            points.append((0.0, 0.0, z))
            continue
        start = len(points)
        points += [(r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments), z) for k in range(segments)]
        rings.append(list(range(start, start + segments)))
    faces = []
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        for k in range(segments):
            k1 = (k + 1) % segments
            if len(a) == 1:
                faces.append([a[0], b[k1], b[k]])
            elif len(b) == 1:
                faces.append([a[k], a[k1], b[0]])
            else:
                faces.append([a[k], a[k1], b[k1], b[k]])
    return points, faces


def _box(center, size):
    (cx, cy, cz), (sx, sy, sz) = center, (size[0] / 2, size[1] / 2, size[2] / 2)
    points = [(cx + dx * sx, cy + dy * sy, cz + dz * sz) for dz in (-1, 1) for dy in (-1, 1) for dx in (-1, 1)]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    return points, faces


def placements(spec: dict, door: dict, height: float, thickness: float, spaces: list[dict]) -> list[dict]:
    """Una perilla de cada lado de la hoja: centro en la cara, normal hacia afuera y si lleva el botón de seguro."""
    swing = door['swing']
    (lx, ly), (hx, hy) = swing['latch_end'], swing['hinge_end']
    length = math.hypot(hx - lx, hy - ly)
    along = ((hx - lx) / length, (hy - ly) / length)  # del canto de la chapa hacia la bisagra
    normal = (-along[1], along[0])
    pos = spec['position']
    cx, cy = lx + along[0] * pos['from_latch_frac'] * length, ly + along[1] * pos['from_latch_frac'] * length
    z = (1 - pos['from_top_frac']) * height
    by_id = {s['id']: s for s in spaces}
    room = by_id.get(swing.get('opens_into'))
    result = []
    for side in (1, -1):
        n = (normal[0] * side, normal[1] * side)
        probe = (cx + n[0] * SIDE_PROBE_M, cy + n[1] * SIDE_PROBE_M)
        result.append({'origin': (cx + n[0] * thickness / 2, cy + n[1] * thickness / 2, z), 'normal': n, 'along': along,
                       'button': room is not None and _inside(probe, room['polygon'])})
    return result


def knob_mesh(spec: dict, places: list[dict]):
    """Malla de las perillas en coordenadas del mundo: X local a lo largo de la hoja, Y arriba, Z hacia afuera."""
    profile = [(r / 1000, z / 1000) for r, z in spec['profile_mm']]
    knob, knob_faces = lathe(profile, spec['segments'])
    tip = max(z for _, z in profile)
    points, faces = [], []
    for p in places:
        parts = [(knob, knob_faces)]
        if p['button'] and 'turn_button' in spec:
            w, h, d = (v / 1000 for v in spec['turn_button']['size_mm'])
            parts.append(_box((0.0, 0.0, tip + d / 2 - 0.002), (w, h, d)))  # asoma del hueco de la perilla
        (ox, oy, oz), (nx, ny), (ax, ay) = p['origin'], p['normal'], p['along']
        if ay * nx - ax * ny < 0:  # el triedro (a lo largo, arriba, normal) debe ser derecho: si no, las caras se invierten
            ax, ay = -ax, -ay
        for local, local_faces in parts:
            base = len(points)
            points += [(ox + x * ax + z * nx, oy + x * ay + z * ny, oz + y) for x, y, z in local]
            faces += [[base + i for i in f] for f in local_faces]
    return points, faces


def oriented_box(origin, along, normal, u, z, n):
    """Caja en un marco (a lo largo, arriba, normal): `u`, `z` y `n` son intervalos (inicio, fin) en metros."""
    (ox, oy, oz), (ax, ay), (nx, ny) = origin, along, normal
    corners = [(uu, zz, nn) for nn in n for zz in z for uu in u]
    points = [(ox + uu * ax + nn * nx, oy + uu * ay + nn * ny, oz + zz) for uu, zz, nn in corners]
    faces = [[0, 2, 3, 1], [4, 5, 7, 6], [0, 1, 5, 4], [2, 6, 7, 3], [0, 4, 6, 2], [1, 3, 7, 5]]
    if ay * nx - ax * ny < 0:  # triedro izquierdo: se invierte el orden para que las normales sigan hacia afuera
        faces = [f[::-1] for f in faces]
    return points, faces


def cylinder(p0, p1, radius: float, segments: int):
    """Cilindro cerrado de `p0` a `p1` (puntos 3D), con las normales hacia afuera."""
    axis = [b - a for a, b in zip(p0, p1)]
    length = math.sqrt(sum(c * c for c in axis))
    w = [c / length for c in axis]
    helper = (0.0, 0.0, 1.0) if abs(w[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = [helper[1] * w[2] - helper[2] * w[1], helper[2] * w[0] - helper[0] * w[2], helper[0] * w[1] - helper[1] * w[0]]
    norm = math.sqrt(sum(c * c for c in u))
    u = [c / norm for c in u]
    v = [w[1] * u[2] - w[2] * u[1], w[2] * u[0] - w[0] * u[2], w[0] * u[1] - w[1] * u[0]]  # (u, v, w) derecho
    local, faces = lathe([(0, 0), (radius, 0), (radius, length), (0, length)], segments)
    points = [tuple(p0[i] + x * u[i] + y * v[i] + z * w[i] for i in range(3)) for x, y, z in local]
    return points, faces


def merge(parts):
    """Junta varias mallas (puntos, caras) en una sola."""
    points, faces = [], []
    for p, f in parts:
        base = len(points)
        points += list(p)
        faces += [[base + i for i in face] for face in f]
    return points, faces
