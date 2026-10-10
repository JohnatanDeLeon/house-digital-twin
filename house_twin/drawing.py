"""Dibujo de planta normalizado: segmentos y textos en metros, agrupados por capa CAD.

Es el contrato entre las fuentes (PDF, DXF) y la construcción de hechos: cualquier
fuente que produzca un `Drawing` alimenta el mismo pipeline.
"""
from dataclasses import dataclass, field

Point = tuple[float, float]
Segment = tuple[Point, Point]

# Qué capa del levantamiento cumple cada rol. Si el DWG usa otros nombres, se ajusta aquí.
LAYER_ROLES = {
    'walls': ('MUROS',),
    'opening_faces': ('VANOS',),
    'glazing': ('VENTANAS',),
    'doors': ('PUERTAS',),
    'room_labels': ('12-TEXTOS',),
    'levels': ('0 NIVELES',),
    'window_labels': ('VENTANAS',),
    'dimensions': ('14-DIM INTERIOR', '23.-COTAS GENERALES'),
    'fixed_furniture': ('9-MUEBLES FIJOS',),  # frentes de closet
}


@dataclass(frozen=True)
class Text:
    layer: str
    value: str
    position: Point


@dataclass
class Drawing:
    source: str
    segments: dict[str, list[Segment]] = field(default_factory=dict)
    texts: list[Text] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def segments_for(self, role: str) -> list[Segment]:
        return [s for layer in LAYER_ROLES[role] for s in self.segments.get(layer, [])]

    def texts_for(self, role: str) -> list[Text]:
        layers = LAYER_ROLES[role]
        return [t for t in self.texts if t.layer in layers]
