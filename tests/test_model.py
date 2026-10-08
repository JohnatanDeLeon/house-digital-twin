import pytest

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
    assert path['reachable'] and path['doors_crossed'] == 2


def test_exterior_zones_connect_without_doors(house):
    path = house.walk_path('patio', 'cochera')
    assert path['reachable'] and path['doors_crossed'] == 0
    neighbors = {n['name']: n['connection'] for n in house.adjacent_rooms('Lavandería')}
    assert neighbors['Patio'] == 'abierto' and neighbors['Baño'] == 'ventana'
