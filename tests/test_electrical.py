from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon

from house_twin.electrical import device_height, device_mesh, load_device_spec
from tests.test_hardware import _volume

ROOT = Path(__file__).resolve().parent.parent


def test_plan_gives_outlets_and_switches_on_a_wall_face(dxf_facts):
    devices = dxf_facts['devices']
    assert sum(d['kind'] == 'outlet' for d in devices) == 12 and sum(d['kind'] == 'switch' for d in devices) == 8
    spaces = {s['id']: Polygon(s['polygon']) for s in dxf_facts['spaces']}
    for d in devices:
        room = spaces[d['space']]
        assert room.exterior.distance(Point(d['position'])) < 1e-3  # sobre la cara del muro
        nx, ny = d['faces_toward']
        assert room.contains(Point(d['position'][0] + nx * 0.05, d['position'][1] + ny * 0.05))  # mira al cuarto
        assert d['from_plan_m'] < 0.15 and d['height']['value'] is None


def test_device_heights_and_meshes(dxf_facts):
    spec = load_device_spec()
    switch = next(d for d in dxf_facts['devices'] if d['kind'] == 'switch')
    outlet = next(d for d in dxf_facts['devices'] if d['kind'] == 'outlet')
    assert device_height(spec, switch)[0] == pytest.approx(1.22)
    assert device_height(spec, outlet)[0] == pytest.approx(0.30)
    for d in (switch, outlet):
        points, faces = device_mesh(spec, d)
        assert _volume(points, faces) > 0
    assert len(device_mesh(spec, outlet)[1]) == 18  # placa y dos módulos


def test_ifc_has_outlets_and_switches(dxf_facts):
    import ifcopenshell.util.element as ue
    import ifcopenshell.validate
    from house_twin.finishes import Finishes, load_materials
    from house_twin.ifc_export import build_ifc
    model = build_ifc(dxf_facts, Finishes(dxf_facts, load_materials(ROOT / 'assets' / 'textures')), devices=load_device_spec())
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    assert len(model.by_type('IfcOutlet')) == 12 and len(model.by_type('IfcSwitchingDevice')) == 8
    assert {ue.get_material(e).Name for e in model.by_type('IfcOutlet') + model.by_type('IfcSwitchingDevice')} == {'placa-negra'}
