# CLAUDE.md — house-digital-twin

Gemelo digital de una casa (Casa Jonhy). Código en inglés, comentarios y documentación en español.

## Regla central: hechos vs. supuestos vs. propuestas

- **Hecho**: dato que sale del plano o que el dueño confirmó. Lleva `source`. Lo que aporta el dueño
  se registra en `sources/owner-annotations.json` (entrada, editable a mano), nunca en los generados.
- **Desconocido**: el plano no lo dice → `value: null` y una entrada en `unknowns`. Nunca inventarlo.
- **Supuesto**: solo donde un formato lo exige (alturas para el IFC). Vive en `ASSUMED_DEFAULTS`
  de `ifc_export.py` y se marca en el Pset `HDT_Provenance`. Jamás se escribe de vuelta a los hechos.
- **Propuesta**: lo que diseña la IA. Va en archivos de variante, nunca modifica `existing.*`.
- Las propuestas no sustituyen la validación estructural ni normativa de un profesional.

## Flujo

`data/raw/plano.dxf` (primaria; el PDF de `sources/` solo valida) → `house_twin.sources.*` (Drawing en metros) → `house_twin.facts.builder` →
`data/facts/existing.facts.json` → `ifc_export` / `model` / `mcp_server`.

- `data/facts/*.json`, `models/*.ifc`, `docs/analysis/02-*.png` y `docs/viewer/*.html` son **generados**: no editarlos a mano,
  regenerar con `python -m house_twin.cli build`.
- Si el CAD usa otros nombres de capa, se ajusta `LAYER_ROLES` en `house_twin/drawing.py`.
- El PDF está ploteado a 1:77.4 aunque el cajetín diga 1:100: la escala sale de las cotas, nunca del rótulo.
- El DXF declara milímetros pero está en metros: `sources/dxf.py` valida unidades por plausibilidad.
- La cota del frente del DXF está forzada a "10.00" sobre 10.03 m reales del dibujo: no confiar en textos de cota.

## Comandos

```bash
.venv/bin/python -m house_twin.cli build [--source sources/casa-jonhy-levantamiento.pdf]
.venv/bin/python -m house_twin.cli compare A B
.venv/bin/python -m house_twin.cli inspect-dxf data/raw/plano.dxf
.venv/bin/python -m pytest
```

Commits: `type(scope): descripción en español` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
