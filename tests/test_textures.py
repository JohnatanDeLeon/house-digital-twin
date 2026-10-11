import json
from pathlib import Path

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


def test_sheet_door_draws_layout_without_copying_the_photo():
    spec = {'seed': 2, 'px_per_m': 1000, 'bevel_mm': 0.5,
            'layout': [
                {'kind': 'level', 'rect_frac': [0.2, 0.1, 0.8, 0.4], 'height_mm': -4},
                {'kind': 'joints', 'rect_frac': [0.2, 0.1, 0.8, 0.4], 'x_frac': [0.5],
                 'profile': [{'offset_frac_w': 0, 'width_frac_w': 0.05, 'height_mm': -2, 'shape': 'v'}]},
                {'kind': 'ribs', 'rect_frac': [0.2, 0.6, 0.8, 0.9], 'x_frac': [0.5], 'base_frac_w': 0.1, 'top_frac_w': 0.05, 'height_mm': 6},
                {'kind': 'welds', 'points_frac': [[0.1, 0.95]], 'diameter_frac_w': 0.05, 'height_mm': 2,
                 'rust_share': 1.0, 'rust_spread': 1.5},
            ],
            'paint': {'variation': 0.0, 'orange_peel_mm': 1, 'orange_peel_height_mm': 0},
            'cavity': {'radius_mm': 5, 'depth_mm': 2, 'darkening': 0.5}, 'dust_opacity': 0.4,
            'roughness': {'base': 0.4, 'rust': 0.9, 'dust': 0.7}}
    colors = {'paint': [30, 31, 34], 'rust': [120, 60, 40], 'dust': [90, 90, 90]}
    base, height, rough, alpha = textures.procedural_sheet_door(spec, (200, 400), colors)
    assert alpha is None                                         # toda lámina: sin huecos
    px = np.asarray(base).astype(int)
    assert height[100, 60] == pytest.approx(-0.004, abs=1e-4)   # tablero hundido
    assert height[100, 100] < height[100, 60]                    # ranura de la duela
    assert height[300, 100] == pytest.approx(0.006, abs=2e-4)    # cresta de la costilla
    assert np.abs(px[20, 20] - colors['paint']).max() <= 2       # pintura plana: color medido, sin brillos
    assert px[380, 20, 0] > px[380, 20, 2] + 20 and rough[380, 20] > 0.45  # óxido (con ruido) en la soldadura


def test_weld_lines_spread_points_at_pitch():
    points = textures._weld_points({'lines': [{'from': [0.1, 0.5], 'to': [0.5, 0.5], 'pitch_frac': 0.1}],
                                    'points_frac': [[0.9, 0.9]]})
    assert points[0] == (0.9, 0.9) and len(points) == 6
    assert points[1] == pytest.approx((0.1, 0.5)) and points[-1] == pytest.approx((0.5, 0.5))


def test_glass_takes_its_material_not_the_photo(tmp_path, monkeypatch):
    monkeypatch.setattr(textures, 'TEXTURES_DIR', tmp_path / 'out')
    (tmp_path / 'out' / 'vidrio').mkdir(parents=True)
    (tmp_path / 'out' / 'vidrio' / 'material.json').write_text(json.dumps({'pbr': {'basecolor_srgb': [70, 72, 76], 'roughness': 0.03}}))
    photo = np.full((400, 300, 3), 40, np.uint8)
    photo[150:250, 100:200] = (200, 150, 120)  # «reflejo» en el vidrio
    Image.fromarray(photo).save(tmp_path / 'foto.jpg')
    spec = {
        'name': 'hoja', 'applies_to': {'openings': ['D01'], 'source': 'test'}, 'photo': 'foto.jpg',
        'corners_px': {'top_left': [0, 0], 'top_right': [300, 0], 'bottom_right': [300, 400], 'bottom_left': [0, 400]},
        'size_m': {'width': 0.3, 'height': 0.4, 'source': 'test'}, 'px_per_m': 500, 'color': {'as_shot': True},
        'relief': {'type': 'flat', 'grain_mm': 0.2}, 'roughness': {'base': 0.7, 'grain': 0.1},
        'opacity': {'holes': [[0.25, 0.25, 0.75, 0.75]], 'glass_material': 'vidrio'},
    }
    (tmp_path / 'spec.json').write_text(json.dumps(spec))
    out = textures.build_texture(tmp_path / 'spec.json', photos_root=tmp_path)
    base = np.asarray(Image.open(out / 'basecolor.jpg')).astype(int)
    assert np.abs(base[100, 75] - [70, 72, 76]).max() <= 3       # el vidrio lleva su color, no el reflejo
    assert np.abs(base[10, 10] - 40).max() <= 3                  # el marco sí sale de la foto
    rough = np.asarray(Image.open(out / 'roughness.png')).astype(float) / 255
    assert rough[50, 37] == pytest.approx(0.03, abs=0.01)


