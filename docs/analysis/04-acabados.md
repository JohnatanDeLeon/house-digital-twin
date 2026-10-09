# Fase 4: acabados y texturas a partir de fotos

Fuente: 14 fotos del dueño, del 2026-10-07 (23:18–23:33) y del 2026-10-08 (07:45–07:56). Todas son de noche, con luz artificial cálida, sin flash, tomadas con un Samsung Galaxy S25 Ultra en gran angular (23 mm equivalente). Las originales están en `sources/fotos/`, fuera de git. Cada material se describe en `sources/texturas/<nombre>.json` y se genera en `assets/textures/<nombre>/` con:

```bash
python -m house_twin.cli texture sources/texturas/<nombre>.json
```

![Vista previa de las texturas en Blender (Cycles)](04-texturas.jpg)

## Materiales

| Material | Tipo | Aplica a | Fuente del dato |
|---|---|---|---|
| `puerta-recamaras` | Mapas: color, rugosidad, relieve | Puertas D02, D05, D06, D07 y D08 | Foto; el dueño dice que las 5 son iguales |
| `piso-interior` | Mapas repetibles (2 × 3 losetas) | Piso de S01–S05, S07 y el tragaluz S08 | Foto; el dueño dice que es el piso de todo el interior |
| `puerta-cocina` | Mapas + opacidad para los vidrios | Puerta D04 | Foto y dueño |
| `azulejo-bano` | Mapas repetibles (3 × 2 azulejos) | Muros del baño S05 | Foto; el dueño dice que es el azulejo del baño con regadera |
| `piso-exterior` | Mapas repetibles (≈ 1 × 1 m, sin juntas) | Piso de S06 y S09–S13 | Foto; el dueño dice que todos los exteriores son de concreto gris |
| `piso-regadera` | Mapas repetibles (2 × 2 losetas de mosaico) | Piso de la regadera (S05) | Foto; el dueño dice que el antiderrapante está solo en la regadera |
| `puerta-pasillo` | Procedural con opacidad de herrería (casi todo hueco) | D10 (cochera ↔ pasillo) y D11 (pasillo ↔ patio) | Medidas de la foto y dueño (las dos son iguales); **no están en el plano** |
| `closet-madera` | Mapas repetibles de la veta impresa (hojas lisas de melamina) | Puertas de closet de 2 recámaras | Foto; el dueño dice que el closet de la recámara más grande (R1) no tiene puertas |
| `puerta-entrada` | Mapas + opacidad para el vidrio | Puerta D03 (entrada a la sala) | Foto y dueño |
| `aluminio-negro` | Constante (color medido) | Marcos y hojas de V01–V10 | Foto; el dueño dice que todas las ventanas son de aluminio negro |
| `vidrio-claro` | Constante (supuesto) | Vidrios de las ventanas y de D04 | Supuesto |
| `vidrio-polarizado` | Constante (supuesto) | Vidrio de D03 | Dueño: «ventanal polarizado»; tono y transmisión supuestos |
| `aplanado-exterior` | Mapas repetibles (≈ 0.5 × 0.5 m) con relieve alto | Muros exteriores del pasillo de servicio, el patio y la cochera | Foto y dueño; el pórtico es más rugoso (pastas de estuco, textura pendiente) |
| `estuco-fachada` | **Sintética** (procedural, repetible) | Fachada a la calle y pórtico | Dueño: punto medio entre dos referencias de catálogo («Lace Trowel» y «Pebbled Dash»); sin foto de la casa |
| `muro-interior` | Constante | Muros interiores | Dueño: yeso blanco con pintura blanca |

**Exteriores y bodega** (dato del dueño): pórtico, bodega, cochera, pasillo de servicio, lavandería y patio no tienen loseta. Su piso es un firme de concreto gris (foto 9); el dueño confirma que es el mismo en todos. El tragaluz tiene la loseta del interior.

## Cómo se obtiene cada textura

1. **Perspectiva:** se marcan las 4 esquinas de la superficie en la foto y se lleva a un rectángulo del tamaño real.
2. **Color:** se corrige en espacio lineal con una superficie que se sabe blanca y está en el mismo plano. Si la foto no tiene blanco, se usa el balance de otra foto con la misma luz y la luminosidad queda declarada como supuesto.
3. **Luz desigual:** se quita dividiendo por una superficie cuadrática ajustada a la luminancia, sin contar las juntas.
4. **Herrajes:** perillas y cerraduras se tapan con un trozo de la misma pieza. Irán como objetos 3D aparte.
5. **Relieve:** sale de la geometría medida en la foto (tableros, juntas, acanalados), más la veta del detalle fino.
6. **Repetición:** los pisos con juntas se recortan por el eje de las juntas. Los que no tienen juntas (concreto) se hacen repetibles mezclando el recorte con una copia desplazada (`make_seamless`).

Los defectos reales (salpicaduras de pintura, marcas) se conservan.

## Hallazgos por foto

### 1. Puerta de recámaras y baños (23:18:45)

- **Puerta:** de 5 tableros realzados (2 arriba, 1 central horizontal y 2 abajo), de pino con nudos entintado nogal y barniz satinado.
- **Proporción:** la hoja mide unas 2.52 veces su ancho de alto; con una altura de ~2.04 m saldría de ~0.80 m de ancho.
- **Herrajes:** perilla de latón envejecido con seguro de botón y 3 bisagras de libro. La puerta abre hacia quien tomó la foto.
- **Marco:** de pino, sin chambrana, con escurrimientos de pintura blanca.
- **Contexto:** apagador de placa negra en el nicho, a la altura de la perilla.
- **Conflicto con el plano:** los vanos de los baños miden 0.80 m (D05) y 0.78 m (D02). Ahí no cabe una hoja de 0.80 m más su marco. Hay que medir la hoja.

### 2. Piso interior (23:19:01)

- **Loseta:** cerámica esmaltada beige claro con veteado tipo mármol, puesta a junta corrida.
- **Esmalte:** brillante, con micro relieve; el reflejo de la lámpara sale moteado.
- **Junta:** gris oscuro, mide el 1.7–1.8 % de la loseta (~5 mm).
- **Geometría:** la cuadrícula es regular; error de 3 px al comprobar con un cruce intermedio.
- **Tamaño:** se estimó ~30 × 30 cm por la escala de la puerta. Falta medirlo.
- **Color:** en la foto no hay blanco de referencia, así que la luminosidad del beige es supuesta.

### 3. Ventana (23:19:20)

- **Ventana:** corrediza de 2 hojas, con perfil de aluminio negro casi puro (`#10110d`).
- **Acabado:** satinado, sin brillo metálico; se trata como pintura o anodizado.
- **Pestillo:** negro, en el larguero de la hoja corrediza.
- **Empotrado:** en el muro, con mocheta y repisón de yeso.
- **Persiana:** encima tiene la caja de una persiana enrollable de aluminio plata. No sabemos si todas las ventanas la tienen.
- **Estado:** salpicaduras de pintura blanca (9–14 % del área de los perfiles laterales) y marcas naranjas en el cabezal. Son de esta ventana y no se generalizan.
- **Vidrio:** la hoja fija se ve con un reflejo verdoso más claro que la corrediza. Puede ser película o vidrio entintado.
- **Medidas:** la foto no muestra la ventana completa (falta el borde izquierdo), así que no se puede medir el ancho.

### 4. Muro interior (23:19:39)

- **Superficie:** yeso liso con pintura blanca mate. El detalle fino de la foto (desviación de 0.98 niveles) es ruido del sensor, no relieve, así que el material va sin mapas.
- **Color:** no se puede medir, porque este mismo blanco es la referencia de las demás fotos. Se declara 235 sRGB.
- **Estado:** una perforación de clavo y rozaduras cerca del piso.
- **Contexto:** pantalla LED montada en el muro.
- Junto a la puerta de la foto 1, el yeso se veía con textura de llana. Puede ser una zona retocada.

### 5. Puerta de la cocina, D04 (23:20:28)

- **Hoja:** marco y hoja de perfil negro con esmalte brillante a brocha.
- **Arriba:** 2 vidrios con retícula blanca (1 barra vertical y 2 horizontales cada uno) y 4 adornos de fundición soldados.
- **Abajo:** tablero de lámina acanalada, con 7 juntas de duela de doble ranura cada ~8.5 cm.
- **Herrajes:** 2 bisagras de munición del lado izquierdo, una cerradura de sobreponer, un pasador con llave y una pieza cilíndrica arriba a la derecha.
- **Material:** las soldaduras, los adornos de fundición y la cerradura de sobreponer son típicos de **herrería de acero**. El dueño dice que es aluminio pintado; queda por confirmar (un imán lo resuelve).
- **Vidrio:** transparente, con suciedad.
- **Contexto:** a la derecha hay azulejo blanco brillante con una cenefa de frutas y platos de talavera. Es un acabado de la cocina que todavía no tiene textura.
- **Medidas:** la textura usa el vano D04 (0.83 m del plano y 2.10 m de U04), suponiendo que el marco negro ocupa todo el vano.

