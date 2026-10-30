"""Cámaras de seguridad en el exterior: cobertura, calidad de imagen y puntos ciegos.

Todo sale de los hechos (muros, vanos, espacios exteriores) y de un plan de cámaras (`variants/camaras-exterior/plan.json`):
una propuesta, no un hecho. El plano se reparte en celdas de 25 cm en las zonas exteriores y en una franja de banqueta
frente a la casa; cada celda exige una calidad de imagen según lo que hay cerca (norma EN 62676-4, niveles DORI):

- detectar (25 px/m): saber que alguien pasa;
- observar (62 px/m): ver qué hace;
- reconocer (125 px/m): saber quién es, si ya se le conoce;
- identificar (250 px/m): reconocer a alguien que no se conoce.

Una cámara cubre una celda si (1) la ve (línea de vista sin muros), (2) cae dentro de su ángulo de visión, (3) no queda
en el punto ciego al pie de la cámara (con la cámara a 2.4 m e inclinada hacia abajo, el suelo pegado al muro no sale) y
(4) la densidad de píxeles en esa celda llega a la que se exige. Los muros se toman como obstáculos de cualquier altura
(la barda y los muros miden ≈ 2.6 m, más que la cámara); el cristal de las ventanas también estorba la vista, porque
no se vigila hacia adentro. Las rejas y la herrería se ven a través, salvo que la propuesta las cierre.
"""
import json
import math
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / 'variants' / 'camaras-exterior' / 'plan.json'
LEVELS = {'detectar': 25, 'observar': 62, 'reconocer': 125, 'identificar': 250}
CELL_M = 0.25
SEE_THROUGH = ('D01', 'V11', 'V12')  # herrería de la casa actual: se ve a través (las hostless, también)
ENTRY_RADIUS_M = {'door': 2.0, 'window': 1.5}  # franja junto a un acceso donde se exige reconocer


def load_plan(path: Path = PLAN_PATH) -> dict:
    return json.loads(Path(path).read_text())


def ppm(distance_m, hfov_deg: float, width_px: int):
    """Píxeles por metro (a lo ancho) a `distance_m` de la cámara."""
    return width_px / (2 * np.asarray(distance_m, float) * math.tan(math.radians(hfov_deg / 2)))


