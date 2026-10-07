"""Calibra la escala del PDF: empareja cada línea de cota con su texto y ajusta pt/m por mínimos cuadrados."""
import sys, json
from pathlib import Path
from common import decode_glyphs, load_prims

DIM_LAYER = '14-DIM INTERIOR'

def dim_segments(prims):
    for p in prims:
        if p['layer'] != DIM_LAYER or len(p['pts']) != 2:
            continue
        (x1, y1), (x2, y2) = p['pts']
        yield {'mid': ((x1+x2)/2, (y1+y2)/2), 'len': ((x2-x1)**2 + (y2-y1)**2) ** 0.5,
               'vertical': abs(x1-x2) < 0.05, 'span': (round(min(x1,x2),2), round(max(x1,x2),2), round(min(y1,y2),2), round(max(y1,y2),2))}

def nearest_text(seg, texts):
    def dist(t):
        mx, my = seg['mid']
        # el texto de una cota vertical va rotado a la izquierda de la línea
        return abs(t['y'] - my) + abs(t['x'] - mx) * (0.3 if seg['vertical'] else 3)
    return min(texts, key=dist)

def walls_origin(prims):
    pts = [q for p in prims if p['layer'] == 'MUROS' for q in p['pts']]
    return (min(x for x, _ in pts), min(y for _, y in pts))

def main(build_dir):
    d = load_prims(build_dir)
    texts = [dict(t, value=float(decode_glyphs(t['text']))) for t in d['texts'] if t['layer'] == DIM_LAYER]
    pairs = []
    for seg in dim_segments(d['prims']):
        t = nearest_text(seg, texts)
        pairs.append((seg, t['value']))
    k = sum(s['len'] * v for s, v in pairs) / sum(v * v for s, v in pairs)
    print(f'escala ajustada: {k:.4f} pt/m  →  1:{72/25.4*1000/k:.1f} en papel (rotulado 1:100)')
    for s, v in sorted(pairs, key=lambda p: -abs(p[0]['len']/k - p[1])):
        print(f"{'V' if s['vertical'] else 'H'} rotulado {v:6.2f}  medido {s['len']/k:7.3f}  resid {100*(s['len']/k - v):+5.1f} cm  span {s['span']}")
    frame = {'pt_per_m': round(k, 4), 'origin_pt': walls_origin(d['prims'])}
    (Path(build_dir) / 'frame.json').write_text(json.dumps(frame))
    print('marco:', frame)

if __name__ == '__main__':
    main(sys.argv[1])