### 6. Puerta de entrada, D03 (23:22:08)

- **Puerta:** metálica, de una hoja. Arriba tiene un vidrio polarizado grande con moldura a inglete; abajo, un tablero hundido.
- **Acabado:** pintura negra mate muy envejecida sobre una superficie rugosa, con moteado claro. Debajo se asoman restos de **pintura verde agua**, el color anterior.
- **Óxido:** en todo el contorno del marco, en el travesaño inferior y en manchas del tablero.
- **Herrajes:** 3 bisagras de munición soldadas a la izquierda. A la derecha, de arriba abajo: aldaba de palanca, cerrojo de seguridad y manija de palanca con seguro (las dos de latón envejecido), y un pasador cromado con llave.
- **Bisagras:** quedan a unos 14 cm del borde izquierdo del conjunto. Probablemente hay un marco fijo ancho a la izquierda y la hoja es más angosta que el vano de 1.00 m.
- **Umbral:** de aluminio, atornillado al piso.
- **Cordones amarillos:** dos, atados arriba. Son provisionales y no entran en la textura.
- **Textura:**
  - Usa el vano D03 (1.00 × 2.10 m) y su relieve tiene más grano, para reproducir la superficie rugosa.
  - Los herrajes se taparon con el mismo larguero; ese parche repite una mancha verde agua de más arriba.
  - **Pasador y cerradero (corrección del dueño, 2026-10-08):** van **solo por dentro**. Como la misma textura se ve de los dos lados, el recorrido los mostraba también hacia el pórtico. Se tapan con el mismo larguero y marco de más arriba (antes se tapaban con un trozo del travesaño, que corre en horizontal). Irán como objeto 3D solo en la cara de la sala.
  - **Vidrio sin foto:** la foto tenía en el vidrio el reflejo del dueño y de la sala, y el recorrido web lo dejaba ver, porque el vidrio de una hoja muestra un 30 % del color base. Ahora, en el hueco de una hoja con `glass_material`, el generador pinta el color de ese vidrio y lo deja liso. Blender no cambia, porque ahí ya usaba el material del vidrio. También aplica a la puerta de la cocina (D04).

### 7. Azulejo del baño con regadera (23:33:31 y 07:53:10)

Son dos fotos del mismo muro. La de lejos (gran angular de 13 mm) da 3 × 2 azulejos para la textura. La de cerca (23 mm) da la proporción y el estado.

- **Azulejo:** cerámico esmaltado, rectangular vertical, puesto a junta corrida. Es gris claro con vetas y nubes beige y blancas tipo mármol o piedra.
- **Esmalte:** muy brillante; la lámpara se refleja como un punto nítido.
- **Proporción:** alto/ancho ≈ 1.47 en la foto de cerca, casi de frente. Es compatible con **20 × 30 cm**, pero falta medirlo.
- **Junta:** boquilla blanca de ≈ 3 mm, hundida, con suciedad oscura. Tiene un **tramo vertical abierto** (sin boquilla) en la parte baja.
- **Color:** en la foto de cerca, el centro de la junta sale *más oscuro* que el azulejo (≈ 113 contra 150), porque está hundida y sucia; lo que se ve claro a sus lados es el canto brillante. Esa foto no sirve como blanco. En la de lejos, junta y canto se mezclan en un tono casi neutro: se usa como referencia aproximada (albedo 225).
- **Textura:** el reflejo de la lámpara en un azulejo se tapó con el mismo azulejo.
- **Contexto:** a la derecha está la puerta de madera de los baños (la misma de `puerta-recamaras`) y abajo a la izquierda, el inodoro.

### 8. Piso antiderrapante de la regadera (07:56:01)

- **Loseta:** cerámica antiderrapante con **diseño de mosaico**. Cada pieza tiene **6 × 6 cuadritos** de superficie granulada, color piedra gris-beige, separados por canales blancos esmaltados.
- **Junta entre losetas:** de cemento gris, ancha (≈ 5–7 mm), sucia y con trazo algo irregular.
- **Tamaño:** la loseta mide ≈ 1.55 veces la tapa de la coladera. Si la coladera es de ~11 cm (medida comercial común), la loseta sale de **17–20 cm**. Se usó 20 × 20 cm.
- **Coladera:** redonda, de acero inoxidable, con 6 ranuras y 2 tornillos, en un aro de cemento. Tiene pelo acumulado y **una grieta en la junta** que sale hacia la derecha.
- **Desgaste:** el estampado se ve gastado en manchas claras sobre varias losetas. Hay manchas amarillas de jabón en la esquina con el muro.
- **Muro de la regadera:** las piezas que se ven arriba de este piso parecen grises, mate y más grandes que el azulejo del resto del baño. Falta confirmarlo.
- **Textura:**
  - Usa 2 × 2 losetas, con la coladera y la sombra fuera del recorte.
  - El relieve tiene dos niveles: junta hundida entre losetas y canales entre cuadritos.
  - Rugosidad: cuadritos mate, canales con brillo y junta mate.
  - El blanco de referencia es el de los canales.

### 9. Piso de concreto de los exteriores (07:47:52)

- **Firme:** de concreto gris con **acabado escobillado en ondas**. Las estrías finas onduladas lo hacen antiderrapante; tiene poros, granos de arena expuestos y algunas piedritas.
- **Color:** con luz de día el gris sale neutro (`#babbbb` tal como lo registró la cámara). La luminosidad media es supuesta (albedo ≈ 0.40), porque la exposición automática no la fija.
- **Manchas gris azuladas** abajo a la derecha. Conservan la textura de ondas y, según el dueño, **no son humedad**. Su origen queda sin identificar (sellador, pintura o cemento de otra mezcla). Quedan fuera del recorte.
- **Junta o grieta diagonal** en el borde derecho, con una superficie más lisa del otro lado (otro colado o una banqueta).
- **Escala:** no hay nada de tamaño conocido en la foto. Se supuso una foto tomada de pie, a ≈ 1.4 m, así que el recorte mide ≈ 1 × 1 m.
- **Textura:** es repetible sin costuras gracias a `make_seamless`. En áreas grandes se nota algo la repetición cada metro; con más fotos del exterior se podría variar.

### 10. Puertas de herrería del pasillo de servicio (07:48:20)

- **Dónde van (dueño, 2026-10-08):** el plano no las dibuja; entran como `add_openings` del dueño, con su rectángulo.
  - **D10, cochera ↔ pasillo:** en y = 6.705 m. En la foto, su poste izquierdo queda al final del muro de la cocina. Cubre de la barda (x = 0.20 m) a la cara del muro de la cocina (x = 1.205 m): 1.005 m.
  - **D11, pasillo ↔ patio:** al final del muro de la recámara 2 (y = 16.945 m), donde se abre el patio ancho. Cubre de la barda al muro de la recámara 2 (x = 1.28 m): 1.08 m. El dueño dice que es igual a D10; no hay foto.
- **El pasillo de servicio crece:** la franja de 1.08 m entre la barda y la recámara 2 queda del lado del pasillo, porque la puerta del patio está al final de ella. El pasillo pasa de 5.95 a 10.62 m² y el patio baja en lo mismo. Entre la cochera, el pasillo y el patio ya no hay paso abierto: se cruzan las dos puertas.
- **Puertas sin muro:** van entre dos muros, no dentro de uno. Por eso no tienen `host_wall` ni hueco (`IfcOpeningElement`) en el IFC. La altura del dato U04 (2.10 m) es la de los vanos de muro y no les llega: esperan la medida del dueño. Mientras tanto, el IFC usa la altura supuesta, marcada como supuesto.
- **Altura estimada de la foto:** ancho/alto = 0.530, calculado con la perspectiva y la focal de la cámara. Las esquinas salen en ángulo recto (coseno 0.003), así que la estimación es consistente. Con 1.005 m de ancho da ≈ 1.90 m. Es solo una referencia, no un dato.
- **Puerta:** de herrería de una hoja. Tiene marco de perfil, 3 barrotes cuadrados torcidos, 3 barrotes lisos con 2 adornos de fundición en rombo cada uno, 4 travesaños, 10 arillos de solera (filas de 3, 4 y 3) y lámina lisa en el tercio inferior.
- **Acabado:** pintura negra a brocha (`#1f1e25` contra el muro del pasillo), con polvo, desgaste y marcas de brocha.
- **Herrajes:** bisagras de perno con ménsula anclada al muro, del lado izquierdo; portacandado de lámina con candado, del lado derecho. Irán como objetos 3D.
- **Textura: dibujada, no copiada** (generador `sheet_door`, igual que D09):
  - La versión anterior pegaba la foto. En los huecos quedaban la calle, la cochera y los cables, y el portacandado, que va de un solo lado. En Blender esos huecos no eran transparentes (la opacidad solo se usaba con vidrio) y en el recorrido se veían al 30 %.
  - Ahora barrotes, travesaños, arillos y adornos se dibujan con las medidas tomadas en la foto rectificada. La opacidad sale de esas mismas piezas: los huecos son transparentes en Blender (Alpha del Principled) y se recortan en el recorrido, donde la sombra también sigue a los barrotes.
  - **Color:** la cámara expuso para la calle, así que la lámina sin referencia daba casi negro (8, 8, 11). Con el muro del pasillo como blanco (albedo supuesto 222) da (31, 30, 37), parecido al negro de la bodega.

