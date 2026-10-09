"""Variantes: propuestas sobre la casa existente (`variants/<id>.json`).

Una variante nunca toca los hechos ni `models/existing.*`: describe cambios por encima. Por ahora, cambios de
acabado de un vano (`changes`: `opening`, `part`, `material`). El IFC de cada variante va en
`models/variants/<id>.ifc` y el recorrido las ofrece en un selector junto a la casa actual.
"""
import copy
import json
from pathlib import Path

from house_twin.finishes import Finishes

ROOT = Path(__file__).resolve().parent.parent
VARIANTS_DIR = ROOT / 'variants'
PARTS = ('leaf', 'frame', 'glass')


def load_variants(folder: Path = VARIANTS_DIR) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))]


def validate(variant: dict, facts: dict, materials: dict[str, dict]) -> list[str]:
    """Problemas que impiden aplicar la variante: vano o material inexistente, parte desconocida."""
    openings = {o['id'] for o in facts['openings']}
    problems = []
    for c in variant['changes']:
        if c['opening'] not in openings:
            problems.append(f"{variant['id']}: no existe el vano {c['opening']}")
        if c['part'] not in PARTS:
            problems.append(f"{variant['id']}: parte desconocida {c['part']}")
        if c['material'] not in materials:
            problems.append(f"{variant['id']}: no existe el material {c['material']}")
    return problems


def apply_variant(finishes: Finishes, variant: dict, materials: dict[str, dict]) -> Finishes:
    """Los acabados de la casa con los cambios de la variante encima; los de la casa no se tocan."""
    result = copy.deepcopy(finishes)
    for c in variant['changes']:
        parts = result.openings.setdefault(c['opening'], {})
        parts[c['part']] = c['material']
        glass = materials[c['material']].get('glass_material')
        if c['part'] == 'leaf' and glass:
            parts['glass'] = glass
    return result


def opening_overrides(variant: dict) -> dict[str, str]:
    """Vano → material de su hoja en la variante (lo que el recorrido cambia al elegirla)."""
    return {c['opening']: c['material'] for c in variant['changes'] if c['part'] == 'leaf'}
