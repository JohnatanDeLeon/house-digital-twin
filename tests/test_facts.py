import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from tests.conftest import space_named


def _opening_at(facts, x, y):
    return next(o for o in facts['openings'] if o['footprint'] and Polygon(o['footprint']).buffer(0.05).contains(Polygon([(x, y), (x+1e-3, y), (x, y+1e-3)])))


def test_counts(facts):
    kinds = [o['kind'] for o in facts['openings'] if o['footprint'] and o['host_wall']]
    assert kinds.count('door') == 9 and kinds.count('window') == 12  # 9 del plano + tragaluz y 2 del pórtico (dueño)
    gates = [o for o in facts['openings'] if o['footprint'] and not o['host_wall']]  # herrería: pasillo (dueño) y portón
    assert [o['kind'] for o in gates] == ['door', 'door', 'door']
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
    # va de la cochera hasta la puerta del patio, al final del muro de la recámara 2 (dueño)
    assert passage['bbox'][1] == pytest.approx(6.702, abs=0.01) and passage['bbox'][3] == pytest.approx(16.945, abs=0.01)
    beside_laundry = Polygon(passage['polygon']).intersection(LineString([(0, 11), (3, 11)])).bounds
    assert laundry['bbox'][0] == pytest.approx(beside_laundry[2], abs=0.01)  # empieza donde termina el pasillo
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
    assert {a['id'] for a in facts['answered']} == {'U01', 'U04', 'U06', 'U09', 'U10', 'U11'}
    assert space_named(facts, 'Tragaluz')['roofed']['value'] is False  # U10: abierto al cielo


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


def test_light_well_window_carries_its_estimate_and_grid(facts):
    well = space_named(facts, 'Tragaluz')
    living = space_named(facts, 'Cocina + Sala + Comedor')
    assert not [o for o in facts['openings'] if o['footprint'] is None]
    window = next(o for o in facts['openings'] if o['kind'] == 'window' and o['detected_by'].startswith('dueño'))
    assert sorted(window['connects']) == sorted([well['id'], living['id']])
    assert window['width'] == pytest.approx(1.03) and window['height']['value'] == 1.62
    assert window['sill_height']['source'].startswith('estimación')  # no lo midió el dueño: se dice de dónde sale
    assert window['grid']['cols'] == 4 and window['grid']['rows'] == 5
    host = next(w for w in facts['walls'] if w['id'] == window['host_wall'])
    assert host['length'] == pytest.approx(1.11, abs=0.02)  # el muro diagonal, no los laterales


def test_unknown_heights_are_null_not_guessed(plan_only_facts):
    assert all(w['height']['value'] is None for w in plan_only_facts['walls'])
    assert all(o['height']['value'] is None for o in plan_only_facts['openings'] if o['kind'] == 'door')
    assert plan_only_facts['levels'][0]['storey_height']['value'] is None


def test_owner_heights_reach_the_facts(facts):
    storey = facts['levels'][0]['storey_height']
    assert storey['value'] == 2.60 and storey['source'].endswith('U01')
    doors = [o for o in facts['openings'] if o['kind'] == 'door' and o['host_wall']]
    assert len(doors) == 9 and all(o['height']['value'] == 2.10 for o in doors if o['id'] != 'D01')
    assert doors[0]['id'] == 'D01' and doors[0]['height']['value'] == 2.30  # la reja llega a la altura de las ventanas
    gates = [o for o in facts['openings'] if o['kind'] == 'door' and not o['host_wall']]
    by_id = {o['id']: o for o in gates}
    assert by_id['D10']['height']['value'] is None and by_id['D11']['height']['value'] is None  # U04 no llega a la herrería
    assert by_id['D12']['height']['value'] == 2.23 and 'foto' in by_id['D12']['height']['source']  # estimación aceptada
    curb = [w for w in facts['walls'] if w['height']['value'] is not None]
    assert [(w['role'], w['height']['value']) for w in curb] == [('sardinel de la regadera', 0.05)]
    assert curb[0]['thickness'] == pytest.approx(0.05, abs=0.005)
    assert all(w['height']['value'] is None for w in facts['walls'] if w not in curb)  # no todos los muros llegan a la losa


def test_walls_do_not_overlap_and_are_valid(facts):
    polys = [Polygon(w['footprint']) for w in facts['walls']]
    assert all(p.is_valid for p in polys)
    assert sum(p.area for p in polys) == pytest.approx(unary_union(polys).area, abs=1e-3)