### 11. Puertas de closet (07:45:49 y 07:46:12)

- **Closet:** empotrado de muro a muro y del piso al techo. Tiene **3 módulos**, cada uno con 2 hojas altas y 2 puertas de maletero arriba.
- **Hojas:** lisas, sin tableros ni molduras. Tienen **jaladeras de barra de acero inoxidable** verticales, en pares al centro de cada módulo, y más cortas en los maleteros.
- **Acabado:** **melamina** (confirmado por el dueño) color chocolate oscuro tipo wengué, con veta vertical impresa fina y satinada.
- **Estado:** huellas y manchas de grasa, un rayón en una hoja y la junta con el muro sin acabar (relleno de yeso, con pintura naranja asomando).
- **Color incierto:** con su blanco de referencia, la foto 1 da `#55484d` (cerca, con reflejo) y la foto 2 `#272426` (lejos, en sombra). Cada blanco recibe otra luz que el closet. Se conservó el tono café de la cámara con una luminosidad intermedia supuesta.
- **Otros acabados que aparecen en la foto 2:**
  - **Techo con textura de tirol** (rugoso). Es un acabado distinto al muro liso y todavía no tiene textura.
  - **Zoclo de loseta** en el muro.
- **Por la regla del dueño:** R1 (16.15 m², la más grande) tiene closet sin puertas, y R2 y R3 sí tienen.

### 12. Aplanado exterior de pasillo, patio y cochera (07:49:12)

- **Acabado:** aplanado de mortero lanzado (**zarpeo / tirol rústico**) con pintura blanca mate. Tiene crestas irregulares, cráteres y poros de 1 a 10 mm, y algunos filos marcados. Coincide con lo que dice el dueño: rugosidad alta, «casi como bordes».
- **Dónde va (corrección del dueño):** muros exteriores del pasillo de servicio, el patio y la cochera. El **pórtico es aún más rugoso, con pastas de estuco**: necesita su propia textura.
- **Estado:** hay polvo gris acumulado en las cavidades, manchas grises y una zona con la pintura desgastada.
- **Relieve:** tiene varias escalas, de detalle fino a crestas de ≈ 1 cm. El generador ahora acepta `grain_blur_px` para fijar la escala más grande que cuenta como relieve; aquí, 24 px. La amplitud de 3 mm es supuesta.
- **Escala:** supuesta. La foto se tomó a ≈ 0.5 m, así que el recorte mide ≈ 0.5 × 0.5 m.
- **Color:** con luz de día difusa sale neutro. La luminosidad del blanco exterior es supuesta (albedo ≈ 0.73).

### 13. Estuco de la fachada y el pórtico (sintético)

- **Por qué es sintético:** el dueño describe el acabado como más rugoso que los demás exteriores, con «pastas de estuco», y da como guía un **punto medio entre dos referencias de catálogo**: «Lace Trowel» (placas grandes aplanadas por la llana, con bordes marcados) y «Pebbled Dash» (grano fino de piedrita). No hay foto de cerca de este acabado.
- **Cómo se genera:** por código (`kind: procedural`), con ruido periódico, así que se repite sin costura. Lleva placas de ≈ 3 cm que cubren ≈ 45 % de la superficie, con 3 mm de relieve y bordes marcados, sobre grano fino de 0.25 mm. Es más oscuro entre placas por polvo y sombra fina, y la semilla es fija.
- **Es una aproximación, no una observación:** forma, tamaño y relieve son interpretación. Hay que reemplazarlo por una textura de foto cuando la haya.
- **Las referencias** son imágenes de catálogo: no se guardan en el repo.
- **Foto de las 07:49:34 (`20261008_074934.jpg`):** muestra una puerta de lámina negra acanalada junto a una ventana con herrería. Los muros de alrededor no tienen placas: uno es de grano rugoso y el otro casi liso con poros. El dueño confirma que es la puerta de la bodega (D09): ver la sección 14.

### 14. Puerta de la bodega D09 (07:49:34)

- **Qué es (dato del dueño):** la puerta de la bodega, fotografiada desde el pórtico.
- **Conjunto:** ocupa el vano de 0.835 × 2.10 m.
  - **Marco de perfil.**
  - **Fijo arriba:** lámina acanalada con 9 costillas a ≈ 8.1 cm, soldada a un ángulo con puntos arriba, abajo y a los lados. La mayoría de las soldaduras tiene óxido.
  - **Hoja:** dos tableros de duela de lámina (8 duelas de ≈ 8 cm, con bordón y ranura en cada unión) con moldura de 2 cm y una solera sobrepuesta a media altura.
- **Herrajes:** la chapa de cilindro va a la izquierda y la jaladera cromada de asa sobre la solera. Las bisagras van a la derecha. No van en la textura: irán como objetos 3D.
- **Cómo se genera: dibujada, no copiada.** La textura de D03 pegó la foto y con ella el reflejo del fotógrafo en el vidrio. Aquí el esmalte refleja el cielo como una mancha azulada, así que la foto rectificada solo se usa para medir:
  - **Geometría:** la posición de cada pieza, en fracciones de la cara.
  - **Colores:** pintura `#1d1f22` (la parte más oscura de las duelas, que coincide con el fijo en sombra), óxido `#493a37` y polvo `#3c3c3e`. El blanco de referencia es el muro derecho, con albedo supuesto de 222.
  - El generador `sheet_door` arma el relieve con esas medidas y oscurece lo hundido. Reparte el óxido de las soldaduras y el polvo de la parte baja con ruido, y el brillo lo da el render con la rugosidad (esmalte satinado, 0.4).
- **Lado de la foto (`viewed_from`):** la textura declara desde qué espacio se fotografió, y la escena orienta la UV para que de ese lado no salga espejada. Aquí la chapa queda a la izquierda vista desde el pórtico. D03 también lo declara: su foto es desde la sala.
- **Supuestos:** las profundidades del relieve, que la cara hacia la bodega es igual y que el conjunto llena el vano.

### 15. Ventana del tragaluz V10 y muros del tragaluz (22:37:24 y 22:37:54)

- **Fotos:** dos desde la sala, de noche, con el gran angular (13 mm): una de cerca y otra de contexto, con techo y piso a la vista.
- **Ventana:** corrediza de **2 hojas con retícula de 2 × 5 vidrios cada una** (4 × 5 en total), de aluminio negro y vidrio claro. Va centrada en el entrante diagonal, en un vano que ocupa casi todo el muro W32.
- **Medidas: estimadas con las fotos.** El dueño las aceptó hasta medirlas, y quedan en `add_openings` con `measure_source`; la incógnita U11 se cierra con esa aclaración.
  - **Cómo:** en la foto de contexto, las 4 esquinas del muro diagonal (1.137 m de cara, 2.60 m de piso a techo) dan el plano del muro, y el marco se mide sobre él. Una esquina, detrás del sillón, se extrapoló.
  - **Resultado:** **ancho 1.03 m, alto ≈ 1.62 m, antepecho ≈ 0.52 m**.
  - **Comprobación:** la proporción ancho/alto con la focal de la cámara da 0.62 en la foto de contexto y 0.65 en la de cerca. Margen: ±5 cm.
- **Retícula:** `grid` en el dato del vano (4 vidrios a lo ancho, 5 a lo alto, perfil de ≈ 3 cm estimado). La dibujan Blender y el recorrido.
- **Hueco en muros diagonales (corrección):** el hueco del IFC se agrandaba sobre X e Y del mundo. En un muro a 45° eso no lo sacaba del espesor y el corte booleano fallaba a medias: la ventana se veía por un hueco de la mitad de ancho. Ahora crece sobre los ejes del propio vano.
- **Muros del tragaluz (dato del dueño): azul turquesa.** Material `muro-tragaluz`, solo para S08.
  - **Tono medido:** ≈ 193°, igual en la foto de R3 (de día, a través de V05) y en la de V10 (de noche, a través del vidrio).
  - **Supuestos:** saturación y luminosidad, a medio camino entre las dos. De día el azul sale recortado en 255; de noche, el muro recibe mucha menos luz que el blanco de referencia.

### 16. Chapas de las puertas de madera (22:38:35 a 22:38:45)

