from pathlib import Path

from house_twin.finishes import Finishes
from house_twin.variants import apply_variant, load_variants, validate

ROOT = Path(__file__).resolve().parent.parent


def _finishes():
    facts = {'site': {'polygon': [[0, 0], [0, 5], [6, 5], [6, 0]]}, 'spaces': []}
    materials = {'puerta-vieja': {'applies_to': {'openings': ['D03']}, 'glass_material': 'vidrio-a'},
                 'puerta-nueva': {'applies_to': {'variant': 'v'}, 'glass_material': 'vidrio-b'}}
    return Finishes(facts, materials), materials


def test_variant_changes_finishes_on_top_without_touching_the_house():
    finishes, materials = _finishes()
    variant = {'id': 'v', 'changes': [{'opening': 'D03', 'part': 'leaf', 'material': 'puerta-nueva'}]}
    proposal = apply_variant(finishes, variant, materials)
    assert proposal.opening('D03') == {'leaf': 'puerta-nueva', 'glass': 'vidrio-b'}
    assert finishes.opening('D03') == {'leaf': 'puerta-vieja', 'glass': 'vidrio-a'}  # la casa actual sigue igual


def test_variant_material_is_not_used_by_the_existing_house():
    finishes, _ = _finishes()
    assert 'puerta-nueva' not in {m for parts in finishes.openings.values() for m in parts.values()}


def test_invalid_variants_are_reported():
    _, materials = _finishes()
    facts = {'openings': [{'id': 'D03'}]}
    variant = {'id': 'v', 'changes': [{'opening': 'D99', 'part': 'hoja', 'material': 'no-existe'}]}
    assert len(validate(variant, facts, materials)) == 3


def test_repo_variants_are_valid(dxf_facts):
    from house_twin.finishes import load_materials
    materials = load_materials(ROOT / 'assets' / 'textures')
    variants = load_variants()
    assert all(not validate(v, dxf_facts, materials) for v in variants)  # puede no haber ninguna


def _remodel():
    return next(v for v in load_variants() if v['id'] == 'cocina-en-u')


def test_remodel_builds_proposed_facts_without_touching_the_house(dxf_facts):
    import copy
    from house_twin.variants import variant_facts
    before = copy.deepcopy(dxf_facts)
    proposed = variant_facts(dxf_facts, _remodel())
    assert dxf_facts == before  # los hechos de la casa no cambian
    openings = {o['id']: o for o in proposed['openings']}
    assert 'D04' not in openings and {'D13', 'D14'} <= set(openings)
    assert openings['D13']['host_wall'] == 'W15' and openings['D14']['host_wall'] == 'W41'
    assert 'W41' in {w['id'] for w in proposed['walls']}
    assert openings['V03']['sill_height']['value'] == 0.95 and openings['V04']['sill_height']['value'] == 0.95
    laundry = next(s for s in proposed['spaces'] if s['id'] == 'S13')
    assert laundry['enclosed']['value'] is True and min(p[0] for p in laundry['polygon']) == 1.375
    assert proposed['provenance']['variant'] == 'cocina-en-u'


def test_geometry_problems_are_reported(dxf_facts):
    variant = {'id': 'v', 'geometry': {'close_openings': ['D99'],
                                       'add_openings': [{'id': 'D50', 'host_wall': 'W99', 'kind': 'door'}]},
               'specs': {'horno': 'variants/no-existe.json'}}
    problems = validate(variant, dxf_facts, {})
    assert any('D99' in p for p in problems) and any('W99' in p for p in problems)
    assert any('horno' in p for p in problems) and any('no-existe' in p for p in problems)


def _kitchen_parts():
    import json
    from house_twin.kitchen import kitchen_parts
    spec = json.loads((ROOT / _remodel()['specs']['kitchen']).read_text())
    return {p['id']: p['mesh'][0] for p in kitchen_parts(spec)}


def _centre(points):
    return tuple(sum(p[i] for p in points) / len(points) for i in (0, 1))


def test_remodel_kitchen_is_a_u_with_the_sink_under_the_window_and_a_sound_work_triangle():
    import math
    parts = _kitchen_parts()
    sink, stove, fridge = (_centre(parts[k]) for k in ('cocina-ventanas-tarja', 'cocina-estufa', 'cocina-refrigerador'))
    assert 2.29 < sink[0] < 2.81 and sink[1] < 7.5          # tarja bajo la ventana V04
    assert stove[0] < 2.05                                    # estufa contra el muro del pasillo de servicio
    assert fridge[1] > 9.3                                    # refrigerador contra el muro del fondo
    legs = [math.dist(sink, stove), math.dist(stove, fridge), math.dist(fridge, sink)]
    assert all(1.2 <= leg <= 2.7 for leg in legs) and 4.0 <= sum(legs) <= 7.9


def test_remodel_kitchen_leaves_the_laundry_door_free():
    for name, points in _kitchen_parts().items():
        xs, ys, zs = zip(*points)
        in_front_of_d13 = min(xs) < 2.25 and max(xs) > 1.45 and max(ys) > 9.25 and min(zs) < 2.1
        assert not in_front_of_d13, name


