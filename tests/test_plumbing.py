from house_twin.plumbing import load_shower_spec, shower_mesh, valve_meshes


def _signed_volume(points, faces):
    v = 0.0
    for f in faces:
        a = points[f[0]]
        for b, c in zip((points[i] for i in f[1:-1]), (points[i] for i in f[2:])):
            v += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    return v


def test_valves_are_on_the_wall_at_owner_height():
    spec = load_shower_spec()
    meshes = valve_meshes(spec)
    assert len(meshes) == 2
    centres = []
    for points, faces in meshes:
        assert _signed_volume(points, faces) > 0  # normales hacia afuera
        assert min(p[0] for p in points) < 4.24 <= max(p[0] for p in points) + 1e-9  # del muro hacia el baño
        centres.append(sum(p[1] for p in points) / len(points))
        assert abs(sum(p[2] for p in points) / len(points) - 1.0) < 0.01
    assert abs(abs(centres[0] - centres[1]) - 0.15) < 1e-6  # 15 cm entre llaves (dueño)


def test_shower_head_hangs_below_the_outlet_and_inside_the_bathroom():
    spec = load_shower_spec()
    points, faces = shower_mesh(spec)
    assert max(p[2] for p in points) <= 1.90 + spec['shower']['pipe_radius_m'] + 1e-9
    assert min(p[0] for p in points) > 2.99  # no atraviesa el muro de enfrente
    assert _signed_volume(points, faces) > 0


def _fixture(kind):
    return {'id': 'X', 'kind': kind, 'space': 'S05', 'back_centre': [2.99, 11.667], 'facing': [1, 0]}


def test_toilet_and_basin_stand_in_front_of_their_wall():
    from house_twin.plumbing import faucet_mesh, load_sanitary_specs, sanitary_mesh, spec_for
    spec = spec_for(load_sanitary_specs(), 'S05')
    for kind, top in (('toilet', 0.775), ('basin', 0.835)):
        points, faces = sanitary_mesh(spec, _fixture(kind))
        assert min(p[0] for p in points) >= 2.99 - 1e-9  # no se mete en el muro
        assert min(p[2] for p in points) >= -1e-9 and abs(max(p[2] for p in points) - top) < 1e-6
        assert _signed_volume(points, faces) > 0
    points, faces = faucet_mesh(spec, _fixture('basin'))
    assert _signed_volume(points, faces) > 0


def test_half_bath_has_its_own_fixtures():
    from house_twin.plumbing import lever_mesh, load_sanitary_specs, material_of, spec_for
    specs = load_sanitary_specs()
    half, main = spec_for(specs, 'S07'), spec_for(specs, 'S05')
    assert half is not main
    assert (material_of(half, 'toilet'), material_of(half, 'basin')) == ('porcelana-blanca', 'porcelana-almendra')
    assert material_of(main, 'toilet') == material_of(main, 'basin') == 'porcelana-hueso'
    fixture = {'id': 'X', 'kind': 'toilet', 'space': 'S07', 'back_centre': [8.563, 2.325], 'facing': [1, 0]}
    points, faces = lever_mesh(half, fixture)
    assert _signed_volume(points, faces) > 0 and min(p[1] for p in points) < 2.325  # del lado sur (izquierda de frente)
    assert lever_mesh(main, fixture) is None
