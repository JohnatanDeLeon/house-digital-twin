"""Detecta vanos emparejando jambas (segmentos cortos de MUROS del largo del espesor de muro)."""
import sys, json
from pathlib import Path
from common import Frame, load_prims
JAMB_LEN = (0.14, 0.22)
OPENING_WIDTH = (0.45, 2.2)
TOL = 0.02

def segments(prims, layer, frame):
    for p in prims:
        if p['layer'] != layer:
            continue
        pts = [frame.to_m(q) for q in p['pts']]
        yield from zip(pts, pts[1:])

def jambs(prims, frame):
    out = []
    for (x1, y1), (x2, y2) in segments(prims, 'MUROS', frame):
        if abs(x1-x2) < TOL and JAMB_LEN[0] <= abs(y2-y1) <= JAMB_LEN[1]:
            out.append(('H', x1, min(y1, y2), max(y1, y2)))  # jamba vertical → vano en muro horizontal
        elif abs(y1-y2) < TOL and JAMB_LEN[0] <= abs(x2-x1) <= JAMB_LEN[1]:
            out.append(('V', y1, min(x1, x2), max(x1, x2)))
    return out

def pair_jambs(js):
    used = set(); result = []
    for i, a in enumerate(js):
        best = None
        for k, b in enumerate(js):
            if k == i or k in used or i in used or a[0] != b[0]:
                continue
            same_band = abs(a[2]-b[2]) < TOL and abs(a[3]-b[3]) < TOL
            gap = b[1] - a[1]
            if same_band and OPENING_WIDTH[0] <= gap <= OPENING_WIDTH[1] and (best is None or gap < best[1]):
                best = (k, gap)
        if best:
            used |= {i, best[0]}
            b = js[best[0]]
            result.append({'wall_axis': a[0], 'from': round(a[1], 3), 'to': round(b[1], 3),
                           'band': [round(a[2], 3), round(a[3], 3)], 'width_m': round(best[1], 3)})
    return result

def window_spans(prims, frame):
    out = []
    for (x1, y1), (x2, y2) in segments(prims, 'VENTANAS', frame):
        if abs(y1-y2) < TOL:
            out.append({'wall_axis': 'H', 'from': min(x1, x2), 'to': max(x1, x2), 'band': [y1-0.06, y1]})
        else:
            out.append({'wall_axis': 'V', 'from': min(y1, y2), 'to': max(y1, y2), 'band': [x1-0.06, x1]})
    return out

def main(build_dir):
    d = load_prims(build_dir); frame = Frame.load(build_dir)
    ops = pair_jambs(jambs(d['prims'], frame))
    wins = window_spans(d['prims'], frame)
    for op in ops:
        op['band_center'] = round(sum(op['band'])/2, 3)
        op['kind'] = 'window' if any(op['wall_axis'] == w['wall_axis'] and op['band'][0]-0.01 <= w['band'][1] <= op['band'][1]+0.01
                                     and op['from']-TOL <= w['from'] and w['to'] <= op['to']+TOL for w in wins) else 'door_or_open'
        print(op)
    (Path(build_dir) / 'openings.json').write_text(json.dumps(ops, indent=1))

if __name__ == '__main__':
    main(sys.argv[1])
