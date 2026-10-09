import json
from pathlib import Path

import pytest

from house_twin.furniture import closet_meshes, front_frame, load_furniture
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
    spec = load_furniture()[0]
    fixture = next(c for c in dxf_facts['fixtures'] if c['space'] == spec['applies_to']['space'])
    (body, body_faces), (handles, handle_faces) = closet_meshes(fixture, spec, 2.6)
    leaves = len(spec['modules']) * len(spec['sections']) * spec['leaves_per_section']
    assert len(body_faces) == 6 * (1 + leaves)  # el cuerpo y una caja por hoja
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
    closets = model.by_type('IfcFurniture')
    assert len(closets) == 1  # solo el de la recámara 3 tiene especificación de su frente
    parts = ue.get_parts(closets[0])
    assert [ue.get_material(p).Name for p in parts] == ['acero-inoxidable']
