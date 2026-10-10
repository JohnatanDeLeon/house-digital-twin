"""Qué acabado lleva cada superficie del modelo, leído del `applies_to` de cada textura.

Solo usa la biblioteca estándar: también lo importa el script de Blender, que corre con el Python de Blender.

- Pisos: texturas con `surface: "piso"`, por espacio.
- Muros: texturas cuyo `surface` habla de muros. Cada cara de muro toma el acabado del espacio al que mira;
  si dos texturas reclaman el mismo espacio gana la más específica (la que lista menos espacios: el azulejo
  del baño sobre el yeso de todo el interior). La cara que mira a la calle toma la textura con `street_facade`.
- Vanos: texturas con `openings`; `part` distingue marco y vidrio de la hoja.
"""
import json
from pathlib import Path

PROBE_M = 0.05      # distancia a la que se mira, desde una cara, en qué espacio cae
JAMB_PROBE_M = 0.3  # una mocheta mira a lo largo del muro: se prueba a los lados para hallar su espacio
FLOOR_SURFACE = 'piso'
SHOWER_FLOOR_SURFACE = 'piso de la regadera'
CEILING_SURFACE = 'techo'
STREET = 'calle'
NEIGHBOUR = 'colindancia'


def load_materials(textures_dir: Path) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text()) for p in sorted(Path(textures_dir).glob('*/material.json'))}


def _inside(point, polygon) -> bool:
    x, y = point
    inside = False
    for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def _claims(materials, matches):
    return sorted(((len(m['applies_to']['spaces']), name, m['applies_to']['spaces'])
                   for name, m in materials.items() if matches(m['applies_to']) and m['applies_to'].get('spaces')),
                  reverse=True)


def _by_space(materials, matches) -> dict[str, str]:
    """Espacio → textura; si dos lo reclaman, gana la que lista menos espacios."""
    return {space: name for _, name, spaces in _claims(materials, matches) for space in spaces}


def _layers_by_space(materials, matches) -> dict[str, list[tuple[str, float, float | None, list | None]]]:
    """Espacio → [(textura, desde, hasta qué altura, zona)], de la más específica a la más general.

    Un lambrín (azulejo hasta 2.10 m) declara `up_to_m` por espacio: una altura, o [desde, hasta] para una franja
    (la cenefa). `region_m` limita la textura a una zona del espacio en planta (el azulejo solo en el nicho de la
    cocina). Donde una capa no aplica, sigue la siguiente; entre dos del mismo espacio gana la franja más angosta."""
    layers = {}
    for _, name, spaces in reversed(_claims(materials, matches)):
        a = materials[name]['applies_to']
        for space in spaces:
            band = a.get('up_to_m', {}).get(space)
            bottom, top = (band if isinstance(band, list) else (0.0, band)) if band is not None else (0.0, None)
            layers.setdefault(space, []).append((name, bottom, top, a.get('region_m', {}).get(space)))
    for space, items in layers.items():  # orden estable: más específica (menos espacios) primero; luego, la franja más angosta
        order = {name: i for i, (name, *_) in enumerate(items)}
        items.sort(key=lambda it: (order[it[0]] if it[3] is None else -1, (it[2] - it[1]) if it[2] is not None else float('inf')))
    return layers


class Finishes:
    def __init__(self, facts: dict, materials: dict[str, dict]):
        self.spaces = [(s['id'], s['polygon']) for s in facts['spaces']]
        self.exterior = {s['id'] for s in facts['spaces'] if s['is_exterior']} | {STREET}
        self.site = facts['site']['polygon']
        self.street_y = min(p[1] for p in self.site)  # el marco de los hechos pone la calle en Y < 0
        self.floors = _by_space(materials, lambda a: a.get('surface') == FLOOR_SURFACE)
        self.shower_floors = _by_space(materials, lambda a: a.get('surface') == SHOWER_FLOOR_SURFACE)
        self.walls = _by_space(materials, lambda a: 'muro' in a.get('surface', ''))
        self.wall_layers = _layers_by_space(materials, lambda a: 'muro' in a.get('surface', ''))
        self.ceilings = _by_space(materials, lambda a: a.get('surface') == CEILING_SURFACE)
        self.street = next((n for n, m in materials.items() if m['applies_to'].get('street_facade')), None)
        self.openings: dict[str, dict[str, str]] = {}
        self.viewpoints: dict[str, str] = {}
        for name, m in sorted(materials.items()):
            for oid in m['applies_to'].get('openings', []):
                if m['applies_to'].get('viewed_from'):
                    self.viewpoints[oid] = m['applies_to']['viewed_from']
                part = {'vidrio': 'glass', 'marcos y hojas': 'frame'}.get(m['applies_to'].get('part'), 'leaf')
                self.openings.setdefault(oid, {})[part] = name
                if part == 'leaf' and m.get('glass_material'):
                    self.openings[oid]['glass'] = m['glass_material']

    def space_at(self, point) -> str | None:
        """Id del espacio que contiene el punto, `calle`, `colindancia` o None (dentro de un muro)."""
        for sid, polygon in self.spaces:
            if _inside(point, polygon):
                return sid
        if _inside(point, self.site):
            return None
        return STREET if point[1] < self.street_y else NEIGHBOUR

    def wall_finish(self, where, z: float | None = None, point=None):
        """Acabado de muro del lugar; con `z` respeta los lambrines y franjas, y con `point` (en planta) las zonas."""
        if where == STREET:
            return self.street
        for name, bottom, top, region in self.wall_layers.get(where, []):
            if region is not None and (point is None or not _inside(point, region)):
                continue
            if z is None or ((top is None or z < top) and z >= bottom):
                return name
        return None

    def wall_split_heights(self) -> list[float]:
        """Alturas en las que cambia el acabado de algún muro: ahí se cortan las caras."""
        return sorted({h for layers in self.wall_layers.values() for _, bottom, top, _ in layers
                       for h in (bottom, top) if h})

    def floor(self, space_id: str) -> str | None:
        return self.floors.get(space_id)

    def shower_floor(self, space_id: str) -> str | None:
        return self.shower_floors.get(space_id)

    def ceiling(self, space_id: str) -> str | None:
        return self.ceilings.get(space_id)

    def wall_face(self, centre, normal, z: float | None = None) -> tuple[str | None, str | None]:
        """(acabado, lugar al que mira) de una cara vertical de muro: centro y normal en planta, y altura del centro."""
        nx, ny = normal
        where = self.space_at((centre[0] + nx * PROBE_M, centre[1] + ny * PROBE_M))
        if where is None:
            # mocheta de un vano o tope de muro: toma el acabado de un lado, prefiriendo el interior
            sides = [self.space_at((centre[0] + sx * JAMB_PROBE_M, centre[1] + sy * JAMB_PROBE_M))
                     for sx, sy in ((-ny, nx), (ny, -nx))]
            sides = [s for s in sides if s not in (None, NEIGHBOUR)]
            sides.sort(key=lambda s: s in self.exterior)
            where = sides[0] if sides else None
        return self.wall_finish(where, z, (centre[0] + nx * PROBE_M, centre[1] + ny * PROBE_M)), where

    def opening(self, opening_id: str) -> dict[str, str]:
        """Partes del vano → textura: `leaf` (hoja), `frame` (marco) y `glass` (vidrio)."""
        return dict(self.openings.get(opening_id, {}))

    def viewed_from(self, opening_id: str) -> str | None:
        """Espacio desde el que se fotografió la hoja: de ese lado la textura se ve sin espejar."""
        return self.viewpoints.get(opening_id)
