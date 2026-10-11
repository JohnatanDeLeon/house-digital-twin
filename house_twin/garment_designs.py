"""Prendas hechas sobre un molde: la misma playera lisa (`template`) con otro estampado encima.

Así, para agregar una playera solo hace falta su dibujo. Sale de una de dos fuentes (`design.from`):

- `product`: una imagen de la prenda (de frente, sobre fondo liso). Se recorta su estampado con `segment_garment`,
  con los parámetros del molde salvo los que el diseño cambie, y su posición se mide sola respecto al cuerpo.
- `art`: solo el dibujo. Si el PNG trae transparencia se usa; si no, se quita su fondo (el color de las orillas).
  Se coloca con `width_m`, `top_m` (bajo el punto más alto de la playera) y `offset_x_m` (desde el centro del cuerpo).

La posición del estampado se guarda en metros respecto al centro del cuerpo y al punto más alto de la playera, así
que un dibujo medido en una prenda cae en el mismo lugar del molde. Si la tela es de otro color que el molde, se tiñe:
`"fabric": "from_image"` (el color medido en la imagen de la prenda) o `fabric_srgb`. Después se cuelga como cualquier
prenda.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from house_twin.hanging import _body_edges, build_hanging, load_maps, write_maps
from house_twin.textures import ROOT, TEXTURES_DIR, _blur, _linear_to_srgb, _srgb_to_linear, segment_garment

SPECS_DIR = ROOT / 'sources' / 'texturas'
DEFAULT_ART_WIDTH_M = 0.28        # ancho de un estampado de pecho en talla M (supuesto)
DEFAULT_ART_TOP_M = 0.12          # del punto más alto de la playera a la orilla de arriba del estampado (supuesto)
DEFAULT_BACKGROUND_TOLERANCE = 40  # diferencia (0–255) con el color del fondo a partir de la cual empieza el dibujo
DEFAULT_INK_ROUGHNESS = 0.6       # serigrafía con tinta plastisol
RECOLOR_RANGE = (0.5, 1.5)        # al teñir, cuánto puede alejarse un pixel del promedio de la tela (la etiqueta no brilla)


def _anchor(alpha: np.ndarray) -> tuple[float, int]:
    """Punto de referencia de una playera extendida: el centro del cuerpo (x) y su punto más alto (y)."""
    left, right = _body_edges(alpha)
    return (left + right) / 2, int(np.argmax(alpha.any(axis=1)))


def _crop_to_alpha(rgb: np.ndarray, alpha: np.ndarray):
    ys, xs = np.nonzero(alpha > 0.5)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1], (x0, y0, x1, y1)


def design_from_product(design: dict, template_spec: dict, photos_root: Path = ROOT):
    """Estampado recortado de una imagen de la prenda y su posición en metros respecto al cuerpo."""
    spec = {**template_spec, **{k: v for k, v in design.items() if k in ('corners_px', 'size_m', 'px_per_m', 'garment')}}
    spec['photo'] = design['image']
    seg = segment_garment(spec, photos_root)
    srgb = _linear_to_srgb(np.clip(seg['lin'], 0, 1))
    fabric = np.median(srgb[seg['garment'] & ~seg['printed']], axis=0)
    alpha = np.clip(_blur(seg['printed'].astype(float), 0.7), 0, 1)
    rgb, alpha, (x0, y0, x1, _) = _crop_to_alpha(srgb, alpha)
    cx, top = _anchor(seg['garment'])
    ppm = spec['px_per_m']
    placement = {'width_m': round((x1 - x0) / ppm, 4), 'top_m': round((y0 - top) / ppm, 4),
                 'offset_x_m': round(((x0 + x1) / 2 - cx) / ppm, 4), 'source': 'medida en la imagen de la prenda',
                 'fabric_srgb': [int(v) for v in np.round(fabric * 255)]}
    return rgb, alpha, placement


def recolor_fabric(layers: dict, alpha: np.ndarray, srgb: list[int]) -> dict:
    """Tiñe la tela del molde: cada pixel conserva cuánto más claro u oscuro es que el promedio de la tela (pliegues,
    tejido, sombras), ahora sobre el color nuevo. Se hace en lineal y con la luminancia, para no cambiar el tono."""
    lin = _srgb_to_linear(layers['basecolor'])
    luminance = lin @ np.array([0.2126, 0.7152, 0.0722])
    relative = np.clip(luminance / max(float(np.median(luminance[alpha])), 1e-4), *RECOLOR_RANGE)
    target = _srgb_to_linear(np.array(srgb, float) / 255)
    return {**layers, 'basecolor': _linear_to_srgb(np.clip(target * relative[..., None], 0, 1))}


def design_from_art(design: dict, photos_root: Path = ROOT):
    """Dibujo suelto: su transparencia, o su fondo quitado. La posición la da el diseño (o los supuestos)."""
    image = ImageOps.exif_transpose(Image.open(photos_root / design['image']))
    if image.mode in ('RGBA', 'LA', 'P') and np.asarray(image.convert('RGBA'))[..., 3].min() < 255:
        rgba = np.asarray(image.convert('RGBA')).astype(float) / 255
        rgb, alpha = rgba[..., :3], rgba[..., 3]
    else:
        rgb = np.asarray(image.convert('RGB')).astype(float) / 255
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        background = np.median(border, axis=0)
        tol = design.get('background_tolerance', DEFAULT_BACKGROUND_TOLERANCE) / 255
        alpha = np.clip((np.abs(rgb - background).max(axis=-1) - tol / 2) / tol, 0, 1)
    rgb, alpha, _ = _crop_to_alpha(rgb, alpha)
    placement = {'width_m': design.get('width_m', DEFAULT_ART_WIDTH_M), 'top_m': design.get('top_m', DEFAULT_ART_TOP_M),
                 'offset_x_m': design.get('offset_x_m', 0.0),
                 'source': 'la del diseño' if 'width_m' in design else 'supuesta: estampado de pecho centrado (talla M)'}
    return rgb, alpha, placement


def place_design(layers: dict, alpha: np.ndarray, ppm: float, art: tuple, roughness: float) -> dict:
    """Pega el estampado sobre los mapas del molde; fuera de la silueta del molde no queda nada."""
    rgb, art_alpha, placement = art
    cx, top = _anchor(alpha)
    w = max(1, round(placement['width_m'] * ppm))
    h = max(1, round(w * rgb.shape[0] / rgb.shape[1]))
    x0 = round(cx + placement['offset_x_m'] * ppm - w / 2)
    y0 = round(top + placement['top_m'] * ppm)
    resize = lambda a: np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((w, h), Image.LANCZOS))
    color = np.stack([resize(rgb[..., c]) for c in range(3)], -1)
    cover = np.zeros(alpha.shape)
    H, W = alpha.shape
    ys, xs = slice(max(0, y0), min(H, y0 + h)), slice(max(0, x0), min(W, x0 + w))
    src = (slice(ys.start - y0, ys.stop - y0), slice(xs.start - x0, xs.stop - x0))
    cover[ys, xs] = np.clip(resize(art_alpha), 0, 1)[src]
    cover *= alpha
    painted = np.zeros(alpha.shape + (3,))
    painted[ys, xs] = np.clip(color, 0, 1)[src]
    a = cover[..., None]
    return {**layers, 'basecolor': layers['basecolor'] * (1 - a) + painted * a,
            'roughness': layers['roughness'] * (1 - a) + roughness * a}


def build_design(spec: dict, photos_root: Path = ROOT) -> Path:
    """Prenda con molde: el estampado del diseño sobre los mapas extendidos del molde, y su versión colgada."""
    design = spec['design']
    template_spec = json.loads((SPECS_DIR / f"{spec['template']}.json").read_text())
    material, layers, alpha = load_maps(TEXTURES_DIR / spec['template'])
    if design['from'] == 'product':
        art = design_from_product(design, template_spec, photos_root)
    else:
        art = design_from_art(design, photos_root)
    fabric = art[2].get('fabric_srgb') if design.get('fabric') == 'from_image' else design.get('fabric_srgb')
    if fabric:  # tela de otro color que el molde: también su propia espalda lisa (la del molde es de su color)
        layers = recolor_fabric(layers, alpha, fabric)
        back = f"{spec['name']}-espalda"
        write_maps(TEXTURES_DIR / back, {**material, 'name': back, 'applies_to': spec['applies_to'],
                                         'source': {'template': spec['template'], 'fabric_srgb': fabric},
                                         'assumptions': material.get('assumptions', []) + ['espalda lisa: el molde teñido']},
                   layers, alpha)
        if spec.get('hanging'):
            spec = {**spec, 'back': {'name': back}, 'hanging': {**spec['hanging'], 'back_name': f"{spec['hanging']['name']}-espalda"}}
    layers = place_design(layers, alpha, material['px_per_m'], art, design.get('roughness', DEFAULT_INK_ROUGHNESS))
    out = TEXTURES_DIR / spec['name']
    source = {'template': spec['template'], 'design': design['image'], 'from': design['from'], 'placement': art[2]}
    write_maps(out, {**material, 'name': spec['name'], 'applies_to': spec['applies_to'], 'source': source,
                     'observed': spec.get('observed', {}), 'assumptions': material.get('assumptions', []) + spec.get('assumptions', [])},
               layers, alpha)
    if spec.get('hanging'):
        build_hanging(spec)
    return out