- **Fotos:** 3 de la chapa de una puerta de madera, de cerca y de noche. Las cinco puertas de madera son iguales (D02, D05, D06, D07 y D08).
- **Chapa:** de perilla tipo bola, de latón envejecido. La roseta es redonda y cepillada (Ø ≈ 5.8 cm) y la perilla mide Ø ≈ 5.5 cm. El hueco del centro tiene un botón de seguro vertical, que va del lado de adentro del cuarto. En el canto van el pestillo y, en el marco, el cerradero (no se modelan).
- **Primer herraje en 3D:** `sources/herrajes/perilla-laton.json` describe el perfil torneado (mm), la posición y el material. `build` lo genera dentro del IFC como `IfcDiscreteAccessory`, parte de su puerta, con una perilla en cada cara y el botón del lado del cuarto.
- **Posición:** sale del parche que tapó la perilla en la foto de la hoja. El centro queda a 0.072 del ancho desde el canto de la chapa (5.8 cm, la entrada estándar de 6 cm) y a 0.485 del alto desde arriba (≈ 1.05 m del piso).
- **Abatimiento (dato del plano):** los 9 bloques `PUERTA` del DXF traen el arco de abatimiento; su centro es la bisagra. Cada puerta tiene ahora `swing` en los hechos: bisagra, canto de la chapa y espacio hacia el que abre. Las cinco de madera abren hacia su cuarto.
  - **Orientación de la textura:** la de madera declara `latch_side: left` (en la foto, la perilla está a la izquierda), y la escena orienta la hoja para que ese canto quede del lado contrario a la bisagra del plano.
  - **Discrepancia en D09:** el plano pone la bisagra en el extremo norte (y = 1.855 m) y la puerta abriendo hacia la bodega. En la foto desde el pórtico, las bisagras se ven a la derecha (el extremo sur). D09 se orienta por su foto (`viewed_from`). Falta que el dueño confirme hacia dónde abre.
- **Latón (`laton-envejecido`):** metálico. El color base se midió en la roseta cepillada, corregido con el muro blanco: `#c5b086`. En el recorrido, los metales reflejan un cuarto genérico; sin él, el latón salía negro.
- **Supuestos:** la salida de la perilla (5.5 cm) y el espesor de la roseta, porque las fotos son de frente; y que la perilla de afuera es igual a la de adentro, sin botón.

### 17. Closet de la recámara 3 (fotos `closet-recamara-3`)

- **Es el de la recámara 3** (dato del dueño). El de la recámara 1 no tiene puertas y queda sin modelar hasta tener sus datos.
- **Recámara 2 (dato del dueño):** igual al de la recámara 3, pero con 4 módulos. `closet-recamara-2.json` se basa en el de R3 (`based_on`) y solo cambia los módulos: sin foto, se reparten iguales en los 2.91 m del plano, con las orillas (1.6 cm) y los postes (6.7 cm) promedio de R3. Quedan módulos de ≈ 0.67 m (supuesto).
- **Dónde (dato del plano):** cada recámara tiene el rótulo CLOSET y una línea de frente en la capa `9-MUEBLES FIJOS`. Los hechos tienen ahora `fixtures`: frente, fondo hasta el muro (0.60 m en las tres) y hacia dónde mira. R3: frente en x = 6.39 m, de y = 8.14 a 10.82 m (2.68 m).
- **Frente (`sources/muebles/closet-recamara-3.json`):** medido en la foto rectificada a 2.68 × 2.60 m, porque va de muro a muro y del piso al techo.
  - **Módulos:** 3 desiguales, de ≈ 0.81, 0.85 y 0.85 m, separados por postes de ≈ 6 cm.
  - **Hojas:** cada módulo tiene 2 hojas altas (≈ 1.95 m) y 2 maleteros (≈ 0.57 m), con juntas de 3 mm.
  - **Jaladeras:** barras de acero inoxidable de 23 cm, en pares a 5.5 cm de la junta central.
- **IFC:** el closet es un `IfcFurniture` (cuerpo y hojas, de `closet-madera`) y sus jaladeras, un `IfcDiscreteAccessory` agregado (`acero-inoxidable`, color medido `#d6d4d7`). Blender toma el material de cada objeto del IFC. En el recorrido, el closet no se atraviesa.
- **Color:** con el pilar blanco como referencia, las hojas bajas dan (64, 53, 42). Cuadra con la textura `closet-madera` (56, 47, 44), que se conserva.
- **Límite del recorrido web:** no oscurece las ranuras (no hay oclusión ambiental), así que las juntas y los postes se notan menos que en Blender.

### 18. Techo de tirol, losa y focos (2026-10-09)

- **Qué está techado (dato del dueño):** todos los techos de la casa son rugosos y blancos (tirol), como los de la sala y la recámara 3, incluido el del pórtico. Con eso, los espacios interiores pasan a `roofed: true` (`interior_roofed` en las anotaciones). El tragaluz, la cochera y la lavandería siguen abiertos; el patio y el pasillo de servicio, sin dato.
- **Losa (`IfcSlab` ROOF):** cubre los espacios techados y los muros que los rodean, y deja abierto el tragaluz. Su espesor es un **supuesto**: 10 cm, porque U02 sigue sin respuesta, y queda marcado en `HDT_Provenance`. El acabado de la azotea no tiene dato y sale en gris violáceo desde arriba.
- **Tirol (`tirol-techo`, sintético):** grano fino de ≈ 8 mm y 1.2 mm de relieve, estimado en la foto del closet de la recámara 3, donde el techo se ve de cerca. Va en un `IfcCovering` CEILING de 1 cm bajo la losa en cada espacio techado.
- **Focos (dato del plano):** 9 salidas en la capa `23- ILUMINACION`:
  - 2 en la sala, 1 en la cocina y 1 en el pasillo de recámaras;
  - 1 en cada recámara, 1 en el baño y 1 en el medio baño.
  - La bodega y el pórtico no tienen salida dibujada.
  - Los hechos tienen `lights` con su espacio.
- **Luminaria (`sources/luminarias/foco-pelado.json`):** portalámparas con foco pelado de luz blanca fría (dato del dueño), torneados. En el IFC es un `IfcLightFixture` con su foco (`IfcDiscreteAccessory`) y `HDT_Light`. Son supuestos:
  - flujo y potencia: 900 lm y 10 W;
  - temperatura de color: 6500 K;
  - el portalámparas, blanco de Ø 9 cm.
- **Blender:** una luz puntual en cada foco, con el flujo real (900 lm ≈ 1.3 W en Blender). El foco no proyecta sombra, porque envuelve a su luz. EEVEE corta cada luz cuando su intensidad baja de un umbral, y una luz real tan débil quedaba con un alcance de pocos centímetros: se le fija un alcance de 10 m. De noche hace falta subir la exposición ≈ +6.5, como lo hace un celular.
- **Recorrido:** botón **Noche/Día**. De noche se apaga el sol, el cielo queda oscuro y se encienden los 9 focos. En la PC tienen sombras, para que la luz no atraviese los muros; en el celular no, porque pesan demasiado. De día, la losa da sombra adentro y el sol solo entra por las ventanas. Eso explicaba que el closet de R2 (de cara al sol) se viera mejor que el de R3 (de espaldas).

### 19. Contactos y apagadores (2026-10-09)

- **Dónde (dato del plano):** los bloques `CONTACTO` (12) y `APAGADOR SIMPLE` (8) están en la capa `5 CORTES`, pero dibujados en planta. Cada uno se lleva a la cara de muro más cercana de su espacio; el símbolo está dibujado a ≈ 10 cm de ella. Los hechos tienen `devices`: punto sobre la cara, normal hacia el cuarto y altura `null` (el plano no la da).
  - **Contactos:** 7 en sala, cocina y comedor; 1 en cada recámara, en el baño y en el medio baño.
  - **Apagadores:** 3 en sala, cocina y comedor; 1 en cada recámara, en el baño y en el medio baño.
- **Cómo (`sources/electrico/placas.json`):** placa negra (dato del dueño), de 7.6 × 11.4 cm (proporción medida en la foto del apagador de R3) y 1 cm de salida. El apagador lleva una tecla plana del tamaño de la placa y el contacto, doble (supuesto).
- **Alturas:** apagadores a **1.22 m**, medidos en la foto del closet de R3 con la altura del closet como escala. Contactos a **0.30 m (supuesto)**. En la cocina probablemente van arriba de la cubierta, y en R3 hay uno alto, sobre la TV.
- **IFC:** `IfcOutlet` (POWEROUTLET) e `IfcSwitchingDevice` (TOGGLESWITCH), con material `placa-negra` y la fuente de su altura en `HDT_Provenance`.
- **Color:** negro satinado (supuesto). En la foto, la placa sale gris carbón por el reflejo del foco, y ese reflejo no se puede separar del color con una sola foto.

### 20. Portón de la cochera (2026-10-09, foto 08:47:26)

