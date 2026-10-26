"""Variantes: propuestas sobre la casa existente (`variants/<id>.json`).

Una variante nunca toca los hechos ni `models/existing.*`: describe cambios por encima.

- `changes`: acabados de un vano (`opening`, `part`, `material`).
- `geometry` (remodelaciones): vanos que se tapian (`close_openings`), muros y vanos nuevos (`add_walls`,
  `add_openings`) y datos que cambian en vanos, espacios y placas (`update_openings`, `update_spaces`,
  `update_devices`, que se mezclan sobre el dato por su `id`) y zonas de acabado que se mueven con la obra
  (`update_materials`: `name` y su nueva `region_m`, p. ej. el azulejo de una cocina reubicada). `variant_facts` aplica todo sobre una copia de los
  hechos: esos son los hechos *propuestos*, con los que se arma el IFC de la variante.
- `specs`: especificaciones propias de la variante (`kitchen`, `laundry`, `bedroom`: la recámara que reemplaza a la de su mismo espacio), en `variants/<id>/`, que reemplazan a las
  de `sources/` solo en la propuesta; `extras` agrega piezas sueltas (cajas, `house_twin/extras.py`).
- Acabados propios: un material con `applies_to.variant` y `variant_applies_to` (espacios, `calle`, franjas, zonas)
  solo cubre muros o pisos en esa propuesta; con `replaces` le quita esos espacios a los acabados de la casa. Una
  variante que solo cambia acabados de muros declara `own_model` para tener su propio modelo 3D.

El IFC de cada variante va en `models/variants/<id>.ifc` y el recorrido las ofrece en un selector junto a la casa
actual; una variante con geometría lleva además su propio modelo 3D.
"""
import copy
import json
from pathlib import Path

from house_twin.finishes import Finishes

ROOT = Path(__file__).resolve().parent.parent
VARIANTS_DIR = ROOT / 'variants'
PARTS = ('leaf', 'frame', 'glass')
SPEC_KINDS = ('kitchen', 'laundry', 'extras', 'bedroom')


def load_variants(folder: Path = VARIANTS_DIR) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(folder).glob('*.json'))]


def has_geometry(variant: dict) -> bool:
    """¿Necesita su propio modelo 3D? Sí si cambia geometría, muebles o acabados de muros y pisos (`own_model`); los
    cambios de hoja de un vano se aplican sobre el modelo de la casa."""
    return bool(variant.get('geometry')) or bool(variant.get('specs')) or bool(variant.get('own_model'))


def _merge_by_id(items: list[dict], updates: list[dict], what: str) -> list[str]:
    by_id = {item['id']: item for item in items}
    missing = []
    for update in updates:
        if update['id'] not in by_id:
            missing.append(f"no existe {what} {update['id']}")
            continue
        by_id[update['id']].update(update)
    return missing


def _apply_geometry(facts: dict, geometry: dict) -> list[str]:
    """Aplica la geometría de una variante sobre `facts` (ya copiado) y devuelve lo que no se pudo aplicar."""
    if not geometry:
        return []
    problems = []
    closed = set(geometry.get('close_openings', []))
    problems += [f'no existe el vano {o}' for o in closed - {o['id'] for o in facts['openings']}]
    facts['openings'] = [o for o in facts['openings'] if o['id'] not in closed]
    facts['walls'] = facts.get('walls', []) + copy.deepcopy(geometry.get('add_walls', []))
    facts['openings'] += copy.deepcopy(geometry.get('add_openings', []))
    walls = {w['id'] for w in facts['walls']}
    problems += [f"el vano {o['id']} va en un muro que no existe ({o['host_wall']})"
                 for o in geometry.get('add_openings', []) if o.get('host_wall') not in walls]
    problems += _merge_by_id(facts['openings'], geometry.get('update_openings', []), 'el vano')
    problems += _merge_by_id(facts['spaces'], geometry.get('update_spaces', []), 'el espacio')
    problems += _merge_by_id(facts['devices'], geometry.get('update_devices', []), 'la placa')
    return problems


