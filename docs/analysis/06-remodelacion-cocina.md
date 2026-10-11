# 06 — Remodelación: cocina en U y lavandería cerrada (propuesta)

Primera remodelación del gemelo. Es una **propuesta**: vive en `variants/cocina-en-u.json` y no modifica los hechos
ni `models/existing.*`. Se recorre en 3D eligiendo «Propuesta: Cocina en U y lavandería cerrada» en el selector
«Versión» del recorrido.

## Lo que pidió el dueño (2026-10-11)

- La puerta de la cocina que sale al pasillo de servicio (D04) debe conectar directo con la lavandería.
- La lavandería se cierra levantando el muro que le falta, y en ese muro nuevo va una puerta al pasillo de servicio.
- La cocineta se reubica, con criterio de arquitecto: no basta con quitarla porque estorba.

## Lo que dice el modelo de la casa

| Elemento | Hoy |
|---|---|
| D04 | Puerta de vidrio de 0.83 × 2.10 m en el muro W13, de la cocina al pasillo de servicio (1.0 m de ancho). |
| Lavandería (S13) | 1.6 × 2.4 m, sin techo y abierta del lado del pasillo. Muros: W15 (cocina), W19 (baño, con la ventana V09) y W25 (recámara 2). Dentro: lavadora y secadora contra W19, boiler y cilindro de gas en la esquina del fondo, repisa sobre W15. |
| Zona de cocina | 2.85 × 3.18 m (x = 1.375–4.225, y = 6.875–10.055), abierta al comedor y al pasillo de recámaras. |
| W15, fondo de la cocina | La barra completa: tarja, estufa, 2 muebles con cajón y 3 alacenas. Detrás están el gas y el agua del baño. |
| Muro de ventanas, hacia la cochera | V03 y V04, a cielo abierto y mirando al NNE: luz pareja, sin sol directo. Pretil a 0.86–0.87 m. |
| W13, hacia el pasillo de servicio | Refrigerador, mueble chico y D04. Sin ventanas: da a la barda. |

La puerta nueva hacia la lavandería solo cabe en el extremo de W15 junto al pasillo (x = 1.45–2.25). A partir de
x = 2.32 la tapa la lavadora del otro lado, y justo ahí están hoy la tarja y su mueble.

## Opciones de cocina que se descartaron

1. **Apretar todo en lo que queda de W15** (1.97 m): tarja junto a la estufa, sin cubierta para preparar y sin luz natural.
2. **El lado abierto hacia el pasillo de recámaras**, el ejemplo de mala decisión del dueño: le quita espacio a la sala y se cruza con el paso de la entrada a las recámaras.
3. **Una «paralela abierta»** (la primera propuesta): dejaba sin usar el muro del pasillo de servicio, que al tapiar D04 es el más largo de la cocina (3.18 m).

## La propuesta: cocina en U abierta hacia el comedor

| Muro | Qué va | Por qué |
|---|---|---|
| Ventanas | Esquinero · **tarja bajo V04** · remate junto al comedor | Luz natural y vista donde más se trabaja; la barra termina junto al comedor, para servir. |
| Pasillo de servicio (W13) | Barra · **estufa con campana** · barra | Extracción directa al exterior por W13; la estufa queda al centro de la U, con apoyo a los 2 lados y fuera del paso. |
| Fondo (W15) | Vestíbulo de la puerta D13 · **refrigerador** · barra | El refri queda a la entrada: se toma algo sin entrar a la zona de trabajo. El paso a la lavandería pasa por ahí, nunca por la estufa. |

### Triángulo de trabajo (tarja–estufa–refrigerador, de centro a centro)

| | Tarja–estufa | Estufa–refri | Refri–tarja | Total |
|---|---|---|---|---|
| Hoy | **0.86 m** (20 cm de cubierta entre los dos) | 2.17 m | 1.91 m | 4.94 m |
| Propuesta | 1.46 m | 2.09 m | 2.63 m | 6.18 m |

- La guía usual pide de 1.2 a 2.7 m por lado y de 4.0 a 7.9 m en total. Viene de los estudios de los años 40 y 50 del Small Homes Council de Illinois y hoy la usan guías como las de la NKBA.
- El lado tarja–estufa es el que más se recorre: lavar, llenar ollas, colar. Por eso debe ser cómodo y tener cubierta entre los dos puntos.
- El lado al refrigerador es el viaje menos frecuente (se sacan varias cosas de una vez), y por eso puede ser el lado largo.
- Pasillo entre las barras: 1.88 m. Paso al vestíbulo de la lavandería: 0.93 m.

### Muebles: los mismos, reacomodados, y 4 piezas nuevas

| Mueble actual | En la propuesta |
|---|---|
| Mueble de la tarja (1.065 m) | Muro de ventanas; la tarja queda centrada bajo V04 (x = 2.57). |
| Mueble chico junto al refri (0.60 m) | Esquinero bajo V03. |
| 2 muebles con cajón (0.49 y 0.515 m) | A los lados de la estufa, en W13. |
| Estufa | W13, con campana nueva (76 cm, a 0.70 m de la estufa, ducto por W13). |
| Refrigerador y su alacena | W15, a la entrada de la cocina. |
| Alacenas de 0.78 m | Una junto a la campana; la otra, recortada a 0.515 m, del otro lado. |
| Alacena de 0.60 m | Sobre la barra nueva de W15. |
| Murales de fruta | A los lados de la estufa. |
| **Nuevos** | Remate de 0.245 m junto al comedor, mueble con cajón de 0.605 m junto al refri, cubiertas y campana. |

