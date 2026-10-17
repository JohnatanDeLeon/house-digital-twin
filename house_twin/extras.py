"""Piezas sueltas de una propuesta, como cajas en coordenadas del mundo (`x`, `y`, `z` en metros): el remate del
pretil de una fachada, el costado de un nicho. `ifc_export` las guarda con su clase (por omisión IfcMember).
Solo biblioteca estándar.
"""
from house_twin.hardware import _box


def box_part(b: dict, ifc: str = 'IfcMember') -> dict:
    (x0, x1), (y0, y1), (z0, z1) = b['x'], b['y'], b['z']
    return {'id': b['id'], 'ifc': b.get('ifc', ifc), 'type': 'USERDEFINED', 'object_type': b.get('object_type', 'pieza'),
            'material': b['material'], 'mesh': _box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0)),
            'source': b['source']}


def extras_parts(spec: dict) -> list[dict]:
    """Las cajas de `boxes`, cada una en el espacio que declara la especificación."""
    parts = [box_part(b) for b in spec.get('boxes', [])]
    for p in parts:
        p.setdefault('space', spec['applies_to']['space'])
    return parts
