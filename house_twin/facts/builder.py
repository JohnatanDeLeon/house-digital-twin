import math
"""Ensambla `house.facts.json`: la fuente de verdad geométrica de la casa.

Regla del modelo: los hechos vienen del plano (o del usuario) y declaran su fuente;
lo que el plano no dice queda en `null` y se lista en `unknowns`. Nada se supone aquí.
"""
import re
from datetime import date

from shapely.geometry import LineString, Point, Polygon

from house_twin.drawing import Drawing
from house_twin.facts.annotations import (SpacePiece, correct_openings, merge_spaces, owner_measurements, owner_openings,
                                          rename_spaces, split_exterior)
from house_twin.facts.faces import partition
from house_twin.facts.naming import labels_inside, space_name
from house_twin.facts.openings import detect_openings
from house_twin.facts.walls import decompose_walls

SCHEMA_VERSION = 1
TOUCH = 0.02            # m: distancia para considerar que dos elementos se tocan
PROPERTY_LINE_MIN = 0.3  # m de contacto con el lindero para marcar un muro como colindante
MAX_WALL_THICKNESS = 0.3
MIN_FACING = 0.3         # m de frente compartido para considerar dos espacios adyacentes
MIN_WALL_SHARE = 0.15    # m: un muro cuenta como separador si aporta ≥ MIN_FACING × esto de franja (descarta esquinas)
CONTENT_LAYERS = {'11-VEGETACION': 'vegetación', '501 ARBOL': 'árbol', '2 AUTOS': 'auto',
                  '9-MUEBLES FIJOS': 'muebles fijos', '8-MUEBLES': 'muebles'}
UNKNOWN = {'value': None, 'source': 'no está en el plano'}

UNKNOWNS = [
    {'id': 'U01', 'topic': 'altura de entrepiso', 'question': '¿Altura de piso terminado a lecho bajo de losa?', 'blocks': ['3D', 'segunda planta']},
    {'id': 'U02', 'topic': 'losa', 'question': '¿Tipo y espesor de losa (concreto, vigueta y bovedilla, lámina)?', 'blocks': ['segunda planta']},
    {'id': 'U03', 'topic': 'estructura', 'question': '¿Dónde hay castillos, columnas, trabes y cuáles muros son de carga?', 'blocks': ['segunda planta', 'remoción de muros']},
    {'id': 'U04', 'topic': 'puertas', 'question': '¿Altura de las puertas?', 'blocks': ['3D']},
    {'id': 'U05', 'topic': 'materiales', 'question': '¿Material de los muros (block, tabique)?', 'blocks': ['estructura']},
    {'id': 'U06', 'topic': 'cochera', 'question': '¿La cochera está techada? ¿Con qué?', 'blocks': ['segunda planta']},
    {'id': 'U07', 'topic': 'cotas generales', 'question': 'En el DXF el frente mide 10.03 m, pero el texto de la cota se forzó a mano a "10.00" (el fondo sí mide 21.25). ¿Cuál es el frente real según escrituras?', 'blocks': []},
    {'id': 'U08', 'topic': 'ventanas', 'question': 'Confirmar que en los rótulos de ventana "a=" es antepecho y "h=" altura de ventana.', 'blocks': []},
    {'id': 'U09', 'topic': 'frente', 'question': 'La franja exterior frente a la sala (entre la cochera y la bodega, con la puerta principal y la peatonal), ¿es parte de la cochera, un acceso/jardín, u otra cosa?', 'blocks': []},
    {'id': 'U10', 'topic': 'tragaluz', 'question': '¿El tragaluz está abierto al cielo o cubierto (domo, vidrio)? Define si cuenta como área interior.', 'blocks': ['segunda planta']},
    {'id': 'U11', 'topic': 'ventana del tragaluz', 'question': '¿Ancho, altura de antepecho y altura de la ventana del tragaluz hacia la sala (muro diagonal de 1.11 m)?', 'blocks': ['3D']},
]


def _coords(poly: Polygon):
    return [[round(x, 3), round(y, 3)] for x, y in list(poly.exterior.coords)[:-1]]


