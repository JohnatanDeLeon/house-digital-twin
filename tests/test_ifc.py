import pytest
import ifcopenshell.validate

from house_twin.ifc_export import build_ifc


def test_ifc_is_schema_valid_and_complete(facts):
    model = build_ifc(facts)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    assert len(model.by_type('IfcWall')) == len(facts['walls'])
    # 9 puertas del plano + 2 de herrería del dueño; 9 ventanas del plano + la del tragaluz (estimada con fotos)
    assert len(model.by_type('IfcDoor')) == 12 and len(model.by_type('IfcWindow')) == 12
    # la herrería va entre dos muros, sin hueco que cortar
    assert len(model.by_type('IfcRelVoidsElement')) == 21 and len(model.by_type('IfcRelFillsElement')) == 21
    assert len(model.by_type('IfcSpace')) == len(facts['spaces'])


def test_ifc_flags_assumed_heights(facts):
    import ifcopenshell.util.element as ue
    model = build_ifc(facts)
    wall = model.by_type('IfcWall')[0]
    assert ue.get_psets(wall)['HDT_Provenance']['HeightAssumed'] is True


def test_ifc_uses_owner_door_height(facts):
    import ifcopenshell.util.element as ue
    model = build_ifc(facts)
    door = next(d for d in model.by_type('IfcDoor') if d.Name == 'D02')
    assert door.OverallHeight == 2.10
    assert ue.get_psets(door)['HDT_Provenance']['HeightAssumed'] is False


def test_ifc_length_unit_is_metre(facts):
    import ifcopenshell.util.unit as uu
    model = build_ifc(facts)
    assert uu.calculate_unit_scale(model) == 1.0


def test_ifc_guids_are_stable_and_unique(facts):
    first, second = build_ifc(facts), build_ifc(facts)
    guids = lambda m: {e.GlobalId: (e.is_a(), e.Name) for e in m.by_type('IfcRoot')}
    assert guids(first) == guids(second)
    assert len(guids(first)) == len(first.by_type('IfcRoot'))
    wall = lambda m: next(w for w in m.by_type('IfcWall') if w.Name == 'W01')
    assert wall(first).GlobalId == wall(second).GlobalId


def test_opening_void_grows_across_a_diagonal_wall():
    from house_twin.ifc_export import _grown
    rect = [(0.0, 0.0), (1.0, -1.0), (1.1, -0.9), (0.1, 0.1)]  # vano a 45°: 1.41 m de largo, 0.14 m de espesor
    grown = _grown(rect, 0.01)
    side = lambda p, q: ((q[0]-p[0])**2 + (q[1]-p[1])**2) ** 0.5
    assert side(grown[0], grown[1]) == pytest.approx(side(rect[0], rect[1]) + 0.02)
    assert side(grown[0], grown[3]) == pytest.approx(side(rect[0], rect[3]) + 0.02)  # sale del espesor del muro
