# Estrategia de Datos en Airtable: "Vertical Asset Stream"

## 1. El Concepto Visual
En lugar de tratar Airtable como una hoja de cálculo tradicional donde "1 Fila = 1 Shot", hemos implementado un modelo de **Flujo Vertical de Activos**.

### ¿Por qué?
En la producción de video con IA, un "Shot" no es una unidad atómica simple. Es una colección de intentos, iteraciones y artefactos intermedios.

**El problema del modelo "Horizontal" (Columnas):**
Si tuvieras una fila por Shot con columnas: `Prompt` | `Image 1` | `Image 2` | `Video`...
1.  **Iteración Limitada:** ¿Qué pasa si generas 10 variaciones de imagen para elegir una? ¿Creas 10 columnas? Se vuelve inmanejable.
2.  **Estados Mezclados:** Un Shot puede tener el Prompt "Aprobado" pero el Video "Fallido". Un solo campo de "Status" por fila no captura esta complejidad.
3.  **Metadatos Perdidos:** Cada imagen tiene su propia URL, Seed, y fecha de generación. Meter todo eso en una celda es imposible.

### Nuestra Solución: Modelo "Vertical" (Filas por Artefacto)
Cada cosa que el sistema genera es un **Registro Único** en la tabla.

Ejemplo de lo que ves ahora:
| Shot ID | Type | Role | Content/Visual | Status |
|---------|------|------|----------------|--------|
| S001 | Planning | - | "A door opens..." (Intent) | Done |
| S001 | Prompt | Start | "Cinematic shot of door..." | Done |
| S001 | Image | Start | [IMAGEN_1.png] | Done |
| S001 | Image | End | [IMAGEN_2.png] | Done |
| S001 | Clip | - | [VIDEO_FINAL.mp4] | Done |

## 2. Argumentos Clave de Diseño

### A. Trazabilidad Granular (Lineage)
Podemos ver la historia completa de un Shot agrupando por `ShotID`. Si el video sale mal, podemos subir la vista y ver:
- ¿Cómo era la imagen de origen? (Fila `Type=Image`)
- ¿Cómo era el prompt? (Fila `Type=Prompt`)
- ¿El prompt obedeció a la planificación? (Fila `Type=Planning`)

### B. Scalabilidad de Prompts y Variaciones
Si decidimos generar **5 videos** para el mismo shot con settings diferentes (para elegir el mejor), el sistema simplemente inserta 5 filas nuevas de `Type=Clip`. No hay que cambiar la estructura de la base de datos.
Esto permite "A/B Testing" de creatividad sin romper la tabla.

### C. Revisión Independiente
Puedes marcar el **Prompt** como "Rejected" mientras mantienes el **Planning** como "Done".
El sistema (Manager) puede leer estos estados independientemente. Si rechazas una imagen en Airtable, el pipeline podría saber automáticamente que debe regenerar *solo esa imagen*, sin tocar el resto.

## 3. Conclusión
Esta tabla no es solo un reporte final; es un **Log de Producción Vivo**.
Permite que el humano intervenga en *cualquier* punto de la cadena (corregir un prompt, cambiar una imagen) sin invalidar el resto del trabajo.
