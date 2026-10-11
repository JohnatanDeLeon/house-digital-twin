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
- **Dónde va (corrección del dueño):** en el closet de la recámara 3, **colgada en vertical como una prenda real**. El closet solo tiene esta prenda; la ropa genérica se quitó.
  - **Colgada** (`playera-venom-colgada`): sale de los mapas de la playera extendida con las mangas caídas (`house_twin/hanging.py`, comando `hang`; no necesita la foto). Queda de 0.70 m de ancho en vez de 0.96 m extendida.
    - **Cómo cae la manga:** sigue cosida a la sisa y su eje baja de su ángulo en la foto a **60° bajo la horizontal** (supuesto: así cae una playera de algodón en un gancho). Cae por fuera del cuerpo, sin montarse encima.
    - **Corrección del dueño (2026-10-10):** antes cada manga giraba 90° como pieza rígida sobre un punto del costado y quedaba encima del cuerpo, con escalones en el hombro: «parecen dobladas».
  - **En el tubo:** cuelga del tubo de arriba del módulo 3 con su gancho, de canto y perpendicular al tubo, como cualquier prenda en un closet. Desde el cuarto se ve su costado (el hombro, la manga cercana y la orilla), no el estampado: el frente mira al costado del closet. Antes iba girada 30° hacia el cuarto para que se viera el estampado; el dueño pidió la perspectiva real (2026-10-10).
  - **Apretada en el fondo:** colgada mide 0.70 m de manga a manga, y como el gancho va a la mitad del fondo, de él a las hojas solo hay 0.28 m. Como en un closet real, la tela se aprieta: `display_parts` angosta la placa a lo que cabe (0.55 m, con 1 cm libre hasta las hojas) y el recorrido le devuelve su ancho al sacarla y la vuelve a apretar al guardarla.
  - **Frente y espalda:** son 2 placas delgadas con la misma silueta. La espalda es la tela sin el estampado, rellenada con el color de la tela de alrededor; no hay foto de la espalda.
- **Interacción en el recorrido** (`DATA.items`): con el módulo 3 abierto y mirando una playera aparece «Sacar la playera de Venom plateada» o «… de la lengua roja» (E o el botón). Con 2 prendas en el mismo tubo se saca la que queda más al centro de la vista, y las piezas de cada una se juntan por id exacto (`playera-venom` es prefijo de `playera-venom-lengua`).
  - **Al sacarla:** se sostiene frente a los ojos, de frente y derecha. Se dibuja en un segundo paso (capa 1), para que la puerta abierta no la corte. Se voltea con R, el botón «Voltear» o la rueda del mouse, y se guarda con E: regresa sola a su gancho.
- **Límites:**
  - La orilla de abajo queda en el borde de la foto, así que el largo puede ser 1–3 cm mayor.
  - Los pliegues y la pelusa vienen de la foto; la placa es plana.
  - La espalda no se fotografió.

### 13. Playera de Venom de la lengua roja (imagen de producto, 2026-10-10)

- **Fuente:** el dueño mandó la imagen de producto de una tienda (de frente, sobre fondo blanco, 1164 × 1200 px), no una foto de la prenda en la casa. Va en `sources/fotos/playera-venom-lengua.jpg` (fuera de git) y se describe en `sources/texturas/playera-venom-lengua.json`.
- **Prenda:** playera negra de algodón, manga corta y cuello redondo. El estampado es la cabeza de Venom de perfil, en gris y blanco, con la lengua roja.
- **Estampado de tinta** (`finish: ink`): a diferencia del foil de la otra playera, la serigrafía se queda con los colores de la imagen y no es metálica.
- **Escala (supuesta, talla M):**
  - A lo ancho, el cuerpo mide 570 px y se supone un pecho de 0.52 m.
  - A lo alto, la imagen de catálogo viene estirada: con la misma escala la playera mediría 0.95 m de largo. El largo se fija en 0.72 m, del punto más alto del hombro al dobladillo.
  - Faltan las medidas reales de la prenda.
- **Dónde va:** colgada en el mismo tubo del módulo 3 del closet de R3, 14.5 cm a la izquierda de la plateada (posición supuesta). Va de canto y apretada contra las hojas, igual que la otra.
- **Colgada** (`playera-venom-lengua-colgada`): con las mangas a 60° bajo la horizontal mide 0.76 × 0.75 m.
- **Límites:**
  - La espalda es lisa, sin imagen.
  - Los colores son los del catálogo, no los de la prenda en la casa.

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
