from pathlib import Path

from house_twin.finishes import Finishes
from house_twin.variants import apply_variant, load_variants, validate

ROOT = Path(__file__).resolve().parent.parent


def _finishes():
    facts = {'site': {'polygon': [[0, 0], [0, 5], [6, 5], [6, 0]]}, 'spaces': []}
    materials = {'puerta-vieja': {'applies_to': {'openings': ['D03']}, 'glass_material': 'vidrio-a'},
                 'puerta-nueva': {'applies_to': {'variant': 'v'}, 'glass_material': 'vidrio-b'}}
    return Finishes(facts, materials), materials


def test_variant_changes_finishes_on_top_without_touching_the_house():
    finishes, materials = _finishes()
    variant = {'id': 'v', 'changes': [{'opening': 'D03', 'part': 'leaf', 'material': 'puerta-nueva'}]}
    proposal = apply_variant(finishes, variant, materials)
    assert proposal.opening('D03') == {'leaf': 'puerta-nueva', 'glass': 'vidrio-b'}
    assert finishes.opening('D03') == {'leaf': 'puerta-vieja', 'glass': 'vidrio-a'}  # la casa actual sigue igual


def test_variant_material_is_not_used_by_the_existing_house():
    finishes, _ = _finishes()
    assert 'puerta-nueva' not in {m for parts in finishes.openings.values() for m in parts.values()}


def test_invalid_variants_are_reported():
    _, materials = _finishes()
    facts = {'openings': [{'id': 'D03'}]}
    variant = {'id': 'v', 'changes': [{'opening': 'D99', 'part': 'hoja', 'material': 'no-existe'}]}
    assert len(validate(variant, facts, materials)) == 3


def test_repo_variants_are_valid(dxf_facts):
    from house_twin.finishes import load_materials
    materials = load_materials(ROOT / 'assets' / 'textures')
    variants = load_variants()
    assert all(not validate(v, dxf_facts, materials) for v in variants)  # puede no haber ninguna
