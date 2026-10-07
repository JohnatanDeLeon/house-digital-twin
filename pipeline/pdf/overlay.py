"""Dibuja lo extraído (muros, vanos, espacios) en metros para validar contra el plano."""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from common import Frame, load_prims
PX_PER_M = 60
MARGIN = 40
PALETTE = [(255,214,165),(202,255,191),(155,246,255),(189,178,255),(255,198,255),(253,255,182),(160,196,255),(255,173,173)]
LAYER_STYLE = {'MUROS': ((20,20,20), 2), 'VANOS': ((200,60,0), 1), 'VENTANAS': ((0,110,220), 2), 'PUERTAS': ((150,150,150), 1)}

def main(work, out_png):
    d = load_prims(work); frame = Frame.load(work)
    grid = np.load(f'{work}/rooms_grid.npy'); rooms = json.load(open(f'{work}/rooms.json'))
    cell = 0.02
    w, h = int(10.05*PX_PER_M)+2*MARGIN, int(21.27*PX_PER_M)+2*MARGIN
    img = Image.new('RGB', (w, h), 'white'); draw = ImageDraw.Draw(img)
    px = lambda x, y: (MARGIN + x*PX_PER_M, h - MARGIN - y*PX_PER_M)
    for (i, j), rid in np.ndenumerate(grid):
        if rid > 0:
            x0, y0 = px(j*cell, (i+1)*cell)
            draw.rectangle([x0, y0, x0+cell*PX_PER_M, y0+cell*PX_PER_M], fill=PALETTE[(rid-1) % len(PALETTE)])
    for layer, (color, width) in LAYER_STYLE.items():
        for p in d['prims']:
            if p['layer'] == layer:
                pts = [px(*frame.to_m(q)) for q in p['pts']]
                draw.line(pts, fill=color, width=width)
    for rid, r in rooms.items():
        x0, y0, x1, y1 = r['bbox_m']
        cx, cy = px((x0+x1)/2, (y0+y1)/2)
        draw.text((cx-40, cy-6), f"{'/'.join(r['names'])}", fill='black')
        draw.text((cx-40, cy+8), f"{r['area_m2']} m2", fill='black')
    for k in range(0, 22):
        draw.text(px(-0.6, k), f'{k}m', fill=(120,120,120))
    img.save(out_png)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
