"""Marco de referencia compartido: convierte coordenadas del PDF (pt) a metros reales.

El marco (pt/m y origen) lo calcula calibrate.py y queda en <build>/frame.json.
Origen = esquina del terreno del lado izquierdo de la calle; X a lo ancho, Y hacia el fondo.
"""
import json
from pathlib import Path

GLYPH_OFFSET = 29  # la fuente subset de AutoCAD desplaza los códigos ASCII
GLYPH_FIXES = {'\x83': 'Ñ'}


def decode_glyphs(text):
    decoded = ''.join(chr(ord(c) + GLYPH_OFFSET) for c in text)
    for wrong, right in GLYPH_FIXES.items():
        decoded = decoded.replace(wrong, right)
    return decoded


def load_prims(build_dir):
    return json.loads((Path(build_dir) / 'prims.json').read_text())


class Frame:
    def __init__(self, pt_per_m, origin_pt):
        self.pt_per_m = pt_per_m
        self.origin_pt = origin_pt

    @classmethod
    def load(cls, build_dir):
        data = json.loads((Path(build_dir) / 'frame.json').read_text())
        return cls(data['pt_per_m'], tuple(data['origin_pt']))

    def to_m(self, point):
        return ((point[0] - self.origin_pt[0]) / self.pt_per_m, (point[1] - self.origin_pt[1]) / self.pt_per_m)
