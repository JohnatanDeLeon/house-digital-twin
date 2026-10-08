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
        'white_reference': {'box_px': [0, 0, 5, 5], 'albedo_srgb': [235, 235, 235]},
        'relief': {'panels': [{'rect_frac': [0.2, 0.2, 0.8, 0.8]}], 'groove_depth_mm': 4, 'bevel_rise_mm': 3, 'bevel_px': 5, 'grain_mm': 0.1},
        'roughness': {'base': 0.45, 'grain': 0.08}, 'assumptions': ['tamaño de prueba'],
    }
    (tmp_path / 'spec.json').write_text(json.dumps(spec))
    out = textures.build_texture(tmp_path / 'spec.json', photos_root=tmp_path)
    assert Image.open(out / 'basecolor.jpg').size == (50, 100)
    assert Image.open(out / 'normal.png').size == (25, 50)
    material = json.loads((out / 'material.json').read_text())
    assert material['assumptions'] == ['tamaño de prueba'] and material['applies_to']['openings'] == ['D01']