La cubierta libre (sin tarja ni estufa) pasa de **1.50 m a 2.96 m**. El azulejo y la cenefa, que hoy cubren los 3 muros
del nicho de la barra, siguen a la cocina en sus 3 muros nuevos (`update_materials`).

### Ventanas V03 y V04

El pretil sube de 0.86–0.87 m a **0.95 m** con 8 a 9 cm de block y un remate impermeable. Así la ventana arranca justo
donde termina el salpicadero (cubierta a 0.90 m más 5 cm). El cerramiento no cambia (2.13–2.14 m) y se pierden solo
unos 9 cm de vidrio. Si las ventanas abren hacia adentro chocarían con la llave de la tarja; corredizas no.

### Lavandería

- **Muro nuevo W41:** 2.40 m de largo y 0.17 m de espesor, alineado con W13, así que el pasillo de servicio conserva su metro de ancho. Por dentro, la lavandería queda de 1.45 × 2.40 m.
- **D13 (cocina–lavandería):** de 0.80 m. Es la puerta de vidrio que era D04: da luz a la esquina más oscura de la cocina. Abre hacia la lavandería, lejos de la estufa.
- **D14 (lavandería–pasillo):** de 0.75 m, de lámina como la de la bodega. Abre hacia la lavandería porque el pasillo mide 1.0 m. Va en el extremo del boiler (y = 11.80–12.55 m), con la bisagra junto al muro de la recámara 2: su barrido libra la lavasecadora y el cilindro de gas.
- **Lavasecadora (dueño, 2026-10-11):** una Samsung de carga frontal de 686 × 984 × 796 mm sustituye a la lavadora de 2 tinas (95 cm) y a la secadora (75 cm).
  - **Dónde:** contra el muro del fondo, en y = 10.85–11.54 m, donde ya están el agua, el desagüe y los contactos. Queda 5 cm separada del muro para las mangueras y su frente llega a x = 1.97 m.
  - **Por qué ahí:** es el único tramo que libran las dos puertas. La hoja de D13 barre el muro del fondo hasta y ≈ 10.79 m. En su posición anterior, D14 golpeaba la puerta redonda de la máquina, y por eso se movió al otro extremo.
  - **Lo que se gana:** el muro del fondo pasa de 1.71 m ocupados a 0.69 m. Quedan libres la esquina bajo V09, junto a la cocina (unos 0.50 × 0.60 m), y unos 0.55 m entre la máquina y el boiler. Ahí cabría un lavadero chico o un mueble alto para detergentes (no están modelados).
  - **Pasillo frente a ella:** 0.60 m. Con la puerta abierta, la máquina ocupa más fondo (la ficha del modelo no lo da; en los combos Samsung de 27" es de 1.2 a 1.4 m), así que se carga desde un lado de la puerta.
  - **Lluvia:** la lavandería sigue sin techo, y una lavasecadora con electrónica no debe mojarse. Hace falta un tejadillo sobre la franja de la máquina, dejando abierto el rincón del boiler y el gas para que ventilen. También conviene un contacto con tierra y protección contra fugas (no modelados).
- **Repisa:** se recorta desde x = 2.30 m para no cruzar D13.
- **Techo:** se recomienda **dejarla sin techo**. Así siguen ventilando el boiler y el gas, la ventana del baño (V09) y la campana. Contra la lluvia basta un tejadillo sobre D13 (no está modelado).

### Instalaciones

- **Gas:** del cilindro de la lavandería a la estufa, por fuera, sobre W13.
- **Agua y drenaje:** hasta el muro de ventanas. **Falta saber por dónde sale el drenaje de la casa.**
- **Electricidad:** el apagador A02 sale de donde va la estufa y pasa al vestíbulo de la lavandería. El contacto C07 sale de detrás del refri y pasa sobre la barra nueva. Faltan contactos sobre la barra de ventanas y luz bajo las alacenas, que no están modelados.

## Cómo está modelada

- **`variants/cocina-en-u.json`, en `geometry`:**
  - tapia D04;
  - agrega W41, D13 y D14;
  - cambia el pretil de V03 y V04;
  - cierra S13;
  - mueve A02 y C07.
- **En `update_materials`:** mueve la zona del azulejo y la cenefa.
- **En `specs`:** usa su propia cocineta y su propia lavandería (`variants/cocina-en-u/`). En `changes` van los acabados de D13 y D14.
- **`build`** escribe los hechos propuestos (`data/facts/variants/cocina-en-u.facts.json`) y su IFC (`models/variants/cocina-en-u.ifc`).
- **`scene`** pasa la variante por Blender y el recorrido la carga con su propio modelo (`casa-cocina-en-u.js`).

## Pendientes y límites

- **Estructura:** no se sabe si W15 es de carga (U03). El hueco de D13 necesita dintel y revisión de un profesional. W41 necesita su cimiento.
- **Medidas:** la lavasecadora usa las de la ficha que dio el dueño; su color, su puerta y su tablero son supuestos. Las de la estufa, el refrigerador y los muebles son las del modelo (medidas comunes o estimadas de fotos): conviene medirlos antes de la obra.
- **Sin modelar:**
  - las chapas de D13 y D14;
  - el tejadillo sobre D13 y la lavasecadora;
  - el lavadero o mueble en el espacio que libera la lavasecadora;
  - los contactos nuevos;
  - la luz bajo las alacenas;
  - las tuberías.
- **Validación:** la propuesta no sustituye la validación estructural ni normativa de un profesional.
