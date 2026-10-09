from house_twin.kitchen import kitchen_parts, load_kitchen


def _signed_volume(points, faces):
    v = 0.0
    for f in faces:
        a = points[f[0]]
        for b, c in zip((points[i] for i in f[1:-1]), (points[i] for i in f[2:])):
            v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return v


def test_kitchen_parts_are_closed_and_inside_the_kitchen():
    parts = kitchen_parts(load_kitchen())
    ids = {p['id'] for p in parts}
    assert {'cocina-estufa', 'cocina-refrigerador', 'cocina-barra-tarja', 'cocina-barra-cubierta-1'} <= ids
    for p in parts:
        points, faces = p['mesh']
        assert _signed_volume(points, faces) > 0, p['id']  # normales hacia afuera
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        assert 1.375 - 1e-6 <= min(xs) and max(xs) <= 4.225 + 1e-6, p['id']  # entre los muros de la cocina
        assert 6.875 - 1e-6 <= min(ys) and max(ys) <= 10.055 + 1e-6, p['id']


def test_counter_and_uppers_heights_follow_the_photo():
    parts = {p['id']: p for p in kitchen_parts(load_kitchen())}
    top = max(q[2] for q in parts['cocina-barra-cubierta-2']['mesh'][0])
    assert abs(top - 0.98) < 1e-6  # cubierta a 0.90 m más el zoclo trasero de 8 cm
    assert abs(min(q[2] for q in parts['cocina-barra-alto-1']['mesh'][0]) - 1.54) < 1e-6
    stove = parts['cocina-estufa']['mesh'][0]
    assert abs((max(q[0] for q in stove) - min(q[0] for q in stove)) - 0.76) < 0.01  # sin perillas: 30"


def test_ifc_with_kitchen_is_valid(dxf_facts):
    import ifcopenshell.validate
    from house_twin.ifc_export import build_ifc
    model = build_ifc(dxf_facts, kitchen=load_kitchen())
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(model, log)
    assert log.statements == []
    assert {e.Name for e in model.by_type('IfcElectricAppliance')} == {'cocina-estufa', 'cocina-refrigerador'}
