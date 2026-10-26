"""Piezas sueltas de una propuesta, en coordenadas del mundo (metros): cajas (`boxes`: el remate del pretil, el costado
de un nicho), cilindros verticales (`cylinders`: un banco, la regadera), cubiertas inclinadas (`slabs`: el techo de la
cochera, el de una palapa; la pendiente va en x o, con `slope_axis: "y"`, en y), luminarias (`lights`) y tiras de LED (`strips`).
`ifc_export` las guarda con su clase; una luminaria es un IfcLightFixture con su luz (Pset HDT_Light) y un
IfcDiscreteAccessory `<id>-foco`, que el recorrido enciende de noche. Solo biblioteca estándar.
"""
from house_twin.hardware import _box, cylinder, merge


def box_part(b: dict, ifc: str = 'IfcMember') -> dict:
    (x0, x1), (y0, y1), (z0, z1) = b['x'], b['y'], b['z']
    return {'id': b['id'], 'ifc': b.get('ifc', ifc), 'type': 'USERDEFINED', 'object_type': b.get('object_type', 'pieza'),
            'material': b['material'], 'mesh': _box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0)),
            'source': b['source']}


def cylinder_part(c: dict, ifc: str = 'IfcBuildingElementProxy') -> dict:
    """Cilindro vertical de radio `radius_m` centrado en (`x`, `y`), de `z[0]` a `z[1]`."""
    x, y = c['x'], c['y']
    return {'id': c['id'], 'ifc': c.get('ifc', ifc), 'type': 'USERDEFINED', 'object_type': c.get('object_type', 'pieza'),
            'material': c['material'], 'mesh': cylinder((x, y, c['z'][0]), (x, y, c['z'][1]), c['radius_m'], 24),
            'source': c['source']}


def slab_part(s: dict) -> dict:
    """Tablero inclinado: la cara de arriba va de `z_top[0]` (en x[0], o en y[0] con `slope_axis: "y"`) a `z_top[1]`
    (en x[1] o y[1]), con su espesor."""
    (x0, x1), (y0, y1), (za, zb), t = s['x'], s['y'], s['z_top'], s['thickness_m']
    points, faces = _box(((x0 + x1) / 2, (y0 + y1) / 2, 0.0), (x1 - x0, y1 - y0, t))
    if s.get('slope_axis') == 'y':
        slope = (zb - za) / (y1 - y0)
        points = [(x, y, z + za - t / 2 + (y - y0) * slope) for x, y, z in points]
    else:
        slope = (zb - za) / (x1 - x0)
        points = [(x, y, z + za - t / 2 + (x - x0) * slope) for x, y, z in points]
    return {'id': s['id'], 'ifc': s.get('ifc', 'IfcPlate'), 'type': 'USERDEFINED', 'object_type': s.get('object_type', 'tablero'),
            'material': s['material'], 'mesh': (points, faces), 'source': s['source']}


def light_parts(lum: dict) -> list[dict]:
    """Luminaria: cuerpo (IfcLightFixture, con su luz) y la parte que brilla (`<id>-foco`).

    - `updown`: arbotante cilíndrico en un muro (`wall_normal` hacia afuera), que alumbra hacia arriba y hacia abajo.
    - `downlight`: empotrado en un techo, con su cara de abajo a `z`.
    """
    (x, y), z = lum['position'], lum['z']
    if lum['kind'] == 'updown':
        (nx, ny), r, h, off = lum['wall_normal'], lum['radius_m'], lum['height_m'], lum['offset_m']
        cx, cy = x + nx * off, y + ny * off
        body = merge([cylinder((cx, cy, z - h / 2), (cx, cy, z + h / 2), r, 24),
                      cylinder((x, y, z), (cx - nx * r, cy - ny * r, z), 0.012, 12)])  # brazo al muro
        glow = merge([cylinder((cx, cy, z - h / 2 - 0.004), (cx, cy, z - h / 2), r * 0.75, 24),
                      cylinder((cx, cy, z + h / 2), (cx, cy, z + h / 2 + 0.004), r * 0.75, 24)])
        centre = (cx, cy, z)
    else:
        r = lum['radius_m']
        body = cylinder((x, y, z + 0.06), (x, y, z), r, 24)  # bote que entra al techo
        glow = cylinder((x, y, z), (x, y, z - 0.004), r * 0.75, 24)
        centre = (x, y, z - 0.02)
    light = {'Lumens': lum['lumens'], 'ColorTemperature': lum['color_temperature_k'], 'PowerW': lum['power_w'],
             'CentreZ': round(centre[2], 3), 'Source': lum['source']}
    return [{'id': lum['id'], 'ifc': 'IfcLightFixture', 'type': 'POINTSOURCE', 'material': lum['body_material'],
             'mesh': body, 'source': lum['source'], 'psets': {'HDT_Light': light}},
            {'id': f"{lum['id']}-foco", 'ifc': 'IfcDiscreteAccessory', 'type': None, 'material': lum['led_material'],
             'mesh': glow, 'source': lum['source']}]


def strip_part(s: dict) -> dict:
    """Tira de LED: barra delgada que brilla de noche (no da luz propia en el recorrido; la dan las luminarias)."""
    return {'id': s['id'], 'ifc': 'IfcLightFixture', 'type': 'USERDEFINED', 'object_type': 'tira de LED', 'material': s['material'],
            'mesh': box_part({**s, 'material': s['material']})['mesh'], 'source': s['source']}


def extras_parts(spec: dict) -> list[dict]:
    """Todas las piezas de la especificación, cada una en el espacio que declara (o el de la especificación)."""
    parts = [box_part(b) for b in spec.get('boxes', [])]
    parts += [cylinder_part(c) for c in spec.get('cylinders', [])]
    parts += [slab_part(s) for s in spec.get('slabs', [])]
    parts += [p for lum in spec.get('lights', []) for p in light_parts(lum)]
    parts += [strip_part(s) for s in spec.get('strips', [])]
    for p in parts:
        p.setdefault('space', spec['applies_to']['space'])
    return parts
