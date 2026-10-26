"""Puerta corrediza colgada de un riel aparente (tipo granero): hoja de cristal templado por fuera del muro, riel con
separadores, carretillas y jaladeras. Se describe en el vano con `slide` (en vez de `swing`):

- `line`: la hoja cerrada en planta, de un extremo al otro (cubre el vano y traslapa en los dos lados).
- `travel`: cuánto se mueve la hoja al abrir (vector en planta).
- `z`: abajo y arriba de la hoja; `thickness_m`: espesor del cristal.
- `wall_normal`: de la hoja hacia el muro. Las profundidades `n` se miden así desde la cara de afuera de la hoja
  (la hoja ocupa de 0 a `thickness_m`).
- `track`: riel (`from`, `to` en planta, `z` de su borde de abajo, `height_m`, profundidad `n`) y la cara del muro
  (`wall_n`), hasta donde llegan sus separadores.
- `hardware`: material, carretillas (`hanger_inset_m` desde cada canto, `wheel_radius_m`) y jaladeras (`pull_u`, `pull_z`).

`ifc_export` guarda la hoja como el IfcDoor y lo demás como IfcDiscreteAccessory de la puerta. Lo que se mueve con la
hoja se llama `<puerta>-...` (el recorrido lo desliza junto con ella); el riel, `riel-<puerta>`, se queda fijo.
Solo biblioteca estándar.
"""
from house_twin.hardware import cylinder, merge, oriented_box


def _frame(slide):
    """Ejes de la hoja: `u` a lo largo (de line[0] a line[1]), `n` de la hoja hacia el muro."""
    (x0, y0), (x1, y1) = slide['line']
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    return (x0, y0), ((x1 - x0) / length, (y1 - y0) / length), tuple(slide['wall_normal']), length


def panel_polygon(slide):
    """La hoja cerrada en planta (rectángulo del espesor del cristal), para extruirla como el IfcDoor."""
    (x0, y0), (ux, uy), (nx, ny), length = _frame(slide)
    t = slide['thickness_m']
    return [(x0, y0), (x0 + ux * length, y0 + uy * length),
            (x0 + ux * length + nx * t, y0 + uy * length + ny * t), (x0 + nx * t, y0 + ny * t)]


def sliding_parts(door_id, slide):
    """Piezas del herraje: id, material, malla y si se mueve con la hoja."""
    origin, along, normal, length = _frame(slide)
    o3 = (*origin, 0.0)
    t, (z0, z1), hw = slide['thickness_m'], slide['z'], slide['hardware']
    tr = slide['track']

    def box(u, z, n):
        return oriented_box(o3, along, normal, tuple(u), tuple(z), tuple(n))

    def point(u, n, z):
        return (o3[0] + along[0] * u + normal[0] * n, o3[1] + along[1] * u + normal[1] * n, z)

    # riel: de `from` a `to`, separado del muro; sus extremos en coordenadas de la hoja
    def u_of(p):
        return (p[0] - origin[0]) * along[0] + (p[1] - origin[1]) * along[1]
    ua, ub = sorted((u_of(tr['from']), u_of(tr['to'])))
    rz, rh, (n0, n1), wall = tr['z'], tr['height_m'], tr['n'], tr['wall_n']
    rail = [box((ua, ub), (rz, rz + rh), (n0, n1))]
    rail += [box((u - 0.02, u + 0.02), (rz + 0.005, rz + rh - 0.005), (n1, wall))
             for u in (ua + 0.08, (ua + ub) / 2, ub - 0.08)]  # separadores al muro
    rail += [cylinder(point(u, n0, rz + rh / 2), point(u, n0 - 0.03, rz + rh / 2), 0.012, 12)
             for u in (ua + 0.015, ub - 0.015)]  # topes en los extremos
    # carretillas: fleje sobre la hoja hasta una rueda que corre encima del riel
    wheel_z, r = rz + rh + hw['wheel_radius_m'], hw['wheel_radius_m']
    carriages = []
    for u in (hw['hanger_inset_m'], length - hw['hanger_inset_m']):
        carriages.append(box((u - 0.02, u + 0.02), (z1 - 0.12, wheel_z), (-0.008, 0.0)))  # fleje por fuera
        carriages.append(box((u - 0.02, u + 0.02), (z1 - 0.12, z1), (t, t + 0.008)))  # contraplaca por dentro
        carriages.append(cylinder(point(u, n0 - 0.008, wheel_z), point(u, n1, wheel_z), r, 20))
    # jaladeras: barra tubular del lado de afuera y cazoleta plana del lado del muro (no choca al deslizar)
    pu, (pz0, pz1) = hw['pull_u'], hw['pull_z']
    pull = [cylinder(point(pu, -0.05, pz0), point(pu, -0.05, pz1), 0.0125, 16)]
    pull += [cylinder(point(pu, 0.0, z), point(pu, -0.05, z), 0.008, 12) for z in (pz0 + 0.04, pz1 - 0.04)]
    flush = [box((pu - 0.03, pu + 0.03), ((pz0 + pz1) / 2 - 0.09, (pz0 + pz1) / 2 + 0.09), (t, t + 0.006))]
    return [
        {'id': f'riel-{door_id}', 'material': hw['material'], 'mesh': merge(rail), 'moves': False},
        {'id': f'{door_id}-carretillas', 'material': hw['material'], 'mesh': merge(carriages), 'moves': True},
        {'id': f'{door_id}-jaladera', 'material': hw['material'], 'mesh': merge(pull + flush), 'moves': True},
    ]
