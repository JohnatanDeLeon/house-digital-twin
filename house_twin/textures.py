"""Texturas PBR a partir de fotos de la casa: color base, rugosidad y relieve (normal map).

Cada textura se describe en un JSON de `sources/texturas/` (esquinas en la foto, tamaño real,
referencia de blanco, parches y relieve) y se regenera con `python -m house_twin.cli texture <spec>`.
La foto original vive solo en la PC del dueño (`sources/fotos/`, fuera de git); al repo entran el
JSON y las texturas de `assets/textures/<nombre>/`.

Lo que sale de la foto es observación; el tamaño real y el blanco de referencia son datos o supuestos
que el JSON declara con su fuente y se copian a `material.json`.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
TEXTURES_DIR = ROOT / 'assets' / 'textures'
PATCH_FEATHER_PX = 12
GRAIN_BLUR_PX = 6  # separa la veta (detalle fino) de la iluminación y el tinte (variación amplia)
DETAIL_MAP_SCALE = 0.5  # rugosidad y normal a media resolución: pesan menos en git y el render no lo nota


def _srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def _perspective_coeffs(dst, src):
    """Coeficientes de PIL.Image.PERSPECTIVE: llevan cada punto de salida a su punto en la foto."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        rhs += [u, v]
    return np.linalg.solve(np.array(rows, float), np.array(rhs, float))


def rectify(photo: Image.Image, corners: dict, size_px: tuple[int, int]) -> Image.Image:
    w, h = size_px
    src = [corners[k] for k in ('top_left', 'top_right', 'bottom_right', 'bottom_left')]
    return photo.transform(size_px, Image.PERSPECTIVE, _perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], src),
                           Image.BICUBIC)


def _to_image(lin):
    return Image.fromarray((_linear_to_srgb(lin) * 255).round().astype(np.uint8))


def color_correct(photo: Image.Image, image: Image.Image, color: dict) -> tuple[Image.Image, list[float]]:
    """Corrige color y exposición en lineal.

    - `white_reference`: una superficie que se sabe blanca, en el mismo plano que la textura (lo más fiable).
    - `gain` + `mean_srgb`: sin blanco en la foto; balance de otra foto con la misma luz y una luminosidad media declarada.
    """
    lin = _srgb_to_linear(np.asarray(image).astype(float) / 255)
    if 'white_reference' in color:
        ref = color['white_reference']
        x0, y0, x1, y1 = ref['box_px']
        pixels = np.asarray(photo.crop((x0, y0, x1, y1))).reshape(-1, 3).astype(float)
        if 'brightest_fraction' in ref:  # referencia delgada (p. ej. una junta blanca) dentro de una zona más amplia
            lum = pixels.mean(axis=1)
            pixels = pixels[lum >= np.quantile(lum, 1 - ref['brightest_fraction'])]
        measured = _srgb_to_linear(np.median(pixels, axis=0) / 255)
        gain = _srgb_to_linear(np.array(ref['albedo_srgb'], float) / 255) / measured
    else:
        balanced = lin * np.array(color['gain'], float)
        target = _srgb_to_linear(np.array(color['mean_srgb'], float) / 255).mean()
        gain = np.array(color['gain'], float) * target / balanced.mean()
    return _to_image(lin * gain), [round(float(g), 4) for g in gain]


def flatten_lighting(image: Image.Image, exclude_darkest: float = 0.2) -> Image.Image:
    """Quita la caída de luz de la foto (más clara cerca de la lámpara) sin tocar el detalle ni el color medio.

    Ajusta una superficie cuadrática a la luminancia (en log, sin el `exclude_darkest` más oscuro: juntas y
    sombras) y la divide. Un difuminado no basta: deja escalones de brillo entre filas de losetas.
    """
    lin = _srgb_to_linear(np.asarray(image).astype(float) / 255)
    lum = np.maximum(lin.mean(axis=2), 1e-4)
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w]
    x, y = xx / w - 0.5, yy / h - 0.5
    terms = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1)
    mask = lum > np.quantile(lum, exclude_darkest)
    coef, *_ = np.linalg.lstsq(terms[mask], np.log(lum[mask]), rcond=None)
    fit = terms @ coef
    return _to_image(lin * np.exp(fit.mean() - fit)[..., None])


def _frac_box(frac, size_px):
    """[x, y, ancho, alto] en fracciones de la textura → píxeles."""
    W, H = size_px
    return round(frac[0] * W), round(frac[1] * H), round(frac[2] * W), round(frac[3] * H)


