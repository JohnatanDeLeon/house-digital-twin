"""Compara los hechos de dos fuentes (p. ej. PDF vs DXF) para validar una con la otra."""
from shapely.geometry import Polygon

OPENING_MATCH_RADIUS = 0.3  # m


def _centre(points):
    poly = Polygon(points)
    return poly.centroid


def _match_spaces(a: dict, b: dict):
    rows = []
    for sa in a['spaces']:
        ca = _centre(sa['polygon'])
        sb = min(b['spaces'], key=lambda s: _centre(s['polygon']).distance(ca))
        rows.append({'space': sa['name'] or sa['id'], 'area_a': sa['area'], 'area_b': sb['area'],
                     'diff_m2': round(sb['area'] - sa['area'], 3), 'name_b': sb['name'] or sb['id']})
    return rows


def _drawn(openings):
    return [o for o in openings if o['footprint'] is not None]


def _match_openings(a: dict, b: dict):
    rows, unmatched_b = [], _drawn(b['openings'])
    for oa in _drawn(a['openings']):
        ca = _centre(oa['footprint'])
        near = [o for o in unmatched_b if _centre(o['footprint']).distance(ca) <= OPENING_MATCH_RADIUS]
        ob = min(near, key=lambda o: _centre(o['footprint']).distance(ca)) if near else None
        if ob:
            unmatched_b.remove(ob)
        rows.append({'opening': oa['id'], 'kind': oa['kind'], 'width_a': oa['width'],
                     'width_b': ob['width'] if ob else None, 'match_b': ob['id'] if ob else None,
                     'diff_m': round(ob['width'] - oa['width'], 3) if ob else None})
    return rows, [o['id'] for o in unmatched_b]


def compare_facts(a: dict, b: dict) -> dict:
    openings, only_b = _match_openings(a, b)
    return {
        'sources': [a['provenance']['source'], b['provenance']['source']],
        'site': {k: [a['site'][k], b['site'][k]] for k in ('width', 'depth', 'area')},
        'counts': {k: [len(a[k]), len(b[k])] for k in ('spaces', 'walls', 'openings')},
        'spaces': _match_spaces(a, b), 'openings': openings, 'openings_only_in_b': only_b,
        'max_space_area_diff_m2': max(abs(r['diff_m2']) for r in _match_spaces(a, b)),
        'max_opening_width_diff_m': max((abs(r['diff_m']) for r in openings if r['diff_m'] is not None), default=None),
    }
