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

`sources/` → `house_twin.sources.*` (Drawing en metros) → `house_twin.facts.builder` →
`data/facts/existing.facts.json` → `ifc_export` / `model` / `mcp_server`.

- `data/facts/*.json`, `models/*.ifc` y `docs/analysis/02-*.png` son **generados**: no editarlos a mano,
  regenerar con `python -m house_twin.cli build`.
- Si el CAD usa otros nombres de capa, se ajusta `LAYER_ROLES` en `house_twin/drawing.py`.
- El PDF está ploteado a 1:77.4 aunque el cajetín diga 1:100: la escala sale de las cotas, nunca del rótulo.

## Comandos

```bash
.venv/bin/python -m house_twin.cli build [--source sources/x.dxf]
.venv/bin/python -m house_twin.cli compare A B
.venv/bin/python -m house_twin.cli inspect-dxf sources/x.dxf
.venv/bin/python -m pytest
```

Commits: `type(scope): descripción en español` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
