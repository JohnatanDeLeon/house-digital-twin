# Casa Jonhy: qué se puede extraer automáticamente del plano

Fuente analizada: [`sources/casa-jonhy-levantamiento.pdf`](../../sources/casa-jonhy-levantamiento.pdf) (el DWG todavía no está disponible en esta sesión).
Sistema de coordenadas: metros, con origen en la esquina del terreno del lado izquierdo de la calle.
X va a lo ancho (0 a 10 m) y Y hacia el fondo (0 = calle/ACCESO, 21.24 = fondo).

---

## 1. Hallazgo principal: el PDF no es una imagen, es CAD vectorial con sus capas

- Lo generó **AutoCAD 2022** (driver `pdfplot16`). Tiene 1 página de 11×17" (doble carta).
- Conserva **las 22 capas del DWG** como capas PDF (OCG). Cada línea se sabe a qué capa pertenece.
- Los textos son texto real (fuente subset con desplazamiento de 29), no curvas, así que se decodifican.

| Capa | Paths | Uso |
|---|---|---|
| `MUROS` | 95 | Caras de muro como líneas dobles. Esta es la base del modelo |
| `VANOS` | 92 | Líneas de cierre de vanos (puertas y ventanas) en ambas caras del muro |
| `VENTANAS` | 27 + 18 textos | Cristal (3 líneas) y rótulos `a=` / `h=` |
| `PUERTAS` | 427 | Hojas y abatimientos |
| `7-EJES` / `0 EJES` | 529 / 40 textos | Ejes A–I y 1–15 |
| `14-DIM INTERIOR` | 30 + 30 textos | Cotas: línea y valor |
| `12-TEXTOS` | 16 textos | Nombres de los espacios |
| `0 NIVELES` | 10 textos | NPT de cada espacio |
| `8-MUEBLES`, `9-MUEBLES FIJOS`, `2 AUTOS`, `501 ARBOL`, `11-VEGETACION`… | — | Mobiliario y ambientación. Se ignoran para el BIM |
| `logo`, `0 SELLO` | — | Cajetín. Se ignora |

**Conclusión:** el dibujo está **limpio y bien organizado por capas**. Es apto para reconstruir el BIM de forma automática.

## 2. Escala: el PDF NO está a 1:100 aunque el cajetín lo diga

Ajusté la escala por mínimos cuadrados con las 30 cotas (línea de cota contra su texto):

- **36.6355 pt/m, que equivale a 1:77.4 en el papel.** Se ploteó "ajustado a hoja".
  - Medir sobre el papel impreso suponiendo 1:100 da errores de cerca del 29 %.
- Las 28 cotas parciales cierran con un residuo de **0.7 cm o menos**, al nivel de la cuantización del PDF (unos 3 mm).
- Las dos cotas generales **no cierran tan bien**:
  - `10.00` mide **10.023 m** (+2.3 cm).
  - `21.25` mide **21.235 m** (−1.5 cm).
  - Puede ser texto sobrescrito en el DWG o un terreno ligeramente distinto. **El DWG lo resolverá.**
- La cadena de ejes no es paralela: los ejes superiores suman 9.85 m y los inferiores 9.79 m.
  - El eje I está en distinta X arriba que abajo, así que es dato a confirmar.

## 3. Hechos extraídos (geometría real)

### Muros (`MUROS`)

| Muro | Espesor |
|---|---|
| Barda perimetral oeste, norte y frente | 0.20 m |
| Barda perimetral este | 0.17 m |
| Muros interiores y fachadas | 0.17 m |
| Murete o división de la regadera del baño | 0.05 m |

- Hay un muro diagonal en el lado de la sala (jardinera).

### Espacios (flood-fill sobre muros y vanos cerrados; área libre entre caras interiores, ±0.05 m²)

| Espacio | Área libre | NPT | Observación |
|---|---|---|---|
| Recámara 1 (con closet) | 15.88 m² | +0.15 | |
| Recámara 2 (con closet) | 15.04 m² | +0.15 | |
| Recámara 3 (con closet) | 14.80 m² | +0.15 | |
| Sala + Comedor + Cocina + pasillo | 42.26 m² | +0.15 | **Espacio abierto: no hay muros entre ellos.** Habrá que partirlo con límites virtuales |
| Baño completo | 1.63 m² + regadera ≈ 1.1 m² | +0.15 | Un murete de 5 cm separa la regadera en otra región |
| ½ baño | 1.33 m² | ±0.00 | |
| Bodega | 1.90 m² | ±0.00 | |
| Exterior: cochera, acceso, lavandería y patio trasero | 90.3 m² | ±0.00 | Todo es un mismo espacio abierto. El patio trasero mide unos 4.3 m de fondo |
| Jardinera junto a la sala (triángulo) | — | | Encerrada, sin rótulo |

- **Suma de interiores habitables: unos 93 m² libres.**
- El desnivel de +0.15 entre el interior y la cochera/bodega/½ baño es dato del plano.

### Vanos

Detectados por capa `VANOS` y pares de jambas. El ancho es el del vano en muro.