def _level_of(poly: Polygon, drawing: Drawing):
    for t in drawing.texts_for('levels'):
        match = re.search(r'NPT\s*([+-]\s*[\d.]+)', t.value)
        if match and poly.contains(Point(t.position)):
            return {'value': float(match.group(1).replace(' ', '')), 'source': f'rótulo "{t.value}"'}
    return dict(UNKNOWN)


def _space_fact(sid, piece: SpacePiece, drawing: Drawing, walls: list[dict]):
    poly = piece.polygon
    labels = labels_inside(poly, drawing.texts_for('room_labels'))
    label_name, contains = space_name(labels)
    partitions = [walls[i] for i in piece.inner_partitions]
    free_area = poly.area - sum(Polygon(w['footprint']).area for w in partitions)
    fact = {
        'id': sid, 'name': piece.owner.get('name', label_name), 'labels': [t.value for t in labels],
        'contains': contains, 'drawn_contents': _contents(poly, drawing),
        'is_exterior': piece.is_exterior, 'polygon': _coords(poly),
        'area': round(free_area, 2), 'perimeter': round(poly.length, 2),
        'bbox': [round(v, 3) for v in poly.bounds], 'floor_level': _level_of(poly, drawing),
        'roofed': piece.owner.get('roofed', dict(UNKNOWN)), 'enclosed': piece.owner.get('enclosed', dict(UNKNOWN)),
        'source': 'plano: caras de MUROS + vanos',
    }
    if piece.owner:
        fact['name_source'] = piece.owner['source']
        fact['owner_note'] = piece.owner.get('note')
    if partitions:
        fact['inner_partitions'] = [w['id'] for w in partitions]
    return fact


def _wall_axis(poly: Polygon, direction):
    if direction is None:
        return None, None
    d = direction
    normal = (-d[1], d[0])
    pts = list(poly.exterior.coords)
    along = [x*d[0] + y*d[1] for x, y in pts]
    across = [x*normal[0] + y*normal[1] for x, y in pts]
    mid = (max(across) + min(across)) / 2
    p = lambda t: [round(d[0]*t + normal[0]*mid, 3), round(d[1]*t + normal[1]*mid, 3)]
    return [p(min(along)), p(max(along))], round(max(along) - min(along), 3)


def _wall_fact(wid, wall, lot: Polygon, exterior: list[Polygon]):
    poly = wall['polygon']
    axis, length = _wall_axis(poly, wall['direction'])
    on_line = poly.boundary.intersection(lot.boundary.buffer(TOUCH)).length >= PROPERTY_LINE_MIN
    faces_exterior = any(poly.buffer(TOUCH).intersects(e) for e in exterior)
    return {
        'id': wid, 'footprint': _coords(poly), 'axis': axis, 'length': length,
        'thickness': round(wall['thickness'], 3) if wall['thickness'] else None,
        'on_property_line': on_line, 'faces_exterior': faces_exterior, 'height': dict(UNKNOWN), 'load_bearing': dict(UNKNOWN),
        'material': dict(UNKNOWN), 'source': 'plano: pares de caras de MUROS',
    }


def _touching(poly: Polygon, items, key='id'):
    zone = poly.buffer(TOUCH)
    return [i[key] for i, geom in items if zone.intersects(geom)]


def _relate_openings(openings, walls, spaces):
    wall_geoms = [(w, Polygon(w['footprint'])) for w in walls]
    space_geoms = [(s, Polygon(s['polygon'])) for s in spaces]
    for o in openings:
        rect = Polygon(o['footprint'])
        hosts = sorted(wall_geoms, key=lambda wg: -wg[1].intersection(rect.buffer(TOUCH)).area)
        o['host_wall'] = hosts[0][0]['id'] if hosts and hosts[0][1].intersects(rect.buffer(TOUCH)) else None
        o['connects'] = _touching(rect, space_geoms)


