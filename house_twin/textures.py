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
    if color.get('as_shot'):  # luz de día y balance de la cámara: se respeta tal cual
        return image, [1.0, 1.0, 1.0]
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


def make_seamless(image: Image.Image) -> Image.Image:
    """Hace repetible un recorte sin juntas (concreto, yeso): lo mezcla con una copia desplazada media textura.

    Un eje a la vez: en cada borde manda la copia desplazada, que ahí es continua al repetir, y hacia el centro
    manda el original. Con pesos de ambos ejes multiplicados, la costura de la copia (en el centro) aparecería
    a lo largo de los bordes. Baja un poco el contraste en las zonas de mezcla.
    """
    out = np.asarray(image).astype(float)
    for axis in (0, 1):
        n = out.shape[axis]
        ramp = np.minimum(np.arange(n) + 0.5, n - np.arange(n) - 0.5) / (n / 2)
        shape = [1, 1, 1]
        shape[axis] = n
        weight = ramp.reshape(shape)
        shifted = np.roll(out, n // 2, axis=axis)
        w_shifted = np.roll(weight, n // 2, axis=axis)
        out = (out * weight + shifted * w_shifted) / (weight + w_shifted)
    return Image.fromarray(out.round().astype(np.uint8))


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


def _opacity(shape, opacity, image: Image.Image | None = None):
    """Máscara de opacidad: 0 en los huecos (vidrios, entre barrotes) y 1 en perfiles, barras, arillos y adornos.

    `opaque` son rectángulos, `rings` arillos y `blobs` adornos (elipses), todo en fracciones de la textura.
    Con `refine_dark`, dentro de una franja de `dilate_px` alrededor de esas piezas solo queda opaco lo que en la
    foto es oscuro: el borde sigue la silueta real de la herrería y no deja ver el fondo claro de la foto.
    """
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    pieces = np.zeros(shape, bool)
    for r in opacity.get('opaque', []):
        x0, y0, x1, y1 = _rect_px(r, shape)
        pieces[y0:y1, x0:x1] = True
    for ring in opacity.get('rings', []):
        cx, cy = ring['center_frac'][0] * w, ring['center_frac'][1] * h
        dist = np.hypot(xx - cx, yy - cy)
        pieces |= np.abs(dist - ring['radius_frac_w'] * w) <= ring['thickness_frac_w'] * w / 2
    for blob in opacity.get('blobs', []):
        cx, cy = blob['center_frac'][0] * w, blob['center_frac'][1] * h
        pieces |= ((xx - cx) / (blob['size_frac_w'][0] * w / 2)) ** 2 + ((yy - cy) / (blob['size_frac_w'][1] * w / 2)) ** 2 <= 1
    holes = np.zeros(shape, bool)
    for r in opacity['holes']:
        x0, y0, x1, y1 = _rect_px(r, shape)
        holes[y0:y1, x0:x1] = True
    refine = opacity.get('refine_dark')
    if refine and image is not None:
        k = 2 * refine['dilate_px'] + 1
        near = np.asarray(Image.fromarray((pieces * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(k))) > 0
        dark = np.asarray(image.convert('L')) <= refine['max_luminance']
        pieces = near & dark
    return np.where(holes, pieces, True).astype(float)


def _normal_map(height_m, px_per_m):
    """Normal map en convención OpenGL (la de Blender): verde = +V, hacia arriba de la textura."""
    dy, dx = np.gradient(height_m, 1 / px_per_m)
    n = np.dstack([-dx, dy, np.ones_like(height_m)])  # las filas crecen hacia abajo: +V = -fila
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n + 1) / 2 * 255).round().astype(np.uint8))


def _grain(base: Image.Image, blur_px: float = GRAIN_BLUR_PX) -> np.ndarray:
    """Detalle de la superficie en [-1, 1]: luminancia menos su versión difuminada.

    `blur_px` fija la escala más grande que cuenta como relieve: pocos píxeles para una veta fina, más para un
    aplanado rugoso con crestas de varios milímetros.
    """
    lum = np.asarray(base.convert('L')).astype(float)
    blur = np.asarray(base.convert('L').filter(ImageFilter.GaussianBlur(blur_px))).astype(float)
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


