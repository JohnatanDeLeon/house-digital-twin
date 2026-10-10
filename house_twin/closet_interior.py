"""Interior de un closet con puertas: torres de repisas y cajones, colgadores y lo que hay guardado, en el marco del
frente del closet (`u` a lo ancho desde la izquierda vista desde el cuarto, `z` arriba, `n` hacia el cuarto: el
interior queda en n < 0). Se describe en el `interior` de `sources/muebles/<closet>.json`. Solo biblioteca estándar.
"""
import math

from house_twin.furniture import front_frame
from house_twin.hardware import cylinder, merge, oriented_box


class _Frame:
    def __init__(self, fixture):
        self.origin, self.along, self.normal = front_frame(fixture)

    def box(self, u, z, n):
        return oriented_box(self.origin, self.along, self.normal, tuple(u), tuple(z), tuple(sorted(n)))

    def point(self, u, z, n):
        (ox, oy, _), (ax, ay), (nx, ny) = self.origin, self.along, self.normal
        return (ox + u * ax + n * nx, oy + u * ay + n * ny, z)

    def cyl(self, a, b, r, seg=14):
        return cylinder(self.point(*a), self.point(*b), r, seg)


class _Bag:
    """Junta mallas por material."""

    def __init__(self):
        self.by_material = {}

    def add(self, material, mesh):
        self.by_material.setdefault(material, []).append(mesh)


def _tower(f, bag, t, wood, back):
    (u0, u1), (n0, n1), top, b = t['u'], t['n'], t['top_m'], 0.018
    bag.add(wood, f.box((u0, u0 + b), (0, top), (n0, n1)))
    bag.add(wood, f.box((u1 - b, u1), (0, top), (n0, n1)))
    bag.add(back, f.box((u0 + b, u1 - b), (0, top), (n0, n0 + 0.006)))           # fondo de triplay
    for z in t['shelves_m'] + [top - b]:
        bag.add(wood, f.box((u0 + b, u1 - b), (z, z + b), (n0, n1)))
    if 'cap_m' in t:  # remate de arriba
        bag.add(wood, f.box((u0, u1), (top, top + t['cap_m']), (n0, n1 + 0.01)))
    for k in range(t.get('drawers', 0)):  # cajones con su ranura para jalar
        d0, d1 = t['drawers_m']
        h = (d1 - d0) / t['drawers']
        z0, z1 = d0 + k * h + 0.004, d0 + (k + 1) * h - 0.004
        bag.add(wood, f.box((u0 + 0.004, u1 - 0.004), (z0, z1), (n1, n1 + 0.02)))
        bag.add(back, f.box(((u0 + u1) / 2 - 0.06, (u0 + u1) / 2 + 0.06), (z1 - 0.03, z1 - 0.018), (n1 + 0.019, n1 + 0.021)))


def _shoe(f, bag, u, z, n, sole, upper, length=0.28, width=0.1):
    """Zapato con la punta hacia el cuarto: suela, empeine y talón."""
    bag.add(sole, f.box((u - width / 2, u + width / 2), (z, z + 0.025), (n - length, n)))
    bag.add(upper, f.box((u - width / 2 + 0.008, u + width / 2 - 0.008), (z + 0.025, z + 0.06), (n - length + 0.02, n - 0.03)))
    bag.add(upper, f.box((u - width / 2 + 0.01, u + width / 2 - 0.01), (z + 0.06, z + 0.1), (n - length + 0.02, n - length + 0.1)))


def _garment(f, bag, u, rod_z, n_mid, length, thick, material, width=0.44):
    """Prenda en gancho: gancho delgado arriba y la prenda colgando, con los hombros un poco más angostos."""
    bag.add('cromo', f.cyl((u, rod_z - 0.005, n_mid), (u, rod_z + 0.045, n_mid), 0.002, 6))
    bag.add('plastico-negro', f.box((u - 0.004, u + 0.004), (rod_z - 0.06, rod_z - 0.05), (n_mid - width / 2, n_mid + width / 2)))
    bag.add(material, f.box((u - thick / 2, u + thick / 2), (rod_z - 0.06 - length, rod_z - 0.06), (n_mid - width / 2 + 0.01, n_mid + width / 2 - 0.01)))