def _lights(drawing, spaces) -> list[dict]:
    """Salidas de foco del plano, con el espacio en el que caen."""
    geoms = [(s['id'], Polygon(s['polygon'])) for s in spaces]
    lights = []
    for x, y in drawing.metadata.get('ceiling_lights', []):
        space = next((sid for sid, g in geoms if g.contains(Point(x, y))), None)
        lights.append({'id': f'L{len(lights) + 1:02d}', 'position': [round(x, 3), round(y, 3)], 'space': space,
                       'source': 'plano: salida de foco en la capa 23- ILUMINACION'})
    return lights


def _devices(drawing, spaces) -> list[dict]:
    """Contactos y apagadores del plano, llevados a la cara de muro más cercana de su espacio.

    Se guarda el punto sobre la cara y la normal hacia el cuarto; la altura no está en el plano.
    """
    geoms = [(s['id'], Polygon(s['polygon'])) for s in spaces]
    result = []
    for d in drawing.metadata.get('devices', []):
        p = Point(d['position'])
        space = next(((sid, g) for sid, g in geoms if g.contains(p)), None)
        if space is None:
            continue
        sid, poly = space
        ring = list(poly.exterior.coords)
        edges = [LineString([a, b]) for a, b in zip(ring, ring[1:]) if a != b]
        edge = min(edges, key=lambda e: e.distance(p))
        on = edge.interpolate(edge.project(p))
        (x0, y0), (x1, y1) = edge.coords
        length = math.hypot(x1 - x0, y1 - y0)
        n = (-(y1 - y0) / length, (x1 - x0) / length)
        if not poly.contains(Point(on.x + n[0] * 0.05, on.y + n[1] * 0.05)):
            n = (-n[0], -n[1])
        prefix = 'C' if d['kind'] == 'outlet' else 'A'
        count = sum(1 for r in result if r['kind'] == d['kind'])
        result.append({'id': f'{prefix}{count + 1:02d}', 'kind': d['kind'], 'space': sid,
                       'position': [round(on.x, 3), round(on.y, 3)], 'faces_toward': [round(n[0], 3), round(n[1], 3)],
                       'from_plan_m': round(p.distance(on), 3),
                       'height': {'value': None, 'source': 'no está en el plano (vista en planta)'},
                       'source': 'plano: bloque ' + ('CONTACTO' if d['kind'] == 'outlet' else 'APAGADOR SIMPLE')})
    return result


PLATE_MATCH_M = 0.05  # el ancla del dueño es el punto del dispositivo sobre la cara del muro


def _shared_plates(devices, annotations):
    """Placas que el dueño dice que son una sola (p. ej. apagador y contacto juntos): el plano las dibuja por
    separado. Todas quedan en el punto de la primera; la posición del plano se conserva en `plan_position`."""
    source = f"{annotations.get('source', 'dueño')} ({annotations.get('confirmed_on', 's/f')})"
    for i, entry in enumerate(annotations.get('shared_plates', [])):
        found = [min(devices, key=lambda d: Point(d['position']).distance(Point(a)), default=None) for a in entry['anchors']]
        if any(d is None or Point(d['position']).distance(Point(a)) > PLATE_MATCH_M for d, a in zip(found, entry['anchors'])):
            continue  # la fuente no trae esos dispositivos (p. ej. el PDF de validación)
        host = found[0]
        for d in found:
            if d is not host:
                d['plan_position'], d['position'] = d['position'], list(host['position'])
            d['plate'] = {'id': f'P{i + 1:02d}', 'with': [o['id'] for o in found if o is not d],
                          'material': entry.get('material'), 'source': entry.get('source', source)}


def _absent_devices(devices, annotations):
    """Dispositivos que el plano dibuja pero que el dueño dice que no existen: quedan en los hechos marcados como
    inexistentes (con la fuente), y no se modelan."""
    source = f"{annotations.get('source', 'dueño')} ({annotations.get('confirmed_on', 's/f')})"
    for entry in annotations.get('absent_devices', []):
        device = min(devices, key=lambda d: Point(d['position']).distance(Point(entry['anchor'])), default=None)
        if device is None or Point(device['position']).distance(Point(entry['anchor'])) > PLATE_MATCH_M:
            continue  # la fuente no trae ese dispositivo (p. ej. el PDF de validación)
        device['exists'] = {'value': False, 'source': entry.get('source', source)}


