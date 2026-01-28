# Reencuadre Estratégico: Antigravity como Orquestador Creativo en Esteroides

## Objetivo
Queremos que Antigravity no sea solo una fábrica técnica, sino un **sistema de orquestación creativa con gates editoriales duros**, equivalente a nuestra orquestación con múltiples GPTs, pero ejecutable, reproducible y escalable.

La meta es:
- Mantener TODAS las garantías creativas y de identidad que hoy logramos manualmente.
- Convertirlas en contratos explícitos, artefactos revisables y gates automáticos.
- Usar Antigravity como motor industrial, no como generador “best effort”.

---

## 1. Principio Rector (no negociable)
**Nada pasa a la siguiente etapa sin aprobación explícita humana.**  
La fábrica no “fluye sola”. Se avanza por disparos conscientes.

---

## 2. Estructura Creativa que debe reflejar el pipeline

Antigravity debe mapear explícitamente este modelo mental:

- El video NO es una secuencia plana de shots.
- Es una **narrativa por bloques** (ej. B01–B10), cada uno con:
  - intención clara,
  - metáfora dominante,
  - contrato visual,
  - estado A → estado B (resultado visible).

👉 Esto debe reflejarse en los artefactos (`shot_spec`, `nanobanana_requests`), no solo en la cabeza del LLM.

---

## 3. Gates equivalentes a nuestra orquestación (hard requirements)

### Gate 0 — Alignment REAL (antes de cualquier cosa)
- Alignment Gateway real es obligatorio.
- Si falla → ERROR y STOP.
- El fallback a Mock solo puede existir en `--mode simulation`.

**Contrato:**
- `alignment.source == FORCED_ALIGNMENT`
- `fallback_used == false`
- Si no se cumple, el pipeline aborta.

---

### Gate 1 — Preview Editorial (sin costo, antes de prompts finales)

**Stage:** `planning`

**Artefacto esperado:**
- `shot_spec.jsonl` organizado por BLOQUES, no solo por orden.
- Cada toma debe incluir explícitamente:
  - bloque narrativo,
  - objetivo de la toma,
  - metáfora,
  - duración real (alineada al audio),
  - número máximo de cambios A→B,
  - rol dramático (problema / fricción / desbloqueo / resultado).

**Regla:**
- Si una toma no tiene A y B definidos como estados estáticos → RECHAZADA.

👉 Este artefacto se revisa y se aprueba ANTES de generar prompts.

---

### Gate 2 — Preview de Especificación (prompts congelables)

**Stage:** `prompts`

**Artefacto canónico:**
- `nanobanana_requests.jsonl` es el “prompt final imprimible”.

Debe contener de forma verificable (no implícita):
- start_frame / end_frame,
- props_count <= 2,
- accent_color único (red OR green),
- reglas “no texto / no UI”,
- constraints del mannequin,
- plan A→B explícito (máx 2 cambios).

**Regla clave:**
- Este archivo se **congela** tras aprobación.
- Images y Clips deben consumir ESTE archivo, no regenerarlo.

👉 Aquí ocurre la aprobación editorial fuerte.

---

### Gate 3 — Preview Visual (imágenes reales, sin animación)

**Stage:** `images --mode real`

**Comportamiento requerido:**
- Genera PNGs reales (full HD).
- Se detiene automáticamente.
- NO ejecuta clips ni assembly.

**Validación humana:**
- Identidad visual correcta.
- Cumplimiento estricto del style contract.
- Claridad A→B.
- Sin texto, sin UI, sin props extra.

👉 Si falla una imagen, se reintenta SOLO Stage 3.

---

### Gate 4 — Producción (animación + assembly)
Solo se ejecuta si Gate 3 fue aprobado explícitamente.

---

## 4. QC que Antigravity debe hacer automáticamente (antes de gastar)

### QC de Especificación (JSON-level, barato)
Antes de images:
- props_count > 2 → FAIL
- más de un accent → FAIL
- falta start/end → FAIL
- cambios A→B > 2 → FAIL
- flags de “texto/UI permitido” → FAIL

👉 Esto reemplaza la vigilancia manual que hoy hacemos con GPTs.

---

## 5. Diferencia clave respecto al estado actual
Hoy Antigravity:
- garantiza que el pipeline corre.

Lo que pedimos:
- que garantice que **el resultado no puede violar identidad, narrativa ni contrato visual**,
- incluso aunque el LLM “se equivoque”.

Eso es lo que hoy nos da nuestra orquestación humana.

---

## 6. Resultado esperado (definición de éxito)
Consideramos que Antigravity está “alineado en esteroides” si:

- Podemos aprobar:
  1) shotmap,
  2) spec/prompts,
  3) imágenes,
  antes de animar.
- El sistema NO avanza solo.
- No existen mocks silenciosos que invaliden decisiones creativas.
- Cada salida es revisable, congelable y trazable por hash.

---

## 7. Pregunta final para ustedes
Con lo que existe hoy (stages + manifests + QC):
- ¿Qué de lo anterior ya está cubierto?
- ¿Qué requiere solo cambios de runbook?
- ¿Qué requiere cambios mínimos de código?

Nuestra intención no es rehacer Antigravity,
sino **convertirlo en la versión industrial de nuestra orquestación creativa**.
