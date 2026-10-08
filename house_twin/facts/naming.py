"""Nombres legibles de espacios a partir de los rótulos del plano (sin inventar usos)."""
from shapely.geometry import Point, Polygon

from house_twin.drawing import Text

PRETTY = {'RECAMARA': 'Recámara', 'BAÑO': 'Baño', 'LAVANDERIA': 'Lavandería', 'SALA': 'Sala',
          'COMEDOR': 'Comedor', 'COCINA': 'Cocina', 'COCHERA': 'Cochera', 'BODEGA': 'Bodega',
          'CLOSET': 'Closet', 'ACCESO': 'Acceso'}
SECONDARY = {'CLOSET'}
STACKED_LINE_GAP = 0.5  # m: rótulos apilados así de cerca son una sola frase ("1/2" + "BAÑO")


def _pretty(label: str) -> str:
    return ' '.join(PRETTY.get(word, word) for word in label.split())


def labels_inside(poly: Polygon, texts: list[Text]) -> list[Text]:
    inside = [t for t in texts if poly.contains(Point(t.position))]
    return sorted(inside, key=lambda t: (-t.position[1], t.position[0]))


def _phrases(labels: list[Text]) -> list[str]:
    phrases, previous = [], None
    for t in labels:
        is_stacked = previous and abs(previous.position[1] - t.position[1]) < STACKED_LINE_GAP \
            and abs(previous.position[0] - t.position[0]) < STACKED_LINE_GAP
        if is_stacked:
            phrases[-1] = f'{phrases[-1]} {t.value}'
        else:
            phrases.append(t.value)
        previous = t
    return phrases


def space_name(labels: list[Text]) -> tuple[str | None, list[str]]:
    """Devuelve (nombre, elementos secundarios como closet)."""
    phrases = _phrases(labels)
    main = [p for p in phrases if p not in SECONDARY] or phrases
    secondary = [_pretty(p) for p in phrases if p in SECONDARY and p not in main]
    return (' + '.join(_pretty(p) for p in main) or None), secondary