def _periodic_noise(shape, feature_px: float, rng) -> np.ndarray:
    """Ruido suave y repetible (periódico) con detalle de ≈ `feature_px`, normalizado a media 0 y desviación 1."""
    h, w = shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    spectrum = np.exp(-(fx ** 2 + fy ** 2) * (np.pi * feature_px) ** 2 / 2)
    field = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal(shape)) * spectrum))
    return (field - field.mean()) / (field.std() + 1e-12)


def procedural_stucco(spec: dict, size_px: tuple[int, int]) -> tuple[Image.Image, np.ndarray, np.ndarray]:
    """Estuco sintético: placas aplanadas con borde marcado (tipo «lace trowel») sobre grano fino («pebbled dash»).

    Solo para acabados sin foto usable: el resultado es una aproximación guiada por la descripción del dueño, no
    una observación. Devuelve color base, altura (m) y rugosidad; todo periódico, así que se repite sin costura.
    """
    rng = np.random.default_rng(spec['seed'])
    shape = (size_px[1], size_px[0])
    px_per_m = spec['px_per_m']
    plates, grain = spec['plates'], spec['grain']
    field = _periodic_noise(shape, plates['size_m'] * px_per_m / 1.5, rng) + 0.35 * _periodic_noise(shape, plates['size_m'] * px_per_m / 6, rng)
    threshold = np.quantile(field, 1 - plates['coverage'])
    # placas: meseta plana arriba del umbral, con rampa corta (borde marcado) y algo de inclinación de la llana
    plate = np.clip((field - threshold) / plates['edge_softness'], 0, 1) ** 0.5
    plate *= 1 + 0.3 * _periodic_noise(shape, plates['size_m'] * px_per_m / 2, rng)
    fine = _periodic_noise(shape, grain['size_m'] * px_per_m, rng)
    height = plate * plates['height_mm'] / 1000 + fine * grain['height_mm'] / 1000
    # color: blanco de pintura, algo más oscuro (polvo, sombra fina) en lo hundido entre placas
    lowness = 1 - np.clip(plate, 0, 1)
    shade = 1 - spec['color']['crevice_darkening'] * lowness - 0.03 * np.clip(-fine, 0, None)
    base = np.array(spec['color']['albedo_srgb'], float) / 255
    lin = _srgb_to_linear(base)[None, None, :] * shade[..., None]
    roughness = np.clip(spec['roughness']['base'] + 0.04 * fine, 0, 1)
    return _to_image(lin), height, roughness


def _blur(field: np.ndarray, sigma_px: float) -> np.ndarray:
    """Difuminado gaussiano con el borde extendido (la superficie no se repite, a diferencia del estuco)."""
    if sigma_px <= 0:
        return field
    pad = int(3 * sigma_px) + 1
    padded = np.pad(field, pad, mode='edge')
    fy, fx = np.fft.fftfreq(padded.shape[0])[:, None], np.fft.fftfreq(padded.shape[1])[None, :]
    kernel = np.exp(-2 * (np.pi * sigma_px) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(padded) * kernel))[pad:-pad, pad:-pad]


def measured_colors(spec: dict, photos_root: Path) -> tuple[dict[str, list[int]], list[float]]:
    """Colores medidos en la foto rectificada y corregida: `darkest` evita brillos y reflejos, `brightest` toma motas."""
    photo = ImageOps.exif_transpose(Image.open(photos_root / spec['photo'])).convert('RGB')
    px_per_m = spec['color']['measure_px_per_m']
    size = (round(spec['size_m']['width'] * px_per_m), round(spec['size_m']['height'] * px_per_m))
    image, gain = color_correct(photo, rectify(photo, spec['corners_px'], size), spec['color'])
    px = np.asarray(image).astype(float)
    colors = {}
    for name, s in spec['color']['samples'].items():
        x0, y0, x1, y1 = _rect_px(s['rect_frac'], px.shape[:2])
        region = px[y0:y1, x0:x1].reshape(-1, 3)
        lum = region.mean(axis=1)
        if s['keep'] == 'darkest':
            region = region[lum <= np.quantile(lum, s['fraction'])]
        else:
            region = region[lum >= np.quantile(lum, 1 - s['fraction'])]
        colors[name] = [int(v) for v in np.median(region, axis=0).round()]
    return colors, gain


