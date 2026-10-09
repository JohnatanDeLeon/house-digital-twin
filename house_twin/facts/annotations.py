"""Hechos aportados por el dueño (`sources/owner-annotations.json`) sobre la partición del plano.

- merge_spaces: une caras que el plano separa pero son un solo espacio (p. ej. baño + regadera).
- rename_spaces: da nombre a un recinto que el plano no rotula (p. ej. el tragaluz).
- exterior_zones: nombra zonas del exterior abierto (cochera, patio…), que no tienen muros que las separen.
- add_openings: vanos que existen pero el plano no dibuja; sin medidas inventadas. Con `footprint` (puertas de
  herrería entre dos muros, que no van dentro de uno) el vano tiene geometría; con `height` y `sill_height`, sus alturas
  (`measure_source` dice de dónde salen si no las midió el dueño); con `grid`, la retícula de una ventana.
- answered_unknowns: respuestas del dueño a las incógnitas del modelo (las resuelve el builder).
  Con `value` (m) el builder además lleva la medida al hecho que contesta (U01, U04).
- measurements: medidas del dueño entre dos muros (anclados por un punto dentro de cada uno). No mueven la
  geometría: se comparan con el plano y la diferencia queda a la vista para decidir qué muro corregir.

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
        anchor = entry.get('host_wall_anchor')
        host = next((w['id'] for w in walls if anchor and Polygon(w['footprint']).buffer(0.01).contains(Point(anchor))), None)
        connects = [s['id'] for a in entry['connects_anchors'] for s in spaces if Polygon(s['polygon']).contains(Point(a))]
        footprint, width = entry.get('footprint'), entry.get('width')
        if footprint:  # ancho = lado largo del rectángulo
            width = round(max(Point(footprint[0]).distance(Point(footprint[1])), Point(footprint[1]).distance(Point(footprint[2]))), 3)
        measured = entry.get('measure_source', source)  # p. ej. una estimación con fotos que el dueño aceptó
        sill = {'value': 0.0, 'source': 'definición de puerta'} if entry['kind'] == 'door' and footprint else dict(unknown)
        if entry.get('sill_height') is not None:  # el antepecho puede tener otra fuente que el alto
            sill = {'value': entry['sill_height'], 'source': entry.get('sill_source', measured)}
        height = {'value': entry['height'], 'source': measured} if entry.get('height') is not None else dict(unknown)
        opening = {'kind': entry['kind'], 'footprint': footprint, 'width': width,
                   'wall_thickness': None, 'detected_by': entry.get('detected_by', source), 'sill_height': sill,
                   'height': height, 'host_wall': host, 'connects': connects, 'owner_note': entry.get('note')}
        if 'leaves' in entry:  # hojas de la puerta: bisagra, canto de la chapa y hacia qué espacio abre
            opening['leaves'] = [{'hinge_end': leaf['hinge_end'], 'latch_end': leaf['latch_end'],
                                  'opens_into': next((s['id'] for s in spaces if Polygon(s['polygon']).contains(Point(leaf['opens_into_anchor']))), None),
                                  'source': leaf['source']} for leaf in entry['leaves']]
        if 'grid' in entry:  # retícula: vidrios a lo ancho (las dos hojas) y a lo alto, y ancho del perfil
            opening['grid'] = {**entry['grid'], 'source': source}
        result.append(opening)
    return result


def correct_openings(openings: list[dict], annotation: dict):
    """Correcciones del dueño a vanos del plano: otra posición (`footprint`) u otra altura.

    El vano se identifica por un punto dentro de su huella del plano. La huella del plano queda en `plan_footprint`
    para no perder el dato original, y el abatimiento se mueve con el vano.
    """
    source = f"{annotation.get('source', 'dueño')} ({annotation.get('confirmed_on', 's/f')})"
    for entry in annotation.get('opening_corrections', []):
        opening = next((o for o in openings if o['footprint'] and Polygon(o['footprint']).buffer(0.01).contains(Point(entry['anchor']))), None)
        if opening is None:
            raise ValueError(f"corrección sin vano en {entry['anchor']}")
        measured = entry.get('measure_source', source)
        if 'footprint' in entry:
            old, new = Polygon(opening['footprint']).centroid, Polygon(entry['footprint']).centroid
            dx, dy = new.x - old.x, new.y - old.y
            opening['plan_footprint'], opening['footprint'] = opening['footprint'], entry['footprint']
            opening['position_source'] = measured
            swing = opening.get('swing')
            if swing:
                for key in ('hinge_end', 'latch_end'):
                    swing[key] = [round(swing[key][0] + dx, 3), round(swing[key][1] + dy, 3)]
                swing['source'] += '; desplazado con el vano'
        if entry.get('height') is not None:
            opening['height'] = {'value': entry['height'], 'source': entry.get('height_source', measured)}
        opening['owner_note'] = entry.get('note')


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


MEASUREMENT_TOLERANCE_M = 0.03  # aplanado y error de cinta: por debajo de esto el plano y la medida coinciden


def owner_measurements(walls: list[dict], annotation: dict) -> list[dict]:
    """Medidas del dueño junto a lo que da el plano entre los mismos muros."""
    result = []
    for entry in annotation.get('measurements', []):
        found = [next((w for w in walls if Polygon(w['footprint']).buffer(0.01).contains(Point(a))), None)
                 for a in entry['wall_anchors']]
        plan = round(Polygon(found[0]['footprint']).distance(Polygon(found[1]['footprint'])), 3) if all(found) else None
        source = f"{annotation.get('source', 'dueño')} ({entry.get('answered_on') or annotation.get('confirmed_on', 's/f')})"
        result.append({'id': entry['id'], 'what': entry['what'], 'walls': [w['id'] if w else None for w in found],
                       'value': entry['value'], 'source': source, 'plan_value': plan,
                       'difference': None if plan is None else round(entry['value'] - plan, 3),
                       'matches_plan': None if plan is None else abs(entry['value'] - plan) <= MEASUREMENT_TOLERANCE_M,
                       'note': entry.get('note')})
    return result