def test_walk_offers_a_remodel_with_its_own_model(dxf_facts):
    from house_twin.variants import variant_facts
    from house_twin.walk import _variant_entry
    variant = _remodel()
    proposed = variant_facts(dxf_facts, variant)
    entry = _variant_entry(variant, dxf_facts, {'facts': proposed, 'glb': None, 'doors': [], 'items': []})
    assert entry['model'] == 'casa-cocina-en-u.js' and entry['overrides'] == {}
    door_ids = {d['id'] for d in entry['house']['doors']}
    assert 'D04' not in door_ids and {'D13', 'D14'} <= door_ids
    assert entry['focus'] is not None


def test_remodel_laundry_combo_clears_both_doors(dxf_facts):
    """La lavasecadora (686 × 796 mm, dueño) y lo demás de la lavandería quedan fuera del barrido de D13."""
    import json
    import math
    from shapely.geometry import LineString, box
    from house_twin.laundry import laundry_parts
    from house_twin.variants import variant_facts
    proposed = {o['id']: o for o in variant_facts(dxf_facts, _remodel())['openings']}
    spec = json.loads((ROOT / _remodel()['specs']['laundry']).read_text())
    parts = {p['id']: p['mesh'][0] for p in laundry_parts(spec)}
    xs, ys, _ = zip(*parts['lavanderia-lavasecadora'])
    assert (round(max(ys) - min(ys), 3), round(max(xs) - min(xs), 3)) == (0.686, 0.796)
    for door in ('D13',):  # D14 es corrediza: ver test_remodel_laundry_sliding_door
        hinge, latch = proposed[door]['swing']['hinge_end'], proposed[door]['swing']['latch_end']
        length = math.dist(hinge, latch)
        closed = math.atan2(latch[1] - hinge[1], latch[0] - hinge[0])
        for deg in range(0, 91, 5):
            a = closed + math.radians(deg)  # las dos abren hacia la lavandería: +y (D13) y +x (D14)
            leaf = LineString([hinge, (hinge[0] + length * math.cos(a), hinge[1] + length * math.sin(a))]).buffer(0.02)
            for name, points in parts.items():
                px, py, pz = zip(*points)
                if min(pz) < 2.1:
                    assert not leaf.intersects(box(min(px), min(py), max(px), max(py))), (door, deg, name)


def test_remodel_takes_the_gas_cylinder_out_of_the_closed_laundry():
    """Al cerrarla, la lavandería queda como cubo de luz de 3.5 m² con calentador: el cilindro sale al pasillo
    (NOM-004-SEDG-2004 6.1.2.1) con 0.60 m libres al frente para cambiarlo (6.1.2.4)."""
    import json
    from house_twin.laundry import laundry_parts
    spec = json.loads((ROOT / _remodel()['specs']['laundry']).read_text())
    gas = next(p for p in laundry_parts(spec) if p['id'] == 'lavanderia-gas')
    xs = [p[0] for p in gas['mesh'][0]]
    assert gas['space'] == 'S12' and max(xs) <= 1.28 and min(xs) - 0.20 >= 0.60  # pasillo; libre hasta la barda
    assert 'boiler' not in spec and spec['heater']['flue']['top_m'] > spec['roof']['z'][1]  # chimenea arriba del techo


def test_remodel_laundry_sliding_door(dxf_facts):
    """D14 es una corrediza de cristal colgada por el lado del pasillo: cubre el vano con traslape, abierta lo deja
    libre, no entra a la lavandería, el pasillo conserva al menos 0.85 m y no choca con el cilindro de gas."""
    import json
    from house_twin.laundry import laundry_parts
    from house_twin.sliding import panel_polygon, sliding_parts
    from house_twin.variants import variant_facts
    from house_twin.walk import doors
    proposed = variant_facts(dxf_facts, _remodel())
    d14 = next(o for o in proposed['openings'] if o['id'] == 'D14')
    slide = d14['slide']
    assert 'swing' not in d14
    ys = [p[1] for p in d14['footprint']]
    (_, a), (_, b) = slide['line']
    assert min(a, b) <= min(ys) - 0.04 and max(a, b) >= max(ys) + 0.04  # traslape sobre el vano
    assert max(a, b) + slide['travel'][1] <= min(ys)  # abierta, el vano queda libre
    spec = json.loads((ROOT / _remodel()['specs']['laundry']).read_text())
    gas = next(p for p in laundry_parts(spec) if p['id'] == 'lavanderia-gas')
    gas_y0 = min(p[1] for p in gas['mesh'][0])
    corridor_x0 = 0.20  # cara de la barda
    meshes = [part['mesh'][0] for part in sliding_parts('D14', slide)] + [[(x, y, 0) for x, y in panel_polygon(slide)]]
    for points in meshes:
        xs, ys_ = [p[0] for p in points], [p[1] for p in points]
        assert max(xs) <= 1.205 + 1e-6  # todo del lado del pasillo (cara de W41)
        assert min(xs) - corridor_x0 >= 0.85  # paso libre en el pasillo
        assert max(ys_) < gas_y0  # no llega al cilindro de gas
    entry = next(d for d in doors(proposed) if d['id'] == 'D14')
    assert entry['slide'] == slide['travel'] and len(entry['leaves']) == 1


