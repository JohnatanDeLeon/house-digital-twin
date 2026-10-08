# Fase 3: el DXF original como fuente primaria

Fuente: [`data/raw/plano.dxf`](../../data/raw/plano.dxf), subido por el dueño en el PR #1. Es un AutoCAD 2018 (`AC1032`) de 10.5 MB.
Desde esta fase, `python -m house_twin.cli build` construye el modelo **desde el DXF**. El PDF queda como validación:

```bash
python -m house_twin.cli compare sources/casa-jonhy-levantamiento.pdf data/raw/plano.dxf
```

## Hallazgos

### 1. Las unidades declaradas están mal

- El encabezado dice `$INSUNITS = 4` (milímetros).
- Los muros miden 10.03 × 21.25 unidades: el dibujo está **en metros**.
- El lector ahora verifica que las unidades declaradas den una casa de tamaño plausible. Si no, las infiere y lo registra en `source_warnings` del JSON de hechos.
- Sin esta verificación la casa habría medido 1 cm.

### 2. La cota de 10.00 m del frente está forzada

| Cota | Texto | Distancia medida en el dibujo |
|---|---|---|
| Frente (dos cotas) | `10.00` (sobrescrito a mano) | **10.03 m** |
| Fondo | 21.25 | 21.25 m |

- Esto explica la discrepancia que veíamos en el PDF (10.023 m).
- Queda como pregunta U07: ¿el frente real (escrituras) es 10.00 o 10.03?

### 3. El DXF confirma lo extraído del PDF

| | PDF | DXF |
|---|---|---|
| Terreno | 10.023 × 21.235 m | 10.03 × 21.25 m |
| Espacios | 10 | 10 (los mismos) |
| Vanos | 18 | 18 (los mismos; ninguno nuevo) |
| Mayor diferencia de área por cuarto | — | 0.07 m² (exterior: 0.12 m²) |
| Mayor diferencia de ancho de vano | — | 2 mm |

- El PDF salió ~0.1 % más chico de forma sistemática, por el ploteo "ajustado a hoja".
- Las coordenadas del DXF son exactas (por ejemplo, caras de muro en 6.705, 10.225 y 12.625 m).
- Los límites de las zonas exteriores que dio el dueño ahora siguen esas caras.

### 4. Lo que trae el DXF y el PDF no imprimió

| Capa | Contenido dentro del lote |
|---|---|
| `5 CORTES` (nombre engañoso) | 12 bloques `CONTACTO` y 8 `APAGADOR SIMPLE` |
| `23- ILUMINACION` | 9 salidas de spot y los arcos de sus circuitos |
| `GAS` | 1 bloque `CENTR` (centro de carga) |
| `12-TEXTOS` (fuera del lote) | simbología eléctrica: acometida, medidor, contactos, spots, centro de carga, interruptor de seguridad |
| `PUERTAS` | 9 bloques `PUERTA` con punto de inserción y giro |
| `0 NIVELES` | 10 bloques `NIVEL 2` con el NPT como atributo |

- **No hay capa de estructura.** Castillos, columnas, trabes y muros de carga siguen siendo desconocidos (U03).
- La instalación eléctrica todavía **no** se incorpora al modelo de hechos. Queda para una fase posterior.

## Modelo resultante (desde el DXF, con los datos del dueño)

13 espacios, 40 muros y 19 vanos (9 puertas, 9 ventanas dibujadas y la V10 declarada por el dueño). Áreas principales:

| Espacio | Área libre (m²) |
|---|---|
| Cocina + Sala + Comedor | 42.89 |
| Recámara 1 | 16.15 |
| Recámara 2 | 15.26 |
| Recámara 3 | 15.03 |
| Baño | 2.94 |
| Bodega | 1.99 |
| 1/2 Baño | 1.46 |
| Tragaluz | 1.15 |
| Patio | 47.25 |
| Cochera | 19.55 |
| Pórtico | 16.15 |
| Pasillo de servicio | 5.95 |
| Lavandería | 3.88 |

Las tablas detalladas de [02-modelo-de-hechos.md](02-modelo-de-hechos.md) se calcularon desde el PDF. Difieren de estas en centésimas de m².
