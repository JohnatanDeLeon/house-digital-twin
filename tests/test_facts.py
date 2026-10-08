import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from tests.conftest import space_named


def _opening_at(facts, x, y):
    return next(o for o in facts['openings'] if o['footprint'] and Polygon(o['footprint']).buffer(0.05).contains(Polygon([(x, y), (x+1e-3, y), (x, y+1e-3)])))


def test_counts(facts):
    kinds = [o['kind'] for o in facts['openings'] if o['footprint']]
    assert kinds.count('door') == 9 and kinds.count('window') == 9
    assert sum(not s['is_exterior'] for s in facts['spaces']) == 8
    assert sorted(s['name'] for s in facts['spaces'] if s['is_exterior']) == ['Cochera', 'Lavandería', 'Pasillo de servicio', 'Patio', 'Pórtico']


def test_plan_alone_splits_bathroom_and_keeps_one_exterior(plan_only_facts):
    assert sum(not s['is_exterior'] for s in plan_only_facts['spaces']) == 9
    assert sum(s['is_exterior'] for s in plan_only_facts['spaces']) == 1


@pytest.mark.parametrize('name,area', [('Recámara 1', 16.12), ('Recámara 2', 15.24), ('Recámara 3', 14.99),
                                       ('Cocina + Sala + Comedor', 42.82), ('Bodega', 1.98), ('1/2 Baño', 1.46)])
def test_room_areas(facts, name, area):
    assert space_named(facts, name)['area'] == pytest.approx(area, abs=0.05)


def test_owner_merges_bathroom_and_shower(facts):
    bath = space_named(facts, 'Baño')
    assert bath['area'] == pytest.approx(2.94, abs=0.05)
    assert bath['floor_level']['value'] == 0.15
    assert len(bath['inner_partitions']) == 1
    assert bath['name_source'].startswith('dueño')


def test_bathroom_window_faces_open_laundry(facts):
    laundry = space_named(facts, 'Lavandería')
    assert laundry['is_exterior'] and laundry['roofed']['value'] is False and laundry['enclosed']['value'] is False
    window = _opening_at(facts, 2.9, 10.6)
    assert sorted(window['connects']) == sorted([space_named(facts, 'Baño')['id'], laundry['id']])


def test_exterior_zones_are_where_the_owner_said(facts):
    assert space_named(facts, 'Patio')['bbox'][1] == pytest.approx(12.617, abs=0.01)
    assert space_named(facts, 'Cochera')['bbox'][2:] == pytest.approx([3.115, 6.702], abs=0.01)
    assert 'COCHERA' in space_named(facts, 'Cochera')['labels']


def test_laundry_does_not_cut_the_service_passage(facts):
    passage = space_named(facts, 'Pasillo de servicio')
    laundry = space_named(facts, 'Lavandería')
    assert passage['bbox'][1] == pytest.approx(6.702, abs=0.01) and passage['bbox'][3] == pytest.approx(12.617, abs=0.01)
    assert laundry['bbox'][0] == pytest.approx(passage['bbox'][2], abs=0.01)  # empieza donde termina el pasillo
    kitchen_door = _opening_at(facts, 1.29, 8.8)
    assert passage['id'] in kitchen_door['connects']


def test_portico_is_roofed_and_garage_is_not(facts):
    portico = space_named(facts, 'Pórtico')
    assert portico['roofed']['value'] is True and space_named(facts, 'Cochera')['roofed']['value'] is False
    main_door = _opening_at(facts, 7.2, 3.33)
    assert portico['id'] in main_door['connects']


def test_owner_answers_close_unknowns(facts, plan_only_facts):
    assert {'U06', 'U09'} <= {u['id'] for u in plan_only_facts['unknowns']}
    assert not {'U06', 'U09'} & {u['id'] for u in facts['unknowns']}
    assert {a['id'] for a in facts['answered']} == {'U06', 'U09'}


def test_site_matches_lot(facts):
    assert facts['site']['width'] == pytest.approx(10.023, abs=0.005)
    assert facts['site']['depth'] == pytest.approx(21.235, abs=0.005)


def test_bodega_door_width_is_the_real_gap(facts):
    door = _opening_at(facts, 8.47, 1.4)
    assert door['kind'] == 'door' and door['width'] == pytest.approx(0.835, abs=0.01)


def test_adjacent_bedroom_doors_are_not_merged(facts):
    widths = sorted(o['width'] for o in facts['openings'] if o['kind'] == 'door' and abs(o['footprint'][0][0] - 5.617) < 0.01)
    assert widths == pytest.approx([0.858, 0.894], abs=0.01)


def test_window_labels_attach_to_nearest_window(facts):
    bath_window = _opening_at(facts, 2.9, 10.6)
    assert bath_window['sill_height']['value'] == 1.28 and bath_window['height']['value'] == 0.60


def test_light_well_has_owner_declared_window_without_invented_size(facts):
    well = space_named(facts, 'Tragaluz')
    living = space_named(facts, 'Cocina + Sala + Comedor')
    declared = [o for o in facts['openings'] if o['footprint'] is None]
    assert len(declared) == 1
    window = declared[0]
    assert window['kind'] == 'window' and sorted(window['connects']) == sorted([well['id'], living['id']])
    assert window['width'] is None and window['height']['value'] is None
    host = next(w for w in facts['walls'] if w['id'] == window['host_wall'])
    assert host['length'] == pytest.approx(1.11, abs=0.02)  # el muro diagonal, no los laterales


def test_unknown_heights_are_null_not_guessed(facts):
    assert all(w['height']['value'] is None for w in facts['walls'])
    assert all(o['height']['value'] is None for o in facts['openings'] if o['kind'] == 'door')
    assert facts['levels'][0]['storey_height']['value'] is None


def test_walls_do_not_overlap_and_are_valid(facts):
    polys = [Polygon(w['footprint']) for w in facts['walls']]
    assert all(p.is_valid for p in polys)
    assert sum(p.area for p in polys) == pytest.approx(unary_union(polys).area, abs=1e-3)


def test_every_opening_has_a_host_wall_and_connects_spaces(facts):
    for o in facts['openings']:  # incluye la ventana declarada por el dueño
        assert o['host_wall'] is not None
        assert 1 <= len(o['connects']) <= 2


def test_perimeter_walls_on_property_line(facts):
    west = [w for w in facts['walls'] if w['axis'] and abs(w['axis'][0][0] - 0.1) < 0.01]
    assert west and all(w['on_property_line'] for w in west)