| Vano | Tipo | Ancho |
|---|---|---|
| Acceso principal (sala ↔ exterior) | puerta | 1.00 m |
| Puerta peatonal en barda | puerta | 0.98 m |
| Recámara 1 | puerta | 0.89 m |
| Recámara 2 | puerta | 0.88 m |
| Recámara 3 | puerta | 0.86 m |
| Cocina ↔ lavandería | puerta | 0.83 m |
| Bodega | puerta | 0.835 m |
| Baño | puerta | 0.80 m |
| ½ baño | puerta | 0.78 m |
| Recámara 2 (fondo) | ventana | 1.50 m (a 0.86, h 1.22) |
| Recámara 1 (fondo) | 2 ventanas | 0.73 y 0.75 m (a 0.85, h 1.22) |
| Recámara 3 (a jardinera) | ventana | 1.24 m (a 0.86, h 1.26) |
| Sala (a cochera) | 2 ventanas | 0.74 y 0.75 m (a 0.85–0.865, h 1.26–1.27) |
| Cocina (a cochera) | 2 ventanas | 0.50 y 0.51 m (a 0.86–0.87, h 1.27) |
| Baño | ventana alta | 0.78 m (a 1.28, h 0.60) |

- **Interpretación a confirmar:** `a=` sería la altura de antepecho y `h=` la altura de la ventana.
  - La ventana del baño, con a=1.28 y h=0.60, es el patrón típico de una ventana alta, lo que apoya esta lectura.
- Algunos vanos (por ejemplo la puerta de la recámara 1) se detectan por `VANOS`, no por jambas.
  - El script de jambas todavía empareja mal un par de ventanas dobles. Se corrige con el DXF, donde puertas y ventanas suelen ser bloques.

Validación visual: [`01-overlay-extraccion-pdf.png`](01-overlay-extraccion-pdf.png) muestra lo extraído (muros, vanos, ventanas y espacios coloreados con su área), redibujado desde los datos en metros.

## 4. Lo que el plano NO contiene

Nada de esto se puede inventar, y es crítico para analizar una segunda planta:

- [NEEDS CLARIFICATION] Altura de piso a techo (entrepiso) y espesor y tipo de losa.
- [NEEDS CLARIFICATION] Estructura: castillos, columnas, trabes, cadenas. El levantamiento no los distingue de los muros, ni separa muros de carga de divisorios.
- [NEEDS CLARIFICATION] Altura de las puertas (el plano solo da el ancho).
- [NEEDS CLARIFICATION] Material de los muros (block, tabique…), cimentación y techo de la cochera (¿está techada?).
- [NEEDS CLARIFICATION] Orientación exacta. Hay una flecha de norte en el cajetín que se puede leer en la siguiente pasada.
- Instalaciones: no aparecen.

## 5. Ruta recomendada

**DWG/DXF → extracción por capas (Python) → `house.facts.json` canónico → IfcOpenShell genera IFC → Bonsai/Blender.**

- **Descartar DWG → IFC directo.** Los conversores generan geometría sin semántica: líneas, no `IfcWall`/`IfcSpace`/`IfcDoor` con relaciones. Es justo lo que no queremos.
- **El PDF ya permite el 90 % del trabajo.** Las capas están, la escala está calibrada y la precisión ronda ±0.5 cm. Se puede avanzar sin esperar el DWG.
- **El DWG/DXF sigue siendo la fuente primaria** porque aporta:
  - coordenadas exactas, sin cuantización;
  - puertas y ventanas como bloques con punto de inserción y rotación;
  - cotas como entidades con su medida real, lo que resuelve 10.00 contra 10.023;
  - capas congeladas o no ploteadas (posible estructura);
  - unidades declaradas.
- **Plan:** pasar el mismo extractor al DXF y diferenciar el resultado contra lo sacado del PDF. Si coinciden, el PDF queda como validación, tal como se decidió.

### Esquema BIM mínimo (IFC4)

- `IfcSite` (terreno con su polígono) → `IfcBuilding` → `IfcBuildingStorey` "Planta baja" (y "Planta alta" en las propuestas).
- `IfcWall`: eje, espesor y altura (pendiente), más la propiedad `LoadBearing` (pendiente: hoy es `unknown`, nunca se supone).
- `IfcOpeningElement` + `IfcDoor`/`IfcWindow`: ancho, antepecho, altura y muro anfitrión (`IfcRelVoidsElement` / `IfcRelFillsElement`).
- `IfcSpace`: polígono, área, NPT y nombre, más los límites virtuales del área social (`IfcVirtualElement`).
- Relaciones `IfcRelSpaceBoundary`, de las que se deriva el grafo de adyacencias y circulación (qué espacio conecta con cuál por qué puerta).
- Cada dato lleva `source` (pdf | dwg | usuario | propuesta) y `confidence`. Así se cumple "la IA propone, el modelo contiene la realidad".

### Arquitectura (prototipo)

```
house.facts.json  ──►  build_ifc.py (IfcOpenShell)  ──►  models/existing.ifc
                                                            │
                         House MCP (Python, FastMCP)  ◄─────┘
                         get_rooms / get_room / adjacency / area
                         find_stair_candidates / create_variant
                         (cada variante = copia IFC en models/proposal-NN.ifc)
                                │
                                └──► Blender + Bonsai (abre el IFC; render por script)
```

## 6. Siguientes pasos

1. ~~Repo propio~~: hecho (`house-digital-twin`).
2. **DXF exportado** del DWG (AutoCAD 2018 DXF, sin purgar), o el DWG para convertirlo con LibreDWG.
3. **Confirmar dependencias** a instalar: `ezdxf`, `shapely`, `ifcopenshell` (todas de pip).
4. **Aclarar los datos de la sección 4**, sobre todo altura de entrepiso y estructura.
5. Prototipo: `build_ifc.py`, un House MCP con `get_rooms`/`get_room`/`adjacency`, y abrir el IFC en Bonsai.
