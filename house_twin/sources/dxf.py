"""Fuente DXF: lee el dibujo con ezdxf, normaliza unidades a metros y entrega un `Drawing`.

- Bloques (INSERT) se explotan conservando la capa: una entidad en la capa "0" hereda la del bloque.
- Arcos, splines y polilíneas con bulge se aproximan por cuerdas (FLATTEN_TOLERANCE_M).
- El origen se traslada a la esquina inferior izquierda de MUROS, igual que la fuente PDF.
"""
from collections import Counter

import ezdxf
from ezdxf import path as ezpath
from ezdxf.units import conversion_factor

from house_twin.drawing import LAYER_ROLES, Drawing, Text

METERS = 6  # código $INSUNITS
FLATTEN_TOLERANCE_M = 0.005
TEXT_TYPES = {'TEXT', 'MTEXT', 'ATTRIB'}
# Si $INSUNITS falta o no cuadra con la geometría, se infiere por el tamaño de los muros
UNIT_GUESSES = ((6, 1, 100), (5, 100, 10_000), (4, 1_000, 100_000))
PLAUSIBLE_HALF_EXTENT_M = (1.0, 100.0)  # mitad del lado mayor de una casa, en metros


def _effective_layer(entity, parent_layer):
    layer = entity.dxf.get('layer', '0')
    return parent_layer if layer == '0' and parent_layer else layer


def _walk(entities, parent_layer=None):
    """Recorre entidades explotando bloques; devuelve (capa, entidad)."""
    for e in entities:
        layer = _effective_layer(e, parent_layer)
        if e.dxftype() == 'INSERT':
            yield from _walk(e.virtual_entities(), layer)
            yield from ((layer, a) for a in e.attribs)
        else:
            yield layer, e


def _text_value(e):
    return e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text


def _polyline_points(e, tolerance):
    if e.dxftype() == 'LINE':
        return [tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]]
    try:
        return [(v.x, v.y) for v in ezpath.make_path(e).flattening(tolerance)]
    except (TypeError, ValueError, AttributeError):
        return []  # entidades sin geometría lineal (sombreados, cotas, imágenes)


def _guess_factor(extent):
    for code, low, high in UNIT_GUESSES:
        if low <= extent <= high:
            return conversion_factor(code, METERS), code
    return 1.0, None


def _raw_entities(doc):
    raw_segments, raw_texts = {}, []
    for layer, e in _walk(doc.modelspace()):
        if e.dxftype() in TEXT_TYPES:
            insert = e.dxf.get('insert')
            if insert is not None:
                raw_texts.append((layer, _text_value(e), (insert.x, insert.y)))
            continue
        raw_segments.setdefault(layer, []).append(e)
    return raw_segments, raw_texts


def load_dxf_drawing(dxf_path: str) -> Drawing:
    doc = ezdxf.readfile(dxf_path)
    declared = doc.header.get('$INSUNITS', 0)
    raw_segments, raw_texts = _raw_entities(doc)
    wall_entities = [e for layer in LAYER_ROLES['walls'] for e in raw_segments.get(layer, [])]
    if not wall_entities:
        raise ValueError(f'El DXF no tiene entidades en las capas de muros {LAYER_ROLES["walls"]}')
    probe = [p for e in wall_entities for p in _polyline_points(e, 1e-3)]
    extent = max(max(x for x, _ in probe) - min(x for x, _ in probe), max(y for _, y in probe) - min(y for _, y in probe))
    factor, unit_code = _guess_factor(extent / 2)
    declared_factor = conversion_factor(declared, METERS) if declared else None
    declared_is_plausible = declared_factor is not None and \
        PLAUSIBLE_HALF_EXTENT_M[0] <= extent / 2 * declared_factor <= PLAUSIBLE_HALF_EXTENT_M[1]
    if declared_is_plausible:
        factor, unit_code = declared_factor, declared
    ox, oy = min(x for x, _ in probe), min(y for _, y in probe)
    to_m = lambda p: (round((p[0] - ox) * factor, 4), round((p[1] - oy) * factor, 4))
    drawing = Drawing(source=f'dxf:{dxf_path}', metadata={
        'dxf_version': doc.dxfversion, 'units_declared': declared, 'units_used': unit_code,
        'units_inferred': unit_code != declared, 'meters_per_unit': factor, 'precision_m': 0.0,
        'units_warning': None if unit_code == declared or not declared else
            f'$INSUNITS={declared} no cuadra con la geometría ({extent:.2f} unidades de lado); se usó {unit_code}',
        'layers': {l.dxf.name: {'off': l.is_off(), 'frozen': l.is_frozen()} for l in doc.layers},
    })
    tolerance = FLATTEN_TOLERANCE_M / factor
    for layer, entities in raw_segments.items():
        for e in entities:
            pts = [to_m(p) for p in _polyline_points(e, tolerance)]
            drawing.segments.setdefault(layer, []).extend((a, b) for a, b in zip(pts, pts[1:]) if a != b)
    drawing.texts = [Text(layer, value, to_m(pos)) for layer, value, pos in raw_texts]
    return drawing


def inventory(dxf_path: str) -> dict:
    """Radiografía del DXF: unidades, capas con su estado y conteo de entidades, bloques usados."""
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    by_layer = Counter((e.dxf.get('layer', '0'), e.dxftype()) for e in msp)
    layers = {}
    for (layer, kind), n in by_layer.items():
        layers.setdefault(layer, {})[kind] = n
    blocks = Counter(e.dxf.name for e in msp.query('INSERT'))
    return {
        'dxf_version': doc.dxfversion, 'insunits': doc.header.get('$INSUNITS', 0),
        'extmin': list(doc.header.get('$EXTMIN', ())), 'extmax': list(doc.header.get('$EXTMAX', ())),
        'layers': {l.dxf.name: {'off': l.is_off(), 'frozen': l.is_frozen(), 'entities': layers.get(l.dxf.name, {})}
                   for l in doc.layers},
        'blocks_used': dict(blocks.most_common()),
    }
