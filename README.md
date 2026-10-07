# house-digital-twin
Digital twin of a residential property, combining BIM/IFC, 3D modeling, spatial analysis, and AI agents through MCP to analyze, optimize, and simulate architectural layouts and remodeling proposals.

## Estado

Fase 1 — extracción de la planta existente desde el levantamiento (PDF vectorial de AutoCAD).
Informe: [`docs/analysis/01-extraccion-pdf.md`](docs/analysis/01-extraccion-pdf.md).

## Estructura

```
sources/              planos originales (fuente de verdad; el DWG va aquí cuando esté)
pipeline/pdf/         PDF → primitivas por capa → hechos en metros
  extract.py          primitivas vectoriales por capa (OCG) y textos
  calibrate.py        escala pt/m por mínimos cuadrados contra las cotas → frame.json
  openings.py         vanos (pares de jambas en MUROS + cristal de VENTANAS)
  rooms.py            espacios por flood-fill sobre muros + vanos cerrados
  overlay.py          imagen de validación en metros
  run.sh              corre todo
data/extracted/pdf/   resultados versionados (frame, vanos, espacios)
docs/analysis/        informes y validaciones
build/                intermedios regenerables (ignorado)
```

## Uso

```bash
pipeline/pdf/run.sh   # requiere python3 con pypdf, numpy y Pillow
```