def _sanitary(drawing, spaces) -> list[dict]:
    """Inodoros y lavabos del plano: el rectángulo del bloque y hacia dónde miran (lejos del muro que tocan)."""
    geoms = [(s['id'], Polygon(s['polygon'])) for s in spaces]
    result, counts = [], {}
    for item in drawing.metadata.get('sanitary', []):
        x0, y0, x1, y1 = item['bbox']
        centre = Point((x0 + x1) / 2, (y0 + y1) / 2)
        space = next(((sid, g) for sid, g in geoms if g.contains(centre)), None)
        if space is None:
            continue
        sid, poly = space
        sides = {(-1, 0): Point(x0, centre.y), (1, 0): Point(x1, centre.y), (0, -1): Point(centre.x, y0), (0, 1): Point(centre.x, y1)}
        back = min(sides, key=lambda k: poly.exterior.distance(sides[k]))
        facing = (-back[0], -back[1])
        depth, width = (x1 - x0, y1 - y0) if back[0] else (y1 - y0, x1 - x0)
        wall_point = sides[back]
        counts[item['kind']] = counts.get(item['kind'], 0) + 1
        prefix = {'toilet': 'WC', 'basin': 'LV'}[item['kind']]
        result.append({'id': f"{prefix}{counts[item['kind']]:02d}", 'kind': item['kind'], 'space': sid,
                       'back_centre': [round(wall_point.x, 3), round(wall_point.y, 3)], 'facing': list(facing),
                       'width': round(width, 3), 'depth': round(depth, 3),
                       'source': 'plano: bloque ' + ('WC' if item['kind'] == 'toilet' else 'LAVABO') + ' (capa 9-MUEBLES FIJOS)'})
    return result


def _interior_roofs(spaces, annotations):
    """Dato del dueño: los espacios interiores sin dato de techo están techados."""
    entry = annotations.get('interior_roofed')
    if not entry:
        return
    source = f"{annotations.get('source', 'dueño')} ({entry.get('answered_on', annotations.get('confirmed_on', 's/f'))})"
    for s in spaces:
        if not s['is_exterior'] and s['roofed']['value'] is None:
            s['roofed'] = {'value': entry['value'], 'source': source}


CLOSET_MAX_DEPTH_M = 1.0  # del frente dibujado al muro: más que esto no es el fondo de un closet


def _closets(drawing, spaces) -> list[dict]:
    """Closets del plano: en un espacio rotulado CLOSET, la línea más larga de muebles fijos es el frente y el
    closet llega de ahí al muro más cercano (el borde del espacio)."""
    fronts = drawing.segments_for('fixed_furniture')
    result = []
    for s in spaces:
        if 'Closet' not in s['contains']:
            continue
        poly = Polygon(s['polygon'])
        inside = [seg for seg in fronts if poly.buffer(0.01).contains(LineString(seg))]
        if not inside:
            continue
        (x0, y0), (x1, y1) = max(inside, key=lambda seg: LineString(seg).length)
        length = math.hypot(x1 - x0, y1 - y0)
        n = (-(y1 - y0) / length, (x1 - x0) / length)
        mid = ((x0 + x1) / 2, (y0 + y1) / 2)
        depths = []
        for sign in (1, -1):
            ray = LineString([mid, (mid[0] + sign * n[0] * CLOSET_MAX_DEPTH_M, mid[1] + sign * n[1] * CLOSET_MAX_DEPTH_M)])
            hit = ray.intersection(poly.exterior)
            if not hit.is_empty:
                depths.append((Point(mid).distance(hit), sign))
        if not depths:
            continue
        depth, sign = min(depths)
        back = [(x + sign * n[0] * depth, y + sign * n[1] * depth) for x, y in ((x0, y0), (x1, y1))]
        result.append({'id': f'F{len(result) + 1:02d}', 'kind': 'closet', 'space': s['id'],
                       'front': [[round(x0, 3), round(y0, 3)], [round(x1, 3), round(y1, 3)]],
                       'faces_toward': [round(-sign * n[0], 3), round(-sign * n[1], 3)],
                       'width': round(length, 3), 'depth': round(depth, 3),
                       'footprint': [[round(x0, 3), round(y0, 3)], [round(x1, 3), round(y1, 3)],
                                     [round(back[1][0], 3), round(back[1][1], 3)], [round(back[0][0], 3), round(back[0][1], 3)]],
                       'source': 'plano: rótulo CLOSET y frente en la capa de muebles fijos; fondo hasta el muro'})
    return result


