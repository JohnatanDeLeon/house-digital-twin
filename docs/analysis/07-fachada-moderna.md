# 07 — Remodelación: fachada moderna (propuesta)

Segunda remodelación del gemelo, independiente de la cocina. Es una **propuesta**: vive en `variants/fachada-moderna.json`
y no modifica los hechos ni `models/existing.*`. En el recorrido se elige «Propuesta: Fachada moderna» en el selector
«Versión» (o `#fachada-moderna` en la página), que arranca en la calle, de frente.

Pedido del dueño (2026-10-17): remodelar la fachada **sin reutilizar texturas existentes**: todas las de la propuesta
son nuevas.

## Lo que hay hoy (hechos)

| Elemento | Hoy |
|---|---|
| Frente | 10.03 m sobre la calle (y = 0): cochera abierta (x = 0.20–3.24), muro del pórtico W03 (3.24–8.56) y frente de la bodega (8.56–10.03). Muros de 2.60 m; la losa (2.60–2.70 m) deja su canto sin acabado a la vista. |
| Acabado | Estuco rugoso gris (`estuco-fachada`) en la cara de la calle y en el pórtico. |
| Vanos | Portón de 2 hojas de herrería con barrotes torcidos, aros y lámina abajo (D12, 3.04 × 2.23 m). Reja peatonal D01 (0.98 × 2.30 m). Aberturas del pórtico sin vidrio, con la misma herrería: V12 (1.50 × 1.30 m) y V11 (2.00 × 1.30 m), con pretil a 1.00 m. |
| Pórtico | Piso de concreto gris (`piso-exterior`). |

**Diagnóstico:**
- Es un plano gris continuo, sin jerarquía: la entrada no se distingue de las ventanas.
- La herrería ornamental (aros y barrotes torcidos) no tiene relación con nada más de la fachada.
- El canto de la losa queda sin rematar.
- La base del muro se ensucia con la lluvia y los golpes, y no tiene protección.

## La propuesta

**Regla de obra:** no se mueven muros ni vanos. Sobre la línea de la calle solo salen el gotero del remate (2 cm) y los
recubrimientos.
Es una remodelación de acabados y herrería: se puede hacer por etapas y sin permisos de obra mayor.

| Zona | Acabado nuevo | Por qué |
|---|---|---|
| Fachada y pórtico | **Aplanado fino blanco cálido** con pintura elastomérica (`aplanado-fino-blanco`) | Fondo limpio y luminoso. La pintura elastomérica sella las fisuras del estuco viejo. |
| Base, de 0 a 0.60 m | **Zócalo de porcelanato tipo piedra grafito** de 60 × 30 cm (`zoclo-porcelanato-grafito`) | Protege del salpicado de lluvia y de los golpes, y asienta visualmente la fachada. |
| Entrada (x = 4.92–6.39) | **Duela de WPC nogal** en tablas verticales de 15 cm (`duela-wpc-nogal`) | Marca la entrada con el único material cálido. El WPC (madera plástica) no se pudre ni pide barniz. |
| Volumen de la bodega (x = 8.39–10.03) | **Microcemento grafito** (`microcemento-grafito`) | Cierra la composición a la derecha y equilibra el portón oscuro de la izquierda. |
| Portón D12 y reja D01 | **Lamas horizontales de aluminio negro mate**, de 9 cm con 2 cm de ranura (`porton-duela-negra`, `reja-duela-negra`) | Privacidad, paso de aire y nada de mantenimiento. Portón y reja son de la misma familia. |
| Aberturas V11 y V12 | **Celosía de lamas verticales** de aluminio negro, de 4 cm con 3 cm de hueco (`celosia-v11`, `celosia-v12`) | El pórtico conserva luz y ventilación; de lado ya no se ve hacia dentro. |
| Borde de la azotea | **Remate de lámina negra mate** de 20 cm (`lamina-negra-mate`, pieza `fachada-remate`) | Cubre el canto de la losa y dibuja una línea superior limpia. |
| Piso del pórtico | **Porcelanato gris claro** de 60 × 60 cm, mate antiderrapante (`porcelanato-portico`) | Exterior cubierto: fácil de limpiar y no resbala mojado. |

**Composición:**
- **Tres franjas horizontales:** zócalo oscuro, muro blanco y remate negro.
- **Dos acentos verticales:** la madera de la entrada y el volumen grafito de la bodega.
- **Herrería unificada:** el negro de portón, reja y celosías repite el del remate.

## Cómo está modelada

- **Texturas:** todas nuevas y sintéticas, porque no hay foto de materiales propuestos. Salen de generadores procedurales en
  `house_twin/textures.py`:
  - `stucco` para el aplanado y el microcemento;
  - `slats`, nuevo, para la duela, las lamas y las celosías, con hueco de opacidad en las ranuras;
  - `subway_tile` con `bond: stack` para el zócalo y el piso.
- **Zonas de la cara de la calle:** cada material propio declara `variant_applies_to`, con `spaces: ["calle"]`, franja
  (`up_to_m`) y zona en planta (`region_m`). Solo la propuesta los toma; la casa actual sigue con su estuco.
  - `replaces` le quita el pórtico al estuco y al piso de concreto.
  - `finishes.wall_finish` ya admite zonas en la calle.
- **Variante:**
  - `own_model` le da su propio modelo 3D, porque cambia acabados de muros que no se pueden cambiar sobre el modelo de la casa.
  - `changes` cambia las hojas de D12, D01, V11 y V12.
  - `specs.extras` agrega el remate (`house_twin/extras.py`).
  - `focus` la hace arrancar en la calle.

## Pendientes y límites

- Colores, piezas y medidas son comerciales y no están medidos: conviene ver muestras físicas a la luz de la calle.
- **Sin modelar:**
  - la iluminación de la fachada (arbotantes junto a la entrada) y el número de la casa;
  - la jardinera y los motores del portón;
  - la cara del pretil de la cochera y la barda lateral.
- **Revisar antes de la obra:**
  - el estado del aplanado viejo bajo el estuco;
  - el reglamento municipal: la duela de WPC con su bastidor sale unos 4 cm de la línea de la calle (en el modelo
    no tiene espesor).