- **Dónde (dato del plano):** el plano dibuja el portón en la capa `PUERTAS`, pero con líneas sueltas y no con un bloque `PUERTA`; por eso no salía como vano. Son 2 hojas de 1.52 m con bisagras en la barda (x = 0.20 m) y en el muro del pórtico (x = 3.24 m), y abren hacia la cochera. Se agrega como D12 en `add_openings`, sin muro anfitrión, con `detected_by` apuntando al plano.
- **Alto (estimación):** **≈ 2.23 m (±5 cm)**. La foto rectificada da una proporción de 1.365. Sale por homografía y por la focal de la cámara (13 mm equivalentes); el coseno entre ejes da −0.007 y casi no depende de la focal. Ese 1.365 se aplica sobre los 3.04 m del plano.
- **Dibujo (`porton-cochera`, `sheet_door`):** la textura no copia la foto, que en los huecos tenía la calle, los coches y el poste. Se dibuja con medidas de la foto, y por hoja lleva:
  - 9 barrotes a ≈ 14 cm entre ejes: 5 torcidos y 4 lisos, con 4 adornos cada liso;
  - 5 arillos de ≈ 12 cm sobre un travesaño de solera;
  - una varilla a la altura del pasador;
  - lámina lisa abajo, desde 1.72 m medidos desde arriba.
  - Las hojas son espejo una de la otra y entre ellas queda una rendija.
- **Color:** la cámara expuso para la calle y la lámina salió saturada a negro (valores crudos de 2 a 8 sobre 255); cualquier blanco de referencia la deja azulada. Se usa el negro medido en la herrería del pasillo (31, 30, 37), y la misma pintura es un supuesto.
- **Fuera de la textura:** el pasador con candado, que va de un solo lado, como el portacandado de D10. Tampoco se modela la caída de ≈ 1 cm de la hoja izquierda en su punta.

### 21. Frente del pórtico: ventanas con herrería y reja peatonal (2026-10-09, fotos 08:46:59 y 08:47:02)

- **Qué hay (fotos desde el pórtico):** el muro W03 no es ciego. Tiene 2 aberturas sin vidrio, cerradas con herrería, sobre un murete; arriba les queda una trabe hasta el techo. Entre ellas está la reja peatonal (D01).
- **Medidas del dueño (con cinta):** la abertura grande mide **2.00 × 1.30 m** y la chica, **1.50 × 1.30 m**. Van como V11 y V12 en `add_openings`, con W03 como muro anfitrión.
- **Estimado con las fotos:**
  - **Método:** homografía de la reja con los 0.98 m de ancho del plano. Las 2 fotos coinciden entre sí. El largo total del muro sale con 1 cm de diferencia.
  - **Antepecho:** ≈ 1.00 m, así que las aberturas llegan a 2.30 m. Con ese antepecho, el alto que da la foto es justo el que midió el dueño.
  - **Pilastras junto a la reja:** 0.29 m del lado de la bodega y 0.20 m del lado de la cochera.
  - **Proporción de las ventanas:** la foto da 3–4 % más anchas que las medidas; se usan las medidas.
- **Posición de D01 (corrección al plano):** la abertura grande arranca en la cara del muro de la bodega (x = 8.393 m), como se ve en las fotos. Con sus 2.00 m y la pilastra de 0.29 m, la reja queda en **x = 5.12–6.10 m**. El plano la pone en x = 6.17–7.15, es decir, ≈ 1.05 m más hacia la bodega.
  - El camino curvo del piso, que va de la reja a la puerta de entrada (D03), cuadra con la posición corregida.
  - Va en `opening_corrections` de las anotaciones. La huella del plano queda en `plan_footprint` y el abatimiento se mueve con el vano.
  - La abertura chica queda en x = 3.42–4.92, y entre ella y el portón queda una pilastra de ≈ 0.18 m.
- **Alto de D01:** ≈ **2.30 m**, porque llega a la misma altura que las ventanas; la foto da 2.29. U04 (2.10 m) no aplica.
- **Herrería** (`reja-portico`, `ventana-portico-grande`, `ventana-portico-chica`, con `sheet_door`): está dibujada con medidas de las fotos rectificadas, en el mismo estilo que el portón.
  - **Reja:** 4 arillos, 3 barrotes torcidos y 2 lisos con 4 adornos, varilla a media altura y lámina abajo.
  - **Ventana grande:** 7 barrotes torcidos y 6 lisos (cada liso con 2 adornos) y 7 arillos.
  - **Ventana chica:** 5 torcidos, 5 lisos y 5 arillos.
- **Color:** la lámina de la reja da **(29, 30, 36)**, con el muro de la bodega como blanco de referencia. Es casi el mismo negro de la herrería del pasillo (31, 30, 37), y las ventanas usan ese valor.
- **Recorrido:** la herrería de las ventanas da sombra; solo las ventanas con vidrio no la dan. Además se corrigió un error: la sombra del foco, que debía estar apagada, se volvía a encender en la línea siguiente.
- **Pendientes:**
  - **Bisagra de D01:** el candado está del lado de la bodega, que es donde el plano pone la bisagra. Falta que el dueño confirme.
  - **Acabados:** el muro de la bodega se ve liso, el techo del pórtico se ve liso (no de tirol), y falta el camino curvo de concreto peinado.
  - **Exterior:** pretil con cornisa, número 134, lámpara y banqueta.
  - **Luz del pórtico:** en el techo hay un portalámparas con lo que parece una cámara tipo foco.

### 22. Regadera: piso antiderrapante, sardinel, llaves y regadera (2026-10-09)

- **Datos del dueño:**
  - Las losetas del antiderrapante miden **20 × 20 cm**; se habían estimado en 17–20 cm.
  - Un **escalón de 5 cm** separa el baño de la regadera. Es el murete de 5 cm del plano (W26), que hasta ahora se modelaba como un muro hasta el techo. Pasa a ser un **sardinel de 5 cm de alto** (`role: sardinel de la regadera`), y su tope lleva el acabado del baño.
  - Las **llaves** están a **1.00 m** de alto y **15 cm** entre sí; la **regadera** sale **90 cm** arriba de ellas, es decir, a 1.90 m.
- **Área de la regadera (hecho `F04`, tipo `shower`):**
  - Es la parte del baño del lado de la ventana alta V09, del sardinel al fondo: **1.25 × 0.93 m**. La sacan las anotaciones (`showers`) a partir del plano y las fotos.
  - Lleva su propio `IfcCovering` (`S05-regadera`) con `piso-regadera`; el resto del baño conserva `piso-interior`.
- **Llaves y regadera** (`sources/sanitarios/regadera.json`, `house_twin/plumbing.py`): las 2 llaves van como `IfcValve` y el brazo con la regadera cuadrada como `IfcSanitaryTerminal`, todo de cromo. Salen del muro del lado del pasillo, junto al fondo.
  - **Estimado con la foto:** centro de las llaves a ≈ 20 cm del fondo, brazo de ≈ 40 cm con caída de ≈ 8 cm y regadera de 20 × 20 cm.
  - **Cromo:** su reflectancia es un valor de tabla, no medido; en un metal pulido, la foto solo muestra el reflejo del cuarto.
  - **Sin modelar:** la regadera de mano con su manguera, la barra y la cortina.
- **Placa del baño (corrección del dueño):** el baño no tiene apagador ni contacto abajo. El plano dibuja el apagador (A05) y el contacto (C10) por separado, pero en la casa son **una sola placa**, en el lugar del apagador, con la tecla arriba y el contacto sencillo abajo (foto).
  - Va en `shared_plates` de las anotaciones. La posición del plano del contacto queda en `plan_position`.
  - Es **beige**, no negra: **(170, 169, 151)**, medido contra el azulejo del mismo muro (`placa-beige`).
  - Su altura es la del apagador, 1.22 m; está supuesta, porque viene de la recámara 3.
- **Inodoro y lavabo:** su posición sale del plano (bloques `WC` y `LAVABO`, hechos `WC02` y `LV02`): los 2 están contra el muro del fondo, con el inodoro del lado de la regadera, igual que en la foto.
  - **Forma:** inodoro de 2 piezas con la tapa cerrada y lavabo de pedestal con mezcladora cromada, armados con perfiles torneados.
  - **Medidas:** son las comunes, **supuestas**: taza a 0.38 m, tanque a 0.77 m y borde del lavabo a 0.83 m.
  - **Color:** hueso, **(185, 183, 170)**, medido en el tanque contra el azulejo de atrás (`porcelana-hueso`).
  - **Medio baño:** el plano también tiene inodoro y lavabo (`WC01` y `LV01`), pero sin foto no se modelan.
  - **Recorrido:** el inodoro y el lavabo frenan el paso, como los muebles.

### 23. Medio baño de la entrada (2026-10-09, fotos 11:31:40 y 11:31:58)

- **Inodoro y lavabo:** su posición sale del plano (bloques `WC` y `LAVABO`, hechos `WC01` y `LV01`): los 2 están contra el muro del pórtico (W27), con el inodoro del lado sur. Las fotos lo confirman. Son otros modelos que los del baño principal, con su propia especificación (`sources/sanitarios/muebles-medio-bano.json`).
  - **Inodoro:** **blanco**, de 2 piezas, con taza alargada y palanca cromada en la esquina del tanque. El color es un blanco común **supuesto**: a contraluz de la ventana sale más claro que el azulejo y no se puede medir.
  - **Lavabo:** de pedestal, **beige almendra**, con mezcladora de 4 pulgadas. El tono se midió en el borde; la claridad es la de la porcelana del otro baño (supuesto). Tiene forma de escudo y se modela como un óvalo.
  - **Medidas:** las comunes, supuestas.
