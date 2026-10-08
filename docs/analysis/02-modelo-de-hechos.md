# Fase 2 — Modelo de hechos, IFC y House MCP

Fuente: [`sources/casa-jonhy-levantamiento.pdf`](../../sources/casa-jonhy-levantamiento.pdf) (el DXF todavía no está en el repo).
Generado con `python -m house_twin.cli build`. Las tablas salen de
[`data/facts/existing.facts.json`](../../data/facts/existing.facts.json).

![Hechos de la planta existente](02-hechos-planta-existente.png)

La imagen se dibuja **solo desde el JSON de hechos**, no desde el PDF. Si coincide con el plano, los hechos están completos.

## Qué cambió respecto a la fase 1

| Aspecto | Fase 1 | Fase 2 |
|---|---|---|
| Espacios | raster de 2 cm con flood-fill | polígonos exactos (shapely) |
| Áreas | subestimadas ~0.2–1.6 m² por el grosor del raster | exactas entre caras de muro |
| Muros | líneas sueltas | **43 tramos rectos** con eje, largo, espesor, colindancia, exposición |
| Vanos | 10 por jambas, varios mal emparejados | **9 puertas + 9 ventanas** con muro anfitrión y espacios que conectan |
| Relaciones | ninguna | adyacencias (puerta / ventana / solo muro) y recorridos por puertas |

## Espacios

| Id | Espacio | Área libre (m²) | Perímetro (m) | NPT |
|---|---|---|---|---|
| S01 | Cocina + Sala + Comedor | 42.82 | 38.47 | 0.15 |
| S02 | Recámara 1 (con closet) | 16.12 | 17.35 | 0.15 |
| S03 | Recámara 2 (con closet) | 15.24 | 16.25 | 0.15 |
| S04 | Recámara 3 (con closet) | 14.99 | 16.80 | 0.15 |
| S05 | Bodega | 1.98 | 5.71 | 0.00 |
| S06 | Baño | 1.78 | 5.34 | — |
| S07 | 1/2 Baño | 1.46 | 4.84 | 0.00 |
| S08 | sin rótulo (regadera del baño, tras murete de 5 cm) | 1.16 | 4.36 | 0.15 |
| S09 | sin rótulo (jardinera; el plano dibuja un árbol) | 1.14 | 4.31 | — |
| S10 | exterior: cochera, acceso, lavandería y patio trasero | 92.65 | 80.26 | 0.00 |

- **Áreas interiores:**
  - Rotuladas: 94.39 m².
  - Contando S08 y S09: 96.69 m².
  - Si la jardinera S09 está a cielo abierto, no debería contarse. Es dato a confirmar.
- **Nivel de piso:** el baño S06 no tiene rótulo propio de NPT. Su rótulo `NPT+0.15` quedó dentro de la regadera, así que S06 queda como desconocido.
- **Nombres:** "Lavandería + Cochera" son solo los rótulos que caen dentro del exterior. El patio trasero no tiene rótulo.

## Vanos

