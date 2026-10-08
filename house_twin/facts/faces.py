"""Partición de la planta en caras: espacios, cuerpos de muro y el exterior del terreno.

Se poligoniza la red de caras de muro (MUROS) cerrada en cada vano detectado; cada cara
resultante es un espacio (amplio, o con rótulo) o un cuerpo de muro (delgado).
"""
from dataclasses import dataclass, field

from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import polygonize, unary_union

from house_twin.drawing import Drawing

COORD_DECIMALS = 3
SPACE_MIN_AREA = 0.5
SPACE_MIN_THICKNESS = 0.3   # 2·área/perímetro: separa recintos de cuerpos de muro


@dataclass
class Faces:
    spaces: list[Polygon] = field(default_factory=list)
    wall_bodies: list[Polygon] = field(default_factory=list)
    lot: Polygon | None = None
    exterior: list[Polygon] = field(default_factory=list)


def _rounded(p):
    return (round(p[0], COORD_DECIMALS), round(p[1], COORD_DECIMALS))


def _boundary_lines(drawing: Drawing, openings: list[dict]):
    lines = [LineString([_rounded(a), _rounded(b)]) for a, b in drawing.segments_for('walls') if _rounded(a) != _rounded(b)]
    for o in openings:
        pts = [tuple(p) for p in o['footprint']]
        lines.append(LineString(pts + [pts[0]]))
    return lines


def _thickness(poly: Polygon) -> float:
    return 2 * poly.area / poly.length


def _is_labeled(poly: Polygon, label_points) -> bool:
    return any(poly.contains(p) for p in label_points)


def partition(drawing: Drawing, openings: list[dict]) -> Faces:
    faces = list(polygonize(unary_union(_boundary_lines(drawing, openings))))
    opening_polys = [Polygon(o['footprint']) for o in openings]
    label_points = [Point(t.position) for t in drawing.texts_for('room_labels')]
    result = Faces()
    for face in faces:
        if any(face.representative_point().within(o) for o in opening_polys):
            continue
        is_room_like = face.area >= SPACE_MIN_AREA and _thickness(face) >= SPACE_MIN_THICKNESS
        if is_room_like or (_is_labeled(face, label_points) and face.area >= SPACE_MIN_AREA):
            result.spaces.append(face)
        else:
            result.wall_bodies.append(face)
    wall_points = [p for seg in drawing.segments_for('walls') for p in seg]
    result.lot = MultiPoint(wall_points).convex_hull
    built = unary_union(faces + opening_polys)
    leftover = result.lot.difference(built)
    pieces = getattr(leftover, 'geoms', [leftover])
    result.exterior = [p for p in pieces if p.area >= SPACE_MIN_AREA]
    return result
