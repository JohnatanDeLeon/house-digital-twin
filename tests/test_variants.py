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


def _facade_proposed(dxf_facts):
    from house_twin.variants import variant_facts
    return {o['id']: o for o in variant_facts(dxf_facts, _facade())['openings']}


def test_facade_sectional_door_closes_the_opening_and_parks_under_the_roof(dxf_facts):
    """El portón seccional tapa el vano cerrado y, abierto, sus paneles quedan acostados bajo el techo: dejan libre la
    altura del vano, no bajan de las vigas y no salen de la cochera (ni a la banqueta)."""
    import json
    import math
    from house_twin.lift import lift_parts, panel_box, path_point
    from house_twin.walk import doors
    d12 = _facade_proposed(dxf_facts)['D12']
    lift, height = d12['lift'], d12['height']['value']
    assert not d12.get('leaves') and lift['panels'] * lift['panel_m'] >= height  # cerrado: tapa el vano
    xs = [p[0] for k in range(lift['panels']) for p in panel_box(lift, k)[0]]
    assert min(xs) - 0.2 <= 0.1 and 3.24 - max(xs) <= 0.1  # casi todo el ancho entre la barda y el pórtico
    spec = json.loads((ROOT / _facade()['specs']['extras']).read_text())
    beams_bottom = min(b['z'][0] for b in spec['boxes'] if b['id'].startswith('cochera-viga'))
    travel = lift['panels'] * lift['panel_m']
    for k in range(lift['panels']):  # abierto
        for s in (k * lift['panel_m'] + travel, (k + 1) * lift['panel_m'] + travel):
            y, z = path_point(lift, s)
            assert height <= z <= beams_bottom and 0 < y < 6.71
    rail_top = lift['track']['z_curve'] + lift['track']['radius_m'] + lift['track']['profile_m']
    assert rail_top <= beams_bottom
    assert all(min(p[1] for p in part['mesh'][0]) >= 0 for part in lift_parts('D12', lift))  # nada sale a la banqueta
    entry = next(d for d in doors(variant_facts_for(dxf_facts)) if d['id'] == 'D12')
    assert entry['lift']['panels'] == lift['panels']
    assert math.isclose(path_point(lift, 0)[0], lift['y'])


def variant_facts_for(dxf_facts):
    from house_twin.variants import variant_facts
    return variant_facts(dxf_facts, _facade())


def test_facade_garage_roof_keeps_light_for_the_kitchen_windows(dxf_facts):
    """El techo cubre la cochera; frente a las ventanas de la cocina (V03, V04) la franja es translúcida."""
    import json
    spec = json.loads((ROOT / _facade()['specs']['extras']).read_text())
    slabs = {s['id']: s for s in spec['slabs']}
    solid, clear = slabs['cochera-techo'], slabs['cochera-techo-translucido']
    assert solid['x'] == [0.2, 3.12] and solid['y'][0] == 0.0 and clear['y'][1] == 6.71 and solid['y'][1] == clear['y'][0]
    assert 6.71 - clear['y'][0] >= 1.5 and clear['material'] == 'policarbonato-satinado'
    windows = [o for o in dxf_facts['openings'] if o['id'] in ('V03', 'V04')]
    assert all(clear['x'][0] <= min(p[0] for p in o['footprint']) and max(p[0] for p in o['footprint']) <= clear['x'][1]
               for o in windows)


def test_facade_lighting_is_warm_and_lights_up_at_night():
    """Arbotantes en la cara de la calle a 1.95 m y empotrados en el techo de la cochera, todos de 3000 K; cada uno
    tiene su `-foco` (el recorrido lo enciende de noche) y su luz para el IFC."""
    import json
    from house_twin.extras import extras_parts
    spec = json.loads((ROOT / _facade()['specs']['extras']).read_text())
    parts = {p['id']: p for p in extras_parts(spec)}
    lights = spec['lights']
    assert sum(lum['kind'] == 'updown' for lum in lights) == 3 and sum(lum['kind'] == 'downlight' for lum in lights) == 2
    for lum in lights:
        assert lum['color_temperature_k'] == 3000 and f"{lum['id']}-foco" in parts
        assert parts[lum['id']]['psets']['HDT_Light']['Lumens'] == lum['lumens']
        assert lum['id'].startswith(('fachada-', 'cochera-'))  # luminarias exteriores para el recorrido
    assert all(lum['position'][1] == 0.0 and lum['z'] == 1.95 for lum in lights if lum['kind'] == 'updown')


