# Consideraciones de Diseño – Visualización del Pipeline de Producción IA

## Contexto
El sistema utiliza un modelo de datos **vertical** (1 fila = 1 artefacto) para registrar planning, prompts, imágenes, clips y sus iteraciones.

Este modelo es **correcto para máquinas**, pero **ruidoso para humanos** si se muestra directamente como una tabla larga.

El objetivo de este documento es definir **cómo debe verse el sistema**, no cambiar la base de datos.

---

## Principio Central
> **La base de datos NO es la interfaz.**

El modelo vertical debe tratarse como un **Log de Producción Vivo**, mientras que los humanos necesitan **vistas jerárquicas, silenciosas y orientadas a decisión**.

---

## Error a Evitar
- Usar la tabla vertical como vista principal
- Mostrar todas las iteraciones al mismo nivel
- Forzar a humanos a interpretar logs técnicos
- Asumir que “más datos visibles = más claridad”

---

## Modelo Mental Correcto (para humanos)

Un humano piensa en esta jerarquía:

SHOT
├─ Planning
├─ Prompt
├─ Images (Start / End)
└─ Clip (Final)

yaml
Copiar código

No en filas.

La interfaz debe reflejar **estructura + causalidad**, no eventos planos.

---

## Regla Clave de Diseño Visual
> **Un humano no debería ver más de 7 artefactos a la vez por Shot.**

Todo lo que exceda eso debe:
- Colapsarse
- Agruparse
- Ocultarse
- O moverse a una vista secundaria

---

## Concepto Crítico: “Selected”
Introducir un campo fuerte:

### `Selected = true`

Solo debe existir **uno activo por nivel lógico**:
- 1 Planning activo
- 1 Prompt activo
- 1 Image Start seleccionada
- 1 Image End seleccionada
- 1 Clip Final

### Impacto Visual
- Lo seleccionado se muestra **en primer plano**
- Lo no seleccionado:
  - Se atenúa (gris)
  - Se colapsa
  - Se oculta por defecto

👉 Esto elimina el 80% del ruido cognitivo.

---

## Separación de Capas (Obligatoria)

### Capa 1 — Vista “Shots” (Panel Principal)
**Propósito:** Decisión rápida

- 1 fila = 1 Shot
- Información visible:
  - ShotID
  - Estado global (derivado)
  - Clip final (thumbnail)
  - Acción siguiente (Review / Regen / Done)

🚫 No mostrar prompts, imágenes ni intentos aquí.

---

### Capa 2 — Vista “Shot Detail” (Árbol Controlado)
**Propósito:** Revisión creativa

Estructura:
- Planning (1 bloque)
- Prompt (lista corta, estados visibles)
- Images Start / End (thumbnails seleccionadas + colapsables)
- Clip final destacado

Comportamiento:
- Mostrar solo lo seleccionado por defecto
- Iteraciones fallidas colapsadas
- Expansión manual bajo demanda

---

### Capa 3 — Vista “Artifact Stream” (Técnica)
**Propósito:** Debug / Auditoría / Agentes

- Tabla vertical completa
- Todas las filas
- Todos los intentos
- Todos los metadatos

⚠️ No es una vista humana por defecto.

---

## Regla de Trazabilidad (No Negociable)
> **Un clip final debe poder explicar su genealogía en máximo 2 pasos.**

Ejemplo:
- Clip Final
  → Image Start / End seleccionadas
    → Prompt activo
      → Planning

Si esto no es posible, el diseño está incompleto.

---

## Metáfora Correcta
- Esto NO es una hoja de cálculo
- Es un **árbol de decisiones colapsable**
- O un **pipeline con estados dominantes**

Pensar más en:
- Árbol
- Pipeline
- Kanban jerárquico

Pensar menos en:
- Tablas largas
- Logs planos
- Reporting tradicional

---

## Conclusión
- El modelo vertical es correcto y no debe eliminarse
- El ruido proviene de una visualización incorrecta
- La solución es **cambiar la vista por defecto**, no los datos
- Humanos ven **estructura y selección**
- Máquinas ven **logs y eventos**

Diseñar la interfaz como un **tablero de piloto**, no como el **registro interno del motor**.