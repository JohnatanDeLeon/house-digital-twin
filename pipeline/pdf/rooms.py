"""Detecta espacios por flood-fill sobre un raster de muros + vanos + ventanas + puertas."""
import sys, json
from pathlib import Path
from collections import deque
import numpy as np
from common import Frame, decode_glyphs, load_prims
CELL = 0.02  # m
BARRIER_LAYERS = {'MUROS', 'VANOS', 'VENTANAS', 'PUERTAS'}

def rasterize(prims, shape, frame):
    grid = np.zeros(shape, dtype=np.int32)  # 0 libre, -1 barrera
    for p in prims:
        if p['layer'] not in BARRIER_LAYERS:
            continue
        pts = [frame.to_m(q) for q in p['pts']]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            n = int(max(abs(x2-x1), abs(y2-y1)) / (CELL/2)) + 1
            for t in np.linspace(0, 1, n+1):
                i = int((y1 + t*(y2-y1)) / CELL); j = int((x1 + t*(x2-x1)) / CELL)
                if 0 <= i < shape[0] and 0 <= j < shape[1]:
                    grid[i, j] = -1
    return grid

def close_openings(grid, openings):
    # cierra cada vano detectado por jambas con una línea en el eje del muro
    for op in openings:
        c = op['band_center']
        for t in np.arange(op['from'], op['to'], CELL/2):
            i, j = (int(c/CELL), int(t/CELL)) if op['wall_axis'] == 'H' else (int(t/CELL), int(c/CELL))
            grid[i, j] = -1

def flood(grid, seed, label):
    q = deque([seed]); grid[seed] = label; count = 0; cells = []
    while q:
        i, j = q.popleft(); count += 1; cells.append((i, j))
        for di, dj in ((1,0),(-1,0),(0,1),(0,-1)):
            a, b = i+di, j+dj
            if 0 <= a < grid.shape[0] and 0 <= b < grid.shape[1] and grid[a, b] == 0:
                grid[a, b] = label; q.append((a, b))
    return cells

def main(build_dir):
    d = load_prims(build_dir); frame = Frame.load(build_dir)
    shape = (int(21.25/CELL)+2, int(10.05/CELL)+2)
    grid = rasterize(d['prims'], shape, frame)
    close_openings(grid, json.loads((Path(build_dir) / 'openings.json').read_text()))
    labels = [(decode_glyphs(t['text']), frame.to_m((t['x'], t['y']))) for t in d['texts'] if t['layer'] == '12-TEXTOS']
    regions = {}
    for name, (x, y) in labels:
        seed = (int((y+0.05)/CELL), int((x+0.3)/CELL))
        if not (0 <= seed[0] < shape[0] and 0 <= seed[1] < shape[1]):
            continue
        rid = grid[seed]
        if rid == 0:
            rid = len(regions) + 1
            cells = flood(grid, seed, rid)
            ii = [c[0] for c in cells]; jj = [c[1] for c in cells]
            regions[rid] = {'names': [], 'area_m2': round(len(cells)*CELL*CELL, 2),
                            'bbox_m': [round(min(jj)*CELL, 2), round(min(ii)*CELL, 2), round((max(jj)+1)*CELL, 2), round((max(ii)+1)*CELL, 2)]}
        if rid > 0:
            regions[rid]['names'].append(name)
    for rid, r in regions.items():
        print(rid, r)
    np.save(Path(build_dir) / 'rooms_grid.npy', grid)
    (Path(build_dir) / 'rooms.json').write_text(json.dumps(regions, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main(sys.argv[1])