def test_remodel_laundry_layout_is_workable(dxf_facts):
    """La barra deja un paso de al menos 0.85 m; la lavasecadora queda frente al vano de D14 (con la corrediza
    abierta se puede hincar para sacar la ropa) y bajo una cubierta para doblar, con holgura sobre la máquina; los
    muebles de piso no se enciman y los contactos quedan entre la barra y las alacenas."""
    import json
    from house_twin.laundry import laundry_parts
    from house_twin.variants import variant_facts
    d14 = next(o for o in variant_facts(dxf_facts, _remodel())['openings'] if o['id'] == 'D14')
    spec = json.loads((ROOT / _remodel()['specs']['laundry']).read_text())
    parts = {p['id']: p['mesh'][0] for p in laundry_parts(spec)}
    box = {k: ([min(p[i] for p in v) for i in range(3)], [max(p[i] for p in v) for i in range(3)]) for k, v in parts.items()}
    w41_face = 1.375
    run = [k for k in box if k.startswith('lavanderia-barra-')]
    assert min(box[k][0][0] for k in run) - w41_face >= 0.85  # paso frente a la barra
    combo_lo, combo_hi = box['lavanderia-lavasecadora']
    dy = [p[1] for p in d14['footprint']]
    assert min(dy) <= combo_lo[1] and combo_hi[1] <= max(dy)  # frente al vano de la corrediza
    top_lo, top_hi = box['lavanderia-doblado-cubierta-1']
    assert 0.02 <= top_lo[2] - combo_hi[2] <= 0.05 and top_lo[0] <= combo_lo[0]  # cubierta encima, con holgura
    floor = ['lavanderia-lavasecadora', 'lavanderia-costado-nicho'] + [k for k in run if '-bajo-' in k]
    for i, a in enumerate(floor):
        for b in floor[i + 1:]:
            (alo, ahi), (blo, bhi) = box[a], box[b]
            assert ahi[0] <= blo[0] + 1e-6 or bhi[0] <= alo[0] + 1e-6 or ahi[1] <= blo[1] + 1e-6 or bhi[1] <= alo[1] + 1e-6, (a, b)
    counter_top = box['lavanderia-barra-cubierta-1'][1][2]
    uppers_bottom = min(box[k][0][2] for k in run if '-alto-' in k)
    assert all(counter_top < d['z'] < uppers_bottom for d in spec['devices'])


def _facade():
    return next(v for v in load_variants() if v['id'] == 'fachada-moderna')


def test_facade_remodel_zones_without_touching_the_house(dxf_facts):
    """La fachada moderna reparte la cara de la calle en zonas (zócalo, marco de duela en la entrada, volumen de
    microcemento, aplanado fino) y cambia el pórtico; la casa actual conserva su estuco y su piso."""
    from house_twin.finishes import Finishes, load_materials
    from house_twin.variants import has_geometry, variant_materials
    materials = load_materials(ROOT / 'assets' / 'textures')
    variant = _facade()
    proposed, today = Finishes(dxf_facts, variant_materials(materials, variant)), Finishes(dxf_facts, materials)
    expect = {(0.3, 4.0): 'zoclo-porcelanato-grafito', (1.5, 5.5): 'duela-wpc-nogal', (1.5, 9.0): 'microcemento-grafito',
              (1.5, 4.0): 'aplanado-fino-blanco'}
    for (z, x), name in expect.items():
        assert proposed.wall_finish('calle', z, (x, -0.05)) == name
        assert today.wall_finish('calle', z, (x, -0.05)) == 'estuco-fachada'
    assert proposed.floor('S11') == 'porcelanato-portico' and today.floor('S11') == 'piso-exterior'
    assert has_geometry(variant) and not validate(variant, dxf_facts, materials)


def test_facade_remodel_uses_only_new_textures():
    """Ninguna textura de la propuesta es de la casa: todas son materiales propios de la variante."""
    from house_twin.finishes import load_materials
    materials = load_materials(ROOT / 'assets' / 'textures')
    variant = _facade()
    own = {n for n, m in materials.items() if m['applies_to'].get('variant') == variant['id']}
    assert {c['material'] for c in variant['changes']} <= own and len(own) >= 9


def test_facade_coping_covers_the_slab_edge():
    """El remate tapa el canto de la losa (2.60–2.70 m) y sale a lo más 2 cm sobre la línea de la calle (y = 0)."""
    import json
    from house_twin.extras import extras_parts
    spec = json.loads((ROOT / _facade()['specs']['extras']).read_text())
    (cap,) = [p for p in extras_parts(spec) if p['id'] == 'fachada-remate']
    xs, ys, zs = zip(*cap['mesh'][0])
    assert min(zs) <= 2.6 and max(zs) >= 2.7 and min(ys) >= -0.02 - 1e-9 and min(xs) <= 3.24 and max(xs) >= 10.03
