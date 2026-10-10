from house_twin.electrical import load_device_spec
from house_twin.laundry import laundry_parts, load_laundry
from tests.test_kitchen import _signed_volume


def _bbox(part):
    pts = part['mesh'][0]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def test_owner_measures_are_exact():
    parts = {p['id']: p for p in laundry_parts(load_laundry(), load_device_spec())}
    (x0, y0, _), (x1, y1, _) = _bbox(parts['lavanderia-lavadora'])
    assert (round(y1 - y0, 3), round(x1 - x0, 3)) == (0.95, 0.5)  # dueño: 95 × 50
    (x0, y0, _), (x1, y1, _) = _bbox(parts['lavanderia-secadora'])
    assert (round(y1 - y0, 3), round(x1 - x0, 3)) == (0.75, 0.65)  # dueño: 75 × 65
    (x0, _, z0), (x1, _, z1) = _bbox(parts['lavanderia-boiler'])
    assert abs((x1 - x0) - 0.30) < 1e-3 and z0 == 0.6  # 30 cm de diámetro sobre base de 60 cm
    tank = [p for p in parts['lavanderia-boiler']['mesh'][0] if abs(((p[0] - 2.62) ** 2 + (p[1] - 12.305) ** 2) ** 0.5 - 0.15) < 1e-6]
    assert abs(max(p[2] for p in tank) - min(p[2] for p in tank) - 1.0) < 1e-9  # 1.00 m de alto


def test_laundry_parts_fit_and_do_not_overlap():
    parts = laundry_parts(load_laundry(), load_device_spec())
    boxes = {}
    for p in parts:
        assert _signed_volume(*p['mesh']) > 0, p['id']
        lo, hi = _bbox(p)
        assert 1.205 - 1e-6 <= lo[0] and hi[0] <= 2.82 + 1e-6 and 10.225 - 1e-6 <= lo[1] and hi[1] <= 12.625 + 1e-6, p['id']
        boxes[p['id']] = (lo, hi)
    floor = ['lavanderia-lavadora', 'lavanderia-secadora', 'lavanderia-boiler-base', 'lavanderia-gas']
    for i, a in enumerate(floor):
        for b in floor[i + 1:]:
            (alo, ahi), (blo, bhi) = boxes[a], boxes[b]
            assert ahi[0] <= blo[0] + 1e-6 or bhi[0] <= alo[0] + 1e-6 or ahi[1] <= blo[1] + 1e-6 or bhi[1] <= alo[1] + 1e-6, (a, b)
