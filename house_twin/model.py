"""Consultas semánticas sobre `house.facts.json`. Es la API que expone el House MCP.

Todo lo que devuelve sale de los hechos; no calcula nada que el plano no respalde.
"""
import json
import unicodedata
from collections import deque
from pathlib import Path


def _normalize(text: str) -> str:
    plain = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return ' '.join(plain.lower().split())


class RoomNotFound(LookupError):
    pass


class HouseModel:
    def __init__(self, facts: dict):
        self.facts = facts
        self._spaces = {s['id']: s for s in facts['spaces']}
        self._walls = {w['id']: w for w in facts['walls']}
        self._openings = {o['id']: o for o in facts['openings']}

    @classmethod
    def from_file(cls, path: str | Path) -> 'HouseModel':
        return cls(json.loads(Path(path).read_text()))

    def _display(self, space) -> str:
        return space['name'] or f"{space['id']} (sin rótulo)"

    def find_room(self, query: str) -> dict:
        """Busca por id (S02), por nombre o por cualquier rótulo, sin importar acentos ni mayúsculas."""
        q = _normalize(query)
        if query.upper() in self._spaces:
            return self._spaces[query.upper()]
        exact = [s for s in self._spaces.values() if s['name'] and _normalize(s['name']) == q]
        partial = [s for s in self._spaces.values()
                   if any(q in _normalize(text) for text in [s['name'] or ''] + s['labels'] + s['contains'])]
        matches = exact or partial
        if len(matches) != 1:
            options = ', '.join(f"{s['id']} {self._display(s)}" for s in matches) or 'ninguno'
            raise RoomNotFound(f'"{query}" coincide con: {options}')
        return matches[0]

    def summary(self) -> dict:
        interior = [s for s in self._spaces.values() if not s['is_exterior']]
        return {
            'name': self.facts['name'], 'site': {k: self.facts['site'][k] for k in ('width', 'depth', 'area')},
            'interior_free_area': round(sum(s['area'] for s in interior), 2),
            'rooms': len(interior), 'walls': len(self._walls),
            'doors': sum(o['kind'] == 'door' for o in self._openings.values()),
            'windows': sum(o['kind'] == 'window' for o in self._openings.values()),
            'unknowns': len(self.facts['unknowns']), 'provenance': self.facts['provenance'],
        }

    def list_rooms(self) -> list[dict]:
        return [{'id': s['id'], 'name': self._display(s), 'area': s['area'], 'is_exterior': s['is_exterior'],
                 'floor_level': s['floor_level']['value']} for s in self._spaces.values()]

    def room_openings(self, room_id: str) -> list[dict]:
        return [{'id': o['id'], 'kind': o['kind'], 'width': o['width'],
                 'to': [self._display(self._spaces[c]) for c in o['connects'] if c != room_id] or ['calle/exterior del lote']}
                for o in self._openings.values() if room_id in o['connects']]

    def get_room(self, query: str) -> dict:
        s = self.find_room(query)
        x0, y0, x1, y1 = s['bbox']
        return {**{k: s[k] for k in ('id', 'labels', 'contains', 'drawn_contents', 'is_exterior', 'area', 'perimeter', 'polygon', 'floor_level')},
                'name': self._display(s), 'bbox_size': [round(x1 - x0, 2), round(y1 - y0, 2)],
                'openings': self.room_openings(s['id']), 'neighbors': self.adjacent_rooms(s['id'])}

    def adjacent_rooms(self, query: str) -> list[dict]:
        room_id = self.find_room(query)['id']
        result = []
        for a in self.facts['adjacency']:
            if room_id not in a['spaces']:
                continue
            other = self._spaces[next(x for x in a['spaces'] if x != room_id)]
            via = 'puerta' if a['doors'] else 'ventana' if a['windows'] else 'solo muro'
            result.append({'id': other['id'], 'name': self._display(other), 'connection': via,
                           'doors': a['doors'], 'windows': a['windows'], 'walls': a['walls']})
        return result

    def area(self, query: str) -> dict:
        s = self.find_room(query)
        return {'id': s['id'], 'name': self._display(s), 'area_m2': s['area'], 'perimeter_m': s['perimeter'],
                'note': 'área libre entre caras interiores de muro'}

    def get_wall(self, wall_id: str) -> dict:
        w = self._walls[wall_id.upper()]
        between = [self._display(self._spaces[x]) for a in self.facts['adjacency'] if w['id'] in a['walls'] for x in a['spaces']]
        hosted = [o['id'] for o in self._openings.values() if o['host_wall'] == w['id']]
        return {**w, 'separates': sorted(set(between)), 'hosts_openings': hosted}

    def walk_path(self, start: str, end: str) -> dict:
        """Recorrido por puertas (BFS) entre dos espacios: la base del análisis de circulación."""
        a, b = self.find_room(start)['id'], self.find_room(end)['id']
        graph: dict[str, list[tuple[str, str]]] = {}
        for o in self._openings.values():
            if o['kind'] == 'door' and len(o['connects']) == 2:
                x, y = o['connects']
                graph.setdefault(x, []).append((y, o['id']))
                graph.setdefault(y, []).append((x, o['id']))
        previous = {a: None}
        queue = deque([a])
        while queue:
            node = queue.popleft()
            for nxt, door in graph.get(node, []):
                if nxt not in previous:
                    previous[nxt] = (node, door)
                    queue.append(nxt)
        if b not in previous:
            return {'reachable': False, 'from': a, 'to': b}
        steps, node = [], b
        while previous[node]:
            node_from, door = previous[node]
            steps.append({'from': self._display(self._spaces[node_from]), 'through': door, 'to': self._display(self._spaces[node])})
            node = node_from
        return {'reachable': True, 'doors_crossed': len(steps), 'steps': steps[::-1]}

    def unknowns(self) -> list[dict]:
        return self.facts['unknowns']
