"""Lectura del content stream de un PDF ploteado por AutoCAD, conservando la capa (OCG) de cada trazo.

Devuelve primitivas en puntos PDF; la conversión a metros la hace `pdf.py`.
"""
from dataclasses import dataclass, field

import pypdf
from pypdf.generic import ContentStream

PAINT_OPS = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'}
NUMERIC_OPS = {'m', 'l', 'c', 'v', 'y', 're', 'cm', 'Tm'}


@dataclass
class RawPath:
    layer: str | None
    points: list[tuple[float, float]]


@dataclass
class RawText:
    layer: str | None
    raw: str
    position: tuple[float, float]


@dataclass
class _State:
    ctm: list[float] = field(default_factory=lambda: [1, 0, 0, 1, 0, 0])
    stack: list = field(default_factory=list)
    layers: list = field(default_factory=list)
    subpaths: list = field(default_factory=list)
    current: list = field(default_factory=list)
    text_matrix: list | None = None

    @property
    def layer(self):
        return self.layers[-1] if self.layers else None


def _mat_mul(a, b):
    return [a[0]*b[0] + a[1]*b[2], a[0]*b[1] + a[1]*b[3], a[2]*b[0] + a[3]*b[2],
            a[2]*b[1] + a[3]*b[3], a[4]*b[0] + a[5]*b[2] + b[4], a[4]*b[1] + a[5]*b[3] + b[5]]


def _apply(m, x, y):
    return (m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5])


def _flush_current(st: _State):
    if len(st.current) > 1:
        st.subpaths.append(st.current)
    st.current = []


def _path_op(st: _State, op: str, f: list[float]):
    if op == 'm':
        _flush_current(st)
        st.current = [_apply(st.ctm, *f)]
    elif op == 'l':
        st.current.append(_apply(st.ctm, *f))
    elif op in ('c', 'v', 'y'):
        st.current.append(_apply(st.ctm, f[-2], f[-1]))  # curva → cuerda (suficiente para hojas de puerta)
    elif op == 're':
        _flush_current(st)
        x, y, w, h = f
        st.subpaths.append([_apply(st.ctm, *p) for p in ((x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y))])
    elif op == 'h' and st.current:
        st.current.append(st.current[0])


def _text_value(operands, op):
    if op == 'Tj':
        return str(operands[0])
    return ''.join(str(x) for x in operands[0] if isinstance(x, (str, bytes)) or type(x).__name__ in ('TextStringObject', 'ByteStringObject'))


def read_content(pdf_path: str) -> tuple[list[RawPath], list[RawText], dict]:
    reader = pypdf.PdfReader(pdf_path)
    page = reader.pages[0]
    oc_names = {k[1:]: v.get_object()['/Name'] for k, v in page['/Resources'].get('/Properties', {}).items()}
    st = _State(); paths: list[RawPath] = []; texts: list[RawText] = []
    for operands, op in ContentStream(page.get_contents(), reader).operations:
        op = op.decode() if isinstance(op, bytes) else op
        f = [float(o) for o in operands] if op in NUMERIC_OPS else None
        if op == 'q':
            st.stack.append(st.ctm[:])
        elif op == 'Q':
            st.ctm = st.stack.pop()
        elif op == 'cm':
            st.ctm = _mat_mul(f, st.ctm)
        elif op == 'BDC':
            tag = str(operands[1])[1:] if len(operands) > 1 else None
            st.layers.append(oc_names.get(tag, tag))
        elif op == 'BMC':
            st.layers.append(st.layer)
        elif op == 'EMC' and st.layers:
            st.layers.pop()
        elif op in ('m', 'l', 'c', 'v', 'y', 're', 'h'):
            _path_op(st, op, f)
        elif op in PAINT_OPS:
            _flush_current(st)
            if op != 'n':
                paths.extend(RawPath(st.layer, sp) for sp in st.subpaths)
            st.subpaths = []
        elif op == 'Tm':
            st.text_matrix = _mat_mul(f, st.ctm)
        elif op in ('Tj', 'TJ') and st.text_matrix:
            texts.append(RawText(st.layer, _text_value(operands, op), (st.text_matrix[4], st.text_matrix[5])))
    info = {'producer': str(reader.metadata.get('/Producer')), 'creator': str(reader.metadata.get('/Creator')),
            'layers': list(oc_names.values())}
    return paths, texts, info
