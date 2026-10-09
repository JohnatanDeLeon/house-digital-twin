import json
from pathlib import Path

from house_twin.finishes import _inside, load_materials
from house_twin.walk import DATA_MARKER, build_walk, entrance

TEXTURES = Path(__file__).resolve().parent.parent / 'assets' / 'textures'


def test_walk_starts_inside_the_front_door(dxf_facts):
    start = entrance(dxf_facts)
    main = next(s for s in dxf_facts['spaces'] if s['name'] == 'Cocina + Sala + Comedor')
    assert start['door'] == 'D03'
    assert _inside(start['at'], main['polygon'])
    assert start['facing'] == [0.0, 1.0]  # hacia el fondo de la casa


def test_build_walk_writes_page_and_light_textures(dxf_facts, tmp_path):
    page = build_walk(dxf_facts, load_materials(TEXTURES), TEXTURES, tmp_path)
    html = page.read_text()
    assert DATA_MARKER not in html
    data = json.loads(html.split('const DATA = ', 1)[1].split(';\n', 1)[0])
    floor = data['materials']['piso-interior']
    assert floor['tileable'] and floor['size_m'] == [0.6, 0.9] and floor['origin_m']['x'] == 4.41
    for path in floor['maps'].values():
        assert (tmp_path / path).exists()
    assert data['materials']['puerta-entrada']['glass'] == 'vidrio-polarizado'


def test_walk_offers_proposals_next_to_the_current_house(tmp_path, dxf_facts):
    import json as _json
    from house_twin.walk import build_walk
    facts = dxf_facts
    variant = {'id': 'v', 'name': 'Propuesta', 'description': 'd', 'changes': [
        {'opening': 'D03', 'part': 'leaf', 'material': 'nueva'}, {'opening': 'V01', 'part': 'glass', 'material': 'otro'}]}
    page = build_walk(facts, {}, tmp_path, tmp_path / 'out', variants=[variant]).read_text()
    data = _json.loads(page.split('const DATA = ')[1].split(';\n')[0])
    focus = data['variants'][0].pop('focus')
    assert data['variants'] == [{'id': 'v', 'name': 'Propuesta', 'description': 'd', 'disclaimer': None, 'overrides': {'D03': 'nueva'}}]
    door = next(o for o in facts['openings'] if o['id'] == 'D03')
    assert focus['at'][1] > max(p[1] for p in door['footprint']) and focus['facing'] == [0.0, -1.0]  # en la sala, mirando la puerta


def test_doors_swing_toward_the_space_they_open_into(dxf_facts):
    from house_twin.walk import doors
    by_id = {d['id']: d for d in doors(dxf_facts)}
    assert by_id['D03']['leaves'][0]['opens_toward'] == [0.0, 1.0]  # la puerta de la entrada abre hacia la sala
    assert len(by_id['D12']['leaves']) == 2 and all(l['opens_toward'][1] > 0 for l in by_id['D12']['leaves'])
    assert by_id['D10']['leaves'][0]['assumed'] and not by_id['D03']['leaves'][0]['assumed']


def test_walk_starts_on_the_street_in_front_of_the_porch_gate(dxf_facts):
    from house_twin.walk import street_start
    start = street_start(dxf_facts)
    assert start['door'] == 'D01' and start['at'][1] < 0 and start['facing'] == [0.0, 1.0]
