"""Imagen de validación de los hechos: se dibuja SOLO desde `house.facts.json`, en metros."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import polylabel

PX_PER_M = 60
MARGIN = 50
SPACE_COLORS = [(255, 214, 165), (202, 255, 191), (155, 246, 255), (189, 178, 255), (255, 198, 255),
                (253, 255, 182), (160, 196, 255), (255, 173, 173), (210, 210, 210)]
EXTERIOR_COLOR = (232, 240, 228)
WALL_COLOR = (40, 40, 40)
DOOR_COLOR = (230, 120, 20)
WINDOW_COLOR = (30, 120, 230)
FONT_CANDIDATES = ('DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'Arial.ttf')
FONT_SIZE = 11


def _font():
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


class _Canvas:
    def __init__(self, width_m, depth_m):
        self.h = int(depth_m * PX_PER_M) + 2 * MARGIN
        self.img = Image.new('RGB', (int(width_m * PX_PER_M) + 2 * MARGIN, self.h), 'white')
        self.draw = ImageDraw.Draw(self.img)
        self.font = _font()

    def px(self, p):
        return (MARGIN + p[0] * PX_PER_M, self.h - MARGIN - p[1] * PX_PER_M)

    def polygon(self, pts, fill, outline=None):
        self.draw.polygon([self.px(p) for p in pts], fill=fill, outline=outline)

    def text(self, p, value, dy=0):
        x, y = self.px(p)
        self.draw.text((x, y + dy), value, fill='black', anchor='mm', font=self.font)


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def render_facts(facts: dict, out_path: Path):
    site = facts['site']
    canvas = _Canvas(site['width'], site['depth'])
    canvas.polygon(site['polygon'], fill=None, outline=(150, 150, 150))
    interiors = [s for s in facts['spaces'] if not s['is_exterior']]
    for s in facts['spaces']:
        color = EXTERIOR_COLOR if s['is_exterior'] else SPACE_COLORS[interiors.index(s) % len(SPACE_COLORS)]
        canvas.polygon(s['polygon'], fill=color)
    for w in facts['walls']:
        canvas.polygon(w['footprint'], fill=WALL_COLOR)
    for o in facts['openings']:
        canvas.polygon(o['footprint'], fill=DOOR_COLOR if o['kind'] == 'door' else WINDOW_COLOR)
        canvas.text(_centroid(o['footprint']), o['id'], dy=-10)
    for s in facts['spaces']:
        # polo de inaccesibilidad: el punto interior más alejado del borde (no cae en pasillos)
        pole = polylabel(Polygon(s['polygon']), tolerance=0.05)
        anchor = (pole.x, pole.y)
        canvas.text(anchor, f"{s['id']} {s['name'] or 'sin rótulo'}")
        canvas.text(anchor, f"{s['area']} m²", dy=14)
    for k in range(0, int(site['depth']) + 1):
        canvas.text((-0.4, k), f'{k}m')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.img.save(out_path)
