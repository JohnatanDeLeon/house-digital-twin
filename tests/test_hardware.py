import json
from pathlib import Path

import pytest

from house_twin.hardware import knob_mesh, lathe, load_hardware, placements

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / 'sources' / 'herrajes' / 'perilla-laton.json').read_text())


def _volume(points, faces):
    """Volumen con signo de una malla cerrada: positivo si las normales miran hacia afuera."""
    total = 0.0
    for f in faces:
        a = points[f[0]]
        for b, c in zip((points[i] for i in f[1:-1]), (points[i] for i in f[2:])):
            total += a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
    return total / 6


def test_lathe_is_closed_and_faces_outward():
    points, faces = lathe([(0, 0), (0.03, 0), (0.03, 0.01), (0, 0.01)], 64)  # disco: un cilindro chato
    assert _volume(points, faces) == pytest.approx(3.14159 * 0.03 ** 2 * 0.01, rel=0.01)


def _door(normal_y):
    """Puerta en un muro horizontal (eje X), con la bisagra a la derecha y el cuarto del lado de `normal_y`."""
    room = {'id': 'R', 'polygon': [[0, 0], [2, 0], [2, 2 * normal_y], [0, 2 * normal_y]]}
    return {'swing': {'latch_end': [0.2, 0.0], 'hinge_end': [1.0, 0.0], 'opens_into': 'R'}}, [room]


@pytest.mark.parametrize('side', [1, -1])
def test_knobs_go_on_both_faces_with_the_button_inside_the_room(side):
    door, spaces = _door(side)
    places = placements(SPEC, door, 2.0, 0.05, spaces)
    assert len(places) == 2 and sum(p['button'] for p in places) == 1
    inside = next(p for p in places if p['button'])
    assert inside['normal'][1] == side                               # el botón mira hacia el cuarto
    assert inside['origin'][0] == pytest.approx(0.2 + 0.072 * 0.8)  # a la entrada medida desde el canto de la chapa
    assert inside['origin'][2] == pytest.approx((1 - 0.485) * 2.0)
    for p in places:  # cada perilla, con o sin espejo, cerrada y con las normales hacia afuera
        points, faces = knob_mesh(SPEC, [p])
        local = [(x - p['origin'][0], y - p['origin'][1], z - p['origin'][2]) for x, y, z in points]
        assert _volume(local, faces) > 0


def test_repo_hardware_goes_on_the_wooden_doors():
    assert [h['applies_to']['leaf_material'] for h in load_hardware()] == ['puerta-recamaras']


def test_plan_door_blocks_give_each_door_its_swing(dxf_facts):
    doors = {o['id']: o for o in dxf_facts['openings'] if o['kind'] == 'door' and o['host_wall']}
    assert all('swing' in d for d in doors.values())  # los 9 bloques PUERTA del CAD, uno por puerta
    names = {s['id']: s['name'] for s in dxf_facts['spaces']}
    wooden = json.loads((ROOT / 'sources' / 'texturas' / 'puerta-recamaras.json').read_text())['applies_to']['openings']
    assert {names[doors[d]['swing']['opens_into']] for d in wooden} <= {'Recámara 1', 'Recámara 2', 'Recámara 3', 'Baño', '1/2 Baño'}


def test_ifc_carries_the_knobs_as_door_parts(dxf_facts):
    import ifcopenshell.util.element as ue
    import ifcopenshell.validate
    from house_twin.finishes import Finishes, load_materials
    from house_twin.ifc_export import build_ifc
    model = build_ifc(dxf_facts, Finishes(dxf_facts, load_materials(ROOT / 'assets' / 'textures')), load_hardware())
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    knobs = model.by_type('IfcDiscreteAccessory')
    assert len(knobs) == 5 and all(ue.get_aggregate(k).is_a('IfcDoor') for k in knobs)
    assert {ue.get_material(k).Name for k in knobs} == {'laton-envejecido'}
