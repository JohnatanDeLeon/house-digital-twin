import json
from pathlib import Path

import pytest

from house_twin.furniture import closet_meshes, front_frame, load_furniture, module_fracs
from house_twin.hardware import cylinder, oriented_box
from tests.test_hardware import _volume

ROOT = Path(__file__).resolve().parent.parent


def test_plan_closets_run_from_their_front_line_to_the_wall(dxf_facts):
    closets = {c['space']: c for c in dxf_facts['fixtures'] if c['kind'] == 'closet'}
    assert len(closets) == 3  # las tres recámaras tienen rótulo CLOSET y frente dibujado
    r3 = closets[next(s['id'] for s in dxf_facts['spaces'] if s['name'] == 'Recámara 3')]
    assert r3['width'] == pytest.approx(2.68, abs=0.01) and r3['depth'] == pytest.approx(0.60, abs=0.01)
    assert r3['faces_toward'] == [1.0, 0.0] or r3['faces_toward'] == [1.0, -0.0]  # el frente mira a la recámara


@pytest.mark.parametrize('along,normal', [((1, 0), (0, 1)), ((1, 0), (0, -1)), ((0, 1), (1, 0))])
def test_primitives_face_outward(along, normal):
    points, faces = oriented_box((0, 0, 0), along, normal, (0, 1), (0, 2), (-0.5, 0))
    assert _volume(points, faces) == pytest.approx(1.0)
    points, faces = cylinder((0, 0, 0), (0.1, 0.2, 0.3), 0.01, 32)
    assert _volume(points, faces) > 0


def test_closet_front_follows_its_spec(dxf_facts):
    spec = next(f for f in load_furniture() if f['name'] == 'closet-recamara-3')
    fixture = next(c for c in dxf_facts['fixtures'] if c['space'] == spec['applies_to']['space'])
    (body, body_faces), (handles, handle_faces) = closet_meshes(fixture, spec, 2.6)
    upper = len(module_fracs(spec, fixture['width'])) * spec['leaves_per_section']
    assert len(body_faces) == 6 * upper  # con interior: solo las hojas de arriba (el cuerpo y las de abajo van aparte)
    origin, along, normal = front_frame(fixture)
    out = [(x - origin[0]) * normal[0] + (y - origin[1]) * normal[1] for x, y, _ in handles]
    assert min(out) == pytest.approx(0, abs=1e-6) and max(out) == pytest.approx(0.032 + 0.006, abs=1e-3)  # salen de las hojas
    assert all(z >= 0 and z <= 2.6 for _, _, z in body)


def test_ifc_carries_the_closet_with_its_handles(dxf_facts):
    import ifcopenshell.util.element as ue
    import ifcopenshell.validate
    from house_twin.finishes import Finishes, load_materials
    from house_twin.hardware import load_hardware
    from house_twin.ifc_export import build_ifc
    model = build_ifc(dxf_facts, Finishes(dxf_facts, load_materials(ROOT / 'assets' / 'textures')), load_hardware(), load_furniture())
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    closets = [f for f in model.by_type('IfcFurniture') if f.Name in ('F02-closet', 'F03-closet')]
    assert len(closets) == 2  # R2 y R3; el de R1 no tiene puertas ni especificación
    for closet in closets:
        assert [ue.get_material(p).Name for p in ue.get_parts(closet)] == ['acero-inoxidable']


def test_bedroom_2_closet_is_bedroom_3_with_four_equal_modules():
    specs = {f['name']: f for f in load_furniture()}
    r2, r3 = specs['closet-recamara-2'], specs['closet-recamara-3']
    assert r2['sections'] == r3['sections'] and r2['handles'] == r3['handles']  # sale de la base
    modules = module_fracs(r2, 2.91)
    widths = [(b - a) * 2.91 for a, b in modules]
    assert len(modules) == 4 and max(widths) - min(widths) < 1e-9 and widths[0] == pytest.approx(0.669, abs=0.002)
    assert modules[0][0] * 2.91 == pytest.approx(0.016) and (1 - modules[-1][1]) * 2.91 == pytest.approx(0.016)


def test_closet_r3_interior_is_hollow_and_leaves_open():
    import json
    from house_twin.closet_interior import interior_parts, leaf_parts
    from house_twin.furniture import closet_meshes, load_furniture
    from tests.test_kitchen import _signed_volume
    facts = json.loads(open('data/facts/existing.facts.json').read())
    fx = next(x for x in facts['fixtures'] if x['id'] == 'F03')
    spec = next(s for s in load_furniture() if s['applies_to']['space'] == 'S04')
    body, _ = closet_meshes(fx, spec, 2.6)
    assert min(p[2] for p in body[0]) > 1.9  # el cuerpo de abajo ya no es un bloque: solo quedan las hojas de arriba
    parts = interior_parts(fx, spec, 2.6)
    assert all(_signed_volume(*p['mesh']) > 0 for p in parts)
    leaves, doors = leaf_parts(fx, spec, 2.6)
    assert len(doors) == 3 and all(len(d['leaves']) == 2 for d in doors)
    assert sum(1 for p in leaves if p['ifc'] == 'IfcFurniture') == 6


def test_closet_r3_only_hangs_the_venom_tee_and_it_fits():
    import json
    from house_twin.closet_interior import display_parts, interior_parts
    from house_twin.furniture import load_furniture
    facts = json.loads(open('data/facts/existing.facts.json').read())
    fx = next(x for x in facts['fixtures'] if x['id'] == 'F03')
    spec = next(s for s in load_furniture() if s['applies_to']['space'] == 'S04')
    assert not any(m.startswith(('F03-interior-ropa', 'F03-interior-piel')) for m in (p['id'] for p in interior_parts(fx, spec, 2.6)))
    parts, items = display_parts(fx, spec)
    assert [i['label'] for i in items] == ['la playera de Venom']
    tee = next(p for p in parts if p['id'] == 'F03-playera-venom')
    xs = [q[0] for q in tee['mesh'][0]]
    assert 5.79 <= min(xs) and max(xs) <= 6.374  # cabe entre el muro y las hojas


def test_closet_r3_tee_hangs_edge_on_and_pressed_to_the_depth():
    import json
    from house_twin.closet_interior import display_parts
    from house_twin.furniture import load_furniture
    facts = json.loads(open('data/facts/existing.facts.json').read())
    fx = next(x for x in facts['fixtures'] if x['id'] == 'F03')
    spec = next(s for s in load_furniture() if s['applies_to']['space'] == 'S04')
    parts, [item] = display_parts(fx, spec)
    assert abs(item['facing'][0]) < 1e-6 and abs(abs(item['facing'][1]) - 1) < 1e-6  # mira a lo ancho del closet: de canto
    assert item['relaxed_width_m'] == 0.6512 and item['size_m'][0] < item['relaxed_width_m']  # apretada en el closet
    xs = [q[0] for p in parts if p['id'] in ('F03-playera-venom', 'F03-playera-venom-espalda') for q in p['mesh'][0]]
    assert abs(max(xs) - 6.364) < 1e-6 and min(xs) > 5.79  # 1 cm libre de las hojas, sin entrar al fondo
