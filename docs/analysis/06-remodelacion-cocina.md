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
- **D14 (lavandería–pasillo):** vano de 0.75 × 2.10 m en el extremo del boiler (y = 11.80–12.55 m), con una **puerta corrediza de cristal templado esmerilado** (dueño, 2026-10-17).
  - **La hoja:** cristal de 10 mm de 85 × 214 cm, que traslapa 5 cm por lado sobre el vano, como piden los fabricantes de puertas tipo granero.
  - **El riel:** aparente, de acero negro mate, del lado del pasillo de servicio y a 4.5 cm del muro, con carretillas y jaladera tubular. Por dentro, la hoja lleva una cazoleta plana.
  - **Hacia dónde corre:** hacia la cocina, sobre el tramo libre de W41 (y = 10.90–11.75 m).
  - **Por qué del lado del pasillo:** del lado de la lavandería, la hoja le quitaría 5 cm al paso de 0.60 m frente a la lavasecadora. Por fuera, la lavandería ya no pierde el barrido de una hoja abatible y el pasillo conserva 0.90 m libres. El cristal esmerilado deja pasar luz sin que se vea hacia dentro.
  - **Ojo:** queda a la intemperie. Herrajes para exterior o inoxidables, y un tope de piso para que el viento no la mueva.
- **Lavasecadora (dueño, 2026-10-11):** una Samsung de carga frontal de 686 × 984 × 796 mm sustituye a la lavadora de 2 tinas y a la secadora.

#### Reorganización de la lavandería

**El hallazgo que manda:** al cerrar la lavandería con W41 queda un cubo de luz de 1.45 × 2.40 m (3.5 m²), con muros de 2.60 m y calentador de agua. La NOM-004-SEDG-2004 (6.1.2.1) no permite ahí un cilindro de gas portátil: ni donde hay calentador, ni con muros de más de 2 m y menos de 9 m² de piso. Abierta al pasillo, como está hoy, sí cumplía. Además, el cilindro quedaba a menos de 1 m de la lavasecadora y sus contactos.

| Hoy | Problema |
|---|---|
| Cilindro de gas junto al boiler | No cumple la norma con la lavandería cerrada. |
| Sin techo | La lluvia cae sobre la lavasecadora. |
| Boiler de depósito sobre una base de 40 × 40 cm | Ocupa el rincón de la entrada. |
| Esquina bajo V09 y 0.55 m junto al boiler | No se usan. |
| Sin lavadero ni guardado | Solo hay una repisa a 1.78 m. |

#### Lavandería moderna (2026-10-17)

El dueño trajo dos referencias: una columna de lavadora y secadora apiladas con muebles grises, y una barra corrida con
tarja, máquinas bajo la cubierta, alacenas de madera, repisas abiertas y azulejo tipo metro. De ellas se toman las
ideas que caben en 1.45 × 2.40 m: barra corrida con tarja, cestos extraíbles y cajones, alacenas encima, salpicadero de
azulejo y una cubierta para doblar sobre la máquina. Lo que no cabe se descarta:
- **Columna apilada:** no aplica, porque es una sola lavasecadora.
- **Repisas y barra para colgar en el muro de enfrente:** dejarían el paso en menos de 0.60 m.

**El límite real es el ancho.** La lavasecadora con sus mangueras ocupa 0.85 m de fondo, y frente a ella quedan 0.60 m.
Las guías piden 0.75–1.0 m para hincarse y sacar la ropa. Girarla hacia el largo del cuarto no funciona: en 1.45 m no
caben la máquina (0.69 m) y una barra (0.55 m) sin que una tape a la otra. **Solución:** la máquina va frente al vano de
la corrediza D14. Con la puerta abierta, delante de ella quedan 1.77 m libres (0.60 + el muro + el pasillo de servicio).
Por eso la corrediza tenía que ir del lado del pasillo.

| Tramo (y), muro del fondo | Pieza | Por qué |
|---|---|---|
| 10.30–10.90 | **Tarja de acero** de 50 × 40 cm, bajo V09 | Remojar y tallar con luz natural. La barra empieza en y = 10.30 m para librar el barrido de D13. Llave abatible negra de 30 cm de alto, que no topa con el pretil de V09 (1.28 m). |
| 10.90–11.35 | **2 cestos extraíbles** | Separar la ropa sucia (blancos y color) sin cestos en el piso. |
| 11.35–11.77 | **3 cajones** | Detergentes, pinzas y trapos, a la mano junto a la máquina. |
| 11.83–12.52 | **Lavasecadora** en un nicho, bajo una cubierta a 1.04 m | Frente al vano de D14. La cubierta (87 × 84 cm, 2.6 cm sobre la máquina) es la mesa para doblar, a la altura cómoda para hacerlo de pie. |
| 11.05–11.95, a 1.50–2.20 m | **2 alacenas** de 35 cm de fondo | Guardado arriba, sin tapar la ventana. Entre la barra y las alacenas quedan los contactos. |
| 12.15–12.50, a 1.55–2.15 m | **Calentador de paso** | Donde estaban las tuberías del boiler, 51 cm sobre la cubierta y a 20 cm de las alacenas. |

- **Barra:** cubierta a 0.92 m, de 55 cm de fondo. El paso entre la barra y el muro W41 es de 0.90 m.
- **Acabados:**
  - Muebles en `melamina-cocina` y cubierta `laminado-cubierta`, los mismos de la cocina, que se ve a través de D13.
  - Jaladeras de acero negro mate, como la corrediza.
  - Azulejo tipo metro blanco de 7.5 × 30 cm con junta gris, del piso a 1.55 m en el muro del fondo. Es un material propuesto y solo lo toma la variante.
- **Instalaciones:** el agua y el desagüe se alargan unos 0.9 m por el muro del fondo hasta el nicho de la máquina.
- **Se quitan:**
  - el lavadero de cemento y el gabinete alto, porque la tarja y la barra los sustituyen;
  - la escoba y el trapeador, que van colgados en el muro W41 con un riel organizador de 10 cm (no modelado).

- **Cilindro de gas:** sale al pasillo de servicio, a la intemperie, contra el muro de la recámara 2, que no tiene ventanas (y ≈ 12.95 m). Al frente quedan 0.75 m hasta la barda (6.1.2.4 pide 0.60 m) y se cambia sin pasar por la cocina (6.1.2.9).
- **Tendedero retráctil:** 3 hilos a 2.35 m, de W41 al muro del fondo, por encima de las alacenas y de las puertas. También sirve para colgar ganchos.
- **Techo de policarbonato:** lámina celular translúcida sobre perfiles, de 2.90 a 3.00 m, con caída hacia el pasillo de servicio. Entre el remate de los muros (2.60 m) y el techo quedan 30–40 cm abiertos. Así el calentador queda en un sitio con ventilación permanente y chimenea (6.5.2.2 y 6.5.2.3), y la ventana del baño sigue ventilando.
- **Calentador de paso, condición:** necesita presión de agua suficiente. Si el tinaco está bajo, conviene uno de rápida recuperación (chico, de piso).
- **Repisa:** se recorta desde x = 2.30 m para no cruzar D13.

### Instalaciones

- **Gas:** del cilindro, ya en el pasillo de servicio, a la estufa por fuera de W41 y W13, y al calentador a través de W41. La instalación la debe hacer un instalador certificado.
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
  - la chapa de D13 y el tope de piso de D14;
  - el canalón del techo de la lavandería;
  - los contactos nuevos;
  - la luz bajo las alacenas;
  - las tuberías.
- **Validación:** la propuesta no sustituye la validación estructural ni normativa de un profesional.