def _showers(spaces, walls, annotations, first_id: int) -> list[dict]:
    """Regaderas: el dueño dice en qué lado del sardinel está (un punto adentro) y el plano da el sardinel (un
    muro de 5 cm que cruza el baño). El área es la parte del espacio de ese lado; el sardinel toma su altura."""
    source = f"{annotations.get('source', 'dueño')} ({annotations.get('confirmed_on', 's/f')})"
    result = []
    for entry in annotations.get('showers', []):
        space = next(s for s in spaces if Polygon(s['polygon']).contains(Point(entry['space_anchor'])))
        curb = next(w for w in walls if Polygon(w['footprint']).buffer(0.01).contains(Point(entry['curb_anchor'])))
        pieces = Polygon(space['polygon']).difference(Polygon(curb['footprint']))
        area = next(g for g in getattr(pieces, 'geoms', [pieces]) if g.contains(Point(entry['space_anchor'])))
        curb['height'] = {'value': entry['curb_height'], 'source': entry.get('curb_source', source)}
        curb['role'] = 'sardinel de la regadera'
        result.append({'id': f'F{first_id + len(result):02d}', 'kind': 'shower', 'space': space['id'],
                       'polygon': [[round(x, 3), round(y, 3)] for x, y in list(area.exterior.coords)[:-1]],
                       'area': round(area.area, 2), 'curb_wall': curb['id'],
                       'source': f"plano: sardinel {curb['id']}; lado de la regadera: {entry.get('side_source', source)}",
                       'owner_note': entry.get('note')})
    return result


SWING_MATCH_M = 0.05  # la bisagra del bloque de puerta cae en el vano (o a pocos cm)


def _axis_ends(footprint):
    """Extremos del eje largo de un vano: los puntos medios de sus lados cortos."""
    p0, p1, p2, p3 = footprint
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if Point(p0).distance(Point(p1)) >= Point(p1).distance(Point(p2)):
        return mid(p0, p3), mid(p1, p2)
    return mid(p0, p1), mid(p3, p2)


def _assign_swings(doors, spaces, swings):
    """Abatimiento de cada puerta según el bloque del CAD: de qué lado va la bisagra y hacia qué espacio abre."""
    space_geoms = [(s['id'], Polygon(s['polygon'])) for s in spaces]
    for swing in swings:
        hinge = Point(swing['hinge'])
        door = min(doors, key=lambda o: Polygon(o['footprint']).distance(hinge), default=None)
        if door is None or Polygon(door['footprint']).distance(hinge) > SWING_MATCH_M:
            continue
        ends = sorted(_axis_ends(door['footprint']), key=lambda e: hinge.distance(Point(e)))
        into = next((sid for sid, g in space_geoms if g.contains(Point(swing['arc_mid']))), None)
        door['swing'] = {'hinge_end': [round(v, 3) for v in ends[0]], 'latch_end': [round(v, 3) for v in ends[1]],
                         'opens_into': into, 'source': 'plano: bloque PUERTA (centro del arco = bisagra)'}


def _facing_zone(a: Polygon, b: Polygon):
    """Franja de muro entre dos espacios que se enfrentan; vacía si solo se tocan de lejos.

    El buffer es redondeado: con esquinas en inglete, dos espacios que solo se miran en diagonal
    por una esquina parecerían compartir muro.
    """
    reach = MAX_WALL_THICKNESS + TOUCH
    return a.buffer(reach, join_style='round').intersection(b.buffer(reach, join_style='round')).difference(a).difference(b)


