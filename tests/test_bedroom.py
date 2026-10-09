from house_twin.bedroom import bedroom_parts, load_bedrooms
from tests.test_kitchen import _signed_volume


def test_master_bedroom_furniture_fits_the_room():
    spec = next(s for s in load_bedrooms() if s['applies_to']['space'] == 'S02')
    for p in bedroom_parts(spec):
        points, faces = p['mesh']
        assert _signed_volume(points, faces) > 0, p['id']
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        assert 5.82 - 1e-6 <= min(xs) and max(xs) <= 9.86 + 1e-6, p['id']
        assert 12.04 - 1e-6 <= min(ys) and max(ys) <= 16.055 + 1e-6, p['id']


def test_open_closet_spans_the_plan_front():
    spec = next(s for s in load_bedrooms() if s['applies_to']['space'] == 'S02')
    closet = next(p for p in bedroom_parts(spec) if p['id'] == 'recamara-closet')
    ys = [q[1] for q in closet['mesh'][0]]
    assert abs((max(ys) - min(ys)) - 2.95) < 1e-6  # el frente del plano


def test_s03_furniture_fits_and_tv_is_85_inches():
    from house_twin.living import _tv
    spec = next(s for s in load_bedrooms() if s['applies_to']['space'] == 'S03')
    for p in bedroom_parts(spec):
        points, faces = p['mesh']
        assert _signed_volume(points, faces) > 0, p['id']
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        assert 1.45 - 1e-6 <= min(xs) and max(xs) <= 5.02, p['id']  # entre el muro poniente y el closet
        assert 12.815 - 1e-6 <= min(ys) and max(ys) <= 16.775 + 1e-6, p['id']
    _, _, (w, h) = _tv(spec['tv'])
    assert abs((w ** 2 + h ** 2) ** 0.5 / 0.0254 - 85) < 1e-6  # dueño
