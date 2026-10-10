"""Luminarias del techo: el plano dice dónde están las salidas (`lights` de los hechos) y `sources/luminarias/` cómo
es lo que cuelga (portalámparas y foco, torneados) y qué luz da. Aquí se arma la malla en coordenadas del mundo;
`ifc_export` la guarda como IfcLightFixture con su foco. Solo biblioteca estándar.
"""
import json
from pathlib import Path

from house_twin.hardware import lathe

ROOT = Path(__file__).resolve().parent.parent
LUMINAIRES_DIR = ROOT / 'sources' / 'luminarias'


def load_luminaires(folder: Path = LUMINAIRES_DIR) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))]


def _hanging(profile_mm, segments, x, y, ceiling):
    """Torneado que cuelga del techo: la Z local crece hacia abajo, así que el espejo invierte el orden de las caras."""
    local, faces = lathe([(r / 1000, z / 1000) for r, z in profile_mm], segments)
    return [(x + lx, y + ly, ceiling - lz) for lx, ly, lz in local], [f[::-1] for f in faces]


def luminaire_meshes(spec: dict, position, ceiling: float):
    """(portalámparas, foco, centro de la luz) de una salida en `position` (x, y) con el techo a `ceiling` m."""
    x, y = position
    socket = _hanging(spec['socket_profile_mm'], spec['segments'], x, y, ceiling)
    bulb = _hanging(spec['bulb_profile_mm'], spec['segments'], x, y, ceiling)
    return socket, bulb, (x, y, ceiling - spec['light']['center_mm'] / 1000)