def apply_patches(image: Image.Image, patches: list[dict]) -> Image.Image:
    """Tapa objetos que no son la superficie (p. ej. la perilla) con un trozo de la misma pieza, con borde difuminado."""
    out = image.copy()
    for p in patches:
        x, y, w, h = _frac_box(p['from_frac'], image.size)
        to = (round(p['to_frac'][0] * image.width), round(p['to_frac'][1] * image.height))
        piece = image.crop((x, y, x + w, y + h))
        mask = Image.new('L', (w, h), 0)
        f = PATCH_FEATHER_PX
        mask.paste(255, (f, f, w - f, h - f))
        out.paste(piece, to, mask.filter(ImageFilter.GaussianBlur(f / 2)))
    return out


def _panel_height(shape, panels_px, relief):
    """Altura (m) de una puerta de tableros realzados: cara del bastidor en 0, ranura en el contorno y bisel que sube al campo."""
    h, w = shape
    height = np.zeros(shape)
    groove = -relief['groove_depth_mm'] / 1000
    rise = relief['bevel_rise_mm'] / 1000
    bevel = relief['bevel_px']
    yy, xx = np.mgrid[0:h, 0:w]
    for x0, y0, x1, y1 in panels_px:
        inside = (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
        edge = np.minimum.reduce([xx - x0, x1 - 1 - xx, yy - y0, y1 - 1 - yy]).astype(float)
        profile = groove + rise * np.clip(edge / bevel, 0, 1)
        height = np.where(inside, profile, height)
    return height


def _grid_height(shape, grid, relief):
    """Altura (m) de un piso de losetas: superficie en 0, junta hundida y canto redondeado.

    La textura empieza y termina en el eje de una junta, así que se repite sin costura.
    """
    h, w = shape
    tile_w, tile_h = w / grid['cols'], h / grid['rows']
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    dist = np.minimum(np.abs(((xx + tile_w / 2) % tile_w) - tile_w / 2), np.abs(((yy + tile_h / 2) % tile_h) - tile_h / 2))
    half = grid['grout_frac'] * tile_w / 2
    depth = relief['grout_depth_mm'] / 1000
    edge = relief['edge_round_px']
    return -depth * np.clip((half + edge - dist) / edge, 0, 1) ** 2, dist <= half


def _rect_px(frac, shape):
    h, w = shape
    x0, y0, x1, y1 = frac
    return round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)


def _features_height(shape, features):
    """Altura (m) armada por elementos: tableros hundidos (`recess`) y acanalados verticales (`grooves`)."""
    height = np.zeros(shape)
    for f in features:
        x0, y0, x1, y1 = _rect_px(f['rect_frac'], shape)
        if f['kind'] == 'recess':
            height[y0:y1, x0:x1] -= f['depth_mm'] / 1000
        elif f['kind'] == 'grooves':
            half = max(1, round(f['width_frac'] * shape[1] / 2))
            for x in f['x_frac']:
                cx = round(x * shape[1])
                height[y0:y1, cx - half:cx + half] -= f['depth_mm'] / 1000
    return height


def _opacity(shape, opacity):
    """Máscara de opacidad: 0 en los vidrios, 1 en perfiles y en la retícula que cruza los vidrios."""
    mask = np.ones(shape)
    for r in opacity['holes']:
        x0, y0, x1, y1 = _rect_px(r, shape)
        mask[y0:y1, x0:x1] = 0
    for r in opacity.get('opaque', []):
        x0, y0, x1, y1 = _rect_px(r, shape)
        mask[y0:y1, x0:x1] = 1
    return mask


def _normal_map(height_m, px_per_m):
    """Normal map en convención OpenGL (la de Blender): verde = +V, hacia arriba de la textura."""
    dy, dx = np.gradient(height_m, 1 / px_per_m)
    n = np.dstack([-dx, dy, np.ones_like(height_m)])  # las filas crecen hacia abajo: +V = -fila
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n + 1) / 2 * 255).round().astype(np.uint8))


def _grain(base: Image.Image) -> np.ndarray:
    """Detalle fino de la veta en [-1, 1]: luminancia menos su versión difuminada."""
    lum = np.asarray(base.convert('L')).astype(float)
    blur = np.asarray(base.convert('L').filter(ImageFilter.GaussianBlur(GRAIN_BLUR_PX))).astype(float)
    detail = lum - blur
    return np.clip(detail / (3 * detail.std() + 1e-6), -1, 1)


def sample_color(photo: Image.Image, color: dict, sample: dict) -> tuple[list[int], list[float]]:
    """Color medio de una zona de la foto, corregido con la misma referencia que las texturas.

    `darkest_fraction` < 1 promedia solo la parte más oscura de la zona: así el color de un perfil negro
    no se mezcla con salpicaduras de pintura ni con el muro del borde.
    """
    x0, y0, x1, y1 = sample['box_px']
    region = photo.crop((x0, y0, x1, y1))
    corrected, gain = color_correct(photo, region, color)
    pixels = np.asarray(corrected).reshape(-1, 3).astype(float)
    lum = pixels.mean(axis=1)
    keep = pixels[lum <= np.quantile(lum, sample.get('darkest_fraction', 1.0))]
    return [int(v) for v in np.median(keep, axis=0).round()], gain


