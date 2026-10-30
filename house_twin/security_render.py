"""Dibujo del plan de cámaras: campos de visión recortados por los muros y calidad de imagen en cada punto exterior.

Dos planos lado a lado, con la calle abajo como en `render.py`. Solo Pillow.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

from house_twin.security import CELL_M, LEVELS, Scene, evaluate, level_of, visibility_polygon

PX = 38
MARGIN = 34
HEAD = 58
FOOT = 112
WALL = (36, 36, 40)
ZONE = (233, 236, 230)
INTERIOR = (250, 250, 250)
DOOR = (230, 120, 20)
WINDOW = (30, 120, 230)
QUALITY = {'identificar': (22, 120, 60), 'reconocer': (88, 170, 98), 'observar': (176, 214, 120),
           'detectar': (240, 214, 100), 'sin imagen': (222, 60, 60)}
PALETTE = [(40, 110, 220), (210, 120, 20), (140, 60, 190), (20, 150, 165), (190, 60, 130), (120, 105, 20),
           (60, 60, 160), (130, 90, 60), (90, 90, 90), (200, 160, 0)]  # sin rojo ni verde: son los de la calidad de imagen
FONT_PATHS = ('DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'Arial.ttf')


def _font(size, bold=False):
    names = (('DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf') if bold else ()) + FONT_PATHS
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


class _Panel:
    def __init__(self, scene: Scene, title: str):
        site = scene.facts['site']
        self.y0 = -scene.plan['street_strip_m']
        self.width = int(site['width'] * PX) + 2 * MARGIN
        self.height = int((site['depth'] - self.y0) * PX) + 2 * MARGIN + HEAD
        self.img = Image.new('RGB', (self.width, self.height), (255, 255, 255))  # RGB: en RGBA Pillow reemplaza el píxel y no mezcla las transparencias
        self.d = ImageDraw.Draw(self.img, 'RGBA')
        self.d.text((MARGIN, 14), title, fill=(20, 20, 20), font=_font(15, True))

    def px(self, p):
        return (MARGIN + p[0] * PX, self.height - MARGIN - (p[1] - self.y0) * PX)

    def polygon(self, geom, fill, outline=None, holes=True):
        """Dibuja un polígono; con `holes`, sus huecos se rellenan del color del interior (los cuartos dentro de los muros)."""
        for g in getattr(geom, 'geoms', [geom]):
            if g.is_empty or g.geom_type != 'Polygon':
                continue
            self.d.polygon([self.px(p) for p in g.exterior.coords], fill=fill, outline=outline)
            for hole in g.interiors if holes else []:
                self.d.polygon([self.px(p) for p in hole.coords], fill=INTERIOR)

    def walls(self, geom):
        """Muros en una capa aparte: sus huecos (los cuartos que cierran) quedan transparentes y no borran lo de abajo."""
        layer = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for g in getattr(geom, 'geoms', [geom]):
            if g.is_empty or g.geom_type != 'Polygon':
                continue
            d.polygon([self.px(p) for p in g.exterior.coords], fill=WALL + (255,))
            for hole in g.interiors:
                d.polygon([self.px(p) for p in hole.coords], fill=(0, 0, 0, 0))
        self.img.paste(layer, mask=layer)

    def base(self, scene: Scene):
        site = scene.facts['site']
        self.polygon(scene.strip, (240, 240, 244, 255))
        self.d.text(self.px((site['width'] / 2, self.y0 + 0.5)), 'calle y banqueta', fill=(130, 130, 140), anchor='mm', font=_font(11))
        self.polygon(Polygon(site['polygon']), INTERIOR, (160, 160, 160))
        self.polygon(scene.exterior, ZONE)
        font = _font(10)
        for s in scene.spaces:
            poly = Polygon(s['polygon'])
            c = poly.representative_point()
            label = s['name'] if self.d.textlength(s['name'], font=font) < (poly.bounds[2] - poly.bounds[0]) * PX - 6 else s['id']
            self.d.text(self.px((c.x, c.y)), label, fill=(120, 124, 116), anchor='mm', font=font)
        self.walls(scene.obstacles)
        for o in scene.facts['openings']:
            if o['footprint']:
                self.polygon(Polygon(o['footprint']).buffer(0.03), DOOR if o['kind'] == 'door' else WINDOW)

    def camera(self, cam, color, label):
        x, y = self.px(cam['mount'])
        a = math.radians(cam['yaw_deg'])
        tip = (x + 15 * math.cos(a), y - 15 * math.sin(a))
        self.d.polygon([(x - 6, y - 6), (x + 6, y - 6), (x + 6, y + 6), (x - 6, y + 6)], fill=color, outline=(0, 0, 0))
        self.d.line([(x, y), tip], fill=(0, 0, 0), width=2)
        self.d.text((x + 11, y - 17), label, fill=(0, 0, 0), font=_font(12, True), stroke_width=2, stroke_fill=(255, 255, 255))


def _cell_polygon(x, y):
    h = CELL_M / 2
    return [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]


def render_plan(scene: Scene, cameras: list[dict], out_path: Path, title: str = '', optional: list[dict] | None = None) -> dict:
    """Dibuja el plan y devuelve la evaluación de cobertura. Las cámaras `optional` se dibujan en hueco y no cuentan en ella."""
    result = evaluate(scene, cameras)
    cells = scene.cells
    left, right = _Panel(scene, f'Campos de visión{title}'), _Panel(scene, f'Calidad de imagen{title}')
    left.base(scene)
    site = scene.facts['site']
    frame = Polygon([(0, left.y0), (site['width'], left.y0), (site['width'], site['depth']), (0, site['depth'])])  # no se dibuja lo que cae en predios vecinos
    for k, cam in enumerate(cameras):
        left.polygon(visibility_polygon(scene, cam).intersection(frame), PALETTE[k % len(PALETTE)] + (55,), PALETTE[k % len(PALETTE)] + (160,), holes=False)
    for k, cam in enumerate(optional or [], len(cameras)):
        left.polygon(visibility_polygon(scene, cam).intersection(frame), (255, 255, 255, 0), (90, 90, 90, 200), holes=False)
    left.walls(scene.obstacles)
    for k, cam in enumerate(cameras):
        left.camera(cam, PALETTE[k % len(PALETTE)], cam['id'])
    for cam in optional or []:
        left.camera(cam, (255, 255, 255), f"{cam['id']} (opcional)")
    right.base(scene)
    for i in range(len(cells['x'])):
        name = 'sin imagen' if result['blind'][i] else level_of(float(result['best_ppm'][i]))
        right.polygon(Polygon(_cell_polygon(cells['x'][i], cells['y'][i])), QUALITY[name] + (235,))
    right.walls(scene.obstacles)
    for k, cam in enumerate(cameras):
        right.camera(cam, PALETTE[k % len(PALETTE)], cam['id'])
    sheet = Image.new('RGB', (left.width + right.width, left.height + FOOT), 'white')
    sheet.paste(left.img.convert('RGB'), (0, 0))
    sheet.paste(right.img.convert('RGB'), (left.width, 0))
    d = ImageDraw.Draw(sheet)
    x = MARGIN
    for name in ('identificar', 'reconocer', 'observar', 'detectar', 'sin imagen'):
        d.rectangle([x, left.height + 18, x + 18, left.height + 36], fill=QUALITY[name], outline=(0, 0, 0))
        label = f'{name} ({LEVELS[name]} px/m)' if name in LEVELS else 'punto ciego'
        d.text((x + 24, left.height + 27), label, fill=(0, 0, 0), anchor='lm', font=_font(12))
        x += 24 + int(d.textlength(label, font=_font(12))) + 22
    d.rectangle([MARGIN, left.height + 52, MARGIN + 18, left.height + 70], fill=DOOR)
    d.text((MARGIN + 24, left.height + 61), 'puerta o reja', fill=(0, 0, 0), anchor='lm', font=_font(12))
    d.rectangle([MARGIN + 150, left.height + 52, MARGIN + 168, left.height + 70], fill=WINDOW)
    d.text((MARGIN + 174, left.height + 61), 'ventana', fill=(0, 0, 0), anchor='lm', font=_font(12))
    d.text((MARGIN, left.height + 88), 'Cámaras a 2.4 m, 4 MP. Se exige reconocer junto a puertas y ventanas, observar en el resto del exterior y '
           'detectar en la banqueta.', fill=(70, 70, 70), anchor='lm', font=_font(11))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return result