def interior_parts(fixture: dict, spec: dict, height: float) -> list[dict]:
    it = spec['interior']
    f = _Frame(fixture)
    bag = _Bag()
    width, depth = fixture['width'], fixture['depth']
    leaf = spec['leaf_thickness_mm'] / 1000
    # cuerpo hueco: costados, piso del maletero, montantes al frente entre módulos, zoclo y la pintura del muro
    c = it['carcass']
    body = spec['materials']['body']
    bag.add(body, f.box((0, 0.018), (0, height), (-depth, -leaf)))
    bag.add(body, f.box((width - 0.018, width), (0, height), (-depth, -leaf)))
    bag.add(body, f.box((0.018, width - 0.018), (c['compartment_top_m'], height), (-depth, -leaf)))  # maletero, cerrado
    for u0, u1 in c['stiles_u']:
        bag.add(body, f.box((u0, u1), (c['plinth_m'], c['compartment_top_m']), (-0.07, -leaf)))
    bag.add('plastico-negro', f.box((0.018, width - 0.018), (0, c['plinth_m']), (-0.08, -leaf)))
    bag.add(c['wall_material'], f.box((0.018, width - 0.018), (c['plinth_m'], c['compartment_top_m']), (-depth, -depth + 0.002)))
    for t in it['towers']:
        _tower(f, bag, t, it['wood'], it['back'])
    # lo guardado en las torres
    for row in it.get('cans', []):
        n = row['n']
        for k, mat in enumerate(row['colors']):
            u = row['u0'] + k * 0.069
            bag.add(mat, f.cyl((u, row['z'], n), (u, row['z'] + 0.15, n), 0.033, 16))
            bag.add('cromo', f.cyl((u, row['z'] + 0.15, n), (u, row['z'] + 0.157, n), 0.029, 16))
    for b in it.get('books', []):
        u = b['u0']
        for thick, h, mat in b['items']:
            bag.add(mat, f.box((u, u + thick), (b['z'], b['z'] + h), (b['n'] - b['depth_m'], b['n'])))
            u += thick + 0.002
    for o in it.get('objects', []):
        (u0, u1), (z0, z1), (n0, n1) = o['u'], o['z'], o['n']
        if o.get('shape') == 'cylinder':
            bag.add(o['material'], f.cyl(((u0 + u1) / 2, z0, (n0 + n1) / 2), ((u0 + u1) / 2, z1, (n0 + n1) / 2), (u1 - u0) / 2, 20))
        else:
            bag.add(o['material'], f.box((u0, u1), (z0, z1), (n0, n1)))
        if o.get('disc'):  # cara redonda (la ventila de la consola)
            d = o['disc']
            bag.add(d['material'], f.cyl((d['u'], d['z'], n1), (d['u'], d['z'], n1 + 0.002), d['r'], 24))
    for s in it.get('shoes', []):
        for u in s['u']:
            for side in (-0.055, 0.055):
                _shoe(f, bag, u + side, s['z'], s['n'], s['sole'], s['upper'])
    # colgador
    h = it['hanging']
    (u0, u1), n_mid = h['u'], h['n']
    for rod in h['rods']:
        bag.add('cromo', f.cyl((u0, rod['z'], n_mid), (u1, rod['z'], n_mid), 0.0125, 14))
        bag.add('cromo', f.box((u0, u0 + 0.01), (rod['z'] - 0.03, rod['z'] + 0.03), (n_mid - 0.03, n_mid + 0.03)))
        bag.add('cromo', f.box((u1 - 0.01, u1), (rod['z'] - 0.03, rod['z'] + 0.03), (n_mid - 0.03, n_mid + 0.03)))
        u = u0 + 0.03
        k = 0
        while u < u1 - 0.03:
            length, thick, mat = rod['garments'][k % len(rod['garments'])]
            _garment(f, bag, u + thick / 2, rod['z'], n_mid, length, thick, mat, rod.get('width_m', 0.44))
            u += thick + rod.get('gap_m', 0.004)
            k += 1
    src = it['source']
    return [{'id': f"{fixture['id']}-interior-{mat}", 'ifc': 'IfcFurniture', 'type': 'USERDEFINED',
             'object_type': 'interior del closet', 'material': mat, 'mesh': merge(meshes), 'source': src}
            for mat, meshes in bag.by_material.items()]


def leaf_parts(fixture: dict, spec: dict, height: float) -> tuple[list[dict], list[dict]]:
    """Hojas de abajo de cada módulo como piezas sueltas (para abrirlas en el recorrido) y sus datos de giro."""
    from house_twin.furniture import module_fracs
    f = _Frame(fixture)
    width = fixture['width']
    gap, leaf = spec['gap_mm'] / 1000, spec['leaf_thickness_mm'] / 1000
    t0, t1 = spec['sections']['lower']
    z0, z1 = (1 - t1) * height + gap / 2, (1 - t0) * height - gap / 2
    hd = spec['handles']
    r, length, standoff = hd['diameter_mm'] / 2000, hd['length_mm'] / 1000, hd['standoff_mm'] / 1000
    hz = (1 - hd['center_from_top_frac']['lower']) * height
    parts, doors = [], []
    for i, (m0, m1) in enumerate(module_fracs(spec, width)):
        u0, u1 = m0 * width, m1 * width
        meeting = (u0 + u1) / 2
        did = f"{fixture['id']}-m{i + 1}"
        leaves = []
        for k, (a, b, hinge_u, side) in enumerate(((u0 + gap / 2, meeting - gap / 2, u0, -1), (meeting + gap / 2, u1 - gap / 2, u1, 1))):
            hu = meeting + side * hd['from_meeting_mm'] / 1000
            handle = [f.cyl((hu, hz - length / 2, standoff), (hu, hz + length / 2, standoff), r, 12)]
            handle += [f.cyl((hu, z, 0), (hu, z, standoff), r * 0.8, 10)
                       for z in (hz - length / 2 + hd['leg_inset_mm'] / 1000, hz + length / 2 - hd['leg_inset_mm'] / 1000)]
            parts.append({'id': f'{did}-hoja-{k}', 'ifc': 'IfcFurniture', 'type': 'USERDEFINED', 'object_type': 'puerta del closet',
                          'material': spec['materials']['leaves'], 'mesh': f.box((a, b), (z0, z1), (-leaf, 0)), 'source': spec['applies_to']['source']})
            parts.append({'id': f'{did}-hoja-{k}-jaladera', 'ifc': 'IfcDiscreteAccessory', 'type': None,
                          'material': hd['material'], 'mesh': merge(handle), 'source': spec['applies_to']['source']})
            hinge, latch = f.point(hinge_u, 0, -leaf / 2), f.point(meeting, 0, -leaf / 2)
            leaves.append({'hinge': [round(hinge[0], 4), round(hinge[1], 4)], 'latch': [round(latch[0], 4), round(latch[1], 4)],
                           'opens_toward': [round(v, 4) for v in fixture['faces_toward']], 'assumed': False})
        doors.append({'id': did, 'label': 'el closet', 'leaves': leaves})
    return parts, doors