def _weld_points(item) -> list[tuple[float, float]]:
    """Puntos de soldadura: los sueltos de `points_frac` y los repartidos a paso fijo sobre cada `lines`.

    `pitch_frac` va en fracción del eje sobre el que corre la línea (ancho si es horizontal, alto si es vertical).
    """
    points = [tuple(p) for p in item.get('points_frac', [])]
    for line in item.get('lines', []):
        (x0, y0), (x1, y1) = line['from'], line['to']
        n = max(1, round(max(abs(x1 - x0), abs(y1 - y0)) / line['pitch_frac']))
        points += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)]
    return points


def procedural_sheet_door(spec: dict, size_px: tuple[int, int], colors: dict[str, list[int]]):
    """Puerta de lámina o de herrería pintada, dibujada por código con las medidas tomadas en la foto rectificada.

    No se copia la foto: los brillos del sol, los reflejos y lo que se ve a través de los huecos no quedan en el
    color base. Lo que sí sale de la foto es la geometría (`layout`, en fracciones de la cara) y los colores
    (`colors`); el desgaste (polvo, óxido en las soldaduras) se reparte con ruido donde la foto lo muestra.
    Con `opacity.holes`, dentro de esos rectángulos solo quedan opacas las piezas (barrotes, arillos, adornos).
    Devuelve color base, altura (m), rugosidad y opacidad (None si la puerta es toda lámina).
    """
    W, H = size_px
    px_per_m = spec['px_per_m']
    rng = np.random.default_rng(spec['seed'])
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = (xx + 0.5) / W, (yy + 0.5) / H
    height = np.zeros((H, W))
    roughness = np.full((H, W), spec['roughness']['base'])
    rust = np.zeros((H, W))
    dust = np.zeros((H, W))
    pieces = np.zeros((H, W), bool)  # herrería que tapa los huecos
    for item in spec['layout']:
        x0, y0, x1, y1 = item.get('rect_frac', (0, 0, 1, 1))
        inside = (u >= x0) & (u < x1) & (v >= y0) & (v < y1)
        h = item.get('height_mm', 0) / 1000
        kind = item['kind']
        if kind == 'level':  # plano a una altura: marco, hoja, tablero hundido, junta entre marco y hoja
            height[inside] = h
        elif kind == 'molding':  # contorno de un tablero en dos escalones: el de afuera a `height_mm`
            edge = np.minimum.reduce([(u - x0) * W, (x1 - u) * W, (v - y0) * H, (y1 - v) * H])
            width = item['width_frac_w'] * W
            height[inside & (edge < width)] = item['inner_height_mm'] / 1000
            height[inside & (edge < width / 2)] = h
        elif kind == 'ribs':  # lámina acanalada: costillas trapezoidales verticales
            half_base, half_top = item['base_frac_w'] * W / 2, item['top_frac_w'] * W / 2
            for c in item['x_frac']:
                d = np.abs(u - c) * W
                height += np.where(inside, h * np.clip((half_base - d) / (half_base - half_top), 0, 1), 0)
        elif kind == 'joints':  # duela: cada unión es un bordón redondo junto a una ranura en V
            for c in item['x_frac']:
                for p in item['profile']:
                    d = np.abs(u - c - p['offset_frac_w']) * W / (p['width_frac_w'] * W / 2)
                    shape = np.sqrt(np.clip(1 - d ** 2, 0, 1)) if p['shape'] == 'round' else np.clip(1 - d, 0, 1)
                    height += np.where(inside, p['height_mm'] / 1000 * shape, 0)
        elif kind == 'welds':  # puntos de soldadura: gota abultada y óxido alrededor de algunos
            r_px = item['diameter_frac_w'] * W / 2
            for px, py in _weld_points(item):
                r = r_px * rng.uniform(0.75, 1.25)
                halo = r * item['rust_spread']
                cx, cy = px * W + rng.normal(0, r / 3), py * H + rng.normal(0, r / 3)
                xs = slice(max(0, int(cx - halo) - 1), min(W, int(cx + halo) + 2))
                ys = slice(max(0, int(cy - halo) - 1), min(H, int(cy + halo) + 2))
                d = np.hypot(xx[ys, xs] - cx, yy[ys, xs] - cy)
                height[ys, xs] += h * np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
                if rng.random() < item['rust_share']:
                    rust[ys, xs] = np.maximum(rust[ys, xs], np.clip(1 - d / halo, 0, 1) ** 0.7)
        elif kind == 'bar':  # barrote o travesaño redondeado; `twist_pitch_mm` lo hace torcido (estrías en diagonal)
            vertical = (x1 - x0) * W < (y1 - y0) * H
            along, across = (yy, (u - (x0 + x1) / 2) * W) if vertical else (xx, (v - (y0 + y1) / 2) * H)
            half = ((x1 - x0) * W if vertical else (y1 - y0) * H) / 2
            profile = h * np.sqrt(np.clip(1 - (across / half) ** 2, 0, 1))
            if 'twist_pitch_mm' in item:
                pitch = item['twist_pitch_mm'] / 1000 * px_per_m
                profile *= 0.7 + 0.3 * np.cos(2 * np.pi * (along + across) / pitch)
            height = np.where(inside, np.maximum(height, profile), height)
            pieces |= inside
        elif kind == 'ring':  # arillo de solera: anillo de sección redondeada
            cx, cy = item['center_frac'][0] * W, item['center_frac'][1] * H
            d = np.abs(np.hypot(xx - cx, yy - cy) - item['radius_frac_w'] * W) / (item['thickness_frac_w'] * W / 2)
            ring = d <= 1
            height = np.where(ring, np.maximum(height, h * np.sqrt(np.clip(1 - d ** 2, 0, 1))), height)
            pieces |= ring
        elif kind == 'ornament':  # adorno de fundición: rombo con picos, más alto al centro
            cx, cy = item['center_frac'][0] * W, item['center_frac'][1] * H
            a, b = item['size_frac_w'][0] * W / 2, item['size_frac_w'][1] * W / 2
            d = np.abs(xx - cx) / a + np.abs(yy - cy) / b
            height = np.where(d <= 1, np.maximum(height, h * (1 - d)), height)
            pieces |= d <= 1
        elif kind == 'dust':  # polvo pegado abajo: motas cada vez más densas hacia el piso
            amount = np.clip((v - y0) / (y1 - y0), 0, 1) ** item['ramp_power'] * item['max_cover']
            speck = _periodic_noise((H, W), item['speck_mm'] / 1000 * px_per_m, rng)
            rows = np.quantile(speck[::4, ::4], 1 - amount[:, 0])[:, None]
            dust = np.where(inside, np.clip((speck - rows) / 0.4, 0, 1) * (amount > 0), dust)
        else:
            raise ValueError(f'elemento de puerta desconocido: {kind}')
        if 'roughness' in item:
            roughness[inside] = item['roughness']
    height = _blur(height, spec['bevel_mm'] / 1000 * px_per_m)
    paint = spec['paint']
    height += _periodic_noise((H, W), paint['orange_peel_mm'] / 1000 * px_per_m, rng) * paint['orange_peel_height_mm'] / 1000
    # color: pintura medida, apenas variada; se oscurece en lo hundido (juntas, ranuras) y lleva óxido y polvo encima
    cavity = np.clip((_blur(height, spec['cavity']['radius_mm'] / 1000 * px_per_m) - height) / (spec['cavity']['depth_mm'] / 1000), 0, 1)
    shade = (1 - spec['cavity']['darkening'] * cavity) * (1 + paint['variation'] * _periodic_noise((H, W), 0.05 * px_per_m, rng))
    lin = _srgb_to_linear(np.array(colors['paint'], float) / 255)[None, None, :] * shade[..., None]
    rough = spec['roughness']
    if rust.any():
        rust *= np.clip(0.6 + 0.4 * _periodic_noise((H, W), 0.003 * px_per_m, rng), 0, 1)
        lin = lin * (1 - rust[..., None]) + _srgb_to_linear(np.array(colors['rust'], float) / 255) * rust[..., None]
        roughness = roughness + (rough['rust'] - roughness) * rust
    if dust.any():
        dust_amount = dust * spec['dust_opacity']
        lin = lin * (1 - dust_amount[..., None]) + _srgb_to_linear(np.array(colors['dust'], float) / 255) * dust_amount[..., None]
        roughness = roughness + (rough['dust'] - roughness) * dust
    alpha = None
    if 'opacity' in spec:
        holes = np.zeros((H, W), bool)
        for x0, y0, x1, y1 in spec['opacity']['holes']:
            holes |= (u >= x0) & (u < x1) & (v >= y0) & (v < y1)
        alpha = np.where(holes & ~pieces, 0.0, 1.0)
        if spec['opacity'].get('glass_material'):  # el vidrio lleva su color y queda liso, como en las hojas de foto
            glass = _glass_pbr(spec['opacity']['glass_material'])
            lin[alpha == 0] = _srgb_to_linear(np.array(glass['basecolor_srgb'], float) / 255)
            roughness = np.where(alpha == 0, glass['roughness'], roughness)
    return _to_image(lin), height, np.clip(roughness, 0, 1), alpha


