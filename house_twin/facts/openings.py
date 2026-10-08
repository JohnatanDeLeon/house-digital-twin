"""Detección de vanos (puertas y ventanas) en muros ortogonales.

Un vano es un rectángulo: un intervalo a lo largo del muro × la banda entre sus dos caras.
Se detecta de dos formas y luego se parte por los tramos donde ambas caras del muro están libres:
  1. Líneas de cierre en la capa VANOS (una en cada cara).
  2. Pares de jambas en MUROS (segmentos cortos del largo del espesor) — puertas sin VANOS.
"""
import re
from dataclasses import dataclass

from house_twin.drawing import Drawing, Segment

AXIS_TOL = 0.005          # m: tolerancia para considerar dos líneas colineales
WALL_THICKNESS = (0.04, 0.26)
JAMB_LENGTH = (0.14, 0.22)
OPENING_WIDTH = (0.45, 2.2)
MIN_FACE_LINE = 0.3       # descarta las marcas cortas de marco
BRIDGE_GAP = 0.3          # une tramos colineales de VANOS separados por huecos de rotulación
WINDOW_LABEL_RADIUS = 1.0


@dataclass
class OpeningRect:
    """along: 'x' si el muro corre a lo largo de X (vano en muro horizontal), 'y' si corre a lo largo de Y."""
    along: str
    start: float
    end: float
    face_a: float
    face_b: float
    method: str

    @property
    def width(self):
        return self.end - self.start

    @property
    def thickness(self):
        return self.face_b - self.face_a

    def corners(self):
        s, e, a, b = self.start, self.end, self.face_a, self.face_b
        pts = [(s, a), (e, a), (e, b), (s, b)]
        return pts if self.along == 'x' else [(y, x) for x, y in pts]

    def center(self):
        cs, cf = (self.start + self.end) / 2, (self.face_a + self.face_b) / 2
        return (cs, cf) if self.along == 'x' else (cf, cs)

    def contains(self, p, margin=0.01):
        s, f = (p[0], p[1]) if self.along == 'x' else (p[1], p[0])
        return self.start - margin <= s <= self.end + margin and self.face_a - margin <= f <= self.face_b + margin


def _orient(seg: Segment):
    """Devuelve (along, offset, start, end) para segmentos ortogonales; None si es diagonal."""
    (x1, y1), (x2, y2) = seg
    if abs(y1 - y2) < AXIS_TOL:
        return 'x', (y1 + y2) / 2, min(x1, x2), max(x1, x2)
    if abs(x1 - x2) < AXIS_TOL:
        return 'y', (x1 + x2) / 2, min(y1, y2), max(y1, y2)
    return None


def _merge_intervals(intervals, bridge):
    merged = []
    for s, e in sorted(intervals):
        if merged and s - merged[-1][1] <= bridge:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


def _face_lines(segments: list[Segment], min_length=0.0, bridge=0.0):
    """Agrupa segmentos colineales en líneas de cara: {(along, offset): [[start, end], ...]}."""
    groups: dict[tuple[str, float], list] = {}
    for seg in segments:
        o = _orient(seg)
        if not o or o[3] - o[2] < min_length:
            continue
        key = next((k for k in groups if k[0] == o[0] and abs(k[1] - o[1]) < AXIS_TOL), (o[0], o[1]))
        groups.setdefault(key, []).append((o[2], o[3]))
    return {k: _merge_intervals(v, bridge) for k, v in groups.items()}


def _rects_from_face_lines(lines) -> list[OpeningRect]:
    rects = []
    keys = sorted(lines)
    for i, (along, off_a) in enumerate(keys):
        for along_b, off_b in keys[i+1:]:
            if along_b != along or not WALL_THICKNESS[0] <= off_b - off_a <= WALL_THICKNESS[1]:
                continue
            for sa, ea in lines[(along, off_a)]:
                for sb, eb in lines[(along_b, off_b)]:
                    s, e = max(sa, sb), min(ea, eb)
                    if e - s >= OPENING_WIDTH[0]:
                        rects.append(OpeningRect(along, s, e, off_a, off_b, 'vanos'))
    return rects


def _jambs(wall_segments):
    for seg in wall_segments:
        o = _orient(seg)
        if o and JAMB_LENGTH[0] <= o[3] - o[2] <= JAMB_LENGTH[1]:
            # una jamba que corre a lo largo de Y cierra un muro que corre a lo largo de X
            yield ('x' if o[0] == 'y' else 'y', o[1], o[2], o[3])


