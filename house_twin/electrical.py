"""Contactos y apagadores: el plano da dónde (`devices` de los hechos, sobre la cara del muro) y
`sources/electrico/placas.json` cómo son y a qué altura. Aquí se arma la malla en coordenadas del mundo;
`ifc_export` la guarda como IfcOutlet o IfcSwitchingDevice. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import merge, oriented_box

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / 'sources' / 'electrico' / 'placas.json'


def load_device_spec(path: Path = SPEC_PATH) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def device_height(spec: dict, device: dict) -> tuple[float, str]:
    """Altura del centro: la del hecho si el dueño la dio; si no, la de la especificación (con su fuente)."""
    if device['height']['value'] is not None:
        return device['height']['value'], device['height']['source']
    kind = spec['switch' if device['kind'] == 'switch' else 'outlet']
    return kind['height_m'], kind['height_source']


def device_mesh(spec: dict, device: dict):
    """Placa (y módulos del contacto) sobre la cara del muro, mirando al cuarto."""
    nx, ny = device['faces_toward']
    along = (-ny, nx)
    z, _ = device_height(spec, device)
    x, y = device['position']
    plate = spec['plate']
    w, h, t = plate['width'], plate['height'], plate['thickness']
    parts = [oriented_box((x, y, z), along, (nx, ny), (-w / 2, w / 2), (-h / 2, h / 2), (0, t))]
    if device['kind'] == 'outlet':
        m = spec['outlet']['module']
        for dz in (-m['spacing'] / 2, m['spacing'] / 2):
            parts.append(oriented_box((x, y, z), along, (nx, ny), (-m['width'] / 2, m['width'] / 2),
                                      (dz - m['height'] / 2, dz + m['height'] / 2), (t, t + m['depth'])))
    return merge(parts)