def _shares_open_edge(a: Polygon, b: Polygon) -> bool:
    """Dos exteriores contiguos sin muro: comparten al menos MIN_FACING de borde."""
    return a.boundary.intersection(b.buffer(TOUCH)).length >= MIN_FACING


def _walls_between(a: Polygon, b: Polygon, wall_geoms: dict) -> list[str]:
    zone = _facing_zone(a, b)
    if zone.area < MIN_FACING * MAX_WALL_THICKNESS:
        return []
    return [wid for wid, g in wall_geoms.items() if g.intersection(zone).area >= MIN_FACING * MIN_WALL_SHARE]


def _adjacency(walls, spaces, openings):
    """Pares de espacios vecinos: separados por muro, contiguos sin muro (exteriores) o unidos por un vano."""
    space_geoms = {s['id']: Polygon(s['polygon']) for s in spaces}
    wall_geoms = {w['id']: Polygon(w['footprint']) for w in walls}
    exterior = {s['id'] for s in spaces if s['is_exterior']}
    pairs = {}
    ids = sorted(space_geoms)
    for i, a in enumerate(ids):
        for b in ids[i+1:]:
            ga, gb = space_geoms[a], space_geoms[b]
            if a in exterior and b in exterior and _shares_open_edge(ga, gb):
                pairs[(a, b)] = {'spaces': [a, b], 'walls': [], 'doors': [], 'windows': [], 'open': True}
                continue
            between = _walls_between(ga, gb, wall_geoms)
            if between:
                pairs[(a, b)] = {'spaces': [a, b], 'walls': between, 'doors': [], 'windows': []}
    for o in openings:
        if len(o['connects']) == 2:
            entry = pairs.setdefault(tuple(sorted(o['connects'])), {'spaces': sorted(o['connects']), 'walls': [], 'doors': [], 'windows': []})
            entry['doors' if o['kind'] == 'door' else 'windows'].append(o['id'])
            if o['kind'] == 'door' and entry.get('open'):
                entry['open'] = False  # el paso entre los dos exteriores lo cierra una puerta (p. ej. de herrería)
    return [pairs[k] for k in sorted(pairs)]


def _contents(poly: Polygon, drawing: Drawing):
    """Capas de ambientación presentes dentro del espacio (dato del plano, no un uso inferido)."""
    found = []
    for layer, label in CONTENT_LAYERS.items():
        if any(poly.contains(Point(a)) for a, _ in drawing.segments.get(layer, [])):
            found.append(label)
    return found