- **Azulejo (dato del dueño):** es el mismo del baño principal, pero solo hasta **2.10 m**; arriba, yeso con pintura blanca.
  - `azulejo-bano` declara `up_to_m: {"S07": 2.10}`, y `Finishes.wall_face` recibe la altura de la cara: por encima del límite sigue el acabado siguiente (`muro-interior`).
  - Blender corta las caras de los muros a esa altura.
- **Contacto (corrección del dueño):** no hay contacto bajo el lavabo. El del plano (C03) queda en los hechos con `exists: false` (`absent_devices` en las anotaciones) y no se modela.
- **Visto en las fotos, sin modelar todavía (faltan medidas):**
  - **Ventana sobre el inodoro:** está en el muro del pórtico (W27) y no aparece en el plano. Tiene vidrio texturizado, marco oscuro y un repisón de azulejo. Desde la calle se ve con protección de herrería; es la «ventana pequeña» que se veía detrás de la abertura del pórtico.
  - **Botiquín:** blanco, con espejo, repisa y toallero, sobre el lavabo.

### 24. Cocineta (2026-10-09, fotos 13:12:33 a 13:13:57)

- **Dónde (plano + fotos):** el plano solo acierta en la estufa (bloque `COCINA`, contra el muro norte) y en el centro de carga (bloque `CENTR`, en el muro del fondo del nicho). La tarja bajo las ventanas y el refrigerador que dibuja el plano no corresponden a la cocina actual.
  - **Barra:** va contra el muro norte, de muro a muro, en el nicho de 2.85 m (x = 1.375–4.225 m).
  - **Mueble chico y refrigerador:** en el muro oeste, entre la esquina y la puerta al pasillo (D04), con una alacena sobre el refrigerador.
- **Medidas (foto de frente, 23 mm):** la barra mide 2.85 m entre muros y la estufa 0.78 m en la foto, lo que cuadra con una estufa de 30" (0.76 m). Con esa escala y la cámara a ≈ 1.10 m:
  - **Barra baja**, de izquierda a derecha:
    - mueble de la tarja de 1.07 m (2 puertas + 1 y frente falso);
    - estufa;
    - 2 muebles de 0.49 m, cada uno con cajón y 2 puertas.
  - **Alturas:** cubierta a 0.90 m y puertas de 0.245 × 0.55 m.
  - **Muebles altos:** de 1.54 a 2.35 m. El de sobre la estufa es más corto (desde 1.72 m) y queda alineado con ella, lo que confirma las medidas.
  - **Supuestos:** profundidades, zoclo de 0.10 m, el mueble chico de 0.60 m y el refrigerador de 0.70 × 0.70 × 1.75 m. La foto de conjunto es de gran angular y no da escala fiable.
- **Melamina** (`melamina-cocina`): la textura es la parte baja de una puerta, sin la jaladera, su sombra ni las marcas de limpieza.
  - **Proporción:** la puerta mide 0.443 por homografía y focal, lo mismo que la foto de frente (0.245 × 0.55 m).
  - **Tratamiento:** se rectificó, se quitó el brillo azulado de la ventana (`flatten_lighting`) y se hizo repetible.
  - **Color:** el tono es el de la cámara con luz de día. La luminosidad sale de los muebles altos contra la pared pintada de al lado, en el mismo plano: **(108, 112, 116)**.
- **Cubierta** (`laminado-cubierta`): la foto tiene el reflejo de la ventana en casi toda la cubierta. Las zonas oscuras con la silueta del dueño son justo donde su cuerpo tapó el reflejo, así que ahí se ve el laminado real.
  - **Lo que no sirvió:** se probó restar el velo del reflejo (`percentile` y por zonas), pero los bordes de la silueta seguían notándose.
  - **Cómo se armó:** con 2 trozos de la franja sin reflejo, en 4 hileras desplazadas y volteadas (`compose`). Funciona porque la veta corre a lo largo. Cada trozo se nivela por filas y columnas (`level_px`), y eso quita las bandas de luz en los empalmes sin borrar las fibras.
  - **Color:** **(74, 74, 77)**, relativo a la melamina de la foto tomada 16 s después (estimación).
- **Modelo** (`sources/cocina/cocineta.json`, `house_twin/kitchen.py`): los muebles son `IfcFurniture`, con cuerpo, frentes con juntas de 3 mm y jaladeras de barra.
  - **Cubiertas:** con zoclo trasero de 8 cm.
  - **Tarja:** de granito negro, con llave cuello de ganso.
  - **Estufa y refrigerador:** son `IfcElectricAppliance` negros, con colores supuestos.
  - **En el recorrido:** todo frena el paso.
- **Azulejo, cenefa y murales** (foto de frente):
  - **Escala:** el muro del fondo mide 2.85 m (plano) y 3085 px → ≈ 1082 px/m. La foto está derecha (verticales paralelas), así que la escala vertical es la misma; con la cubierta (0.90 m) como ancla, la cámara queda a ≈ 1.09 m.
  - **Hasta dónde llega el azulejo:** la línea que parecía el techo es el **remate del azulejo, a ≈ 2.23 m**; arriba hay pintura blanca y el techo queda fuera de la foto. Cubre los 3 muros del nicho de la barra, del piso a 2.23 m. Afuera del nicho, el muro es pintado.
  - **`azulejo-cocina`:** blanco brillante con veteado beige tenue, de **≈ 20 × 30 cm (supuesto)**: juntas cada 205–220 × 320–335 px. Es una columna de 1 × 2 azulejos recortada a la izquierda del mueble alto, sin el reflejo de la ventana y con los agujeros de taquetes tapados. El color se midió contra el muro pintado de arriba: (198, 202, 196).
  - **`cenefa-cocina`:** listelo de frutas de **≈ 20 × 5.5 cm a 1.24–1.29 m**. Una pieza tomada tal cual (es un diseño impreso) y repetida en los 3 muros.
  - **`mural-frutas`:** 2 murales iguales, de 2 azulejos (0.40 m) cada uno, sobre la cenefa y hasta el mueble alto (1.295–1.537 m). Su centro está en x = 2.02 y 3.55 m. Se tomó el mural derecho, que no tiene enfrente la llave de la tarja. En el modelo es una placa de 3 mm (`IfcCovering` CLADDING).
  - **Cómo se aplica:** `Finishes` acepta franjas (`up_to_m: [desde, hasta]`) y zonas en planta (`region_m`); entre capas del mismo espacio gana la franja más angosta. Blender corta los muros en esas alturas y zonas.
  - **Límite:** la cuadrícula se alinea con la junta de arriba de la cenefa. Debajo, las juntas reales quedan 5.5 cm más abajo.
- **Pendiente:**
  - el protector de vidrio detrás de la estufa;
  - el microondas con su repisa y la cortina;
  - el centro de carga en el costado derecho.

### 25. Sala: sofá en L y televisión (2026-10-09, fotos 13:40:54 y 13:41:14; 2026-10-07, 23:22 y 23:23)

- **Sofá (dato del dueño: 220 × 220 cm):** es modular, en L, con 2 reclinables en las puntas, una cuña en el rincón y 1 asiento más por lado.
  - **Posición (fotos):** el lado largo tiene el respaldo contra el muro de la recámara 3 (y = 7.93 m) y el brazo derecho junto al escalón del tragaluz (x = 8.45 m), así que su esquina queda en x ≈ 6.23 m (± 0.3 m). El otro lado sale hacia el comedor con el respaldo libre, como en la foto desde la mesa.
  - **Medidas supuestas:** profundidad 0.95 m, asiento a 0.48 m, respaldo a 1.00 m y brazos de 0.16 m. Son las comunes de un sofá reclinable.
  - **Modelo:** `IfcFurniture` (`sources/sala/sala.json`, `house_twin/living.py`), con cojines separados por una junta. En el recorrido frena el paso.
- **Tela (`tela-sofa`):** tejido jaspeado gris. Es el centro del respaldo en la foto de cerca, sin el vivo de arriba ni la sombra de abajo, sin la caída de luz y repetible.
  - **Escala:** ≈ 5500 px/m (el cojín ocupa el ancho de la foto).
  - **Color:** **(150, 153, 159)**, medido en la foto de conjunto de día contra el muro de atrás. En la foto de cerca el muro está en sombra y no sirve.
