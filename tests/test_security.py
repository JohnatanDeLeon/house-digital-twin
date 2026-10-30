import math

import numpy as np
import pytest
from shapely.geometry import Point

from house_twin.security import (LEVELS, Scene, camera_coverage, cameras_in, entry_report, evaluate, load_plan, ppm,
                                 scenarios, suggest)
from house_twin.variants import load_variants


@pytest.fixture(scope='module')
def plan():
    return load_plan()


@pytest.fixture(scope='module')
def scenes(dxf_facts, plan):
    variants = {v['id']: v for v in load_variants()}
    return {sc['id']: scene for sc, scene in scenarios(plan, dxf_facts, variants)}


def test_pixel_density_follows_the_lens():
    """4 MP (2688 px) con 100° de ángulo: 250 px/m a 4.5 m y 125 a 9 m, las distancias de identificar y reconocer."""
    assert float(ppm(4.5, 100, 2688)) == pytest.approx(250, rel=0.02)
    assert float(ppm(9.0, 100, 2688)) == pytest.approx(125, rel=0.02)
    assert float(ppm(10, 55, 2688)) > LEVELS['identificar']  # el lente de 6 mm identifica a 10 m: sirve para el pasillo


def test_plan_leaves_no_blind_spot_in_any_scenario(scenes, plan):
    """La casa actual y la casa con cada remodelación: ninguna celda exterior sin la calidad que se exige, y en todo
    acceso se reconoce a quien llega (125 px/m) en cada punto de su franja."""
    assert set(scenes) == {'hoy', 'cocina-en-u', 'fachada-moderna', 'ambas'}
    for name, scene in scenes.items():
        result = evaluate(scene, cameras_in(scene, plan))
        assert result['blind_points'] == [], name
        assert all(z['covered_pct'] == 100 for z in result['zones'].values()), name
        assert min(e['worst_ppm'] for e in entry_report(scene, result)) >= LEVELS['reconocer'], name


def test_a_missing_camera_leaves_blind_spots(scenes, plan):
    """La evaluación sí detecta: sin la cámara del pasillo o sin las del patio quedan puntos ciegos en esas zonas."""
    scene = scenes['hoy']
    without = lambda cid: [c for c in cameras_in(scene, plan) if c['id'] != cid]
    corridor = evaluate(scene, without('C5'))
    assert corridor['zones']['S12']['covered_pct'] < 100 or corridor['zones']['S13']['covered_pct'] < 100
    patio = evaluate(scene, [c for c in cameras_in(scene, plan) if c['id'] not in ('C7', 'C8')])
    assert patio['zones']['S09']['covered_pct'] < 100


def test_walls_block_the_view_and_see_through_gates_do_not(scenes, plan, dxf_facts):
    hoy = scenes['hoy']
    c5 = next(c for c in plan['cameras'] if c['id'] == 'C5')
    assert hoy.sees(c5['mount'], np.array([0.7]), np.array([9.0]))[0]  # pasillo
    assert not hoy.sees(c5['mount'], np.array([2.5]), np.array([14.0]))[0]  # detrás del muro de la recámara 2
    street, inside = (1.7, -2.0), (np.array([1.7]), np.array([2.5]))  # de la banqueta, frente al portón, a la cochera
    assert hoy.sees(street, *inside)[0]  # el portón de herrería deja ver
    assert not scenes['fachada-moderna'].sees(street, *inside)[0]  # el de lámina, no


def test_laundry_stops_being_exterior_when_it_is_closed(scenes, plan):
    assert 'S13' in {s['id'] for s in scenes['hoy'].spaces} and 'S13' not in {s['id'] for s in scenes['cocina-en-u'].spaces}
    assert 'C6' in {c['id'] for c in cameras_in(scenes['hoy'], plan)}
    assert 'C6' not in {c['id'] for c in cameras_in(scenes['ambas'], plan)}


def test_cameras_hang_on_walls_and_cover_each_others_base(scenes, plan):
    """Cada cámara está a 10 cm de la cara de un muro (no flota), y como no ve el suelo pegado a su pared, lo que
    queda al pie de cada una lo cubre otra."""
    hoy = scenes['hoy']
    cameras = cameras_in(hoy, plan)
    for cam in cameras:
        gap = hoy.obstacles.distance(Point(cam['mount']))
        assert 0.05 <= gap <= 0.15, cam['id']
        cells = hoy.cells
        near = np.hypot(cells['x'] - cam['mount'][0], cells['y'] - cam['mount'][1]) < plan['min_ground_distance_m']
        assert near.any()
        others = [camera_coverage(hoy, c)['ppm'] >= cells['required'] for c in cameras if c['id'] != cam['id']]
        assert np.all(np.any(others, axis=0)[near]), cam['id']  # el pie de la cámara no se queda ciego


def test_search_needs_as_many_cameras_as_the_plan(scenes, plan):
    """El plan no es de sobra: la búsqueda automática del mínimo tampoco baja de 8 cámaras en la casa actual."""
    found = suggest(scenes['hoy'], min_separation_m=1.0)
    assert found['unreachable'] == [] and len(found['cameras']) >= len(cameras_in(scenes['hoy'], plan)) - 1
    assert len(found['cameras']) == 8


def test_optional_camera_adds_redundancy_not_coverage(scenes, plan):
    """La novena cámara no hace falta para cubrir (el plan base ya no deja ciegos), pero en la casa remodelada casi
    duplica lo que ven dos cámaras en la cochera y el pórtico, donde los portones y las rejas ya no dejan ver."""
    scene = scenes['ambas']
    base, full = cameras_in(scene, plan), cameras_in(scene, plan, optional=True)
    assert [c['id'] for c in full if c not in base] == ['C9']
    front = np.isin(scene.cells['zone'], ('S10', 'S11'))
    double = lambda cams: float((evaluate(scene, cams)['count'][front] >= 2).mean())
    assert double(full) > double(base) + 0.3 and double(full) > 0.8