def build_procedural(spec: dict, out: Path, photos_root: Path = ROOT) -> Path:
    px_per_m = spec['px_per_m']
    size_px = (round(spec['size_m']['width'] * px_per_m), round(spec['size_m']['height'] * px_per_m))
    source = {'method': 'procedural', 'seed': spec['seed'], 'references': spec.get('references', [])}
    if spec['generator'] == 'stucco':
        base, height, roughness = procedural_stucco(spec, size_px)
        alpha = None
        parameters = {k: spec[k] for k in ('plates', 'grain', 'color', 'roughness')}
    elif spec['generator'] == 'sheet_door':
        if 'srgb' in spec['color']:  # propuesta: colores elegidos, no medidos en una foto
            colors, gain = spec['color']['srgb'], None
        else:
            colors, gain = measured_colors(spec, photos_root)
        base, height, roughness, alpha = procedural_sheet_door(spec, size_px, colors)
        parameters = {k: spec[k] for k in ('layout', 'paint', 'cavity', 'bevel_mm', 'roughness', 'dust_opacity', 'opacity')
                      if k in spec}
        source.update(photo=spec.get('photo'), photo_meta=spec.get('photo_meta', {}), color=spec['color'],
                      white_balance_gain=gain, **({'measured_srgb': colors} if gain is not None else {}))
    else:
        raise ValueError(f'generador desconocido: {spec["generator"]}')
    out.mkdir(parents=True, exist_ok=True)
    detail_px = (round(size_px[0] * DETAIL_MAP_SCALE), round(size_px[1] * DETAIL_MAP_SCALE))
    base.save(out / 'basecolor.jpg', quality=92)
    Image.fromarray((roughness * 255).round().astype(np.uint8)).resize(detail_px, Image.LANCZOS).save(out / 'roughness.png', optimize=True)
    _normal_map(height, px_per_m).resize(detail_px, Image.LANCZOS).save(out / 'normal.png', optimize=True)
    maps = {'basecolor': 'basecolor.jpg', 'roughness': 'roughness.png', 'normal': 'normal.png (OpenGL)'}
    if alpha is not None:  # huecos de la herrería: transparentes, sin vidrio
        Image.fromarray((alpha * 255).astype(np.uint8)).save(out / 'opacity.png', optimize=True)
        maps['opacity'] = 'opacity.png (0 = hueco)'
    material = {
        'name': spec['name'], 'applies_to': spec['applies_to'], 'kind': 'procedural', 'tileable': spec['tileable'],
        'size_m': spec['size_m'], 'px_per_m': px_per_m, 'size_px': list(size_px), 'maps': maps,
        'glass_material': spec.get('opacity', {}).get('glass_material'), 'source': source, 'parameters': parameters,
        'observed': spec.get('observed', {}), 'assumptions': spec.get('assumptions', []),
    }
    (out / 'material.json').write_text(json.dumps(material, ensure_ascii=False, indent=1) + '\n')
    return out