class Scene:
    """Obstáculos y celdas por cubrir, a partir de unos hechos (los de la casa o los de una propuesta)."""

    def __init__(self, facts: dict, plan: dict, see_through=SEE_THROUGH):
        self.facts, self.plan = facts, plan
        holes = [Polygon(o['footprint']) for o in facts['openings'] if o['id'] in see_through and o['footprint']]
        walls = []
        for w in facts['walls']:
            p = Polygon(w['footprint'])
            for h in holes:
                if p.intersects(h):
                    p = p.difference(h)
            walls.append(p)
        for o in facts['openings']:  # un portón seccional es lámina cerrada: estorba la vista
            lift = o.get('lift')
            if lift:  # junto con el hueco que queda entre la línea de la calle y el panel (14 cm: nadie cabe ahí)
                low = min(p[1] for p in o['footprint'])
                walls.append(box(lift['x'][0], low, lift['x'][1], lift['y'] + lift['thickness_m']))
        self.obstacles = unary_union(walls)
        shapely.prepare(self.obstacles)
        width = facts['site']['width']
        # un espacio exterior que una propuesta cierra con muros (la lavandería de la cocina en U) ya no es exterior
        self.spaces = [s for s in facts['spaces'] if s['is_exterior'] and (s.get('enclosed') or {}).get('value') is not True]
        self.exterior = unary_union([Polygon(s['polygon']) for s in self.spaces])
        self.strip = box(0, -plan['street_strip_m'], width, 0)
        self.entries = self._entries()
        self.cells = self._cells()

    def _entries(self) -> list[dict]:
        """Accesos (puertas y ventanas) que dan a un espacio exterior o a la calle."""
        spaces = {s['id'] for s in self.spaces}
        found = []
        for o in self.facts['openings']:
            if not o['footprint'] or not (set(o['connects']) & spaces):
                continue
            kind = 'door' if o['kind'] == 'door' else 'window'
            found.append({'id': o['id'], 'kind': kind, 'shape': Polygon(o['footprint']).buffer(0.001)})
        return found

    def _cells(self) -> dict:
        """Centros de celda, qué calidad exigen y a qué zona pertenecen."""
        width, depth = self.facts['site']['width'], self.facts['site']['depth']
        xs, ys = np.meshgrid(np.arange(CELL_M / 2, width, CELL_M), np.arange(-self.plan['street_strip_m'] + CELL_M / 2, depth, CELL_M))
        x, y = xs.ravel(), ys.ravel()
        in_zone = shapely.contains_xy(self.exterior, x, y) & ~shapely.contains_xy(self.obstacles, x, y)
        in_strip = shapely.contains_xy(self.strip, x, y)
        keep = in_zone | in_strip
        x, y, in_strip = x[keep], y[keep], in_strip[keep]
        required = np.where(in_strip, LEVELS['detectar'], LEVELS['observar']).astype(float)
        pts = shapely.points(x, y)
        near_entry = np.zeros(len(x), bool)
        for e in self.entries:
            near_entry |= shapely.distance(pts, e['shape']) <= ENTRY_RADIUS_M[e['kind']]
        required[near_entry] = LEVELS['reconocer']
        zone_id = np.full(len(x), '', dtype=object)
        zone_id[in_strip] = 'calle'
        for s in self.spaces:
            zone_id[shapely.contains_xy(Polygon(s['polygon']), x, y) & ~in_strip] = s['id']
        return {'x': x, 'y': y, 'required': required, 'zone': zone_id, 'strip': in_strip, 'entry': near_entry}

    def sees(self, origin, xs, ys) -> np.ndarray:
        """¿Hay línea de vista del punto `origin` a cada celda?"""
        lines = shapely.linestrings(np.stack([np.stack([np.full(len(xs), origin[0]), np.full(len(xs), origin[1])], -1),
                                               np.stack([xs, ys], -1)], 1))
        return ~shapely.intersects(lines, self.obstacles)


def camera_coverage(scene: Scene, cam: dict, los: np.ndarray | None = None) -> dict:
    """Qué celdas ve una cámara y con cuántos píxeles por metro."""
    plan, cells = scene.plan, scene.cells
    lens = plan['lenses_mm'][str(cam['lens_mm'])]
    mx, my = cam['mount']
    dx, dy = cells['x'] - mx, cells['y'] - my
    ground = np.hypot(dx, dy)
    slant = np.hypot(ground, plan['mount_height_m'] - plan['target_height_m'])
    bearing = np.degrees(np.arctan2(dy, dx))
    off = np.abs((bearing - cam['yaw_deg'] + 180) % 360 - 180)
    density = ppm(np.maximum(slant, 1e-6), lens['hfov_deg'], plan['sensor']['width_px'])
    visible = scene.sees((mx, my), cells['x'], cells['y']) if los is None else los
    seen = visible & (off <= lens['hfov_deg'] / 2) & (ground >= plan['min_ground_distance_m'])
    return {'seen': seen, 'ppm': np.where(seen, density, 0.0)}


def evaluate(scene: Scene, cameras: list[dict]) -> dict:
    """Cobertura de un conjunto de cámaras: celdas ciegas, calidad por zona y redundancia."""
    cells = scene.cells
    per = [camera_coverage(scene, c) for c in cameras]
    best = np.max([p['ppm'] for p in per], axis=0) if per else np.zeros(len(cells['x']))
    meets = np.array([p['ppm'] >= cells['required'] for p in per]) if per else np.zeros((0, len(cells['x'])), bool)
    count = meets.sum(axis=0)
    blind = count == 0
    zones = {}
    for z in sorted(set(cells['zone'])):
        m = cells['zone'] == z
        zones[z] = {'cells': int(m.sum()), 'area_m2': round(float(m.sum()) * CELL_M ** 2, 1),
                    'covered_pct': round(100 * float((~blind[m]).mean()), 1),
                    'redundant_pct': round(100 * float((count[m] >= 2).mean()), 1)}
    return {'best_ppm': best, 'count': count, 'blind': blind, 'zones': zones, 'per_camera': per,
            'blind_points': [(round(float(x), 2), round(float(y), 2)) for x, y in zip(cells['x'][blind], cells['y'][blind])]}


