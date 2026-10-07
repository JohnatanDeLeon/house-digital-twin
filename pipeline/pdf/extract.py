"""Extrae primitivas vectoriales por capa (OCG) de un PDF ploteado por AutoCAD."""
import sys, json, collections
import pypdf
from pypdf.generic import ContentStream

def mat_mul(a, b):
    return [a[0]*b[0]+a[1]*b[2], a[0]*b[1]+a[1]*b[3], a[2]*b[0]+a[3]*b[2],
            a[2]*b[1]+a[3]*b[3], a[4]*b[0]+a[5]*b[2]+b[4], a[4]*b[1]+a[5]*b[3]+b[5]]

def apply(m, x, y):
    return (m[0]*x+m[2]*y+m[4], m[1]*x+m[3]*y+m[5])

def main(pdf_path, build_dir):
    out_path = f'{build_dir}/prims.json'
    reader = pypdf.PdfReader(pdf_path)
    page = reader.pages[0]
    props = page['/Resources']['/Properties']
    oc_names = {k[1:]: v.get_object()['/Name'] for k, v in props.items()}
    ops = ContentStream(page.get_contents(), reader).operations
    ctm = [1, 0, 0, 1, 0, 0]; stack = []
    layer_stack = []; width = 1; stroke = (0, 0, 0)
    subpaths = []; cur = []
    prims = []; texts = []
    text_m = None; font = None
    def layer(): return layer_stack[-1] if layer_stack else None
    for operands, op in ops:
        op = op.decode() if isinstance(op, bytes) else op
        f = [float(o) for o in operands if isinstance(o, (int, float)) or hasattr(o, 'as_numeric')] if op in ('m','l','c','v','y','re','cm','w','RG','Tm','Td','TD') else None
        if op == 'q': stack.append((ctm[:], width, stroke))
        elif op == 'Q': ctm, width, stroke = stack.pop()
        elif op == 'cm': ctm = mat_mul(f, ctm)
        elif op == 'w': width = f[0]
        elif op == 'RG': stroke = tuple(f)
        elif op == 'BDC':
            tag = str(operands[1])[1:] if len(operands) > 1 else None
            layer_stack.append(oc_names.get(tag, tag))
        elif op == 'BMC': layer_stack.append(layer())
        elif op == 'EMC':
            if layer_stack: layer_stack.pop()
        elif op == 'm':
            if len(cur) > 1: subpaths.append(cur)
            cur = [apply(ctm, *f)]
        elif op == 'l': cur.append(apply(ctm, *f))
        elif op in ('c', 'v', 'y'):
            cur.append(apply(ctm, f[-2], f[-1]))  # aproximación: solo extremo de la curva
        elif op == 're':
            x, y, w_, h_ = f
            if len(cur) > 1: subpaths.append(cur)
            subpaths.append([apply(ctm, x, y), apply(ctm, x+w_, y), apply(ctm, x+w_, y+h_), apply(ctm, x, y+h_), apply(ctm, x, y)])
            cur = []
        elif op == 'h':
            if cur: cur.append(cur[0])
        elif op in ('S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'):
            if len(cur) > 1: subpaths.append(cur)
            if op != 'n':
                scale = (ctm[0]**2 + ctm[1]**2) ** 0.5
                for sp in subpaths:
                    prims.append({'layer': layer(), 'op': op, 'w': round(width*scale, 3),
                                  'rgb': stroke, 'pts': [(round(x, 3), round(y, 3)) for x, y in sp]})
            subpaths = []; cur = []
        elif op == 'Tf': font = (str(operands[0]), float(operands[1]))
        elif op == 'Tm': text_m = mat_mul(f, ctm)
        elif op in ('Tj', 'TJ'):
            s = operands[0]
            s = ''.join(str(x) for x in s if not isinstance(x, (int, float)) and not hasattr(x, 'as_numeric')) if op == 'TJ' else str(s)
            if text_m:
                texts.append({'layer': layer(), 'text': s, 'x': round(text_m[4], 2), 'y': round(text_m[5], 2),
                              'size': round(font[1]*(text_m[0]**2+text_m[1]**2)**0.5, 2) if font else None})
    json.dump({'layers': list(oc_names.values()), 'prims': prims, 'texts': texts}, open(out_path, 'w'))
    c = collections.Counter(p['layer'] for p in prims); t = collections.Counter(x['layer'] for x in texts)
    for name in sorted(set(c) | set(t), key=str):
        print(f'{str(name):28s} paths={c[name]:6d} texts={t[name]:4d}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
