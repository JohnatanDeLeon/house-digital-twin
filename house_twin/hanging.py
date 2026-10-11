"""Prenda colgada a partir de sus mapas extendidos (`assets/textures/<prenda>/`), sin volver a la foto.

En un gancho, la manga de una playera no gira como pieza rígida: sigue cosida a la sisa y solo cae. Cada manga se
recorta del costado del cuerpo (recto, medido cerca de la orilla de abajo) hacia afuera, y se redibuja de modo que la
sisa queda fija y el eje de la manga baja de su ángulo en la foto (`α0`, medido en la silueta) a `sleeve_angle_deg`
bajo la horizontal. La manga no se monta sobre el cuerpo: cae por fuera de él, como en una prenda colgada de frente.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from house_twin.textures import DETAIL_MAP_SCALE, TEXTURES_DIR, _component

EDGE_INSET_PX = 6   # lo que la manga debe sobresalir del costado para contar como manga
MARGIN_PX = 8       # aire alrededor de la silueta al recortar


def _body_edges(alpha: np.ndarray) -> tuple[int, int]:
    """Costados del cuerpo: la mediana de la silueta entre el 80 y el 95 % del alto (lejos de mangas y dobladillo)."""
    H, W = alpha.shape
    rows = [y for y in range(int(H * 0.8), int(H * 0.95)) if alpha[y].any()]
    left = int(np.median([np.argmax(alpha[y]) for y in rows]))
    right = int(np.median([W - 1 - np.argmax(alpha[y][::-1]) for y in rows]))
    return left, right


def _sleeve(alpha: np.ndarray, edge: int, side: int) -> dict:
    """La manga de un lado: su máscara, el hombro (lo más alto de la prenda en el costado) y el ángulo de su eje."""
    H, W = alpha.shape
    cols = np.arange(W)
    outside = (cols < edge - EDGE_INSET_PX) if side < 0 else (cols > edge + EDGE_INSET_PX)
    sticking = [y for y in range(H) if (alpha[y] & outside).any()]
    seed_y = sticking[len(sticking) // 2] if sticking else None
    if seed_y is None:
        return {'mask': np.zeros_like(alpha), 'edge': edge, 'side': side, 'tan0': 0.0}
    seed_x = edge - EDGE_INSET_PX - 1 if side < 0 else edge + EDGE_INSET_PX + 1
    beyond = alpha & ((cols < edge)[None, :] if side < 0 else (cols > edge)[None, :])
    mask = _component(beyond, (seed_x, seed_y)) if beyond[seed_y, seed_x] else beyond & outside[None, :]
    return {'mask': mask, 'edge': edge, 'side': side, 'tan0': _axis_slope(mask, edge, side)}


def _axis_slope(mask: np.ndarray, edge: int, side: int) -> float:
    """Pendiente del eje de la manga en la foto (hacia abajo y afuera): el promedio de sus orillas de arriba y abajo,
    ajustadas por mínimos cuadrados en la mitad de la manga más cercana al hombro (la punta es el dobladillo)."""
    xs = np.nonzero(mask.any(axis=0))[0]
    reach = (edge - xs.min()) if side < 0 else (xs.max() - edge)
    d = np.arange(1, max(2, reach // 2))
    cols = edge - d if side < 0 else edge + d
    tops = np.array([np.argmax(mask[:, c]) for c in cols], float)
    bottoms = np.array([mask.shape[0] - 1 - np.argmax(mask[::-1, c]) for c in cols], float)
    return float((np.polyfit(d, tops, 1)[0] + np.polyfit(d, bottoms, 1)[0]) / 2)


def _bilinear(layer: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    H, W = layer.shape[:2]
    x0, y0 = np.clip(np.floor(xs).astype(int), 0, W - 2), np.clip(np.floor(ys).astype(int), 0, H - 2)
    fx, fy = np.clip(xs - x0, 0, 1)[..., None], np.clip(ys - y0, 0, 1)[..., None]
    top = layer[y0, x0] * (1 - fx) + layer[y0, x0 + 1] * fx
    bottom = layer[y0 + 1, x0] * (1 - fx) + layer[y0 + 1, x0 + 1] * fx
    return top * (1 - fy) + bottom * fy


def _drop(sleeve: dict, shape, angle_deg: float):
    """Coordenadas de origen de cada pixel de destino de la manga caída (mapeo inverso) y el giro de su tela.

    Un pixel a `d` del costado está, en la foto, sobre la recta del eje que sale de la sisa en `y − d·tan α0`; colgada,
    esa recta sale del mismo punto de la sisa con el ángulo nuevo y conserva su largo."""
    H, W = shape
    edge, side = sleeve['edge'], sleeve['side']
    a0, a1 = math.atan(sleeve['tan0']), math.radians(angle_deg)
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    out = (edge - xs) if side < 0 else (xs - edge)  # distancia hacia afuera del costado, en el destino
    s = out / math.cos(a1)                          # largo sobre el eje
    src_x = edge + side * s * math.cos(a0)
    src_y = ys - s * (math.sin(a1) - math.sin(a0))
    valid = out > 0
    return src_x, src_y, valid, (a1 - a0) * (1 if side < 0 else -1)


def _rotate_normals(normal: np.ndarray, turn: float) -> np.ndarray:
    """Gira el plano de un normal map (OpenGL: x a la derecha, y arriba) como giró la tela."""
    n = normal * 2 - 1
    c, s = math.cos(turn), math.sin(turn)
    x, y = n[..., 0] * c - n[..., 1] * s, n[..., 0] * s + n[..., 1] * c
    return (np.stack([x, y, n[..., 2]], -1) + 1) / 2


def hang_layers(layers: dict[str, np.ndarray], alpha: np.ndarray, angle_deg: float) -> tuple[dict, np.ndarray]:
    """Cuelga una prenda: `layers` son mapas a resolución completa (H×W×C, 0–1) y `alpha` su silueta."""
    left, right = _body_edges(alpha)
    sleeves = [_sleeve(alpha, left, -1), _sleeve(alpha, right, 1)]
    body = alpha & ~sleeves[0]['mask'] & ~sleeves[1]['mask']
    out = {k: v * body[..., None] for k, v in layers.items()}
    new_alpha = body.astype(float)
    for sl in sleeves:
        src_x, src_y, valid, turn = _drop(sl, alpha.shape, angle_deg)
        a = _bilinear(sl['mask'].astype(float)[..., None], src_x, src_y)[..., 0] * valid
        hit = a > 0.5
        new_alpha = np.where(hit, 1.0, new_alpha)
        for k, v in layers.items():
            piece = _bilinear(v * sl['mask'][..., None], src_x, src_y) / np.maximum(a, 1e-3)[..., None]
            if k == 'normal':
                piece = _rotate_normals(piece, turn)
            out[k] = np.where(hit[..., None], piece, out[k])
    return out, new_alpha > 0.5


def _crop_box(alpha: np.ndarray):
    ys, xs = np.nonzero(alpha)
    H, W = alpha.shape
    return max(0, ys.min() - MARGIN_PX), min(H, ys.max() + MARGIN_PX + 1), max(0, xs.min() - MARGIN_PX), min(W, xs.max() + MARGIN_PX + 1)


def load_maps(folder: Path) -> tuple[dict, dict[str, np.ndarray], np.ndarray]:
    """Mapas de una prenda extendida a resolución completa (los de detalle se generan a media resolución)."""
    material = json.loads((folder / 'material.json').read_text())
    alpha = np.asarray(Image.open(folder / 'opacity.png').convert('L')) > 127
    size = alpha.shape[::-1]
    read = lambda f, mode: np.asarray(Image.open(folder / f).convert(mode).resize(size, Image.BILINEAR)).astype(float) / 255
    layers = {'basecolor': read('basecolor.jpg', 'RGB'), 'roughness': read('roughness.png', 'L')[..., None],
              'normal': read('normal.png', 'RGB')}
    if (folder / 'metallic.png').exists():
        layers['metallic'] = read('metallic.png', 'L')[..., None]
    return material, layers, alpha


def write_maps(out: Path, material: dict, layers: dict, alpha: np.ndarray):
    """Escribe los mapas de una prenda (los de detalle a media resolución) y su `material.json`, en una carpeta limpia."""
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob('*'):
        stale.unlink()
    H, W = alpha.shape
    detail = (round(W * DETAIL_MAP_SCALE), round(H * DETAIL_MAP_SCALE))
    to8 = lambda a: (np.clip(a, 0, 1) * 255).round().astype(np.uint8)
    Image.fromarray(to8(layers['basecolor'])).save(out / 'basecolor.jpg', quality=92)
    Image.fromarray(to8(layers['roughness'][..., 0])).resize(detail, Image.LANCZOS).save(out / 'roughness.png', optimize=True)
    Image.fromarray(to8(layers['normal'])).resize(detail, Image.LANCZOS).save(out / 'normal.png', optimize=True)
    Image.fromarray(alpha.astype(np.uint8) * 255).save(out / 'opacity.png', optimize=True)
    if 'metallic' in layers:
        Image.fromarray(to8(layers['metallic'][..., 0])).resize(detail, Image.LANCZOS).save(out / 'metallic.png', optimize=True)
    (out / 'material.json').write_text(json.dumps({**material, 'size_px': [W, H]}, ensure_ascii=False, indent=1) + '\n')


def build_hanging(spec: dict) -> list[Path]:
    """Versiones colgadas (frente y, si hay, espalda) de una prenda cuyos mapas extendidos ya están generados."""
    hang = spec['hanging']
    angle = hang['sleeve_angle_deg']
    size_source = (f'la prenda extendida con cada manga caída a {angle}° bajo la horizontal, cosida a la sisa '
                   f'(hang_layers)')
    pairs = [(spec['name'], hang['name'])] + ([(spec['back']['name'], hang['back_name'])] if spec.get('back') else [])
    _, _, front_alpha = load_maps(TEXTURES_DIR / spec['name'])
    written = []
    for flat, hanging in pairs:
        material, layers, _ = load_maps(TEXTURES_DIR / flat)
        layers, hung = hang_layers(layers, front_alpha, angle)  # la espalda cae con la misma silueta que el frente
        y0, y1, x0, x1 = _crop_box(hung)
        layers, hung = {k: v[y0:y1, x0:x1] for k, v in layers.items()}, hung[y0:y1, x0:x1]
        px_per_m = material['px_per_m']
        size = {'width': round(hung.shape[1] / px_per_m, 4), 'height': round(hung.shape[0] / px_per_m, 4),
                'source': size_source}
        write_maps(TEXTURES_DIR / hanging, {**material, 'name': hanging, 'size_m': size,
                                            'assumptions': material.get('assumptions', []) + [hang['note']]}, layers, hung)
        written.append(TEXTURES_DIR / hanging)
    return written