def level_of(value: float) -> str:
    for name in ('identificar', 'reconocer', 'observar', 'detectar'):
        if value >= LEVELS[name]:
            return name
    return 'sin imagen'


def visibility_polygon(scene: Scene, cam: dict, steps: int = 90) -> Polygon:
    """Lo que alcanza a ver una cámara, recortado por los muros, hasta donde da el nivel mínimo (para dibujarlo)."""
    plan = scene.plan
    lens = plan['lenses_mm'][str(cam['lens_mm'])]
    mx, my = cam['mount']
    reach = plan['sensor']['width_px'] / (2 * math.tan(math.radians(lens['hfov_deg'] / 2)) * LEVELS['observar'])
    points = [(mx, my)]
    for k in range(steps + 1):
        angle = math.radians(cam['yaw_deg'] - lens['hfov_deg'] / 2 + lens['hfov_deg'] * k / steps)
        end = (mx + reach * math.cos(angle), my + reach * math.sin(angle))
        ray = LineString([(mx, my), end])
        hit = ray.intersection(scene.obstacles)
        if not hit.is_empty:
            near = min((Point(p).distance(Point(mx, my)), p) for g in getattr(hit, 'geoms', [hit])
                       for p in (g.coords if g.geom_type != 'Polygon' else g.exterior.coords))
            end = near[1]
        points.append(end)
    return Polygon(points).buffer(0)


def candidate_mounts(scene: Scene, step_m: float = 0.5, offset_m: float = 0.1) -> list[dict]:
    """Posiciones posibles: sobre las caras de los muros que dan al exterior, cada `step_m`, a `offset_m` de la cara.

    Cada una lleva la dirección en que mira la pared (la cámara solo puede mirar hacia afuera de ella)."""
    zone = scene.exterior.union(scene.strip.buffer(0)).buffer(0.15)
    mounts = []
    for poly in getattr(scene.obstacles, 'geoms', [scene.obstacles]):
        ring = poly.exterior
        n = max(int(ring.length / step_m), 4)
        for k in range(n):
            a, b = ring.interpolate(k * ring.length / n), ring.interpolate(k * ring.length / n + 0.01)
            tx, ty = b.x - a.x, b.y - a.y
            length = math.hypot(tx, ty) or 1.0
            for sign in (1, -1):  # las dos caras del segmento: se queda la que da al exterior
                nx, ny = sign * ty / length, -sign * tx / length
                pos = (a.x + nx * offset_m, a.y + ny * offset_m)
                if zone.contains(Point(pos)) and not scene.obstacles.contains(Point(pos)):
                    mounts.append({'mount': (round(pos[0], 3), round(pos[1], 3)), 'normal_deg': math.degrees(math.atan2(ny, nx))})
    unique = {}
    for m in mounts:
        unique[(round(m['mount'][0], 1), round(m['mount'][1], 1))] = m
    return list(unique.values())


def near(candidates: list[dict], point, radius_m: float) -> np.ndarray:
    """Índices (máscara) de las candidatas a menos de `radius_m` de un punto."""
    return np.array([math.dist(c['mount'], point) < radius_m for c in candidates], bool) if radius_m > 0 else np.zeros(len(candidates), bool)