def build_material(spec: dict, out: Path, photos_root: Path) -> Path:
    """Material sin mapas (perfil liso, vidrio): color medido en la foto y parámetros PBR declarados."""
    photo = ImageOps.exif_transpose(Image.open(photos_root / spec['photo'])).convert('RGB')
    pbr = dict(spec['pbr'])
    gain = None
    if 'sample' in pbr:
        pbr['basecolor_srgb'], gain = sample_color(photo, spec['color'], pbr.pop('sample'))
    material = {
        'name': spec['name'], 'applies_to': spec['applies_to'], 'kind': 'constant', 'pbr': pbr,
        'source': {'photo': spec['photo'], 'photo_meta': spec.get('photo_meta', {}), 'color': spec.get('color'),
                   'white_balance_gain': gain, 'sample': spec['pbr'].get('sample')},
        'observed': spec.get('observed', {}), 'assumptions': spec.get('assumptions', []),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / 'material.json').write_text(json.dumps(material, ensure_ascii=False, indent=1) + '\n')
    return out


def build_texture(spec_path: Path, photos_root: Path = ROOT) -> Path:
    spec = json.loads(spec_path.read_text())
    if spec.get('kind') == 'constant':
        return build_material(spec, TEXTURES_DIR / spec['name'], photos_root)
    px_per_m = spec['px_per_m']
    size_m = (spec['size_m']['width'], spec['size_m']['height'])
    size_px = (round(size_m[0] * px_per_m), round(size_m[1] * px_per_m))
    photo = ImageOps.exif_transpose(Image.open(photos_root / spec['photo'])).convert('RGB')

    base = rectify(photo, spec['corners_px'], size_px)
    if 'flatten_lighting' in spec:
        base = flatten_lighting(base, spec['flatten_lighting'].get('exclude_darkest', 0.2))
    base, gain = color_correct(photo, base, spec['color'])
    base = apply_patches(base, spec.get('patches', []))

    relief = spec['relief']
    W, H = size_px
    grain = _grain(base)
    rough = spec['roughness']
    roughness = rough['base'] - grain * rough['grain']
    if relief['type'] == 'features':
        shape_height = _features_height(grain.shape, relief['features'])
    elif relief['type'] == 'panels':
        panels_px = [[round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)]
                     for x0, y0, x1, y1 in (p['rect_frac'] for p in relief['panels'])]
        shape_height = _panel_height(grain.shape, panels_px, relief)
    else:
        shape_height, grout = _grid_height(grain.shape, spec['grid'], relief)
        roughness = np.where(grout, rough['grout'], roughness)
    height = shape_height + grain * relief['grain_mm'] / 1000
    roughness = np.clip(roughness, 0, 1)

    out = TEXTURES_DIR / spec['name']
    out.mkdir(parents=True, exist_ok=True)
    detail_px = (round(size_px[0] * DETAIL_MAP_SCALE), round(size_px[1] * DETAIL_MAP_SCALE))
    base.save(out / 'basecolor.jpg', quality=92)
    Image.fromarray((roughness * 255).round().astype(np.uint8)).resize(detail_px, Image.LANCZOS).save(out / 'roughness.png', optimize=True)
    _normal_map(height, px_per_m).resize(detail_px, Image.LANCZOS).save(out / 'normal.png', optimize=True)
    maps = {'basecolor': 'basecolor.jpg', 'roughness': 'roughness.png', 'normal': 'normal.png (OpenGL)'}
    if 'opacity' in spec:
        Image.fromarray((_opacity(grain.shape, spec['opacity']) * 255).astype(np.uint8)).save(out / 'opacity.png', optimize=True)
        maps['opacity'] = 'opacity.png (0 = vidrio)'
    material = {
        'name': spec['name'], 'applies_to': spec['applies_to'],
        'size_m': spec['size_m'], 'px_per_m': px_per_m, 'size_px': list(size_px), 'tileable': relief['type'] == 'grid',
        'grid': spec.get('grid'),
        'maps': maps, 'glass_material': spec.get('opacity', {}).get('glass_material'),
        'source': {'photo': spec['photo'], 'photo_meta': spec.get('photo_meta', {}),
                   'color': spec['color'], 'white_balance_gain': gain},
        'observed': spec.get('observed', {}), 'assumptions': spec.get('assumptions', []),
    }
    (out / 'material.json').write_text(json.dumps(material, ensure_ascii=False, indent=1) + '\n')
    return out
