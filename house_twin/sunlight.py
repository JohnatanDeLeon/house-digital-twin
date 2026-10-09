"""Orientación de la casa y sol de la vista previa, compartidos por la escena de Blender y el recorrido web.

Solo biblioteca estándar: también lo importa el Python de Blender.
"""
import math

# Orientación medida por el dueño con brújula: la fachada mira a 27° y el fondo (+Y), a 207°. No se sabe si es
# norte magnético o verdadero (en Saltillo difieren ≈ 4°); basta para la luz.
BACK_AZIMUTH_DEG = 207
SUN_AZIMUTH_DEG, SUN_ELEVATION_DEG = 150, 50  # media mañana de octubre en Saltillo, aproximado


def direction(azimuth_deg: float, elevation_deg: float = 0.0) -> tuple[float, float, float]:
    """Rumbo de brújula → vector del modelo (x a lo ancho, y al fondo, z arriba; +X a 90° a la derecha de +Y)."""
    a, e = math.radians(azimuth_deg - BACK_AZIMUTH_DEG), math.radians(elevation_deg)
    return (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))


def sun_direction() -> tuple[float, float, float]:
    """Dirección hacia el sol."""
    return direction(SUN_AZIMUTH_DEG, SUN_ELEVATION_DEG)
