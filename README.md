# house-digital-twin
Digital twin of a residential property, combining BIM/IFC, 3D modeling, spatial analysis, and AI agents through MCP to analyze, optimize, and simulate architectural layouts and remodeling proposals.

## Estado

| Fase | Estado |
|---|---|
| 1. Extracción de la planta desde el levantamiento (PDF vectorial) | ✅ [informe](docs/analysis/01-extraccion-pdf.md) |
| 2. Modelo de hechos → IFC → House MCP (solo lectura) | ✅ [informe](docs/analysis/02-modelo-de-hechos.md) |
| 3. Validación contra el DXF original; el DXF pasa a ser la fuente | ✅ [informe](docs/analysis/03-validacion-dxf.md) |
| 4. Fidelidad visual: Blender + Bonsai, materiales, texturas e iluminación | en curso: [acabados](docs/analysis/04-acabados.md) |
| Variantes y propuestas de remodelación (`create_variant`) | sin fecha |

## Cómo funciona

```
data/raw/plano.dxf (primaria) | sources/*.pdf (validación) ──► Drawing (metros, por capa CAD)
                              │
                              ▼
                 data/facts/existing.facts.json   ← fuente de verdad: hechos + incógnitas
                    │                    │
                    ▼                    ▼
        models/existing.ifc        House MCP (Claude)
        (Blender + Bonsai)         get_room, walk_path, …
```

La regla del modelo: **los hechos vienen del plano y declaran su fuente; lo que el plano no dice
queda en `null` y se lista en `unknowns`**. El IFC necesita alturas, así que usa supuestos
explícitos que quedan marcados en el Pset `HDT_Provenance` de cada elemento.

## Instalación

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip
```

## Uso

```bash
.venv/bin/python -m house_twin.cli build                              # DXF → hechos → IFC → imagen → visor
.venv/bin/python -m house_twin.cli build --source sources/casa-jonhy-levantamiento.pdf  # desde el PDF
.venv/bin/python -m house_twin.cli inspect-dxf data/raw/plano.dxf     # capas, entidades, bloques, unidades
.venv/bin/python -m house_twin.cli compare sources/casa-jonhy-levantamiento.pdf data/raw/plano.dxf
.venv/bin/python -m house_twin.cli texture sources/texturas/puerta-recamaras.json  # foto → texturas PBR
.venv/bin/python -m pytest
```

### Conectar Claude a la casa (MCP)

`.mcp.json` registra el servidor `house` para Claude Code al abrir el repo
(en Windows cambia `command` a `.venv\\Scripts\\python.exe`). Para Claude Desktop, agrega lo mismo
en su `claude_desktop_config.json` con rutas absolutas.

Herramientas: `house_summary`, `list_rooms`, `get_room`, `get_adjacent_rooms`, `calculate_area`,
`get_wall`, `walk_path`, `list_unknowns`.

### Ver el modelo en 3D

En el navegador (también en el celular): `docs/viewer/casa-jonhy-3d.html`, generado por `build`.
Gira con el dedo, toca un espacio para ver su ficha, cambia a vista en planta o corta los muros a 1 m.

En Blender:

Abre `models/existing.ifc` en Blender con el add-on [Bonsai](https://bonsaibim.org)
(*File → Open IFC Project*). Los espacios (`IfcSpace`) se pueden ocultar para ver muros y vanos.
Probado con Blender 5.2.2 LTS y Bonsai 0.9.0 (Bonsai 0.9 exige Blender 5.1 o más nuevo).
Después de un `build`, *File → Revert IFC Project* recarga el modelo. Los GlobalId son deterministas, así que
el mismo elemento conserva su GUID entre `build`s.

## Estructura

```
data/raw/plano.dxf    plano original (fuente primaria)
sources/              PDF del levantamiento (validación) y owner-annotations.json (hechos del dueño)
house_twin/
  drawing.py          contrato Drawing: segmentos y textos en metros por capa (LAYER_ROLES)
  sources/            adaptadores: pdf.py (+ pdf_content.py), dxf.py
  facts/              openings.py, faces.py, walls.py, naming.py, annotations.py, builder.py
  ifc_export.py       hechos → IFC4 (IfcOpenShell)
  model.py            consultas semánticas (HouseModel)
  mcp_server.py       House MCP
  render.py           imagen de validación
  viewer.py           visor 3D web (+ viewer_template.html, three.js)
  compare.py          hechos de dos fuentes lado a lado
  cli.py
data/facts/           existing.facts.json (generado, versionado)
models/               existing.ifc (generado, versionado)
docs/analysis/        informes
tests/
```