def test_garment_texture_cuts_the_silhouette_and_marks_the_foil():
    folder = Path(__file__).resolve().parent.parent / 'assets' / 'textures' / 'playera-venom'
    material = json.loads((folder / 'material.json').read_text())
    alpha = np.asarray(Image.open(folder / 'opacity.png')) > 128
    metal = np.asarray(Image.open(folder / 'metallic.png')) > 128
    assert 0.45 < alpha.mean() < 0.75  # la playera, sin la sábana
    assert 0.01 < material['source']['print_coverage'] < 0.06  # el estampado es una parte chica
    assert not alpha[0, 0] and alpha[alpha.shape[0] // 2, alpha.shape[1] // 2]
    assert metal.any()


def test_ink_print_keeps_its_colors_and_is_not_metallic():
    folder = Path(__file__).resolve().parent.parent / 'assets' / 'textures' / 'playera-venom-lengua'
    material = json.loads((folder / 'material.json').read_text())
    assert 'metallic' not in material['maps'] and not (folder / 'metallic.png').exists()
    base = np.asarray(Image.open(folder / 'basecolor.jpg')).astype(int)
    alpha = np.asarray(Image.open(folder / 'opacity.png')) > 128
    red = alpha & (base[..., 0] - base[..., 1] > 80)
    assert red.sum() > 1000  # la lengua sigue roja: la tinta no se repinta de un solo color


def _tee_mask(H=300, W=400):
    """Playera de prueba extendida: cuerpo de 200 px y mangas horizontales que salen 80 px de cada costado."""
    alpha = np.zeros((H, W), bool)
    alpha[40:290, 100:300] = True   # cuerpo
    alpha[40:110, 20:100] = True    # manga izquierda
    alpha[40:110, 300:380] = True   # manga derecha
    return alpha


def test_hanging_sleeves_drop_beside_the_body_without_folding_over_it():
    import math
    from house_twin.hanging import hang_layers
    alpha = _tee_mask()
    color = np.zeros(alpha.shape + (3,))
    color[..., 0] = np.arange(alpha.shape[1]) / alpha.shape[1]  # rojo según la columna de origen
    layers, hung = hang_layers({'basecolor': color}, alpha, 60)
    body = np.zeros_like(alpha)
    body[40:290, 100:300] = True
    assert (hung & body).sum() == body.sum()                                        # el cuerpo queda entero
    assert np.allclose(layers['basecolor'][body][..., 0], color[body][..., 0])     # y la manga no se le monta encima
    cols = np.nonzero(hung.any(axis=0))[0]
    reach = 80 * math.cos(math.radians(60))
    assert cols.min() >= 100 - reach - 2 and cols.max() <= 299 + reach + 2       # sobresale solo lo que da el ángulo
    rows_left = np.nonzero(hung[:, :100].any(axis=1))[0]
    assert rows_left.min() <= 42 and rows_left.max() > 110 + 60                    # sigue cosida al hombro y cae


def test_hanging_turns_the_sleeve_normals_with_the_fabric():
    from house_twin.hanging import hang_layers
    alpha = _tee_mask()
    flat = np.zeros(alpha.shape + (3,))
    flat[...] = [1.0, 0.5, 1.0]  # normal que apunta a la derecha de la imagen (x = +1)
    layers, hung = hang_layers({'normal': flat}, alpha, 60)
    left_sleeve = hung.copy()
    left_sleeve[:, 100:] = False
    n = layers['normal'][left_sleeve] * 2 - 1
    assert np.allclose(n[:, 1], np.sin(np.radians(60)), atol=0.02)  # la manga izquierda giró 60° en contra del reloj


def test_template_tee_is_plain_and_shared_by_the_designed_tee():
    root = Path(__file__).resolve().parent.parent / 'assets' / 'textures'
    base = np.asarray(Image.open(root / 'playera-base' / 'opacity.png')) > 128
    tee = np.asarray(Image.open(root / 'playera-venom-lengua' / 'opacity.png')) > 128
    assert np.array_equal(base, tee)  # misma silueta: solo cambia el estampado
    color = np.asarray(Image.open(root / 'playera-base' / 'basecolor.jpg')).astype(int)
    assert not (base & (color[..., 0] - color[..., 1] > 80)).any()  # el molde ya no tiene la lengua roja
    material = json.loads((root / 'playera-venom-lengua' / 'material.json').read_text())
    assert material['source']['template'] == 'playera-base' and material['source']['from'] == 'product'


def _template_maps():
    from house_twin.hanging import load_maps
    from house_twin.textures import TEXTURES_DIR
    return load_maps(TEXTURES_DIR / 'playera-base')


def test_art_design_uses_its_transparency_and_lands_where_the_spec_says(tmp_path):
    from house_twin.garment_designs import _anchor, design_from_art, place_design
    art = np.zeros((100, 200, 4), np.uint8)
    art[..., :3] = [255, 0, 0]
    art[20:80, 50:150, 3] = 255  # rectángulo rojo opaco dentro de un PNG transparente
    Image.fromarray(art, 'RGBA').save(tmp_path / 'dibujo.png')
    material, layers, alpha = _template_maps()
    rgb, cover, placement = design_from_art({'image': 'dibujo.png', 'width_m': 0.2, 'top_m': 0.15}, tmp_path)
    assert cover.shape == (60, 100) and placement['offset_x_m'] == 0.0  # recortado a lo que se ve
    out = place_design(layers, alpha, material['px_per_m'], (rgb, cover, placement), 0.6)
    ppm, (cx, top) = material['px_per_m'], _anchor(alpha)
    y, x = round(top + 0.15 * ppm + 0.06 * ppm), round(cx)  # el centro del rectángulo (0.2 × 0.12 m)
    assert np.allclose(out['basecolor'][y, x], [1, 0, 0], atol=0.02)
    assert np.allclose(out['roughness'][y, x], 0.6, atol=0.01)
    assert np.allclose(out['basecolor'][~alpha], layers['basecolor'][~alpha])  # fuera de la playera no se pinta


def test_art_design_without_transparency_drops_its_background(tmp_path):
    from house_twin.garment_designs import design_from_art
    art = np.full((80, 80, 3), 30, np.uint8)  # fondo oscuro liso
    art[20:60, 20:60] = [240, 200, 40]
    Image.fromarray(art).save(tmp_path / 'dibujo.png')  # RGB, sin canal de transparencia
    _, cover, placement = design_from_art({'image': 'dibujo.png'}, tmp_path)
    assert cover.shape == (40, 40) and cover.min() > 0.99
    assert placement['source'].startswith('supuesta')


def test_designed_tee_on_another_fabric_color_is_dyed_and_gets_its_own_back():
    root = Path(__file__).resolve().parent.parent / 'assets' / 'textures'
    material = json.loads((root / 'playera-i-love-julio' / 'material.json').read_text())
    gray = material['source']['placement']['fabric_srgb']
    assert all(120 < c < 170 for c in gray)  # la tela gris de la imagen, no el negro del molde
    for name in ('playera-i-love-julio', 'playera-i-love-julio-espalda'):
        base = np.asarray(Image.open(root / name / 'basecolor.jpg')).astype(float)
        alpha = np.asarray(Image.open(root / name / 'opacity.png')) > 128
        assert np.abs(np.median(base[alpha], axis=0) - gray).max() < 15  # teñida, también la espalda
    front = np.asarray(Image.open(root / 'playera-i-love-julio' / 'basecolor.jpg')).astype(int)
    dark = (front.sum(-1) < 120) & alpha
    red = (front[..., 0] - front[..., 1] > 100) & alpha
    assert dark.sum() > 2000 and red.sum() > 2000  # el estampado oscuro y rojo se detectó por contraste
