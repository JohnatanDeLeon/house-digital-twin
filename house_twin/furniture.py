"""Muebles empotrados (closets): el plano da dónde están (`fixtures` de los hechos) y `sources/muebles/` cómo es
su frente (módulos, hojas, jaladeras), medido en una foto. Aquí se arma la malla en coordenadas del mundo;
`ifc_export` la guarda como IfcFurniture con sus jaladeras (IfcDiscreteAccessory). Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import cylinder, merge, oriented_box

ROOT = Path(__file__).resolve().parent.parent
FURNITURE_DIR = ROOT / 'sources' / 'muebles'
HANDLE_SEGMENTS = 16


def load_furniture(folder: Path = FURNITURE_DIR) -> list[dict]:
    """Especificaciones de muebles; `based_on` toma otra como base y la pisa con lo que declara."""
    specs = {p.stem: json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))}
    resolved = []
    for spec in specs.values():
        base = specs[spec['based_on']] if 'based_on' in spec else {}
        base = {k: v for k, v in base.items() if k != 'interior'}  # el interior es de cada closet, no se hereda
        resolved.append({**base, **spec})
    return resolved


def module_fracs(spec: dict, width: float) -> list[list[float]]:
    """Módulos en fracciones del frente: medidos (lista) o repartidos iguales entre orillas y postes."""
    modules = spec['modules']
    if isinstance(modules, list):
        return modules
    n, margin, post = modules['count'], modules['margin_m'], modules['post_m']
    each = (width - 2 * margin - (n - 1) * post) / n
    return [[(margin + i * (each + post)) / width, (margin + i * (each + post) + each) / width] for i in range(n)]


def front_frame(fixture: dict):
    """Origen (extremo izquierdo visto desde el cuarto), dirección a lo ancho y normal hacia el cuarto."""
    nx, ny = fixture['faces_toward']
    along = (-ny, nx)  # derecha de quien mira el frente
    a, b = fixture['front']
    left = min((a, b), key=lambda p: p[0] * along[0] + p[1] * along[1])
    return (left[0], left[1], 0.0), along, (nx, ny)


def closet_meshes(fixture: dict, spec: dict, height: float):
    """(cuerpo y hojas, jaladeras): dos mallas, porque llevan materiales distintos."""
    origin, along, normal = front_frame(fixture)
    width, depth = fixture['width'], fixture['depth']
    gap, leaf = spec['gap_mm'] / 1000, spec['leaf_thickness_mm'] / 1000
    z_of = lambda frac_from_top: (1 - frac_from_top) * height
    box = lambda u, z, n: oriented_box(origin, along, normal, u, z, n)
    interior = 'interior' in spec  # con interior, el cuerpo y las hojas de abajo los arma closet_interior
    parts = [] if interior else [box((0, width), (0, height), (-depth, -leaf))]  # cuerpo: del muro hasta atrás de las hojas
    handles = []
    h = spec['handles']
    r, length, standoff = h['diameter_mm'] / 2000, h['length_mm'] / 1000, h['standoff_mm'] / 1000
    for m0, m1 in module_fracs(spec, width):
        u0, u1 = m0 * width, m1 * width
        meeting = (u0 + u1) / 2
        for section, (t0, t1) in spec['sections'].items():
            if interior and section == 'lower':
                continue
            z0, z1 = z_of(t1) + gap / 2, z_of(t0) - gap / 2
            for a, b, side in ((u0 + gap / 2, meeting - gap / 2, -1), (meeting + gap / 2, u1 - gap / 2, 1)):
                parts.append(box((a, b), (z0, z1), (-leaf, 0)))
                hu = meeting + side * h['from_meeting_mm'] / 1000
                hz = z_of(h['center_from_top_frac'][section])
                at = lambda u, z, n: (origin[0] + u * along[0] + n * normal[0], origin[1] + u * along[1] + n * normal[1], z)
                handles.append(cylinder(at(hu, hz - length / 2, standoff), at(hu, hz + length / 2, standoff), r, HANDLE_SEGMENTS))
                for leg in (hz - length / 2 + h['leg_inset_mm'] / 1000, hz + length / 2 - h['leg_inset_mm'] / 1000):
                    handles.append(cylinder(at(hu, leg, 0), at(hu, leg, standoff), r * 0.8, HANDLE_SEGMENTS))
    return merge(parts), merge(handles)