| Id | Tipo | Ancho (m) | Antepecho / altura (m) | Muro | Conecta |
|---|---|---|---|---|---|
| D01 | puerta | 0.979 | — / ? | W03 | Exterior ↔ calle (puerta peatonal en barda) |
| D02 | puerta | 0.780 | — / ? | W06 | Zona social ↔ 1/2 Baño |
| D03 | puerta | 1.002 | — / ? | W07 | Zona social ↔ Exterior (acceso principal) |
| D04 | puerta | 0.832 | — / ? | W13 | Cocina ↔ Lavandería |
| D05 | puerta | 0.799 | — / ? | W19 | Zona social ↔ Baño |
| D06 | puerta | 0.878 | — / ? | W26 | Zona social ↔ Recámara 2 |
| D07 | puerta | 0.858 | — / ? | W08 | Zona social ↔ Recámara 3 |
| D08 | puerta | 0.894 | — / ? | W08 | Zona social ↔ Recámara 1 |
| D09 | puerta | 0.835 | — / ? | W24 | Bodega ↔ Exterior |
| V01 | ventana | 0.744 | 0.865 / 1.27 | W07 | Sala ↔ Cochera |
| V02 | ventana | 0.750 | 0.85 / 1.26 | W07 | Sala ↔ Cochera |
| V03 | ventana | 0.498 | 0.86 / 1.27 | W13 | Cocina ↔ Cochera |
| V04 | ventana | 0.511 | 0.87 / 1.27 | W23 | Cocina ↔ Cochera |
| V05 | ventana | 1.238 | 0.86 / 1.26 | W04 | Recámara 3 ↔ Jardinera |
| V06 | ventana | 0.734 | 0.85 / 1.22 | W10 | Recámara 1 ↔ Patio trasero |
| V07 | ventana | 0.750 | 0.855 / 1.23 | W10 | Recámara 1 ↔ Patio trasero |
| V08 | ventana | 1.500 | 0.86 / 1.22 | W09 | Recámara 2 ↔ Patio trasero |
| V09 | ventana | 0.780 | 1.28 / 0.60 | W15 | Regadera ↔ Lavandería (ventana alta) |

## Muros

- 43 tramos rectos, sin solapes entre sí, que cubren toda la masa de muro del plano (23.49 m²).
- Los encuentros (esquinas, T) quedan asignados al tramo más largo.
- 9 tramos están **sobre el lindero** (`on_property_line`) y 23 dan al exterior (`faces_exterior`).
- Espesores medidos: 0.05 (murete de la regadera), 0.17–0.19 (muros) y 0.20 (barda).
  - Hay un tramo de 0.265 m: la barda este junto al ½ baño y la bodega.
- Desconocido para todos: altura, si es de carga, material.

## IFC (`models/existing.ifc`)

- IFC4 sin errores de esquema (`ifcopenshell.validate`). La geometría 3D se genera completa, cortes de vano incluidos.
- Contenido:
  - `IfcSite → IfcBuilding → IfcBuildingStorey`;
  - 43 `IfcWall`;
  - 18 `IfcOpeningElement` que vacían su muro anfitrión, rellenos con 9 `IfcDoor` y 9 `IfcWindow`;
  - 10 `IfcSpace`.
- **Supuestos** (solo en el IFC, marcados en `HDT_Provenance`):
  - entrepiso 2.40 m;
  - puertas 2.10 m.
- Las ventanas usan el antepecho y la altura del plano.
- Sin probar todavía en Blender/Bonsai desde aquí. Validado solo con IfcOpenShell.

## House MCP

Servidor `house` (`python -m house_twin.mcp_server`, ya registrado en `.mcp.json`):

| Herramienta | Qué responde |
|---|---|
| `house_summary` | terreno, área interior, conteos, procedencia |
| `list_rooms` / `get_room` | espacios; detalle con polígono, vanos y vecinos |
| `get_adjacent_rooms` | vecinos y si se conectan por puerta, ventana o solo muro |
| `calculate_area` | área libre y perímetro |
| `get_wall` | eje, largo, espesor, colindancia, qué separa, qué vanos tiene |
| `walk_path` | recorrido por puertas entre dos espacios |
| `list_unknowns` | lo que el plano no dice y qué análisis bloquea |

Los nombres se buscan sin importar acentos ni mayúsculas: "recamara 1" funciona, y "sala" encuentra la zona social. Si la búsqueda es ambigua, responde con las opciones.

## Incógnitas que bloquean la segunda planta

Están en `unknowns` del JSON (U01–U08): entrepiso, losa, estructura y muros de carga, altura de puertas, materiales, techo de la cochera, la discrepancia de las cotas generales (10.023 contra 10.00) y la lectura de `a=`/`h=`.

## Pendiente para la fase 3

1. Subir el DXF a `sources/` y correr `inspect-dxf` y `compare`.
   - El adaptador ya está probado con un DXF sintético: en cm y en m, con y sin `$INSUNITS`, y con puertas como bloque.
2. Si el DXF trae capas que el PDF no imprimió (estructura), mapearlas en `LAYER_ROLES`.