def _rects_from_jambs(wall_segments) -> list[OpeningRect]:
    jambs = sorted(_jambs(wall_segments))
    rects, used = [], set()
    for i, (along, pos, fa, fb) in enumerate(jambs):
        if i in used:
            continue
        for k in range(i + 1, len(jambs)):
            a2, p2, fa2, fb2 = jambs[k]
            same_band = a2 == along and abs(fa2 - fa) < AXIS_TOL and abs(fb2 - fb) < AXIS_TOL
            if k not in used and same_band and OPENING_WIDTH[0] <= p2 - pos <= OPENING_WIDTH[1]:
                rects.append(OpeningRect(along, pos, p2, fa, fb, 'jambs'))
                used |= {i, k}
                break
    return rects


def _subtract(intervals, cut_start, cut_end):
    out = []
    for s, e in intervals:
        if cut_end <= s or cut_start >= e:
            out.append((s, e))
            continue
        if cut_start > s:
            out.append((s, cut_start))
        if cut_end < e:
            out.append((cut_end, e))
    return out


def _free_on_face(rect: OpeningRect, face: float, wall_lines):
    """Tramos de [start, end] sobre la cara `face` que no están ocupados por muro."""
    free = [(rect.start, rect.end)]
    for (along, offset), intervals in wall_lines.items():
        if along == rect.along and abs(offset - face) <= AXIS_TOL:
            for s, e in intervals:
                free = _subtract(free, s, e)
    return free


def _split_by_wall_gaps(rect: OpeningRect, wall_lines) -> list[OpeningRect]:
    """Un vano solo existe donde ambas caras del muro están libres; puede partirse en varios."""
    free_b = _free_on_face(rect, rect.face_b, wall_lines)
    pieces = []
    for sa, ea in _free_on_face(rect, rect.face_a, wall_lines):
        for sb, eb in free_b:
            s, e = max(sa, sb), min(ea, eb)
            if e - s >= OPENING_WIDTH[0]:
                pieces.append(OpeningRect(rect.along, s, e, rect.face_a, rect.face_b, rect.method))
    return pieces


def _overlaps(a: OpeningRect, b: OpeningRect):
    if a.along != b.along or abs(a.face_a - b.face_a) > 0.03:
        return False
    return min(a.end, b.end) - max(a.start, b.start) > 0.5 * min(a.width, b.width)


def _label_value(drawing: Drawing, prefix: str, centre):
    candidates = []
    for t in drawing.texts_for('window_labels'):
        match = re.search(rf'(?:^|\n)\s*{prefix}\s*=\s*([\d.]+)', t.value)
        if match:
            d = ((t.position[0]-centre[0])**2 + (t.position[1]-centre[1])**2) ** 0.5
            candidates.append((d, float(match.group(1))))
    near = [c for c in candidates if c[0] <= WINDOW_LABEL_RADIUS]
    return min(near)[1] if near else None


def detect_openings(drawing: Drawing) -> list[dict]:
    """Devuelve vanos como dicts de hechos (sin id ni relaciones; eso lo asigna el builder)."""
    walls = drawing.segments_for('walls')
    wall_lines = _face_lines(walls)
    rects = _rects_from_face_lines(_face_lines(drawing.segments_for('opening_faces'), MIN_FACE_LINE, BRIDGE_GAP))
    rects += [r for r in _rects_from_jambs(walls) if not any(_overlaps(r, x) for x in rects)]
    rects = [piece for r in rects for piece in _split_by_wall_gaps(r, wall_lines)]
    glazing = [((a[0]+b[0])/2, (a[1]+b[1])/2) for a, b in drawing.segments_for('glazing')]
    return [_to_fact(r, glazing, drawing) for r in rects]


def _to_fact(rect: OpeningRect, glazing, drawing: Drawing) -> dict:
    is_window = any(rect.contains(p) for p in glazing)
    fact = {
        'kind': 'window' if is_window else 'door',
        'footprint': [[round(x, 3), round(y, 3)] for x, y in rect.corners()],
        'width': round(rect.width, 3),
        'wall_thickness': round(rect.thickness, 3),
        'detected_by': rect.method,
    }
    if is_window:
        centre = rect.center()
        fact['sill_height'] = _fact_value(_label_value(drawing, 'a', centre), 'label "a=" (interpretación: antepecho)')
        fact['height'] = _fact_value(_label_value(drawing, 'h', centre), 'label "h="')
    else:
        fact['sill_height'] = {'value': 0.0, 'source': 'definición de puerta'}
        fact['height'] = {'value': None, 'source': 'no está en el plano'}
    return fact


def _fact_value(value, source):
    return {'value': value, 'source': source if value is not None else 'no está en el plano'}
