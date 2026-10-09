from house_twin.living import _tv, living_parts, load_living
from tests.test_kitchen import _signed_volume


def test_sofa_is_220_by_220_and_inside_the_living_room():
    parts = {p['id']: p for p in living_parts(load_living())}
    points, faces = parts['sala-sofa']['mesh']
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    assert abs((max(xs) - min(xs)) - 2.2) < 1e-6 and abs((max(ys) - min(ys)) - 2.2) < 1e-6  # dueño
    assert max(ys) <= 7.93 and max(xs) <= 8.45  # contra el muro de la recámara 3, antes del escalón del tragaluz
    assert _signed_volume(points, faces) > 0


def test_tv_is_75_inches_on_the_east_wall():
    spec = load_living()
    _, screen, (w, h) = _tv(spec['tv'])
    assert abs((w ** 2 + h ** 2) ** 0.5 / 0.0254 - 75) < 1e-6
    xs = [p[0] for p in screen[0]]
    assert 9.6 < min(xs) and max(xs) < 9.763  # sobre el muro de x = 9.763 m