def _window_remodel():
    return next(v for v in load_variants() if v['id'] == 'recamara-2-ventana')


def test_bedroom_window_moves_to_the_side_wall_with_the_same_size(dxf_facts):
    """V08 (detrás de la cabecera) se tapia y V13 la sustituye en W12 con el mismo vano: la luz y la ventilación no bajan."""
    from house_twin.variants import variant_facts
    proposed = {o['id']: o for o in variant_facts(dxf_facts, _window_remodel())['openings']}
    old = next(o for o in dxf_facts['openings'] if o['id'] == 'V08')
    assert 'V08' not in proposed and 'V08' in {o['id'] for o in dxf_facts['openings']}  # la casa existente no cambia
    new = proposed['V13']
    assert (new['width'], new['sill_height']['value'], new['height']['value']) == \
           (old['width'], old['sill_height']['value'], old['height']['value'])
    assert new['host_wall'] == 'W12' and new['connects'] == ['S03', 'S12']


def test_bedroom_window_clears_the_bed_the_closet_and_the_minisplit(dxf_facts):
    """V13 cabe en W12 (con ≥ 0.40 m a la esquina), queda fuera de la cabecera y de la unidad del minisplit."""
    import json
    from house_twin.variants import variant_facts
    proposed = variant_facts(dxf_facts, _window_remodel())
    window = next(o for o in proposed['openings'] if o['id'] == 'V13')
    ys = [p[1] for p in window['footprint']]
    wall = next(w for w in proposed['walls'] if w['id'] == 'W12')
    room = next(s for s in proposed['spaces'] if s['id'] == 'S03')
    y_min, y_max = min(ys), max(ys)
    assert room['bbox'][3] - y_max >= 0.40  # a la esquina con el muro del patio
    assert min(p[1] for p in wall['footprint']) < y_min and max(p[1] for p in wall['footprint']) > y_max
    spec = json.loads((ROOT / 'sources' / 'recamaras' / 'recamara-s03.json').read_text())
    mini_y = (12.815 + spec['minisplit']['u'][0], 12.815 + spec['minisplit']['u'][1])
    top = window['sill_height']['value'] + window['height']['value']
    assert y_min >= mini_y[1] or top <= spec['minisplit']['z'][0]
    # la cabecera (la cama) queda contra el muro del patio, donde V08 ya no está
    assert spec['bed']['headboard_wall']['origin'][1] == 16.775


def _two_windows():
    return next(v for v in load_variants() if v['id'] == 'recamara-2-dos-ventanas')


def test_two_windows_flank_the_headboard_without_touching_it_or_the_closet(dxf_facts):
    """V08 se tapia y V13/V14 flanquean la cabecera en W09: quedan a ≥ 0.10 m de ella, simétricas, a ≥ 0.15 m de la esquina
    y del closet, y suman casi lo que daba V08 (la luz no baja de 10 % del piso)."""
    import json
    from house_twin.variants import variant_facts
    proposed = variant_facts(dxf_facts, _two_windows())
    ids = {o['id']: o for o in proposed['openings']}
    assert 'V08' not in ids and 'V08' in {o['id'] for o in dxf_facts['openings']}
    spec = json.loads((ROOT / 'sources' / 'recamaras' / 'recamara-s03.json').read_text())
    centre, half = spec['bed']['headboard_wall']['origin'][0], spec['bed']['headboard']['width_m'] / 2
    room = next(s for s in proposed['spaces'] if s['id'] == 'S03')
    closet = next(f for f in proposed['fixtures'] if f['kind'] == 'closet' and f['space'] == 'S03')
    spans = {}
    for oid in ('V13', 'V14'):
        w = ids[oid]
        xs = [p[0] for p in w['footprint']]
        spans[oid] = (min(xs), max(xs))
        assert w['host_wall'] == 'W09' and w['connects'] == ['S03', 'S09']
        assert (w['sill_height']['value'], w['height']['value']) == (0.86, 1.22)
    (l0, l1), (r0, r1) = spans['V13'], spans['V14']
    assert centre - half - l1 >= 0.10 - 1e-9 and r0 - (centre + half) >= 0.10 - 1e-9
    assert abs((centre - l1) - (r0 - centre)) < 1e-9  # simétricas respecto del eje de la cama
    assert l0 - room['bbox'][0] >= 0.15 - 1e-9
    assert min(p[0] for p in closet['footprint']) - r1 >= 0.15
    area = sum((s[1] - s[0]) * 1.22 for s in spans.values())
    floor = (room['bbox'][2] - room['bbox'][0]) * (room['bbox'][3] - room['bbox'][1])
    assert area / floor >= 0.10


