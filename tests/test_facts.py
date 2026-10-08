import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

from tests.conftest import space_named


def _opening_at(facts, x, y):
    return next(o for o in facts['openings'] if Polygon(o['footprint']).buffer(0.05).contains(Polygon([(x, y), (x+1e-3, y), (x, y+1e-3)])))


def test_counts(facts):
    kinds = [o['kind'] for o in facts['openings']]
    assert kinds.count('door') == 9 and kinds.count('window') == 9
    assert sum(not s['is_exterior'] for s in facts['spaces']) == 9
    assert sum(s['is_exterior'] for s in facts['spaces']) == 1


@pytest.mark.parametrize('name,area', [('Recámara 1', 16.12), ('Recámara 2', 15.24), ('Recámara 3', 14.99),
                                       ('Cocina + Sala + Comedor', 42.82), ('Bodega', 1.98), ('1/2 Baño', 1.46)])
def test_room_areas(facts, name, area):
    assert space_named(facts, name)['area'] == pytest.approx(area, abs=0.05)


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


def test_unknown_heights_are_null_not_guessed(facts):
    assert all(w['height']['value'] is None for w in facts['walls'])
    assert all(o['height']['value'] is None for o in facts['openings'] if o['kind'] == 'door')
    assert facts['levels'][0]['storey_height']['value'] is None


def test_walls_do_not_overlap_and_are_valid(facts):
    polys = [Polygon(w['footprint']) for w in facts['walls']]
    assert all(p.is_valid for p in polys)
    assert sum(p.area for p in polys) == pytest.approx(unary_union(polys).area, abs=1e-3)


def test_every_opening_has_a_host_wall_and_connects_spaces(facts):
    for o in facts['openings']:
        assert o['host_wall'] is not None
        assert 1 <= len(o['connects']) <= 2


def test_perimeter_walls_on_property_line(facts):
    west = [w for w in facts['walls'] if w['axis'] and abs(w['axis'][0][0] - 0.1) < 0.01]
    assert west and all(w['on_property_line'] for w in west)
