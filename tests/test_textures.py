import json

import numpy as np
import pytest
from PIL import Image

from house_twin import textures


def test_rectify_maps_each_corner_to_its_corner():
    photo = Image.new('RGB', (400, 300), 'black')
    corners = {'top_left': (50, 40), 'top_right': (350, 60), 'bottom_right': (330, 260), 'bottom_left': (70, 250)}
    colors = {'top_left': (255, 0, 0), 'top_right': (0, 255, 0), 'bottom_right': (0, 0, 255), 'bottom_left': (255, 255, 0)}
    for k, (x, y) in corners.items():
        photo.paste(colors[k], (x - 4, y - 4, x + 5, y + 5))
    out = np.asarray(textures.rectify(photo, corners, (100, 200)))
    for k, (x, y) in {'top_left': (1, 1), 'top_right': (98, 1), 'bottom_right': (98, 198), 'bottom_left': (1, 198)}.items():
        nearest = min(colors, key=lambda c: np.abs(out[y, x].astype(int) - colors[c]).sum())
        assert nearest == k, (k, out[y, x])  # interpolación bicúbica: se compara con el color más cercano


def test_normal_map_is_opengl():
    flat = np.asarray(textures._normal_map(np.zeros((20, 20)), 1000))
    assert np.allclose(flat[10, 10], (128, 128, 255), atol=1)
    rises_right = np.tile(np.linspace(0, 0.01, 20), (20, 1))
    rises_down = rises_right.T
    assert np.asarray(textures._normal_map(rises_right, 1000))[10, 10, 0] < 128  # la normal mira a la izquierda
    assert np.asarray(textures._normal_map(rises_down, 1000))[10, 10, 1] > 128   # sube hacia abajo: mira hacia arriba (+V)


def test_raised_panel_profile():
    relief = {'groove_depth_mm': 4, 'bevel_rise_mm': 3, 'bevel_px': 10}
    h = textures._panel_height((100, 100), [[20, 20, 80, 80]], relief)
    assert h[5, 5] == 0                              # bastidor
    assert h[50, 20] == pytest.approx(-0.004)        # ranura del contorno
    assert h[50, 50] == pytest.approx(-0.001)        # campo del tablero: ranura + bisel


def test_build_texture_writes_maps_and_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(textures, 'TEXTURES_DIR', tmp_path / 'out')
    Image.new('RGB', (300, 400), (120, 80, 50)).save(tmp_path / 'foto.jpg')
    spec = {
        'name': 'prueba', 'applies_to': {'openings': ['D01'], 'source': 'test'},
        'photo': 'foto.jpg', 'corners_px': {'top_left': [10, 10], 'top_right': [290, 10], 'bottom_right': [290, 390], 'bottom_left': [10, 390]},
        'size_m': {'width': 0.1, 'height': 0.2, 'source': 'test'}, 'px_per_m': 500,
        'color': {'white_reference': {'box_px': [0, 0, 5, 5], 'albedo_srgb': [235, 235, 235]}},
        'relief': {'type': 'panels', 'panels': [{'rect_frac': [0.2, 0.2, 0.8, 0.8]}], 'groove_depth_mm': 4, 'bevel_rise_mm': 3, 'bevel_px': 5, 'grain_mm': 0.1},
        'roughness': {'base': 0.45, 'grain': 0.08}, 'assumptions': ['tamaño de prueba'],
    }
    (tmp_path / 'spec.json').write_text(json.dumps(spec))
    out = textures.build_texture(tmp_path / 'spec.json', photos_root=tmp_path)
    assert Image.open(out / 'basecolor.jpg').size == (50, 100)
    assert Image.open(out / 'normal.png').size == (25, 50)
    material = json.loads((out / 'material.json').read_text())
    assert material['assumptions'] == ['tamaño de prueba'] and material['applies_to']['openings'] == ['D01']