def variant_facts(facts: dict, variant: dict) -> dict:
    """Hechos propuestos: los de la casa con la geometría de la variante encima. Los de la casa no se tocan."""
    result = copy.deepcopy(facts)
    problems = _apply_geometry(result, variant.get('geometry', {}))
    if problems:
        raise ValueError(f"{variant['id']}: " + '; '.join(problems))
    result['name'] = f"{facts['name']} — propuesta: {variant['name']}"
    result['provenance'] = {**facts['provenance'], 'variant': variant['id'], 'variant_kind': variant.get('kind')}
    return result


def variant_materials(materials: dict[str, dict], variant: dict) -> dict[str, dict]:
    """Los materiales con las zonas de acabado que la variante mueve y los acabados propios de la variante en muros o
    pisos (`variant_applies_to` de un material con `applies_to.variant`, que la casa existente no toma); los de la
    casa no se tocan."""
    updates = variant.get('update_materials', [])
    own = [n for n, m in materials.items()
           if m.get('variant_applies_to') and m['applies_to'].get('variant') == variant['id']]
    if not updates and not own:
        return materials
    result = copy.deepcopy(materials)
    for name in own:
        own_to = dict(result[name]['variant_applies_to'])
        for replaced in own_to.pop('replaces', []):  # acabados de la casa que la propuesta sustituye en sus espacios
            a = result[replaced]['applies_to']
            a['spaces'] = [s for s in a.get('spaces', []) if s not in own_to.get('spaces', [])]
            if own_to.get('street_facade'):
                a.pop('street_facade', None)
        result[name]['applies_to'] = {**result[name]['applies_to'], **own_to}
    for update in updates:
        result[update['name']]['applies_to']['region_m'] = update['region_m']
    return result


def variant_specs(variant: dict, defaults: dict, root: Path = ROOT) -> dict:
    """Las especificaciones de la casa (`defaults`, por tipo) con las que la variante reemplaza."""
    specs = dict(defaults)
    for kind, path in variant.get('specs', {}).items():
        specs[kind] = json.loads((root / path).read_text())
    return specs


def variant_bedrooms(variant: dict, bedrooms: list[dict], root: Path = ROOT) -> list[dict]:
    """Las recámaras de la casa; la que la variante declara en `specs.bedroom` reemplaza a la de su mismo espacio."""
    path = variant.get('specs', {}).get('bedroom')
    if not path:
        return bedrooms
    new = json.loads((root / path).read_text())
    return [new if b['applies_to']['space'] == new['applies_to']['space'] else b for b in bedrooms]


def validate(variant: dict, facts: dict, materials: dict[str, dict]) -> list[str]:
    """Problemas que impiden aplicar la variante: geometría que no cuadra con los hechos, vano o material
    inexistente, parte desconocida, especificación que no existe."""
    proposed = copy.deepcopy(facts)
    problems = [f"{variant['id']}: {p}" for p in _apply_geometry(proposed, variant.get('geometry', {}))]
    problems += [f"{variant['id']}: tipo de especificación desconocido {k}" for k in variant.get('specs', {}) if k not in SPEC_KINDS]
    problems += [f"{variant['id']}: no existe {p}" for p in variant.get('specs', {}).values() if not (ROOT / p).exists()]
    problems += [f"{variant['id']}: no existe el material {u['name']}" for u in variant.get('update_materials', [])
                 if u['name'] not in materials]
    openings = {o['id'] for o in proposed['openings']}
    for c in variant.get('changes', []):
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
    for c in variant.get('changes', []):
        parts = result.openings.setdefault(c['opening'], {})
        parts[c['part']] = c['material']
        glass = materials[c['material']].get('glass_material')
        if c['part'] == 'leaf' and glass:
            parts['glass'] = glass
    return result


def opening_overrides(variant: dict) -> dict[str, str]:
    """Vano → material de su hoja en la variante (lo que el recorrido cambia al elegirla). Una variante con geometría
    ya trae sus acabados en su propio modelo: no cambia nada sobre el de la casa."""
    if has_geometry(variant):
        return {}
    return {c['opening']: c['material'] for c in variant.get('changes', []) if c['part'] == 'leaf'}