def test_two_windows_move_the_mirror_off_the_new_window(dxf_facts):
    """El espejo de la casa existente (sobre el buro izquierdo, x = 1.95–2.27 m) quedaría delante de V13: la propuesta lo
    pasa al muro poniente, sin cruzar la cama ni los buros, y la casa existente conserva el suyo."""
    from house_twin.bedroom import load_bedrooms
    from house_twin.variants import variant_bedrooms
    base = load_bedrooms()
    mine = {b['applies_to']['space']: b for b in variant_bedrooms(_two_windows(), base)}['S03']
    old = {b['applies_to']['space']: b for b in base}['S03']
    assert old['mirror']['wall']['origin'] == [1.45, 16.775]  # no se toca el original
    m = mine['mirror']
    assert m['wall']['origin'] == [1.45, 12.815] and m['wall']['into_room'] == [1, 0]
    y0, y1 = (12.815 + u for u in m['u'])
    nightstand_y0 = 16.775 - mine['nightstands']['size_m'][1] - 0.0
    assert y1 < nightstand_y0 - 0.1  # no se cruza con el buro (y ≥ 16.375 m)
    assert not (1.95 <= m['wall']['origin'][0] + m['lean_m'] <= 2.27 and y1 > 16.4)
    assert {k: v for k, v in mine.items() if k not in ('mirror', '_doc')} == {k: v for k, v in old.items() if k not in ('mirror', '_doc')}


def _patio():
    return next(v for v in load_variants() if v['id'] == 'patio-social')


def _patio_parts():
    import json
    from house_twin.extras import extras_parts
    spec = json.loads((ROOT / _patio()['specs']['extras']).read_text())
    return spec, {p['id']: p for p in extras_parts(spec)}


def _bbox(part):
    pts = part['mesh'][0]
    return [(min(p[i] for p in pts), max(p[i] for p in pts)) for i in range(3)]


def _apart(a, b, gap=0.0):
    return any(a[i][1] + gap <= b[i][0] or b[i][1] + gap <= a[i][0] for i in range(3))


def test_patio_parts_stay_inside_the_patio(dxf_facts):
    """Todo lo que propone el patio (menos los arbotantes, pegados al muro a propósito) cae dentro del polígono de S09."""
    from house_twin.finishes import _inside
    spec, parts = _patio_parts()
    patio = next(s for s in dxf_facts['spaces'] if s['id'] == 'S09')['polygon']
    lights = {lum['id'] for lum in spec['lights']}
    for pid, part in parts.items():
        if pid.split('-foco')[0] in lights:
            continue
        (x0, x1), (y0, y1), _ = _bbox(part)
        assert all(_inside(p, patio) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))), pid