def test_tile_grid_relief_is_seamless():
    h, grout = textures._grid_height((300, 200), {'cols': 2, 'rows': 3, 'grout_frac': 0.04}, {'grout_depth_mm': 1.5, 'edge_round_px': 3})
    assert grout[0, 50] and grout[50, 0] and grout[100, 50] and grout[50, 100]  # bordes y ejes de junta
    assert h[50, 50] == 0 and h[0, 50] == pytest.approx(-0.0015)
    assert np.allclose(h[:, 0], h[:, -1], atol=1e-4) and np.allclose(h[0], h[-1], atol=1e-4)  # se repite sin costura


def test_flatten_lighting_removes_gradient():
    ramp = np.linspace(80, 200, 120)[:, None, None] * np.ones((120, 90, 3))
    flat = np.asarray(textures.flatten_lighting(Image.fromarray(ramp.astype(np.uint8)), exclude_darkest=0)).astype(float)
    assert flat[:10].mean() == pytest.approx(flat[-10:].mean(), abs=3)


def test_features_relief_and_opacity():
    shape = (200, 100)
    h = textures._features_height(shape, [
        {'kind': 'recess', 'rect_frac': [0.1, 0.5, 0.9, 0.9], 'depth_mm': 3},
        {'kind': 'grooves', 'rect_frac': [0.1, 0.5, 0.9, 0.9], 'x_frac': [0.5], 'width_frac': 0.04, 'depth_mm': 1.5}])
    assert h[20, 50] == 0 and h[150, 30] == pytest.approx(-0.003) and h[150, 50] == pytest.approx(-0.0045)
    mask = textures._opacity(shape, {'holes': [[0.1, 0.1, 0.9, 0.4]], 'opaque': [[0.48, 0.1, 0.52, 0.4]]})
    assert mask[50, 20] == 0 and mask[50, 50] == 1 and mask[150, 50] == 1


def test_constant_material_samples_darkest_part(tmp_path, monkeypatch):
    monkeypatch.setattr(textures, 'TEXTURES_DIR', tmp_path / 'out')
    photo = Image.new('RGB', (100, 100), (200, 200, 200))  # muro blanco de referencia
    photo.paste((20, 20, 20), (50, 0, 100, 100))            # perfil negro
    photo.paste((230, 230, 230), (90, 0, 100, 100))         # salpicadura de pintura sobre el perfil
    photo.save(tmp_path / 'foto.png')
    spec = {'name': 'perfil', 'kind': 'constant', 'applies_to': {}, 'photo': 'foto.png',
            'color': {'white_reference': {'box_px': [0, 0, 40, 100], 'albedo_srgb': [200, 200, 200]}},
            'pbr': {'sample': {'box_px': [50, 0, 100, 100], 'darkest_fraction': 0.5}, 'roughness': 0.35}}
    (tmp_path / 'spec.json').write_text(json.dumps(spec))
    out = textures.build_texture(tmp_path / 'spec.json', photos_root=tmp_path)
    material = json.loads((out / 'material.json').read_text())
    assert material['pbr']['basecolor_srgb'] == [20, 20, 20] and material['pbr']['roughness'] == 0.35