- **Televisión (dato del dueño: 75")**: pantalla de 1.66 × 0.93 m (`IfcAudioVisualAppliance`).
  - **Posición:** en el muro del fondo (este, x = 9.763 m), centrada a 1.93 m de la esquina con el muro de la entrada (y ≈ 5.35 m), con el borde de abajo a ≈ 1.16 m.
  - **Cómo se midió:** en la foto desde el comedor, ese muro de 3.21 m da ≈ 134 px/m y el de 2.60 m de alto ≈ 131 px/m. Las 2 escalas coinciden.
- **Comedor (dato del dueño: mesa de 200 × 110 cm; fotos del 2026-10-09):** una mesa con 6 sillas: 2 por lado y 1 en cada cabecera.
  - **Posición (fotos):** el lado largo va hacia el muro de la entrada. La silla de la cabecera queda frente a la ventana V01 y las del lado poniente, metidas bajo la mesa, a ≈ 5 cm del muro (x = 3.285 m). Con eso, la mesa queda centrada en x ≈ 4.20 m, y ≈ 5.20 m (± 0.2 m).
  - **Medidas supuestas:** altura de 0.76 m, 2 pedestales y sillas comunes (asiento de 0.46 m a 0.47 m de alto, respaldo a 1.00 m). El respaldo calado y curvo se simplifica a un marco con tablilla.
  - **Colores (contra el muro, con la luz de la ventana):** la madera **(60, 44, 37)**, medida en el respaldo y la tablilla de las sillas, y el tapiz de los asientos **(83, 71, 63)**.
  - **Plano:** el bloque `COMEDOOR` del plano la pone en otro lugar (x = 3.55–6.03, y = 4.41–6.24); manda la foto.
- **Pendiente:** la mesa de centro de vidrio, las cortinas grises de la entrada y de las ventanas, el perchero de la entrada y el contacto bajo la TV (no está en el plano).

### 26. Recámara mayor: closet abierto, cama, buros, escritorio y televisión (2026-10-09)

- **Qué cuarto es:** el dueño la llama «recámara 2», pero por las fotos es la que el plano rotula RECAMARA 1 (S02): tiene 2 ventanas al patio (V06 y V07) detrás de la cabecera y el closet junto a la puerta. En el modelo, S03 (la del closet de 4 módulos con puertas) sigue siendo «Recámara 2». **Falta confirmarlo con el dueño.**
- **Closet abierto** (`pino-closet`): ocupa todo el frente del plano (F01, 2.95 m) y no tiene puertas, lo que confirma la nota de que «R1 no tiene puertas».
  - **Medidas:** con el frente del plano, la foto da ≈ 800 px/m. De ahí salen la cajonera de 5 cajones con 2 repisas, un colgador doble, una torre de 7 repisas, un colgador abierto y el entrepaño corrido a 1.90 m (± 3 cm).
  - **Textura:** la cara de un cajón, rectificada. Medida contra el pilar pintado.
- **Cama de latón:** la cabecera va contra el muro del patio, entre las ventanas (centro x ≈ 8.20 m).
  - **Forma:** postes negros con perillas y anillos de latón; barrotes, travesaños y arillos de latón.
  - **Supuestos:** el tamaño matrimonial (1.37 × 1.90 m) y las alturas comunes.
- **Buros:** 2, negros, de 2 cajones con jaladeras de latón, a los lados de la cabecera (medidas comunes).
- **Escritorio:** en la esquina del muro de la TV con el muro oriente, con pedestal blanco (1.20 × 0.60 m, supuesto).
- **Televisión (dato del dueño: 75")**: pantalla de 1.66 × 0.93 m, centrada en el muro de la puerta, con el centro a ≈ 1.97 m del piso. La foto había hecho estimar 85" por la perspectiva del gran angular.
- **Minisplit:** en el muro oriente, junto a la esquina con el muro del patio y cerca del techo (0.82 × 0.29 × 0.20 m, tamaño común supuesto), como `IfcUnitaryEquipment` SPLITSYSTEM.
- **Sin modelar:** la ropa, los peluches, el telescopio, la silla, el póster y las cortinas negras.

## Recorrido del interior (2026-10-08, fotos de conjunto)

Fotos de conjunto en `sources/fotos/` (fuera de git): `bano-general`, `bano-regadera`, `sala-comedor-1`, `comedor-hacia-cocina`, `comedor-hacia-sala`, `sala-hacia-comedor`, `cocina-frente`, `cocina-sala`, `cocina-cortina`, `pasillo-recamaras` y `closet-3`. Todas son de noche, con gran angular y luz de los focos. No sirven para texturas, sí para confirmar el modelo y encontrar lo que falta.

### Confirma lo que ya está en el modelo

- **Piso:** loseta beige del interior en sala, comedor, cocina, pasillo, recámaras y baño, con **zoclo de loseta** en todos los muros.
- **Muros:** yeso liso y blanco, salvo los azulejos de baño y cocina.
- **Baño:**
  - **Regadera y muros:** la regadera tiene el **mismo azulejo** beige marmoleado que el resto del baño, del piso al techo y en todos los muros. Las piezas «grises» de la foto del piso eran el mismo azulejo en sombra, así que la textura `azulejo-bano` aplica a todo el baño.
  - **Piso de la regadera:** el mosaico antiderrapante ocupa todo el rectángulo de la regadera. La separan una cortina y una barra; no se ve canceles ni escalón alto.
  - **Ventana alta (V09):** está sobre la regadera, con **vidrio texturizado traslúcido** (no claro) y marco negro. Coincide con el antepecho alto del plano (1.28 m).
- **Puertas de madera:** las de las recámaras y el medio baño se ven iguales a la de la foto 1.
- **Puerta de la cocina (D04):** se ve en la cocina a la izquierda, con su retícula y herrería.

### Nuevo o distinto del plano

- **Techo:** todo el interior tiene **tirol** (rugoso).
  - En la sala y el comedor se ven **líneas rectas paralelas y fisuras** que cruzan el plafón. Pueden ser las juntas de una losa de **vigueta y bovedilla** (pista para U02) o fisuras del aplanado.
  - Hay manchas en el comedor, cerca del muro de la cocina. Posible humedad: conviene revisarlas.
- **Luminarias:** son **portalámparas de porcelana con foco desnudo** al centro de cada zona, no spots empotrados.
  - Se ven 2 en la sala y el comedor, 1 en la cocina, 1 en el pasillo y 1 en la zona de la mesa.
  - El DXF trae 9 «spots» en `23- ILUMINACION`: probablemente marcan la **posición**, pero el tipo de luminaria es este.
- **Cocina:**
  - **Gabinetes:** altos y bajos de **melamina gris oscuro con veta**, distinta del wengué de los closets, con jaladeras de barra.
  - **Cubierta y equipo:** cubierta negra brillante (tipo granito), tarja negra, estufa Mabe de 6 quemadores negra y refrigerador negro.
  - **Azulejo:** blanco brillante hasta ≈ 2 m (pintura blanca arriba), con **cenefa de frutas** a la altura de la cubierta y **2 paneles de talavera** con frutas sobre ella.
  - **Centro de carga:** en el muro derecho de la cocina. Hay que compararlo con la capa `GAS` del DXF.
- **Sala:**
  - **Ventana negra con retícula**, en un **entrante en ángulo**. El dueño confirmó que es la ventana del tragaluz hacia la sala: **V10**, en el muro diagonal W32 (1.07 m), que el plano no dibuja. Medidas y retícula: ver la sección 15 (la estimación de esta foto, 0.8 × 1.1 m, quedó corregida).
  - En la sala también se ven la puerta de entrada D03 por dentro y dos cortinas grises a sus lados, que tapan las ventanas V01 y V02.
- **Cortina negra entre la cocina y el comedor:** cuelga junto al refrigerador. El dueño confirmó que solo tapa la ventana que hay ahí, la de la cocina más cercana al comedor: **V04** (x = 2.30–2.81 m en W21). No es un vano nuevo.
- **Pasillo de las recámaras:** angosto, con 3 puertas de madera y foco al centro. Coincide con el «pasillo a las recámaras» incluido en S01.

### Recámara con closet y una ventana (fotos `recamara-a-1` a `recamara-a-4`)

- **Es la Recámara 3** (confirmado por el dueño) y la ventana es la **V05**, al tragaluz. Por ella se ven el muro azul claro del tragaluz y, al fondo, el vano de V10 hacia la sala.
- **La ventana confirma el plano:** medida por proporción contra la altura de 2.60 m, el antepecho queda en ≈ 0.8 m y la parte alta en ≈ 2.05 m. El plano da 0.86 m y 2.12 m, dentro del error de la foto.
- **Detalles de la ventana:** corrediza de 2 hojas, aluminio negro y vidrio claro. Por dentro no tiene herrería. Arriba lleva una **persiana enrollable con caja de aluminio, por dentro**: la «persiana plata» de la foto de la ventana era esta, no una exterior.
- **Acabados:** loseta del interior con zoclo, yeso blanco y techo de tirol. La puerta es la de pino de la foto 1. El closet es de melamina wengué, con 2 módulos completos a la vista y maleteros.
- **Instalaciones:** foco en portalámparas al centro. Hay apagador de placa negra junto a la puerta y un contacto alto sobre la TV.
- **Daño en el muro de la ventana:** en la parte baja, sobre el zoclo, hay manchas rojizas, pintura descascarada y aplanado dañado a lo largo de todo el muro. Es típico de **humedad por capilaridad (salitre)**. El tragaluz está **abierto al cielo** (U10, dato del dueño): la lluvia que cae ahí es la causa probable. Conviene revisar el desagüe y la impermeabilización de su base.
- **Uso actual:** oficina, con escritorio de pie, monitores y caminadora. Es mobiliario, no acabado.

### Muebles vistos (para una capa de mobiliario, no son acabados)

- **Sala:** sala en L gris reclinable y mesa de centro redonda de vidrio.
- **Comedor:** mesa de comedor oscura con 6 sillas talladas.
- **Muro de la sala:** TV de pared.
- **Ventanas de la sala:** cortinas grises. La ventana de la cocina junto al refrigerador lleva cortina negra.

## Fachada y orientación (2026-10-08, 08:12–09:29)

Fotos: `fachada-1.jpg` y `fachada-2.jpg` (gran angular de 13 mm, desde la calle) y `brujula.jpg` (captura de una app de brújula tomada en el pórtico, frente al muro de V01, V02 y D03).

### Orientación (medida del dueño)

- **Lectura de la brújula:** rumbo **207° (SSO)**, con la cámara apuntando de frente al muro W07, es decir, de la calle hacia el fondo del lote (+Y del modelo).
- **Hacia dónde mira la fachada:** hacia la calle, **27° (NNE)**.
- **Coordenadas que reporta la app:** 25°22'47" N, 101°00'36" O (Saltillo).
- **Consecuencias para la luz del sol:** la fachada casi no recibe sol directo (solo de mañana en verano). El patio del fondo mira al SSO y recibe el sol de la tarde.
- **Cautelas:**
  - No sabemos si la app da el norte magnético o el verdadero. En Saltillo la diferencia es de unos pocos grados al este.
  - La intensidad que muestra (39 µT) parece algo baja para el campo de la zona. La herrería de la ventana pudo desviar la lectura.
  - Conviene repetir la medición lejos de metal, con el celular paralelo a la banqueta.

### Composición observada

- **Volumen:** una planta con losa plana. Arriba lleva un **pretil con cornisa moldurada** y el número **134** pintado en la cornisa y en el poste izquierdo.
- **Cochera (izquierda):**
  - **Portón de herrería de dos hojas** del mismo estilo que las puertas del pasillo: barrotes torcidos y lisos con adornos, arillos arriba y lámina abajo.
  - Detrás se ven las ventanas de la cocina (V03, V04) con **protecciones de herrería** y, al fondo, la puerta del pasillo de servicio.
  - **Medidor de luz y un registro** en el poste izquierdo.
- **Frente del pórtico (centro):** **no es un muro ciego**, como lo da el plano (W03 solo con la puerta D01). Tiene un murete de antepecho, pilastras, **dos aberturas grandes cerradas con herrería** (barrotes, arillos y adornos) y la **reja peatonal** al centro (D01). Encima hay una trabe.
- **Bodega (derecha):** muro ciego.
- **Protecciones:** todas las ventanas que se ven tienen protecciones de herrería por fuera.
- **Remate:** gárgolas o tubos de desagüe en el pretil, una luminaria de muro junto al número, una antena en la azotea y cables de la calle.
- **Acabado exterior:** pintura blanca sobre **aplanado rugoso tipo zarpeo o tirol rústico** (grano grueso, visible de cerca en la base y en la foto de la brújula). Es distinto del yeso liso del interior y le falta textura.
- **Exterior inmediato:** la banqueta es del mismo concreto escobillado en ondas, la guarnición tiene restos de pintura amarilla y hay plantas creciendo en la junta con el muro.

### Estimaciones (no son medidas)

Si se supone que la reja peatonal mide 2.10 m de alto, la foto 2, casi frontal, da:

| Elemento | Altura estimada |
|---|---|
| Antepecho de las aberturas del pórtico | ≈ 0.98 m |
| Parte alta de las aberturas | ≈ 2.15 m |
| Remate de la cornisa | ≈ 2.8–2.9 m |

Esto es coherente con los 2.60 m de piso a techo más la losa y el pretil.

### A revisar con el dueño

- **Posición de la reja peatonal:** en la foto parece ≈ 0.5 m más a la izquierda de donde el plano pone D01 (x = 6.17–7.15 m). Con gran angular y sin vista frontal limpia no es concluyente.
- **Detrás de la abertura derecha del pórtico** se ven una ventana pequeña con protección y un vano oscuro. El plano no tiene ninguna ventana entre D03 y la bodega: podría ser una ventana del medio baño que el plano no dibuja.

## Aplicación al modelo (2026-10-08)

`python -m house_twin.cli scene --render` abre el IFC con Bonsai, aplica las texturas y guarda `models/existing.blend`.

- **Muros:** cada cara toma el acabado del espacio al que mira. El baño lleva azulejo y el resto del interior, yeso blanco. Pasillo de servicio, patio y cochera llevan aplanado, y pórtico y fachada, estuco. Los muros se cortan en los límites de los espacios, porque una misma cara puede dar al baño y al pasillo. Las mochetas de los vanos toman el acabado del lado interior.
- **Pisos:** nuevos `IfcCovering` (FLOORING) de 1 cm bajo el nivel 0, uno por espacio, con su material (`piso-interior` o `piso-exterior`).
- **Puertas y ventanas:** el IFC lleva su material; las de vidrio, como `IfcMaterialConstituentSet` (Hoja/Marco + Vidrio). Las puertas estiran la foto a todo el vano. Las ventanas son corredizas de 2 hojas, con perfil de 4.5 cm y traslape central de 6 cm (**supuesto**).
- **Escala real:** las coordenadas de textura se calculan en metros y cada textura se repite según su `size_m`.
- **Luz de la vista previa:** sol a 150° de rumbo y 50° de altura (media mañana de octubre, aproximado). La orientación sale de la brújula del dueño: la fachada mira a 27°.

| Aérea | Sala hacia la cocina | Pasillo de recámaras | Baño |
|---|---|---|---|
| ![](05-renders/aerea.jpg) | ![](05-renders/sala-cocina.jpg) | ![](05-renders/pasillo.jpg) | ![](05-renders/bano.jpg) |

**Pasillo de recámaras (dato del dueño, 2026-10-08):**
- **Medida:** mide **1.10 m** de muro a muro; el plano da 1.21 m entre W18 y W16. Queda registrado como medida M01, con aviso en `source_warnings`. La geometría todavía no se movió, porque falta saber qué muro está corrido.
- **Loseta:** caben 3 enteras de 30 × 30 cm, una medida que el dueño confirma. Según la foto `pasillo-recamaras`, las juntas arrancan en el muro del baño y el corte de ≈ 20 cm queda junto a la recámara 3. La textura del piso se alinea a ese muro (`grid.origin_m`).

**Sin acabado todavía** (salen en gris violáceo para que se noten):
- **Muros de la lavandería S13:** ninguna textura la incluye. ¿Llevan el mismo aplanado que el pasillo y el patio?
- **D01** (reja peatonal del pórtico): falta su foto.

**Con textura, pero sin geometría en el modelo:**
- `closet-madera`: falta el closet de R1 (sin puertas).

**Falta para un render fiel:**
- Zoclo, persianas y cortinas.

## Pendientes del dueño

1. **Aplanados exteriores:** foto de cerca del estuco de la fachada y el pórtico, con luz rasante y algo de tamaño conocido, para reemplazar la textura sintética. ¿Dónde se tomó la foto 07:47:26 (aplanado de grano fino con estrías)?
2. **Medidas:** ancho y alto de la hoja de una puerta de recámara y de una de baño. Para saber qué muro del pasillo está corrido: ancho interior del baño (el plano da 1.25 m) y de la recámara 3 de este a oeste (el plano da 4.07 m).
3. **Puerta D04:** ¿aluminio o acero? ¿Su vidrio es claro?
4. **Closets:** foto del de la recámara 1 (sin puertas: ¿entrepaños, tubo?); del de la recámara 2, el ancho de un módulo para confirmar el reparto. Una foto del techo de tirol de cerca.
5. **Puertas de herrería del pasillo (D10, D11):** alto, del piso a lo más alto del marco (estimado ≈ 1.90 m). La posición ya está. **Portón de la cochera (D12):** alto con cinta (estimado ≈ 2.23 m).
6. **Baño:** medida del azulejo y hasta qué altura llega (¿al techo o a media altura?), y en qué muros está (¿todo el baño o solo la regadera?). Medida de la loseta antiderrapante y del área de la regadera. ¿El muro de la regadera tiene otro azulejo?
7. **Puerta D03:** ancho de la hoja (¿hay un marco fijo a la izquierda?) y qué tan oscuro es el polarizado (¿se ve hacia adentro de día?).
8. **Ventanas:** ¿todas tienen persiana enrollable? ¿La hoja fija tiene vidrio entintado o película?
9. **Calibración de color:** una foto de día del piso con una hoja blanca tamaño carta encima.
10. **Lavandería:** ¿qué acabado tienen sus muros? **V10:** medir ancho, alto y antepecho con cinta (hoy son una estimación con fotos).
11. **Fotos nuevas:** el azulejo y la cenefa de la cocina de frente, la cara exterior de las puertas y los acabados exteriores (pendientes para mañana).
