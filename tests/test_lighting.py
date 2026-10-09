from pathlib import Path

import pytest

from house_twin.lighting import load_luminaires, luminaire_meshes
from tests.test_hardware import _volume

ROOT = Path(__file__).resolve().parent.parent


def test_plan_gives_nine_ceiling_lights_in_their_rooms(dxf_facts):
    names = {s['id']: s['name'] for s in dxf_facts['spaces']}
    lights = dxf_facts['lights']
    assert len(lights) == 9
    rooms = [names[l['space']] for l in lights]
    assert rooms.count('Cocina + Sala + Comedor') == 4  # 2 en la sala, la cocina y el pasillo de recámaras
    assert {'Recámara 1', 'Recámara 2', 'Recámara 3', 'Baño', '1/2 Baño'} <= set(rooms)


def test_interior_spaces_are_roofed_by_the_owner(dxf_facts):
    for s in dxf_facts['spaces']:
        if not s['is_exterior']:
            assert s['roofed']['value'] is (s['name'] != 'Tragaluz')  # el tragaluz está abierto al cielo


def test_luminaire_hangs_from_the_ceiling_and_faces_outward():
    spec = load_luminaires()[0]
    (sp, sf), (bp, bf), centre = luminaire_meshes(spec, (1.0, 2.0), 2.59)
    for points, faces in ((sp, sf), (bp, bf)):
        local = [(x - 1.0, y - 2.0, z - 2.5) for x, y, z in points]
        assert _volume(local, faces) > 0
    assert max(z for _, _, z in sp) == pytest.approx(2.59)  # el portalámparas está pegado al techo
    assert max(z for _, _, z in bp) < 2.59                   # y el foco cuelga de él
    assert min(z for _, _, z in bp) < centre[2] < max(z for _, _, z in bp)  # la luz está dentro del foco


def test_ifc_has_roof_ceilings_and_lights(dxf_facts):
    import ifcopenshell.util.element as ue
    import ifcopenshell.validate
    from house_twin.finishes import Finishes, load_materials
    from house_twin.ifc_export import build_ifc
    model = build_ifc(dxf_facts, Finishes(dxf_facts, load_materials(ROOT / 'assets' / 'textures')), luminaires=load_luminaires())
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    slab = model.by_type('IfcSlab')
    assert len(slab) == 1 and ue.get_pset(slab[0], 'HDT_Provenance')['ThicknessAssumed'] is True
    fixtures = model.by_type('IfcLightFixture')
    assert len(fixtures) == 9
    assert all(ue.get_pset(f, 'HDT_Light')['ColorTemperature'] == 6500 for f in fixtures)
    assert {ue.get_material(p).Name for f in fixtures for p in ue.get_parts(f)} == {'foco-led'}
