import ifcopenshell.validate

from house_twin.ifc_export import build_ifc


def test_ifc_is_schema_valid_and_complete(facts):
    model = build_ifc(facts)
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    assert len(model.by_type('IfcWall')) == len(facts['walls'])
    assert len(model.by_type('IfcDoor')) == 9 and len(model.by_type('IfcWindow')) == 9  # la del tragaluz no tiene medidas
    assert len(model.by_type('IfcRelVoidsElement')) == 18 and len(model.by_type('IfcRelFillsElement')) == 18
    assert len(model.by_type('IfcSpace')) == len(facts['spaces'])


def test_ifc_flags_assumed_heights(facts):
    import ifcopenshell.util.element as ue
    model = build_ifc(facts)
    wall = model.by_type('IfcWall')[0]
    assert ue.get_psets(wall)['HDT_Provenance']['HeightAssumed'] is True


def test_ifc_uses_owner_door_height(facts):
    import ifcopenshell.util.element as ue
    model = build_ifc(facts)
    door = model.by_type('IfcDoor')[0]
    assert door.OverallHeight == 2.10
    assert ue.get_psets(door)['HDT_Provenance']['HeightAssumed'] is False


def test_ifc_length_unit_is_metre(facts):
    import ifcopenshell.util.unit as uu
    model = build_ifc(facts)
    assert uu.calculate_unit_scale(model) == 1.0