def test_patio_pool_keeps_clear_of_walls_windows_and_equipment(dxf_facts):
    """La alberca queda a ≥ 0.85 m de todos los muros, a ≥ 0.90 m de las ventanas bajas de la casa (V06–V08) y sin
    chocar con la caseta, la palapa, la jardinera ni los muebles; tiene 3.8 × 1.9 m de agua a 1.22 m (≈ 8.8 m³)."""
    _, parts = _patio_parts()
    walls = [parts[f'alberca-muro-{k}'] for k in ('norte', 'sur', 'poniente', 'oriente')]
    x0 = min(_bbox(w)[0][0] for w in walls); x1 = max(_bbox(w)[0][1] for w in walls)
    y0 = min(_bbox(w)[1][0] for w in walls); y1 = max(_bbox(w)[1][1] for w in walls)
    patio = next(s for s in dxf_facts['spaces'] if s['id'] == 'S09')['polygon']
    assert y0 - 16.945 >= 0.85 and 21.05 - y1 >= 0.85 and x0 - 0.2 >= 0.85  # a los muros del patio (caras interiores)
    for oid in ('V06', 'V07', 'V08'):
        window = next(o for o in dxf_facts['openings'] if o['id'] == oid)
        wx0, wx1 = min(p[0] for p in window['footprint']), max(p[0] for p in window['footprint'])
        dx = max(wx0 - x1, x0 - wx1, 0.0)
        dy = min(abs(p[1] - y0) for p in window['footprint'])
        assert (dx * dx + dy * dy) ** 0.5 >= 0.90, oid
    water = _bbox(parts['alberca-agua'])
    inner_x, inner_y = water[0][1] - water[0][0], water[1][1] - water[1][0]
    assert abs(water[2][1] + 0.80 - 1.22) < 1e-6  # agua a 0.42 m sobre el piso + 0.80 m bajo él = 1.22 m de profundidad
    assert abs(inner_x - 3.8) < 1e-6 and abs(inner_y - 1.9) < 1e-6
    assert 8.5 <= inner_x * inner_y * 1.22 <= 9.0  # volumen de agua (m³)
    pool = [(x0, x1), (y0, y1), (0.0, 0.54)]
    for pid, part in parts.items():
        if pid.startswith(('caseta', 'jardinera', 'palapa-poste', 'barra', 'banco', 'mesa', 'banca', 'planta', 'regadera')):
            assert _apart(pool, _bbox(part), 0.20), pid  # 0.20 m para pasar y rematar


def test_patio_palapa_roof_clears_the_neighbour_the_windows_and_the_grill(dxf_facts):
    """El alero de la palapa queda a ≥ 0.25 m del muro de la colindancia y a ≥ 0.7 m de las ventanas de la recámara mayor;
    la campana del asador queda a ≥ 0.9 m por debajo del techo de palma."""
    _, parts = _patio_parts()
    roofs = [parts['palapa-techo-poniente'], parts['palapa-techo-oriente']]
    rx0, rx1 = min(_bbox(r)[0][0] for r in roofs), max(_bbox(r)[0][1] for r in roofs)
    ry0 = min(_bbox(r)[1][0] for r in roofs)
    assert 9.86 - rx1 >= 0.25 - 1e-9
    assert ry0 - 16.22 >= 0.70  # ventanas V06 y V07, en el muro y = 16.22 m
    hood_top = _bbox(parts['asador-campana'])[2][1]
    hood_x0, hood_x1 = _bbox(parts['asador-campana'])[0]
    # el techo sobre la campana: sube de 2.35 m (alero, x = 6.05 m) a 3.60 m (cumbrera, x = 7.825 m) y baja del otro lado
    z_roof = lambda x: 2.35 + (min(x, 15.65 - x) - 6.05) * (3.60 - 2.35) / (7.825 - 6.05) - 0.12  # cara de abajo
    assert min(z_roof(x) for x in (hood_x0, hood_x1)) - hood_top >= 0.9


def test_patio_proposal_uses_only_known_materials():
    """Los materiales de las piezas existen (casa o propuesta) y los nuevos solo los toma esta variante."""
    import json
    from house_twin.finishes import load_materials
    from house_twin.variants import validate
    mats = load_materials(ROOT / 'assets' / 'textures')
    spec, parts = _patio_parts()
    for pid, part in parts.items():
        assert part['material'] in mats, (pid, part['material'])
    for name in ('agua-alberca', 'concreto-alberca', 'piedra-coping', 'palma-tratada', 'madera-tratada', 'planta-verde', 'mosaico-alberca'):
        assert mats[name]['applies_to']['variant'] == 'patio-social' and 'openings' not in mats[name]['applies_to']
