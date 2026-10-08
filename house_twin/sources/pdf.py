"""Fuente PDF: lee el plano vectorial, calibra la escala contra las cotas y entrega un `Drawing` en metros.

El PDF se ploteó "ajustado a hoja", así que la escala del cajetín (1:100) no sirve:
se ajusta pt/m por mínimos cuadrados emparejando cada línea de cota con su valor.
"""
from house_twin.drawing import LAYER_ROLES, Drawing, Text
from house_twin.sources.pdf_content import RawPath, RawText, read_content

GLYPH_OFFSET = 29  # la fuente subset de AutoCAD desplaza los códigos ASCII
GLYPH_FIXES = {'\x83': 'Ñ'}
DIMENSION_LAYER = '14-DIM INTERIOR'


def decode_glyphs(text: str) -> str:
    decoded = ''.join(chr(ord(c) + GLYPH_OFFSET) for c in text)
    for wrong, right in GLYPH_FIXES.items():
        decoded = decoded.replace(wrong, right)
    return decoded


def _length(a, b):
    return ((b[0]-a[0])**2 + (b[1]-a[1])**2) ** 0.5


def _dimension_pairs(paths: list[RawPath], texts: list[RawText]):
    values = [(float(decode_glyphs(t.raw)), t.position) for t in texts if t.layer == DIMENSION_LAYER]
    for p in paths:
        if p.layer != DIMENSION_LAYER or len(p.points) != 2:
            continue
        a, b = p.points
        mid = ((a[0]+b[0])/2, (a[1]+b[1])/2)
        is_vertical = abs(a[0]-b[0]) < 0.05
        # el texto de una cota vertical va girado junto a la línea: pesa menos la distancia en X
        weight = 0.3 if is_vertical else 3
        value, _ = min(values, key=lambda v: abs(v[1][1]-mid[1]) + abs(v[1][0]-mid[0]) * weight)
        yield _length(a, b), value


def calibrate(paths: list[RawPath], texts: list[RawText]) -> dict:
    pairs = list(_dimension_pairs(paths, texts))
    pt_per_m = sum(length * v for length, v in pairs) / sum(v * v for _, v in pairs)
    residuals = sorted(((v, round(length/pt_per_m - v, 4)) for length, v in pairs), key=lambda r: -abs(r[1]))
    wall_points = [q for p in paths if p.layer in LAYER_ROLES['walls'] for q in p.points]
    origin = (min(x for x, _ in wall_points), min(y for _, y in wall_points))
    return {'pt_per_m': pt_per_m, 'origin_pt': origin, 'paper_scale': 72 / 25.4 * 1000 / pt_per_m,
            'dimension_residuals_m': residuals}


def load_pdf_drawing(pdf_path: str) -> Drawing:
    paths, texts, info = read_content(pdf_path)
    cal = calibrate(paths, texts)
    k, (ox, oy) = cal['pt_per_m'], cal['origin_pt']
    to_m = lambda p: (round((p[0]-ox)/k, 4), round((p[1]-oy)/k, 4))
    drawing = Drawing(source=f'pdf:{pdf_path}', metadata={**info, 'calibration': cal, 'precision_m': 0.12 / k})
    for p in paths:
        pts = [to_m(q) for q in p.points]
        drawing.segments.setdefault(p.layer, []).extend((a, b) for a, b in zip(pts, pts[1:]) if a != b)
    drawing.texts = [Text(t.layer, decode_glyphs(t.raw), to_m(t.position)) for t in texts]
    return drawing
