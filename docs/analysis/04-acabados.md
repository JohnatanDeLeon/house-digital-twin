# Fase 4: acabados y texturas a partir de fotos

Fuente: 10 fotos del dueño, del 2026-10-07 (23:18–23:33) y del 2026-10-08 (07:47–07:56). Todas son de noche, con luz artificial cálida, sin flash, tomadas con un Samsung Galaxy S25 Ultra en gran angular (23 mm equivalente). Las originales están en `sources/fotos/`, fuera de git. Cada material se describe en `sources/texturas/<nombre>.json` y se genera en `assets/textures/<nombre>/` con:

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
| `puerta-entrada` | Mapas + opacidad para el vidrio | Puerta D03 (entrada a la sala) | Foto y dueño |
| `aluminio-negro` | Constante (color medido) | Marcos y hojas de V01–V10 | Foto; el dueño dice que todas las ventanas son de aluminio negro |
| `vidrio-claro` | Constante (supuesto) | Vidrios de las ventanas y de D04 | Supuesto |
| `vidrio-polarizado` | Constante (supuesto) | Vidrio de D03 | Dueño: «ventanal polarizado»; tono y transmisión supuestos |
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
  - El cerradero del pasador queda, porque va en el marco.

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

## Pendientes del dueño

1. **Medidas:** ancho y alto de la hoja de una puerta de recámara y de una de baño, y tamaño de la loseta del piso.
2. **Puerta D04:** ¿aluminio o acero? ¿Su vidrio es claro?
3. **Baño:** medida del azulejo y hasta qué altura llega (¿al techo o a media altura?), y en qué muros está (¿todo el baño o solo la regadera?). Medida de la loseta antiderrapante y del área de la regadera. ¿El muro de la regadera tiene otro azulejo?
4. **Puerta D03:** ancho de la hoja (¿hay un marco fijo a la izquierda?) y qué tan oscuro es el polarizado (¿se ve hacia adentro de día?).
5. **Ventanas:** ¿todas tienen persiana enrollable? ¿La hoja fija tiene vidrio entintado o película?
6. **Calibración de color:** una foto de día del piso con una hoja blanca tamaño carta encima.
7. **Fotos nuevas:** el azulejo y la cenefa de la cocina de frente, la cara exterior de las puertas y los acabados exteriores (pendientes para mañana).