def suggest(scene: Scene, max_cameras: int = 12, yaw_step: int = 15, min_separation_m: float = 0.0, keep: list[dict] | None = None) -> dict:
    """Búsqueda voraz del menor número de cámaras que cubre todas las celdas con la calidad exigida.

    Con `min_separation_m`, dos cámaras no pueden quedar más cerca que eso (así un solo golpe no deja ciega una zona).
    Con `keep`, parte de unas cámaras ya instaladas y solo agrega las que faltan.
    Devuelve las cámaras elegidas (en orden), y las celdas que ninguna posición alcanza a cubrir."""
    cells, plan = scene.cells, scene.plan
    n = len(cells['x'])
    candidates, rows = [], []
    for m in candidate_mounts(scene):
        los = scene.sees(m['mount'], cells['x'], cells['y'])
        for lens in plan['lenses_mm']:
            for yaw in range(0, 360, yaw_step):
                if abs((yaw - m['normal_deg'] + 180) % 360 - 180) > 100:  # mirando hacia la pared: no
                    continue
                cam = {'mount': m['mount'], 'yaw_deg': yaw, 'lens_mm': float(lens) if '.' in lens else int(lens)}
                cover = camera_coverage(scene, cam, los)['ppm'] >= cells['required']
                if cover.any():
                    candidates.append(cam)
                    rows.append(cover)
    matrix = np.array(rows)
    reachable = matrix.any(axis=0)
    covered = np.zeros(n, bool)
    chosen = []
    for cam in keep or []:
        covered |= camera_coverage(scene, cam)['ppm'] >= cells['required']
    while len(chosen) < max_cameras and (reachable & ~covered).any():
        gain = (matrix & ~covered).sum(axis=1)
        for cam in chosen + list(keep or []):  # no se repiten posiciones cercanas
            gain[near(candidates, cam['mount'], min_separation_m)] = 0
        best = int(gain.argmax())
        if gain[best] == 0:
            break
        chosen.append(candidates[best])
        covered |= matrix[best]
    unreachable = [(round(float(x), 2), round(float(y), 2)) for x, y in zip(cells['x'][~reachable], cells['y'][~reachable])]
    return {'cameras': chosen, 'candidates': len(candidates), 'unreachable': unreachable}


def entry_report(scene: Scene, result: dict) -> list[dict]:
    """Por acceso (puerta o ventana al exterior): cuánta de su franja de «reconocer» ve una cámara, cuánta ven dos, y la
    mejor calidad de imagen en el punto donde se para quien llega (0.5 m frente al acceso, del lado exterior)."""
    cells, count, best = scene.cells, result['count'], result['best_ppm']
    pts = shapely.points(cells['x'], cells['y'])
    report = []
    for e in scene.entries:
        near = shapely.distance(pts, e['shape']) <= ENTRY_RADIUS_M[e['kind']]
        near &= cells['required'] >= LEVELS['reconocer']
        if not near.any():
            continue
        report.append({'id': e['id'], 'kind': e['kind'], 'cells': int(near.sum()),
                       'covered_pct': round(100 * float((count[near] >= 1).mean()), 1),
                       'redundant_pct': round(100 * float((count[near] >= 2).mean()), 1),
                       'worst_ppm': round(float(best[near].min())), 'median_ppm': round(float(np.median(best[near])))})
    return report


def cameras_in(scene: Scene, plan: dict, optional: bool = False) -> list[dict]:
    """Las cámaras del plan que aplican a esta escena: la de un espacio exterior solo cuenta mientras ese espacio sea
    exterior, y las opcionales (`optional`: dan redundancia, no cobertura) solo si se piden."""
    spaces = {s['id'] for s in scene.spaces}
    return [c for c in plan['cameras'] if (optional or not c.get('optional'))
            and c.get('requires_exterior_space', next(iter(spaces), None)) in spaces]


def scenarios(plan: dict, facts: dict, variants: dict[str, dict]):
    """Escenas del plan: la casa actual y la casa con cada remodelación (los hechos propuestos se encadenan)."""
    from house_twin.variants import variant_facts
    for sc in plan['scenarios']:
        current = facts
        for vid in sc['variants']:
            current = variant_facts(current, variants[vid])
        yield sc, Scene(current, plan, see_through=tuple(sc.get('see_through', SEE_THROUGH)))
