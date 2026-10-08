"""Hechos aportados por el dueño (`sources/owner-annotations.json`) sobre la partición del plano.

- merge_spaces: une caras que el plano separa pero son un solo espacio (p. ej. baño + regadera).
- rename_spaces: da nombre a un recinto que el plano no rotula (p. ej. el tragaluz).
- exterior_zones: nombra zonas del exterior abierto (cochera, patio…), que no tienen muros que las separen.
- add_openings: vanos que existen pero el plano no dibuja; sin medidas inventadas.
- answered_unknowns: respuestas del dueño a las incógnitas del modelo (las resuelve el builder).
  Con `value` (m) el builder además lleva la medida al hecho que contesta (U01, U04).

Todo lo que sale de aquí lleva `source` del dueño; lo que no se nombra queda sin nombre.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

MIN_PIECE_AREA = 0.5
CLOSE_GAP = 0.03  # m: cierra divisiones delgadas (≤ 6 cm) entre las caras que se unen


@dataclass
class SpacePiece:
    polygon: Polygon
    is_exterior: bool
    owner: dict = field(default_factory=dict)
    inner_partitions: list = field(default_factory=list)


def load_annotations(path: Path | None) -> dict:
    if path is None or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())


def _owner_fields(annotation: dict, entry: dict) -> dict:
    source = f"{annotation.get('source', 'dueño')} ({annotation.get('confirmed_on', 's/f')})"
    fields = {'name': entry['name'], 'source': source, 'note': entry.get('note')}
    for key in ('roofed', 'enclosed'):
        if key in entry:
            fields[key] = {'value': entry[key], 'source': source}
    return fields


def merge_spaces(pieces: list[SpacePiece], wall_polys: list[Polygon], annotation: dict) -> list[SpacePiece]:
    for entry in annotation.get('merge_spaces', []):
        anchors = [Point(p) for p in entry['anchors']]
        chosen = [p for p in pieces if any(p.polygon.contains(a) for a in anchors)]
        if len(chosen) < 2:
            continue
        closed = unary_union([p.polygon for p in chosen]).buffer(CLOSE_GAP, join_style='mitre').buffer(-CLOSE_GAP, join_style='mitre')
        partitions = [i for i, w in enumerate(wall_polys) if closed.contains(w.representative_point())]
        merged = SpacePiece(closed, chosen[0].is_exterior, _owner_fields(annotation, entry), partitions)
        pieces = [p for p in pieces if p not in chosen] + [merged]
    return pieces


def rename_spaces(pieces: list[SpacePiece], annotation: dict) -> list[SpacePiece]:
    for entry in annotation.get('rename_spaces', []):
        anchor = Point(entry['anchor'])
        for piece in pieces:
            if piece.polygon.contains(anchor):
                piece.owner = {**_owner_fields(annotation, entry), **{k: v for k, v in piece.owner.items() if k != 'name'}}
    return pieces


def owner_openings(walls: list[dict], spaces: list[dict], annotation: dict) -> list[dict]:
    """Vanos declarados por el dueño: se ubican por muro y espacios; medidas en null si el plano no las tiene."""
    source = f"{annotation.get('source', 'dueño')} ({annotation.get('confirmed_on', 's/f')})"
    unknown = {'value': None, 'source': 'no está en el plano'}
    result = []
    for entry in annotation.get('add_openings', []):
        host = next((w['id'] for w in walls if Polygon(w['footprint']).buffer(0.01).contains(Point(entry['host_wall_anchor']))), None)
        connects = [s['id'] for a in entry['connects_anchors'] for s in spaces if Polygon(s['polygon']).contains(Point(a))]
        result.append({'kind': entry['kind'], 'footprint': None, 'width': entry.get('width'),
                       'wall_thickness': None, 'detected_by': source, 'sill_height': dict(unknown),
                       'height': dict(unknown), 'host_wall': host, 'connects': connects, 'owner_note': entry.get('note')})
    return result


def split_exterior(exterior: list[Polygon], annotation: dict) -> list[SpacePiece]:
    zones = annotation.get('exterior_zones', [])
    rest = unary_union(exterior)
    pieces = []
    for entry in zones:
        region = Polygon(entry['region'])
        part = rest.intersection(region)
        rest = rest.difference(region)
        polys = [g for g in getattr(part, 'geoms', [part]) if g.geom_type == 'Polygon' and g.area >= MIN_PIECE_AREA]
        if polys:
            pieces.append(SpacePiece(max(polys, key=lambda g: g.area), True, _owner_fields(annotation, entry)))
    pieces += [SpacePiece(g, True) for g in getattr(rest, 'geoms', [rest]) if g.geom_type == 'Polygon' and g.area >= MIN_PIECE_AREA]
    return pieces