def _glass_pbr(name: str) -> dict:
    """PBR del vidrio de una hoja: sale de su `material.json`, así que el vidrio se genera antes que la puerta."""
    return json.loads((TEXTURES_DIR / name / 'material.json').read_text())['pbr']


def build_texture(spec_path: Path, photos_root: Path = ROOT) -> Path:
    spec = json.loads(spec_path.read_text())
    if spec.get('kind') == 'constant':
        return build_material(spec, TEXTURES_DIR / spec['name'], photos_root)
    if spec.get('kind') == 'procedural':
        return build_procedural(spec, TEXTURES_DIR / spec['name'], photos_root)
    px_per_m = spec['px_per_m']
    size_m = (spec['size_m']['width'], spec['size_m']['height'])
    size_px = (round(size_m[0] * px_per_m), round(size_m[1] * px_per_m))
    photo = ImageOps.exif_transpose(Image.open(photos_root / spec['photo'])).convert('RGB')

    base = rectify(photo, spec['corners_px'], size_px)
    if 'flatten_lighting' in spec:
        base = flatten_lighting(base, spec['flatten_lighting'].get('exclude_darkest', 0.2))
    base, gain = color_correct(photo, base, spec['color'])
    base = apply_patches(base, spec.get('patches', []))
    if spec.get('seamless'):
        base = make_seamless(base)
    W, H = size_px
    glass = None
    if 'opacity' in spec:
        alpha = _opacity((H, W), spec['opacity'], base)
        px = np.asarray(base).copy()
        fill = spec['opacity'].get('fill_pieces_srgb')
        if fill:  # en los huecos, las piezas finas toman el color de la pintura: su borde en la foto es cielo o fondo
            holes = _opacity((H, W), {'holes': spec['opacity']['holes']}) == 0
            px[holes & (alpha > 0)] = fill
        if spec['opacity'].get('glass_material'):
            # en el vidrio la foto muestra reflejos (el fotógrafo, la sala) o lo de atrás, no la superficie:
            # se pinta con el color del material del vidrio y queda liso
            glass = _glass_pbr(spec['opacity']['glass_material'])
            px[alpha == 0] = glass['basecolor_srgb']
        base = Image.fromarray(px)

    relief = spec['relief']
    grain = _grain(base, relief.get('grain_blur_px', GRAIN_BLUR_PX))
    rough = spec['roughness']
    roughness = rough['base'] - grain * rough['grain']
    if relief['type'] == 'flat':
        shape_height = np.zeros(grain.shape)
    elif relief['type'] == 'features':
        shape_height = _features_height(grain.shape, relief['features'])
    elif relief['type'] == 'panels':
        panels_px = [[round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)]
                     for x0, y0, x1, y1 in (p['rect_frac'] for p in relief['panels'])]
        shape_height = _panel_height(grain.shape, panels_px, relief)
    else:
        shape_height, grout = _grid_height(grain.shape, spec['grid'], relief)
        if 'subgrid' in spec['grid']:  # loseta con diseño de mosaico: canales entre cuadritos dentro de cada pieza
            sub = spec['grid']['subgrid']
            n = sub['per_tile']
            sub_height, channel = _grid_height(
                grain.shape, {'cols': spec['grid']['cols'] * n, 'rows': spec['grid']['rows'] * n, 'grout_frac': sub['line_frac']},
                {'grout_depth_mm': sub['depth_mm'], 'edge_round_px': sub['edge_round_px']})
            shape_height = np.where(grout, shape_height, shape_height + sub_height)
            roughness = np.where(channel, rough['channel'], roughness)
        roughness = np.where(grout, rough['grout'], roughness)
    height = shape_height + grain * relief['grain_mm'] / 1000
    if glass is not None:
        roughness = np.where(alpha == 0, glass['roughness'], roughness)
    roughness = np.clip(roughness, 0, 1)

    out = TEXTURES_DIR / spec['name']
    out.mkdir(parents=True, exist_ok=True)
    detail_px = (round(size_px[0] * DETAIL_MAP_SCALE), round(size_px[1] * DETAIL_MAP_SCALE))
    base.save(out / 'basecolor.jpg', quality=92)
    Image.fromarray((roughness * 255).round().astype(np.uint8)).resize(detail_px, Image.LANCZOS).save(out / 'roughness.png', optimize=True)
    _normal_map(height, px_per_m).resize(detail_px, Image.LANCZOS).save(out / 'normal.png', optimize=True)
    maps = {'basecolor': 'basecolor.jpg', 'roughness': 'roughness.png', 'normal': 'normal.png (OpenGL)'}
    if 'opacity' in spec:
        Image.fromarray((alpha * 255).astype(np.uint8)).save(out / 'opacity.png', optimize=True)
        maps['opacity'] = 'opacity.png (0 = vidrio)'
    material = {
        'name': spec['name'], 'applies_to': spec['applies_to'],
        'size_m': spec['size_m'], 'px_per_m': px_per_m, 'size_px': list(size_px), 'tileable': relief['type'] == 'grid' or bool(spec.get('seamless')),
        'grid': spec.get('grid'),
        'maps': maps, 'glass_material': spec.get('opacity', {}).get('glass_material'),
        'source': {'photo': spec['photo'], 'photo_meta': spec.get('photo_meta', {}),
                   'color': spec['color'], 'white_balance_gain': gain},
        'observed': spec.get('observed', {}), 'assumptions': spec.get('assumptions', []),
    }
    (out / 'material.json').write_text(json.dumps(material, ensure_ascii=False, indent=1) + '\n')
    return out
