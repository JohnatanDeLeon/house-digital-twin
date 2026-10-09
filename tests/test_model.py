import pytest
from shapely.geometry import Polygon

from house_twin.facts.builder import _walls_between
from house_twin.model import HouseModel, RoomNotFound


@pytest.fixture(scope='module')
def house(facts):
    return HouseModel(facts)


def test_find_room_ignores_accents_and_case(house):
    assert house.find_room('recamara 1')['name'] == 'Recámara 1'
    bodega_id = house.find_room('bodega')['id']
    assert house.find_room(bodega_id.lower())['name'] == 'Bodega'


def test_find_room_by_label_inside_open_plan(house):
    assert house.find_room('sala')['name'] == 'Cocina + Sala + Comedor'


def test_ambiguous_room_lists_options(house):
    with pytest.raises(RoomNotFound, match='Recámara 1.*Recámara 2'):
        house.find_room('closet')


def test_bedrooms_are_reached_from_living_area_by_door(house):
    neighbors = {n['name']: n['connection'] for n in house.adjacent_rooms('sala')}
    assert neighbors['Recámara 1'] == neighbors['Recámara 2'] == neighbors['Recámara 3'] == 'puerta'


def test_bedrooms_share_wall_without_door(house):
    neighbors = {n['name']: n['connection'] for n in house.adjacent_rooms('Recámara 1')}
    assert neighbors['Recámara 3'] == 'solo muro'


def test_walk_path_from_garage_to_bedroom(house):
    path = house.walk_path('cochera', 'Recámara 2')
    assert path['reachable'] and path['doors_crossed'] == 3  # herrería del pasillo, cocina y recámara


def test_service_passage_joins_patio_and_garage_through_its_gates(house):
    path = house.walk_path('patio', 'cochera')
    assert path['reachable'] and path['doors_crossed'] == 2  # las dos puertas de herrería
    assert [step['to'] for step in path['steps']] == ['Pasillo de servicio', 'Cochera']
    neighbors = {n['name']: n['connection'] for n in house.adjacent_rooms('Lavandería')}
    assert neighbors == {'Pasillo de servicio': 'abierto', 'Baño': 'ventana', 'Cocina + Sala + Comedor': 'solo muro',
                         'Recámara 2': 'solo muro'}


def test_corner_contact_is_not_adjacency():
    # dos cuartos que solo se miran en diagonal por una esquina, con un muro en ella, no son vecinos
    a = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    b = Polygon([(2.2, 2.2), (4, 2.2), (4, 4), (2.2, 4)])
    corner = {'W1': Polygon([(2, 2), (2.2, 2), (2.2, 2.2), (2, 2.2)])}
    assert _walls_between(a, b, corner) == []
    assert _walls_between(a, Polygon([(2.2, 0), (4, 0), (4, 2), (2.2, 2)]), {'W2': Polygon([(2, 0), (2.2, 0), (2.2, 2), (2, 2)])}) == ['W2']


def test_service_passage_runs_along_bedroom_2(house):
    assert house.adjacent_rooms('Recámara 2') and 'Pasillo de servicio' in {n['name'] for n in house.adjacent_rooms('Recámara 2')}
