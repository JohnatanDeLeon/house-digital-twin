"""Portón seccional (`lift` en el vano): paneles horizontales que suben por guías laterales, dan la vuelta en una curva
y quedan acostados bajo el techo. No invade la banqueta al abrir, a diferencia de un basculante. Se describe con:

- `x`: de un canto al otro de los paneles; `y`: el plano de los paneles (cara de afuera), detrás del vano.
- `panels`: cuántos y su alto (`panel_m`); `thickness_m`.
- `track`: la vertical sube hasta `z_curve`, gira con radio `radius_m` y sigue horizontal hacia `direction` (+1: hacia
  dentro, y creciente) hasta `length_m`.
- `operator`: el motor de techo (`motor_y`, caja `motor_m`), su riel al centro y las fotoceldas (`photocell_z`).

El primer panel es el IfcDoor (lo que el vano rellena); los demás, `<puerta>-panel-<k>`, son IfcDiscreteAccessory de la
puerta y el recorrido los mueve por la misma trayectoria. Guías y motor (`guias-<puerta>`, `operador-<puerta>`) quedan
fijos. Solo biblioteca estándar.
"""
import math

from house_twin.hardware import _box, merge


def path_point(lift: dict, s: float) -> tuple[float, float]:
    """(y, z) del canto de abajo de la trayectoria a `s` metros de recorrido desde el piso."""
    tr, y0, sign = lift['track'], lift['y'], lift['track']['direction']
    zc, r = tr['z_curve'], tr['radius_m']
    if s <= zc:
        return y0, s
    arc = math.pi * r / 2
    if s <= zc + arc:
        a = (s - zc) / r
        return y0 + sign * r * (1 - math.cos(a)), zc + r * math.sin(a)
    return y0 + sign * (r + s - zc - arc), zc + r


def panel_box(lift: dict, k: int) -> tuple[list, list]:
    """Panel `k` (0 = el de abajo) con el portón cerrado: caja vertical en el plano de los paneles."""
    (x0, x1), h, t, y0 = lift['x'], lift['panel_m'], lift['thickness_m'], lift['y']
    sign = lift['track']['direction']
    y_in = y0 + sign * t
    return _box(((x0 + x1) / 2, (y0 + y_in) / 2, k * h + h / 2), (x1 - x0, t, h))


def lift_parts(door_id: str, lift: dict) -> list[dict]:
    """Paneles 2…n (el 1 es el IfcDoor), guías y motor: id, material, malla y si se mueve."""
    (x0, x1), y0, sign = lift['x'], lift['y'], lift['track']['direction']
    tr, op = lift['track'], lift['operator']
    parts = [{'id': f'{door_id}-panel-{k + 1}', 'material': lift['material'], 'mesh': panel_box(lift, k), 'moves': True}
             for k in range(1, lift['panels'])]
    # guías: ángulo vertical a cada lado, curva (en 6 tramos) y tramo horizontal colgado del techo
    g, rails = tr['profile_m'], []
    for gx in (x0 - g, x1):
        steps = [path_point(lift, s) for s in
                 [0, tr['z_curve']] + [tr['z_curve'] + math.pi * tr['radius_m'] / 2 * i / 6 for i in range(1, 7)]
                 + [tr['z_curve'] + math.pi * tr['radius_m'] / 2 + tr['length_m']]]
        for (ya, za), (yb, zb) in zip(steps, steps[1:]):
            yc, zc, length = (ya + yb) / 2, (za + zb) / 2, math.hypot(yb - ya, zb - za)
            vertical = abs(zb - za) >= abs(yb - ya)
            size = (g, g, length + g) if vertical else (g, length + g, g)
            rails.append(_box((gx + g / 2, yc + sign * g / 2, zc), size))
    # motor de techo: riel al centro, de la cabeza del portón al motor, y la caja del motor colgada al fondo
    xm, (mw, md, mh), rail_z = (x0 + x1) / 2, op['motor_m'], tr['z_curve'] + tr['radius_m'] + 0.05
    y_head, y_motor = y0 + sign * 0.15, op['motor_y']
    operator = [_box((xm, (y_head + y_motor) / 2, rail_z + 0.02), (0.04, abs(y_motor - y_head), 0.04)),
                _box((xm, y_motor + sign * md / 2, rail_z), (mw, md, mh))]
    photocells = [_box((px, y0 + sign * 0.06, op['photocell_z']), (0.04, 0.05, 0.08)) for px in (x0 + 0.03, x1 - 0.03)]
    parts += [{'id': f'guias-{door_id}', 'material': tr['material'], 'mesh': merge(rails), 'moves': False},
              {'id': f'operador-{door_id}', 'material': op['material'], 'mesh': merge(operator + photocells), 'moves': False}]
    return parts
