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


def test_r3_l_desk_is_160_by_100_in_the_corner():
    spec = next(s for s in load_bedrooms() if s['applies_to']['space'] == 'S04')
    parts = {p['id']: p for p in bedroom_parts(spec)}
    pts = parts['r3-escritorio']['mesh'][0]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    assert (round(max(xs), 3), round(max(ys), 3)) == (9.86, 11.86)  # en la esquina oriente-norte
    assert (round(max(ys) - min(ys), 3), round(max(xs) - min(xs), 3)) == (1.6, 1.0)  # dueño: 160 × 100
    for p in parts.values():
        q = p['mesh'][0]
        assert 5.79 - 1e-6 <= min(v[0] for v in q) and max(v[0] for v in q) <= 9.86 + 1e-6, p['id']
        assert 8.14 - 1e-6 <= min(v[1] for v in q) and max(v[1] for v in q) <= 11.86 + 1e-6, p['id']


def test_office_objects_are_detailed_and_closed():
    spec = next(s for s in load_bedrooms() if s['applies_to']['space'] == 'S04')
    parts = bedroom_parts(spec)
    ids = {p['id'] for p in parts}
    assert {'r3-teclado', 'r3-impresora-tinta-cian', 'r3-caminadora-franja', 'r3-silla-base', 'r3-monitores-pantalla-izq', 'r3-audifonos'} <= ids
    keyboard = next(p for p in parts if p['id'] == 'r3-teclado')
    assert len(keyboard['mesh'][1]) > 6 * 80  # teclas una por una, no un bloque
    for p in parts:
        assert _signed_volume(*p['mesh']) >= 0, p['id']
