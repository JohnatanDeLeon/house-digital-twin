"""Oficina de la recámara 3 con el detalle de las fotos: escritorio en L con patas eléctricas, brazo triple con 2
monitores y charola de laptop, teclado con sus teclas, mouse y tapetes, impresora de tanques, dock, caminadora,
silla gamer y audífonos. Cada objeto se arma en su marco local (x a la derecha, y hacia el frente, z arriba) y se
coloca con un giro y una traslación (`place`). Solo biblioteca estándar.
"""
import math

from house_twin.hardware import _box, cylinder, lathe, merge


def place(mesh, at, facing, base_z=0.0, tilt_deg=0.0):
    """Mueve una malla local al mundo: el frente local (+y) mira hacia `facing`; `tilt_deg` la inclina hacia atrás
    sobre el eje x local antes de girarla. Las rotaciones conservan el sentido de las caras."""
    points, faces = mesh
    fx, fy = facing
    n = math.hypot(fx, fy)
    fx, fy = fx / n, fy / n
    a = math.radians(tilt_deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for x, y, z in points:
        y, z = y * ca - z * sa, y * sa + z * ca
        out.append((at[0] + x * fy + y * fx, at[1] - x * fx + y * fy, base_z + z))
    return out, faces


def box(x0, x1, y0, y1, z0, z1):
    return _box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0))


