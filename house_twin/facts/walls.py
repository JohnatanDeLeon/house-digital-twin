"""Descomposición de la masa de muros en tramos rectos (la unidad que luego se mueve o se elimina).

1. Región de muro = cuerpos de muro ∪ vanos (un muro con puerta sigue siendo un solo muro).
2. Cada par de caras paralelas a distancia de espesor define una franja recta.
3. Franjas y vanos sobre la misma banda se unen: un tramo recto por componente.
4. Los tramos se asignan de mayor a menor largo; los encuentros (esquinas, T) quedan
   en el tramo más largo y los restos se pegan al tramo con el que más borde comparten.
"""
from dataclasses import dataclass
import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from house_twin.drawing import Drawing

THICKNESS_RANGE = (0.04, 0.30)
MIN_OVERLAP = 0.1
PARALLEL_TOL = 1e-3
STRIP_INSIDE_RATIO = 0.9
MIN_RESIDUAL_AREA = 1e-4
SNAP = 1e-3  # m: absorbe diferencias de redondeo entre franjas y vanos contiguos


@dataclass
class Strip:
    polygon: Polygon
    direction: tuple[float, float]
    axis: LineString
    thickness: float


def _unit(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    n = math.hypot(dx, dy)
    return (dx/n, dy/n), n


def _canonical(d):
    return d if (d[0] > PARALLEL_TOL or (abs(d[0]) <= PARALLEL_TOL and d[1] > 0)) else (-d[0], -d[1])


def _strip_between(s1, s2):
    """Franja entre dos segmentos paralelos, sobre el tramo donde se solapan sus proyecciones."""
    (a, b), (c, e) = s1, s2
    d, length = _unit(a, b)
    d = _canonical(d)
    normal = (-d[1], d[0])
    offset = (c[0]-a[0]) * normal[0] + (c[1]-a[1]) * normal[1]
    if not THICKNESS_RANGE[0] <= abs(offset) <= THICKNESS_RANGE[1]:
        return None
    project = lambda p: (p[0]-a[0]) * d[0] + (p[1]-a[1]) * d[1]
    lo = max(min(project(a), project(b)), min(project(c), project(e)))
    hi = min(max(project(a), project(b)), max(project(c), project(e)))
    if hi - lo < MIN_OVERLAP:
        return None
    p = lambda t, o: (a[0] + d[0]*t + normal[0]*o, a[1] + d[1]*t + normal[1]*o)
    poly = Polygon([p(lo, 0), p(hi, 0), p(hi, offset), p(lo, offset)])
    axis = LineString([p(lo, offset/2), p(hi, offset/2)])
    return Strip(poly, d, axis, abs(offset))


def _is_parallel(s1, s2):
    d1, n1 = _unit(*s1)
    d2, n2 = _unit(*s2)
    return n1 > 0 and n2 > 0 and abs(d1[0]*d2[1] - d1[1]*d2[0]) < PARALLEL_TOL


def _strips(segments, region):
    found = []
    for i, s1 in enumerate(segments):
        for s2 in segments[i+1:]:
            if not _is_parallel(s1, s2):
                continue
            strip = _strip_between(s1, s2)
            if strip and strip.polygon.intersection(region).area >= STRIP_INSIDE_RATIO * strip.polygon.area:
                found.append(strip)
    return found


def _band_key(strip: Strip):
    d = strip.direction
    normal = (-d[1], d[0])
    c = strip.axis.interpolate(0.5, normalized=True)
    return (round(d[0], 2), round(d[1], 2), round(c.x*normal[0] + c.y*normal[1], 2), round(strip.thickness, 2))


def _snap_union(geoms):
    grown = [g.buffer(SNAP, join_style='mitre') for g in geoms]
    return unary_union(grown).buffer(-SNAP, join_style='mitre')


def _merge_bands(strips, openings):
    bands: dict[tuple, list[Strip]] = {}
    for s in strips:
        bands.setdefault(_band_key(s), []).append(s)
    runs = []
    for key, members in bands.items():
        geoms = [s.polygon for s in members]
        merged = _snap_union(geoms + [o for o in openings if any(o.buffer(SNAP).intersects(g) for g in geoms)])
        for part in getattr(merged, 'geoms', [merged]):
            runs.append({'polygon': part, 'direction': members[0].direction, 'thickness': members[0].thickness})
    return runs


def _run_length(run):
    d = run['direction']
    coords = list(run['polygon'].exterior.coords)
    proj = [x*d[0] + y*d[1] for x, y in coords]
    return max(proj) - min(proj)


def _polygonal(geom):
    """Descarta líneas y puntos sueltos que dejan las operaciones booleanas."""
    parts = getattr(geom, 'geoms', [geom])
    return unary_union([g for g in parts if g.geom_type in ('Polygon', 'MultiPolygon') and g.area > 0])


def _assign(runs, region):
    claimed = Polygon()
    walls = []
    for run in sorted(runs, key=_run_length, reverse=True):
        own = _polygonal(run['polygon'].intersection(region).difference(claimed))
        if own.area > MIN_RESIDUAL_AREA:
            walls.append({**run, 'polygon': own})
            claimed = claimed.union(own)
    residual = _polygonal(region.difference(claimed))
    for piece in getattr(residual, 'geoms', [residual]):
        if piece.area <= MIN_RESIDUAL_AREA:
            continue
        shared = lambda w: w['polygon'].boundary.intersection(piece.boundary).length
        host = max(walls, key=shared)
        if shared(host) > 0:
            host['polygon'] = _polygonal(_snap_union([host['polygon'], piece]))
        else:
            walls.append({'polygon': piece, 'direction': None, 'thickness': None})
    for w in walls:
        # apertura morfológica: elimina astillas de menos de 2·SNAP que dejan los redondeos del PDF
        opened = w['polygon'].buffer(-SNAP, join_style='mitre').buffer(SNAP, join_style='mitre')
        w['polygon'] = _polygonal(opened.simplify(SNAP / 10))
    # un tramo partido por un muro más largo que lo cruza queda como dos tramos
    return [{**w, 'polygon': part} for w in walls for part in getattr(w['polygon'], 'geoms', [w['polygon']])]


def decompose_walls(drawing: Drawing, wall_bodies: list[Polygon], opening_polys: list[Polygon]) -> list[dict]:
    region = unary_union(wall_bodies + opening_polys).buffer(0)
    segments = [s for s in drawing.segments_for('walls') if s[0] != s[1]]
    runs = _merge_bands(_strips(segments, region), opening_polys)
    return _assign(runs, region)
