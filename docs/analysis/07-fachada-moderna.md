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
| Reja D01 | **Lamas horizontales de aluminio negro mate**, de 9 cm con 2 cm de ranura (`reja-duela-negra`) | Privacidad, paso de aire y nada de mantenimiento; repite las ranuras del portón seccional. |
| Aberturas V11 y V12 | **Celosía de lamas verticales** de aluminio negro, de 4 cm con 3 cm de hueco (`celosia-v11`, `celosia-v12`) | El pórtico conserva luz y ventilación; de lado ya no se ve hacia dentro. |
| Borde de la azotea | **Remate de lámina negra mate** de 20 cm, de la barda al lindero (`lamina-negra-mate`, pieza `fachada-remate`) | Cubre el canto de la losa y el del techo nuevo de la cochera, y dibuja una línea superior continua. |
| Piso del pórtico | **Porcelanato gris claro** de 60 × 60 cm, mate antiderrapante (`porcelanato-portico`) | Exterior cubierto: fácil de limpiar y no resbala mojado. |

## Cochera techada y portón seccional eléctrico (dueño, 2026-10-17)

### Techo

- **Qué es:** techo ligero sobre toda la cochera (x = 0.20–3.12, y = 0–6.71), de multipanel aislado de 5 cm (lámina, poliuretano y lámina) sobre 3 vigas de acero negro de 10 × 15 cm. Las vigas se apoyan en la barda y en el muro de la casa (W14).
- **Altura y pendiente:** arriba queda a 2.64–2.70 m, a la par de la losa del pórtico, con 2 % de pendiente hacia la barda, donde va el canalón.
- **El cuidado que pide:** las ventanas de la cocina (V03 y V04) dan a la cochera y hoy reciben luz del cielo. Un techo opaco las dejaría a oscuras. Por eso los últimos 1.61 m (y = 5.10–6.71), frente a ellas, son de **policarbonato satinado**, que deja pasar luz difusa.
- **Frente:** sobre el portón, un dintel aplanado cierra el techo, y el remate negro corre de la barda al lindero.

### Portón

**Seccional eléctrico que abre hacia arriba.** Se descartó el basculante: al abrir gira y su canto inferior sale hacia la
calle, y aquí el portón está en la línea de la banqueta. El seccional sube vertical por guías y se acuesta bajo el techo,
así que no invade la banqueta y ocupa poco espacio.

- **Paneles:** 4, de acero relleno de poliuretano en negro mate, con ranuras horizontales cada 10 cm (`porton-seccional-negro`). Miden 2.92 × 0.57 m y suman 2.27 m, 4 cm más que el vano de 2.23 m. Van detrás del vano, en y = 0.14 m.
- **Guías:** suben hasta 2.28 m, giran con un radio de 12 cm y siguen horizontales a 2.40 m, bajo las vigas (2.44 m). Abierto, el portón deja libres los 2.23 m de alto y llega hasta y ≈ 2.3 m dentro de la cochera.
- **Mecanismo:** motor de techo con riel al centro (motor en y ≈ 2.75 m) y fotoceldas de seguridad a 15 cm del piso. El techo nuevo es lo que hace posible el seccional, porque sostiene las guías y el motor.
- **En el recorrido:** cada panel sigue la trayectoria de las guías: vertical, curva y horizontal.

### Iluminación (3000 K, luz cálida)

- **Arbotantes «up & down»:** 3 arbotantes cilíndricos negros a 1.95 m, de 800 lm cada uno. Dos van a los lados de la entrada, sobre la duela, y uno al centro del volumen grafito. Bañan el muro en dos haces, hacia arriba y hacia abajo, sin deslumbrar.
- **Línea de LED bajo el remate:** en perfil de aluminio, dibuja de noche el borde de la azotea.
- **Cochera:** 2 empotrados de LED de 7 W en el techo.

### Precauciones

- **Gases del motor:** con la cochera cerrada, los gases del coche pueden entrar a la cocina por V03 y V04. No hay que dejar el motor encendido con el portón cerrado. Además conviene una rejilla de ventilación alta en el dintel o dejar ventilada la unión del techo con la barda (no modelado).
- **La barda es de colindancia:** apoyar en ella las vigas pide revisar su estructura y, en su caso, el acuerdo con el vecino. La alternativa es poner postes de acero junto a la barda.
- **Instalación eléctrica:** el motor necesita un contacto dedicado en el techo, y los arbotantes, un circuito exterior con protección contra fugas.

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
  - `specs.extras` (`variants/fachada-moderna/piezas.json`, `house_twin/extras.py`) agrega el remate, el dintel, las vigas, el techo (`slabs`), las luminarias (`lights`: IfcLightFixture con su luz y un `-foco` que el recorrido enciende de noche) y la tira de LED (`strips`).
  - `geometry.update_openings` convierte D12 en seccional (`lift`, `house_twin/lift.py`).
  - `focus` la hace arrancar en la calle.

## Pendientes y límites

- Colores, piezas y medidas son comerciales y no están medidos: conviene ver muestras físicas a la luz de la calle.
- **Sin modelar:**
  - el número de la casa, la jardinera, el canalón y la rejilla de ventilación de la cochera;
  - la cara del pretil de la cochera y la barda lateral.
- **Revisar antes de la obra:**
  - el estado del aplanado viejo bajo el estuco;
  - el reglamento municipal: la duela de WPC con su bastidor sale unos 4 cm de la línea de la calle (en el modelo
    no tiene espesor).