def prism(poly, z0, z1):
    """Prisma de un polígono convexo; las caras salen hacia afuera sin importar el sentido del polígono."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    if area < 0:
        poly = poly[::-1]
    n = len(poly)
    points = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return points, faces


def ellipsoid(rx, ry, rz, segments=20):
    """Medio elipsoide (domo) sobre z = 0, como el cuerpo de un mouse."""
    profile = [(0, 0)] + [(math.cos(t), math.sin(t)) for t in (0.0, 0.5, 0.9, 1.2, 1.45)] + [(0, 1)]
    points, faces = lathe([(r, z) for r, z in profile], segments)
    return [(x * rx, y * ry, z * rz) for x, y, z in points], faces


def part(pid, ifc, material, meshes, source, ptype='USERDEFINED', object_type=None, image_facing=None):
    """Pieza para el IFC. `image_facing` (vector en planta) marca una imagen (pantalla): su UV encuadra la foto en la
    cara que mira hacia allá, sin espejar."""
    out = {'id': pid, 'ifc': ifc, 'type': ptype, 'object_type': object_type, 'material': material,
           'mesh': merge(meshes) if isinstance(meshes, list) else meshes, 'source': source}
    if image_facing:
        out['image_facing'] = [round(v, 4) for v in image_facing]
    return out


# ---------- escritorio en L (marco del mundo: lado largo contra el muro oriente, lado corto contra el norte) ----------
def desk(d):
    (cx, cy), h, t = d['corner'], d['height_m'], d['top_m']
    L, D = d['main']['length_m'], d['main']['depth_m']
    R, W = d['return']['length_m'], d['return']['depth_m']
    r = d['fillet_m']
    top = [box(cx - D, cx, cy - L, cy, h - t, h), box(cx - R, cx - D, cy - W, cy, h - t, h)]
    px, py = cx - D, cy - W  # rincón interior de la L
    arc = [(px - r + r * math.cos(k * math.pi / 16), py - r + r * math.sin(k * math.pi / 16)) for k in range(9)]
    top += [prism([(px, py), a, b], h - t, h) for a, b in zip(arc, arc[1:])]  # curva del rincón
    frame = [box(cx - D / 2 - 0.025, cx - D / 2 + 0.025, cy - L + 0.1, cy - 0.12, h - t - 0.03, h - t)]  # viga
    frame.append(box(cx - R + 0.1, cx - D, cy - W / 2 - 0.02, cy - W / 2 + 0.02, h - t - 0.025, h - t))  # travesaño del lado corto
    for ly in d['legs_y']:
        lx = cx - D / 2
        frame += [box(lx - 0.045, lx + 0.045, ly - 0.03, ly + 0.03, 0.04, 0.42),          # tramo de abajo
                  box(lx - 0.037, lx + 0.037, ly - 0.024, ly + 0.024, 0.42, h - t - 0.03),  # tramo de arriba
                  box(lx - 0.29, lx + 0.29, ly - 0.03, ly + 0.03, 0.012, 0.045),            # pie en T
                  box(lx - 0.06, lx + 0.06, ly - 0.06, ly + 0.06, h - t - 0.035, h - t - 0.03)]  # placa
        frame += [cylinder((lx + s * 0.26, ly, 0.0), (lx + s * 0.26, ly, 0.012), 0.016, 10) for s in (-1, 1)]  # niveladores
    c = d['control']
    panel = box(cx - D - 0.004, cx - D + 0.05, c['y'] - 0.08, c['y'] + 0.08, h - t - 0.035, h - t)
    buttons = [box(cx - D - 0.008, cx - D - 0.003, c['y'] - 0.06 + k * 0.024, c['y'] - 0.045 + k * 0.024, h - t - 0.027, h - t - 0.012) for k in range(6)]
    hook = d['hook']
    hx, hy = hook['at']
    hook_m = [box(hx - 0.03, hx + 0.03, hy - 0.01, hy + 0.01, h - t - 0.05, h - t), box(hx - 0.01, hx + 0.01, hy - 0.06, hy - 0.01, h - t - 0.06, h - t - 0.04)]
    src = f"{d['size_source']}; {d['position_source']}; {d['assumptions']}"
    return [part(d['id'], 'IfcFurniture', d['top_material'], top, src, 'DESK'),
            part(f"{d['id']}-patas", 'IfcFurniture', d['frame_material'], frame + hook_m, src, 'DESK'),
            part(f"{d['id']}-control", 'IfcFurniture', 'plastico-negro-brillante', [panel] + buttons, src, 'DESK')]


def headphones(hp):
    """Diadema en arco y 2 almohadillas, colgados de un gancho (el arco en el plano del frente)."""
    r, n = hp['radius_m'], 10
    arc = [(r * math.cos(math.pi * k / n), 0.0, r * math.sin(math.pi * k / n)) for k in range(n + 1)]
    band = [cylinder(a, b, 0.009, 8) for a, b in zip(arc, arc[1:])]
    cups = [cylinder((s * (r + 0.005) - 0.018, 0, -0.03), (s * (r + 0.005) + 0.018, 0, -0.03), 0.045, 18) for s in (-1, 1)]
    cups += [cylinder((s * r, 0, -0.01), (s * r, 0, 0.0), 0.012, 8) for s in (-1, 1)]
    return place(merge(band + cups), hp['at'], hp['facing'], hp['z'] - r)


# ---------- monitores y charola ----------
def _monitor_local(w, hh):
    """Monitor en su marco: pantalla en +y; bisel delgado, barbilla abajo con el logotipo y cuerpo trasero."""
    bez, chin = 0.007, 0.018
    shell = [box(-w / 2 - bez, w / 2 + bez, -0.012, 0.0, -hh / 2 - chin, hh / 2 + bez),
             box(-0.16, 0.16, -0.045, -0.012, -0.12, 0.08),        # cuerpo trasero
             box(-0.05, 0.05, -0.055, -0.045, -0.05, 0.05)]        # placa VESA
    logo = box(-0.025, 0.025, 0.0, 0.001, -hh / 2 - chin * 0.62, -hh / 2 - chin * 0.38)
    screen = box(-w / 2, w / 2, 0.0, 0.0015, -hh / 2, hh / 2)
    return merge(shell), screen, logo


def monitors(mo, d):
    (px, py), h = mo['pole_at'], d['height_m']
    diag = mo['diagonal_in'] * 0.0254
    w, hh = diag * 16 / math.hypot(16, 9), diag * 9 / math.hypot(16, 9)
    face = mo['facing']
    arm = [cylinder((px, py, h), (px, py, h + mo['pole_height_m']), 0.018, 16),
           cylinder((px, py, h + mo['pole_height_m']), (px, py, h + mo['pole_height_m'] + 0.01), 0.022, 16),  # tapa
           box(px - 0.04, px + 0.07, py - 0.035, py + 0.035, h - 0.1, h - 0.07),   # abrazadera bajo la cubierta
           box(px + 0.045, px + 0.07, py - 0.035, py + 0.035, h - 0.1, h + 0.04),
           box(px - 0.05, px + 0.07, py - 0.04, py + 0.04, h, h + 0.02)]
    shells, screens, logos, faces = [], {}, [], {}
    for side, sid in ((1, 'izq'), (-1, 'der')):
        cy_ = py + side * (w / 2 + mo['gap_m'] / 2)
        toe = math.radians(mo['toe_in_deg'])
        f = (face[0] * math.cos(toe) - side * face[1] * 0, face[1] - side * math.sin(toe))
        at = (px + face[0] * mo['reach_m'], cy_)
        shell, screen, logo = _monitor_local(w, hh)
        z = mo['centre_z']
        shells.append(place(shell, at, f, z))
        screens[sid] = place(screen, at, f, z)
        faces[sid] = f
        logos.append(place(logo, at, f, z))
        cz = z - 0.0
        elbow = (px + face[0] * 0.03, py + side * 0.18, cz)
        arm += [cylinder((px, py, cz), elbow, 0.013, 10), cylinder(elbow, (at[0] - face[0] * 0.05, at[1], cz), 0.013, 10),
                cylinder((px, py, cz - 0.03), (px, py, cz + 0.03), 0.026, 14)]  # collar
    t = mo['tray']
    tx, ty = t['centre']
    tz = h + t['z_above_desk_m']
    arm += [cylinder((px, py, tz + 0.02), (tx + 0.08, ty, tz + 0.02), 0.012, 10),
            cylinder((px, py, tz - 0.01), (px, py, tz + 0.05), 0.024, 14)]
    tw, td = t['size_m']
    tray_local = merge([box(-tw / 2, tw / 2, -td / 2, td / 2, 0.0, 0.006),
                        box(-tw / 2, tw / 2, td / 2 - 0.008, td / 2, 0.0, 0.03)]  # tope de enfrente
                       + [box(-tw / 2 + 0.03 + k * 0.045, -tw / 2 + 0.05 + k * 0.045, -td / 2 + 0.02, td / 2 - 0.03, 0.006, 0.008) for k in range(8)])
    tray = place(tray_local, (tx, ty), face, tz, -t['tilt_deg'])
    lw, ld = t['laptop_m']
    base_local = box(-lw / 2, lw / 2, -ld / 2, ld / 2, 0.006, 0.022)
    deck_local = box(-lw / 2 + 0.02, lw / 2 - 0.02, -ld / 2 + 0.02, ld / 2 - 0.08, 0.022, 0.0235)
    lid_h = t['laptop_screen_m'][1] + 0.025
    lid_local = box(-lw / 2, lw / 2, -0.006, 0.0, 0.0, lid_h)
    scr_local = box(-t['laptop_screen_m'][0] / 2, t['laptop_screen_m'][0] / 2, 0.0, 0.0015, 0.012, 0.012 + t['laptop_screen_m'][1])
    back = (tx - face[0] * (ld / 2) * math.cos(math.radians(t['tilt_deg'])), ty)
    zb = tz + 0.022 + (ld / 2) * math.sin(math.radians(t['tilt_deg']))
    laptop = [place(base_local, (tx, ty), face, tz, -t['tilt_deg']), place(lid_local, back, face, zb, t['lid_open_deg'] - 90)]
    keys = place(deck_local, (tx, ty), face, tz, -t['tilt_deg'])
    lscreen = place(scr_local, back, face, zb, t['lid_open_deg'] - 90)
    src = mo['source']
    return [part(mo['id'], 'IfcAudioVisualAppliance', 'plastico-negro-brillante', shells + laptop, src, 'DISPLAY'),
            part(f"{mo['id']}-brazo", 'IfcFurniture', 'acero-negro-mate', arm + [tray], src, 'USERDEFINED', 'brazo para 2 monitores y laptop'),
            part(f"{mo['id']}-logos", 'IfcAudioVisualAppliance', 'plastico-blanco', logos, src, 'DISPLAY'),
            part(f"{mo['id']}-teclado-laptop", 'IfcAudioVisualAppliance', 'acero-negro-mate', keys, src, 'DISPLAY'),
            part(f"{mo['id']}-pantalla-izq", 'IfcAudioVisualAppliance', 'pantalla-monitor-izq', screens['izq'], src, 'DISPLAY', image_facing=faces['izq']),
            part(f"{mo['id']}-pantalla-der", 'IfcAudioVisualAppliance', 'pantalla-monitor-der', screens['der'], src, 'DISPLAY', image_facing=faces['der']),
            part(f"{mo['id']}-pantalla-laptop", 'IfcAudioVisualAppliance', 'pantalla-laptop', lscreen, src, 'DISPLAY', image_facing=face)]


# ---------- cosas sobre el escritorio ----------
def desktop(dt, h):
    k = dt['keyboard']
    kw, kd = k['size_m']
    body = box(-kw / 2, kw / 2, -kd / 2, kd / 2, 0.0, 0.022)
    keys, u, gap = [], 0.0185, 0.0025
    main_cols = 15
    for row in range(6):
        y = kd / 2 - 0.012 - row * (u + gap) - u / 2 - (0.006 if row else 0)
        n = main_cols if row < 5 else 8
        widths = [u] * n if row != 5 else [u * 1.25] * 3 + [u * 5.5] + [u * 1.25] * 4
        if row == 5:
            n = len(widths)
        x = -kw / 2 + 0.012
        for wk in widths[:n]:
            if x + wk > kw / 2 - 0.1:
                break
            keys.append(box(x, x + wk, y - u / 2, y + u / 2, 0.022, 0.031))
            x += wk + gap
        for c in range(4):  # teclado numérico
            xn = kw / 2 - 0.085 + c * (u + gap)
            keys.append(box(xn, xn + u, y - u / 2, y + u / 2, 0.022, 0.031))
    glow = box(-kw / 2 + 0.008, kw / 2 - 0.008, -kd / 2 + 0.008, kd / 2 - 0.008, 0.022, 0.024)
    face, at = k['facing'], k['at']
    m = dt['mouse']
    pad = dt['mouse_pad']
    mat = dt['desk_mat']
    src = dt['source']
    printer = _printer(dt['printer'], h)
    dock = dt['dock']
    dlx, dly = dock['at']
    laptop = dt['closed_laptop']
    parts = [
        part('r3-teclado', 'IfcFurniture', 'plastico-negro-brillante', [place(body, at, face, h)] + [place(q, at, face, h) for q in keys], src, 'USERDEFINED', 'teclado'),
        part('r3-teclado-luz', 'IfcFurniture', 'rgb-teclado', place(glow, at, face, h), src, 'USERDEFINED', 'retroiluminación del teclado'),
        part('r3-mouse', 'IfcFurniture', 'plastico-negro-brillante',
             [place(ellipsoid(0.033, 0.062, 0.038), m['at'], m['facing'], h + 0.003)], src, 'USERDEFINED', 'mouse'),
        part('r3-mouse-luz', 'IfcFurniture', 'rgb-teclado', place(box(-0.006, 0.006, 0.015, 0.03, 0.0, 0.041), m['at'], m['facing'], h + 0.003), src, 'USERDEFINED', 'logotipo del mouse'),
        part('r3-tapete-mouse', 'IfcFurniture', 'tapete-azul', place(box(-pad['size_m'][0] / 2, pad['size_m'][0] / 2, -pad['size_m'][1] / 2, pad['size_m'][1] / 2, 0, 0.003), pad['at'], face, h), src, 'USERDEFINED', 'tapete del mouse'),
        part('r3-tapete-teclado', 'IfcFurniture', 'tela-negra', place(box(-mat['size_m'][0] / 2, mat['size_m'][0] / 2, -mat['size_m'][1] / 2, mat['size_m'][1] / 2, 0, 0.004), mat['at'], face, h - 0.0005), src, 'USERDEFINED', 'tapete del teclado'),
        part('r3-dock', 'IfcFurniture', 'plastico-negro-brillante', place(box(-0.06, 0.06, -0.04, 0.04, 0, 0.035), (dlx, dly), dock['facing'], h), src, 'USERDEFINED', 'dock / mini PC'),
        part('r3-dock-led', 'IfcFurniture', 'led-azul', place(cylinder((0.025, 0.04, 0.0175), (0.025, 0.043, 0.0175), 0.008, 12), (dlx, dly), dock['facing'], h), src, 'USERDEFINED', 'LED del dock'),
        part('r3-laptop-cerrada', 'IfcFurniture', 'acero-negro-mate', place(box(-laptop['size_m'][0] / 2, laptop['size_m'][0] / 2, -laptop['size_m'][1] / 2, laptop['size_m'][1] / 2, 0, 0.017), laptop['at'], face, h), src, 'USERDEFINED', 'laptop cerrada'),
    ]
    return parts + printer


def _printer(p, h):
    """Impresora de tanques: cuerpo, tapa del escáner, soporte de papel atrás, ranura de salida y el bloque de
    tanques de tinta en la esquina de enfrente, con sus 4 colores."""
    w, d, ht = p['size_m']
    body = [box(-w / 2, w / 2 - 0.075, -d / 2, d / 2, 0.0, ht - 0.035), box(-w / 2, w / 2, -d / 2, d / 2 - 0.08, 0.0, ht - 0.035),
            box(-w / 2 + 0.005, w / 2 - 0.08, -d / 2 + 0.005, d / 2 - 0.005, ht - 0.035, ht),    # tapa del escáner
            box(w / 2 - 0.075, w / 2, -d / 2, d / 2 - 0.08, ht - 0.035, ht - 0.02)]
    support = place(box(-w / 2 + 0.06, w / 2 - 0.12, -0.003, 0.003, 0.0, 0.2), (0.0, -d / 2 + 0.03), (0, 1), ht - 0.04, 20)
    body.append(support)
    slot = box(-w / 2 + 0.06, w / 2 - 0.14, d / 2, d / 2 + 0.002, 0.03, 0.06)   # salida del papel
    buttons = [box(-w / 2 + 0.03 + k * 0.03, -w / 2 + 0.045 + k * 0.03, d / 2, d / 2 + 0.003, ht - 0.03, ht - 0.018) for k in range(4)]
    tank_block = box(w / 2 - 0.075, w / 2, d / 2 - 0.08, d / 2, 0.0, ht - 0.02)
    tanks = {}
    for k, mat in enumerate(('acero-negro-mate', 'tinta-cian', 'tinta-magenta', 'tinta-amarilla')):
        x0 = w / 2 - 0.07 + k * 0.017
        tanks[mat] = box(x0, x0 + 0.012, d / 2, d / 2 + 0.002, 0.03, ht - 0.05)
    at, face = p['at'], p['facing']
    src = p['source']
    out = [part('r3-impresora', 'IfcFurniture', 'plastico-negro-brillante', [place(m, at, face, h) for m in body + [tank_block] + buttons], src, 'USERDEFINED', 'impresora'),
           part('r3-impresora-salida', 'IfcFurniture', 'tela-negra', place(slot, at, face, h), src, 'USERDEFINED', 'salida de papel')]
    out += [part(f'r3-impresora-{mat}', 'IfcFurniture', mat, place(m, at, face, h), src, 'USERDEFINED', 'tanque de tinta') for mat, m in tanks.items()]
    return out


# ---------- caminadora ----------
def treadmill(t):
    L, W, H = t['size_m']
    hood = t['hood_m']
    deck = [box(-W / 2, W / 2, -L / 2, L / 2 - hood, 0.02, H - 0.015),
            box(-W / 2, W / 2, L / 2 - hood, L / 2, 0.02, H + 0.03)]                         # motor
    rails = [box(s * W / 2 - (0.05 if s > 0 else 0), s * W / 2 + (0.05 if s < 0 else 0), -L / 2, L / 2 - hood, H - 0.015, H) for s in (-1, 1)]
    belt = box(-W / 2 + 0.05, W / 2 - 0.05, -L / 2 + 0.03, L / 2 - hood, H - 0.02, H - 0.004)
    display = box(-0.09, 0.09, L / 2 - hood + 0.02, L / 2 - 0.03, H + 0.03, H + 0.034)
    wheels = [cylinder((s * (W / 2 - 0.04) - 0.012, y, 0.02), (s * (W / 2 - 0.04) + 0.012, y, 0.02), 0.02, 12)
              for s in (-1, 1) for y in (-L / 2 + 0.06, L / 2 - 0.06)]
    stripe = box(-W / 2 - 0.002, -W / 2, -L / 2 + 0.05, L / 2 - 0.05, 0.035, 0.045)        # franja verde del costado
    at, face, src = t['at'], t['facing'], t['source']
    return [part('r3-caminadora', 'IfcFurniture', 'acero-negro-mate', [place(m, at, face) for m in deck + rails + wheels], src, 'USERDEFINED', 'caminadora'),
            part('r3-caminadora-banda', 'IfcFurniture', 'tela-negra', [place(belt, at, face), place(display, at, face)], src, 'USERDEFINED', 'banda de la caminadora'),
            part('r3-caminadora-franja', 'IfcFurniture', 'verde-acento', place(stripe, at, face), src, 'USERDEFINED', 'franja verde')]


# ---------- silla gamer ----------
def chair(c):
    seat_z, sw, sd = c['seat_z_m'], c['seat_m'][0], c['seat_m'][1]
    base = []
    for k in range(5):  # estrella de 5 brazos con rodajas
        a = 2 * math.pi * k / 5 + math.pi / 2
        ex, ey = 0.32 * math.cos(a), 0.32 * math.sin(a)
        base.append(cylinder((0, 0, 0.1), (ex, ey, 0.075), 0.022, 8))
        base += [cylinder((ex - 0.02 * math.sin(a), ey + 0.02 * math.cos(a), 0.03), (ex + 0.02 * math.sin(a), ey - 0.02 * math.cos(a), 0.03), 0.03, 12),
                 cylinder((ex, ey, 0.06), (ex, ey, 0.075), 0.01, 6)]
    base += [cylinder((0, 0, 0.07), (0, 0, 0.12), 0.045, 16), cylinder((0, 0, 0.12), (0, 0, seat_z - 0.1), 0.028, 14),
             box(-0.12, 0.12, -0.12, 0.12, seat_z - 0.13, seat_z - 0.09)]                 # mecanismo
    cush = [box(-sw / 2 + 0.06, sw / 2 - 0.06, -sd / 2, sd / 2, seat_z - 0.09, seat_z),
            box(-sw / 2, -sw / 2 + 0.07, -sd / 2, sd / 2 - 0.03, seat_z - 0.09, seat_z + 0.045),   # alas del asiento
            box(sw / 2 - 0.07, sw / 2, -sd / 2, sd / 2 - 0.03, seat_z - 0.09, seat_z + 0.045),
            box(-sw / 2 + 0.06, sw / 2 - 0.06, sd / 2 - 0.05, sd / 2, seat_z - 0.09, seat_z + 0.02)]
    bh = c['back_h_m']
    back_local = [box(-0.25, 0.25, -0.05, 0.03, 0.0, bh),
                  box(-0.29, -0.2, -0.04, 0.08, 0.05, bh * 0.75), box(0.2, 0.29, -0.04, 0.08, 0.05, bh * 0.75),   # alas
                  box(-0.17, 0.17, -0.05, 0.03, bh, bh + 0.05),
                  box(-0.12, 0.12, 0.03, 0.09, bh - 0.2, bh - 0.06),                                                  # almohada
                  box(-0.17, 0.17, 0.03, 0.1, 0.12, 0.3)]                                                            # cojín lumbar
    back = [place(m, (0.0, -sd / 2 + 0.03), (0, 1), seat_z - 0.02, c['recline_deg']) for m in back_local]
    arms = []
    for s in (-1, 1):
        x = s * (sw / 2 + 0.05)
        arms += [box(x - 0.02, x + 0.02, -0.08, -0.04, seat_z - 0.1, seat_z + 0.2), box(x - 0.045, x + 0.045, -0.15, 0.13, seat_z + 0.2, seat_z + 0.24)]
    foot = [box(-0.2, 0.2, sd / 2 - 0.02, sd / 2 + 0.01, seat_z - 0.16, seat_z - 0.12)]                  # posapiés guardado
    logo = [place(cylinder((0, 0.03, bh - 0.12), (0, 0.032, bh - 0.12), 0.06, 20), (0.0, -sd / 2 + 0.03), (0, 1), seat_z - 0.02, c['recline_deg'])]
    at, face, src = c['at'], c['facing'], c['source']
    w = lambda ms: [place(m, at, face) for m in ms]
    return [part('r3-silla', 'IfcFurniture', 'vinil-negro', w(cush + back + arms), src, 'CHAIR'),
            part('r3-silla-base', 'IfcFurniture', 'acero-negro-mate', w(base + foot), src, 'CHAIR'),
            part('r3-silla-logo', 'IfcFurniture', 'plastico-blanco', w(logo), src, 'CHAIR')]


def office_parts(spec):
    d = spec['desk']
    parts = desk(d) + monitors(spec['monitors'], d) + desktop(spec['desktop'], d['height_m']) + treadmill(spec['treadmill']) + chair(spec['chair'])
    hp = spec.get('headphones')
    if hp:
        parts.append(part('r3-audifonos', 'IfcFurniture', 'plastico-negro-brillante', headphones(hp), hp['source'], 'USERDEFINED', 'audífonos'))
    return parts