def test_every_opening_has_a_host_wall_and_connects_spaces(facts):
    for o in facts['openings']:  # incluye la ventana declarada por el dueño
        if o['kind'] == 'door' and o['detected_by'].startswith('dueño'):  # herrería entre dos muros: une dos espacios
            assert o['host_wall'] is None and len(o['connects']) == 2
            continue
        if o['id'] == 'D12':  # portón: dibujado en el plano sin bloque, entre dos muros y hacia la calle
            assert o['host_wall'] is None and o['connects'] == ['S10'] and o['width'] == 3.04
            continue
        assert o['host_wall'] is not None
        assert 1 <= len(o['connects']) <= 2


def test_perimeter_walls_on_property_line(facts):
    west = [w for w in facts['walls'] if w['axis'] and abs(w['axis'][0][0] - 0.1) < 0.01]
    assert west and all(w['on_property_line'] for w in west)


def _runs_along(opening, wall):
    """El vano está sobre la banda del muro y en su misma dirección."""
    (x0, y0), (x1, y1) = wall['axis'][0], wall['axis'][-1]
    xs = [p[0] for p in opening['footprint']]; ys = [p[1] for p in opening['footprint']]
    horizontal = abs(x1 - x0) > abs(y1 - y0)
    if (max(xs) - min(xs) > max(ys) - min(ys)) != horizontal:
        return False
    lo, hi = (min(ys), max(ys)) if horizontal else (min(xs), max(xs))
    mid = y0 if horizontal else x0
    return lo - 0.01 <= mid <= hi + 0.01


@pytest.mark.parametrize('source', ['facts', 'dxf_facts'])
def test_openings_belong_to_the_wall_they_run_along(source, request):
    """Un vano es del muro que atraviesa, no del que solo lo toca de costado (las ventanas de la cocina)."""
    facts = request.getfixturevalue(source)
    walls = {w['id']: w for w in facts['walls']}
    for o in facts['openings']:
        if o['footprint'] is None:
            continue
        near = [w for w in walls.values() if Polygon(w['footprint']).distance(Polygon(o['footprint'])) < 0.01]
        aligned = [w['id'] for w in near if _runs_along(o, w)]
        assert not aligned or o['host_wall'] in aligned, (o['id'], o['host_wall'], aligned)
    kitchen = [_opening_at(facts, 1.6, 6.79), _opening_at(facts, 2.5, 6.79)]
    assert kitchen[0]['host_wall'] == kitchen[1]['host_wall']


def test_owner_measurement_is_compared_with_the_plan(dxf_facts):
    hallway = next(m for m in dxf_facts['measurements'] if m['id'] == 'M01')
    assert hallway['walls'] == ['W18', 'W16']
    assert hallway['value'] == 1.10 and hallway['plan_value'] == pytest.approx(1.21, abs=0.005)
    assert hallway['matches_plan'] is False
    assert any(w.startswith('M01:') for w in dxf_facts['source_warnings'])


def test_owner_corrects_plan_opening_position(dxf_facts):
    d01 = next(o for o in dxf_facts['openings'] if o['id'] == 'D01')
    assert d01['plan_footprint'][0][0] == pytest.approx(6.17, abs=0.01) and d01['footprint'][0] == [5.123, 0.0]  # el dato del plano se conserva
    assert d01['swing']['hinge_end'] == [6.103, 0.1] and 'desplazado' in d01['swing']['source']
    assert 'dueño' in d01['position_source']


def test_portico_windows_are_measured_by_owner(facts):
    by_id = {o['id']: o for o in facts['openings']}
    assert (by_id['V11']['width'], by_id['V11']['height']['value']) == (2.0, 1.3)
    assert (by_id['V12']['width'], by_id['V12']['height']['value']) == (1.5, 1.3)
    assert by_id['V11']['host_wall'] == by_id['V12']['host_wall'] == 'W03'
    assert 'estimación' in by_id['V11']['sill_height']['source'] and 'cinta' in by_id['V11']['height']['source']


def test_shower_area_is_the_bathroom_beyond_the_curb(facts):
    shower = next(f for f in facts['fixtures'] if f['kind'] == 'shower')
    curb = next(w for w in facts['walls'] if w['id'] == shower['curb_wall'])
    assert shower['space'] == 'S05' and curb['role'] == 'sardinel de la regadera'
    xs, ys = [p[0] for p in shower['polygon']], [p[1] for p in shower['polygon']]
    assert (min(xs), max(xs)) == pytest.approx((2.99, 4.24), abs=0.01)  # el PDF de validación difiere en mm
    assert (min(ys), max(ys)) == pytest.approx((10.225, 11.155), abs=0.01)
