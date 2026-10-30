# CLAUDE.md — house-digital-twin

Gemelo digital de una casa (Casa Jonhy). Código en inglés, comentarios y documentación en español.

## Regla central: hechos vs. supuestos vs. propuestas

- **Hecho**: dato que sale del plano o que el dueño confirmó. Lleva `source`. Lo que aporta el dueño
  se registra en `sources/owner-annotations.json` (entrada, editable a mano), nunca en los generados.
- **Desconocido**: el plano no lo dice → `value: null` y una entrada en `unknowns`. Nunca inventarlo.
- **Supuesto**: solo donde un formato lo exige (alturas para el IFC). Vive en `ASSUMED_DEFAULTS`
  de `ifc_export.py` y se marca en el Pset `HDT_Provenance`. Jamás se escribe de vuelta a los hechos.
- **Propuesta**: lo que diseña la IA. Va en archivos de variante, nunca modifica `existing.*`.
  `variants/<id>.json` con `changes` de acabado por vano (`opening`, `part`, `material`); el material de una
  propuesta no lista `openings` en su `applies_to` (usa `variant`), así la casa existente no lo toma. Una
  remodelación agrega `geometry` (`close_openings`, `add_walls`, `add_openings`, `update_openings`/`_spaces`/
  `_devices` por `id`), `update_materials` (zonas de acabado que se mueven) y `specs` propias en `variants/<id>/`
  (`kitchen`, `laundry`). `variants.variant_facts` arma los hechos propuestos sobre una copia: `build` los escribe
  en `data/facts/variants/<id>.facts.json` y el IFC en `models/variants/<id>.ifc`; `scene` le hace su propio modelo
  (`casa-<id>.js`) y el recorrido lo carga al elegirla en el selector «Versión» (`#<id>` en la página).
  Acabados propios de una propuesta: material con `applies_to.variant` y `variant_applies_to` (espacios o `calle`,
  `up_to_m`, `region_m`, `replaces`); la casa no los toma. `own_model` da modelo propio a una variante que solo cambia
  acabados; `specs.extras` agrega piezas sueltas (`house_twin/extras.py`). Puertas corredizas: `slide` en el vano
  (`house_twin/sliding.py`) en vez de `swing`.
- Las propuestas no sustituyen la validación estructural ni normativa de un profesional.

## Flujo

`data/raw/plano.dxf` (primaria; el PDF de `sources/` solo valida) → `house_twin.sources.*` (Drawing en metros) → `house_twin.facts.builder` →
`data/facts/existing.facts.json` → `ifc_export` / `model` / `mcp_server`.

- `data/facts/*.json`, `models/*.ifc`, `docs/analysis/02-*.png` y `docs/viewer/*.html` son **generados**: no editarlos a mano,
  regenerar con `python -m house_twin.cli build`. `docs/viewer/recorrido/` y `docs/analysis/05-renders/` salen de `scene`.
- `docs/` se publica en GitHub Pages (`.github/workflows/ci-cd.yml`, en cada push a `main` tras `pytest` y la revisión de
  que `build` no cambia nada más que fechas). `docs/index.html` es la portada, escrita a mano. `scene` no corre en el CI:
  el recorrido regenerado se sube al repo.
- Si el CAD usa otros nombres de capa, se ajusta `LAYER_ROLES` en `house_twin/drawing.py`.
- El PDF está ploteado a 1:77.4 aunque el cajetín diga 1:100: la escala sale de las cotas, nunca del rótulo.
- El DXF declara milímetros pero está en metros: `sources/dxf.py` valida unidades por plausibilidad.
- La cota del frente del DXF está forzada a "10.00" sobre 10.03 m reales del dibujo: no confiar en textos de cota.

## Texturas

- Fotos del dueño en `sources/fotos/` (fuera de git: privadas y pesadas). Cada textura se describe en
  `sources/texturas/<nombre>.json` (esquinas, tamaño, blanco de referencia, parches, relieve) con posiciones
  en fracciones de la superficie, y se genera en `assets/textures/<nombre>/` con
  `python -m house_twin.cli texture sources/texturas/<nombre>.json`. No editar los mapas a mano.
- Tamaños y blancos de referencia que no estén medidos van en `assumptions` y en `size_m.source`.
- Normal maps en convención OpenGL (la de Blender).
- Dónde va cada textura lo dice su `applies_to` (`spaces` + `surface`, `openings` + `part`, `street_facade`);
  `house_twin/finishes.py` lo resuelve (gana la textura que lista menos espacios) y lo usan el IFC (pisos como
  `IfcCovering` y materiales de vanos) y `blender_scene.py`. Una superficie sin acabado sale en gris violáceo (`sin-dato`).
- `finishes.py` solo usa la biblioteca estándar: lo importa también el Python de Blender.
- Herrajes (chapas) en `sources/herrajes/<nombre>.json`: perfil torneado, posición en fracciones de la hoja y material.
  `house_twin/hardware.py` (solo stdlib) arma la malla y `ifc_export` la guarda como `IfcDiscreteAccessory`, parte de
  su puerta. Necesitan el abatimiento (`swing`) que sale de los bloques `PUERTA` del DXF.
- Playeras nuevas: se hacen sobre el molde `playera-base` (`sources/texturas/playera-base.json`, la playera lisa) y
  solo cambia el estampado. Cada una es un JSON con `"template": "playera-base"` y un `design`:
  `"from": "product"` (imagen de la prenda de frente; el estampado se recorta y se coloca solo) o `"from": "art"`
  (solo el dibujo: mejor PNG con transparencia; sin ella se quita el color de las orillas, así que el dibujo no debe
  usar ese color; se coloca con `width_m`, `top_m` bajo el punto más alto y `offset_x_m`). Si el estampado es más
  oscuro que la tela o de otro color, se detecta con `"detect": "contrast"`. Una tela de otro color tiñe el molde
  (`"fabric": "from_image"` o `fabric_srgb`) y saca su propia espalda; si no, la espalda es `playera-base-colgada`. Se generan con `texture`, el molde primero, y se cuelgan agregándolas al `display` del closet.
  Lo hace `house_twin/garment_designs.py`; la versión colgada, `house_twin/hanging.py`.
- Closets: el plano da dónde (`fixtures` de los hechos); `sources/muebles/<nombre>.json` da su frente (módulos,
  hojas, jaladeras) en fracciones medidas en una foto. `house_twin/furniture.py` arma la malla e `ifc_export` la
  guarda como `IfcFurniture` con sus jaladeras. Sin especificación del frente, el closet no se modela.

## Comandos

```bash
.venv/bin/python -m house_twin.cli build [--source sources/casa-jonhy-levantamiento.pdf]
.venv/bin/python -m house_twin.cli compare A B
.venv/bin/python -m house_twin.cli inspect-dxf data/raw/plano.dxf
.venv/bin/python -m house_twin.cli texture sources/texturas/puerta-recamaras.json
.venv/bin/python -m house_twin.cli hang sources/texturas/playera-venom.json   # solo la prenda colgada, desde sus mapas extendidos
.venv/bin/python -m house_twin.cli scene [--render]   # necesita `blender` con Bonsai en el PATH
.venv/bin/python -m house_twin.cli cameras [--search]   # plan de cámaras exteriores: cobertura, puntos ciegos y las figuras 08-*
.venv/bin/python -m pytest
```

Commits: `type(scope): descripción en español` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