def build_facts(drawing: Drawing, annotations: dict | None = None) -> dict:
    annotations = annotations or {}
    openings = detect_openings(drawing)
    faces = partition(drawing, openings)
    opening_polys = [Polygon(o['footprint']) for o in openings]
    walls_raw = decompose_walls(drawing, faces.wall_bodies, opening_polys)

    walls = [_wall_fact(f'W{i+1:02d}', w, faces.lot, faces.exterior) for i, w in enumerate(walls_raw)]
    interior = merge_spaces([SpacePiece(p, False) for p in faces.spaces], [w['polygon'] for w in walls_raw], annotations)
    interior = rename_spaces(interior, annotations)
    exterior = split_exterior(faces.exterior, annotations)
    pieces = sorted(interior, key=lambda p: -p.polygon.area) + sorted(exterior, key=lambda p: -p.polygon.area)
    spaces = [_space_fact(f'S{i+1:02d}', piece, drawing, walls) for i, piece in enumerate(pieces)]
    doors = [o for o in openings if o['kind'] == 'door']
    windows = [o for o in openings if o['kind'] == 'window']
    for prefix, group in (('D', doors), ('V', windows)):
        for i, o in enumerate(group):
            o['id'] = f'{prefix}{i+1:02d}'
    _relate_openings(doors + windows, walls, spaces)
    _assign_swings(doors, spaces, drawing.metadata.get('door_swings', []))
    _interior_roofs(spaces, annotations)
    for o in owner_openings(walls, spaces, annotations):
        o['id'] = f"V{len(windows)+1:02d}" if o['kind'] == 'window' else f"D{len(doors)+1:02d}"
        (windows if o['kind'] == 'window' else doors).append(o)
    openings = doors + windows
    correct_openings(openings, annotations)

    closets = _closets(drawing, spaces)
    fixtures = closets + _showers(spaces, walls, annotations, len(closets) + 1) + _sanitary(drawing, spaces)
    devices = _devices(drawing, spaces)
    _shared_plates(devices, annotations)
    _absent_devices(devices, annotations)

    cal = drawing.metadata.get('calibration', {})
    lot_w = faces.lot.bounds[2] - faces.lot.bounds[0]
    lot_d = faces.lot.bounds[3] - faces.lot.bounds[1]
    facts = {
        'schema_version': SCHEMA_VERSION,
        'name': 'Casa Jonhy — planta existente',
        'units': 'm',
        'frame': 'origen en la esquina del terreno a la izquierda de la calle; X a lo ancho, Y hacia el fondo',
        'provenance': {
            'source': drawing.source, 'built_on': date.today().isoformat(),
            'precision_m': round(drawing.metadata.get('precision_m', 0), 4),
            'calibration': {k: cal[k] for k in ('pt_per_m', 'paper_scale') if k in cal},
            'owner_annotations': annotations.get('confirmed_on'),
        },
        'site': {'polygon': _coords(faces.lot), 'width': round(lot_w, 3), 'depth': round(lot_d, 3),
                 'area': round(faces.lot.area, 2), 'labeled_dimensions': [10.00, 21.25]},
        'source_warnings': [w for w in [drawing.metadata.get('units_warning')] if w],
        'levels': [{'id': 'L0', 'name': 'Planta baja', 'elevation': 0.0, 'storey_height': dict(UNKNOWN)}],
        'spaces': spaces, 'walls': walls, 'openings': openings, 'fixtures': fixtures,
        'lights': _lights(drawing, spaces), 'devices': devices,
        'adjacency': _adjacency(walls, spaces, openings),
        'measurements': owner_measurements(walls, annotations),
        **_unknowns(annotations),
    }
    _apply_answered_values(facts, annotations)
    for m in facts['measurements']:
        if m['matches_plan'] is False:
            facts['source_warnings'].append(f"{m['id']}: el dueño mide {m['value']} m ({m['what']}) y el plano da "
                                            f"{m['plan_value']} m entre {' y '.join(m['walls'])}")
    return facts


def _owner_source(annotations: dict, answer: dict) -> str:
    return f"{annotations.get('source', 'dueño')} ({answer.get('answered_on') or annotations.get('confirmed_on', 's/f')})"


def _apply_answered_values(facts: dict, annotations: dict):
    """Las respuestas con `value` numérico pasan a los hechos que contestan; sin `value` solo cierran la incógnita.

    U01 → altura de piso terminado a lecho bajo de losa del nivel; U04 → altura de vano de las puertas
    que el plano deja sin altura. U04 habla de vanos en muros: no llega a las puertas sin muro (herrería entre
    dos muros), que esperan su propia medida.
    """
    for answer in annotations.get('answered_unknowns', []):
        if answer.get('value') is None:
            continue
        fact = {'value': answer['value'], 'source': f"{_owner_source(annotations, answer)}: {answer['id']}"}
        if answer['id'] == 'U01':
            facts['levels'][0]['storey_height'] = fact
        elif answer['id'] == 'U04':
            for o in facts['openings']:
                if o['kind'] == 'door' and o['host_wall'] and o['height']['value'] is None:
                    o['height'] = dict(fact)


def _unknowns(annotations: dict) -> dict:
    """Las incógnitas que el dueño ya respondió salen de `unknowns` y quedan registradas con su respuesta."""
    answers = {a['id']: a for a in annotations.get('answered_unknowns', [])}
    return {
        'unknowns': [u for u in UNKNOWNS if u['id'] not in answers],
        'answered': [{**u, 'answer': answers[u['id']]['answer'], 'source': _owner_source(annotations, answers[u['id']])}
                     for u in UNKNOWNS if u['id'] in answers],
    }