def test_mosaic_subgrid_sets_channel_roughness(tmp_path, monkeypatch):
    monkeypatch.setattr(textures, 'TEXTURES_DIR', tmp_path / 'out')
    Image.new('RGB', (200, 200), (150, 140, 130)).save(tmp_path / 'foto.png')
    spec = {'name': 'mosaico', 'applies_to': {}, 'photo': 'foto.png',
            'corners_px': {'top_left': [0, 0], 'top_right': [200, 0], 'bottom_right': [200, 200], 'bottom_left': [0, 200]},
            'grid': {'cols': 1, 'rows': 1, 'grout_frac': 0.05, 'subgrid': {'per_tile': 4, 'line_frac': 0.2, 'depth_mm': 0.8, 'edge_round_px': 1}},
            'size_m': {'width': 0.2, 'height': 0.2}, 'px_per_m': 1000,
            'color': {'white_reference': {'box_px': [0, 0, 200, 200], 'albedo_srgb': [150, 140, 130]}},
            'relief': {'type': 'grid', 'grout_depth_mm': 2, 'edge_round_px': 2, 'grain_mm': 0},
            'roughness': {'base': 0.75, 'grain': 0, 'channel': 0.25, 'grout': 0.9}}
    (tmp_path / 'spec.json').write_text(json.dumps(spec))
    out = textures.build_texture(tmp_path / 'spec.json', photos_root=tmp_path)
    r = np.asarray(Image.open(out / 'roughness.png')).astype(float) / 255
    assert r[50, 0] == pytest.approx(0.9, abs=0.02)    # junta entre losetas (borde; el mapa va a media resolución)
    assert r[50, 25] == pytest.approx(0.25, abs=0.02)  # canal entre cuadritos (1/4 de la loseta)
    assert r[60, 60] == pytest.approx(0.75, abs=0.02)  # cuadrito


def test_make_seamless_matches_opposite_edges():
    # rampa de 0 a 240 en x: al repetirla sin tratar salta 240 entre el borde derecho y el izquierdo
    ramp = np.tile(np.linspace(0, 240, 80), (64, 1))
    image = Image.fromarray(np.dstack([ramp] * 3).astype(np.uint8))
    out = np.asarray(textures.make_seamless(image)).astype(float)[..., 0]
    wrap_jump = np.abs(out[:, -1] - out[:, 0]).max()
    interior_jump = np.abs(np.diff(out, axis=1)).max()
    assert wrap_jump <= 2 and interior_jump <= 6  # ni costura al repetir ni costura nueva en el centro


def test_opacity_rings_and_dark_refinement():
    shape = (200, 100)
    ring = {'holes': [[0, 0, 1, 1]], 'rings': [{'center_frac': [0.5, 0.25], 'radius_frac_w': 0.3, 'thickness_frac_w': 0.04}]}
    mask = textures._opacity(shape, ring)
    assert mask[50, 80] == 1 and mask[50, 50] == 0 and mask[150, 80] == 0  # en el arillo, en su centro y fuera
    # la barra modelada es más ancha que la real: solo queda lo oscuro de la foto (la barra real mide 4 px)
    photo = np.full((200, 100, 3), 220, np.uint8)
    photo[:, 48:52] = 15
    bar = {'holes': [[0, 0, 1, 1]], 'opaque': [[0.44, 0, 0.56, 1]], 'refine_dark': {'dilate_px': 2, 'max_luminance': 80}}
    refined = textures._opacity(shape, bar, Image.fromarray(photo))
    assert refined[100, 50] == 1 and refined[100, 45] == 0 and refined[100, 20] == 0


def test_procedural_stucco_is_tileable_and_reproducible():
    spec = {'seed': 1, 'px_per_m': 1000,
            'plates': {'size_m': 0.03, 'coverage': 0.45, 'edge_softness': 0.12, 'height_mm': 3.0},
            'grain': {'size_m': 0.0015, 'height_mm': 0.25},
            'color': {'albedo_srgb': [222, 222, 220], 'crevice_darkening': 0.12}, 'roughness': {'base': 0.9}}
    base, height, rough = textures.procedural_stucco(spec, (200, 160))
    assert height.shape == (160, 200) and base.size == (200, 160)
    # periódico: el salto al repetir es como un paso interior
    assert np.abs(height[:, -1] - height[:, 0]).mean() < 3 * np.abs(np.diff(height, axis=1)).mean()
    again, _, _ = textures.procedural_stucco(spec, (200, 160))
    assert np.array_equal(np.asarray(base), np.asarray(again))  # misma semilla, mismo resultado
    assert 0 < (height > 0.0015).mean() < 0.8                    # hay placas, pero no cubren todo
