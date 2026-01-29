# **FinanceVideoPlatform — System Flow & Business Logic (LOCKED: Clean Score Jump)**

**Este documento reemplaza el flow anterior.**  
Objetivo: que el sistema produzca un **Rough Cut** consistente con la Biblia LOCKED, **sin inventar criterio**, con QA automático y con optimización de costo (reuso/caché).

## **0) Principios no negociables (LOCKED)**

1. **La imagen nunca compite con el voiceover**: lo pacea y lo recompensa.  
2. **Cero humanos**: no personas, no manos, no siluetas, no ropa, no figurines.  
3. **Cero texto/markings**: no letras, no números, no símbolos, no logos, no QR/barcodes, no “grabados” ni emboss.  
4. **Amber solo en UNLOCK (L3)**. Fuera de UNLOCK = 0 amber.  
5. **Sistema cerrado** (micro-mechanics): el fluido nunca “sale al exterior” (no leaks/pouring/puddles).  
6. **QA gates = enforcement automático**: FAIL → RERENDER (máx 3 intentos → “needs manual prompt”).  
7. **Shot Menu cerrado (12 arquetipos)**: Royki/app no inventa arquetipos nuevos.

---

## **1) Visión general del pipeline**

**Entradas (obligatorias, juntas):**

* `script.txt` (VO final locked)  
* `voiceover.mp3` (VO final)  
* `style_bible_LOCKED.md` (Clean Score Jump 01172026)

**Flujo:**  
`Ingest & QC` → `Planning (Beat-Sheet + ClipPlan)` → `Prompts (Sanitize)` → `Init Frames (Generate/Reuse)` → `Clips (Veo 3.1)` → `Assembly (Rough Cut + Timeline)`

Nota clave: **no se generan fotos “a ciegas”**.  
Cada beat debe tener **ClipPlan (intención del clip)** antes de generar el init frame.

---

## **2) Artefactos (outputs) del sistema**

* `run_manifest.json`: metadata de corrida (hash de inputs, parámetros, estado por fase).  
* `vo_map.json`: mapa opcional de timestamps (para QC / referencia editorial, no para setear duraciones Veo).  
* `beat_sheet.jsonl`: 1 línea por beat (estructura + enums; sin texto prohibido en prompts).  
* `clip_plan.jsonl`: 1 línea por beat con intención de movimiento (acción única, cámara, intensidad).  
* `prompt_pack.jsonl`: `prompt_init_frame` + `prompt_clip` **ya saneados**.  
* `qc_report.json`: resumen de QA y rerenders.  
* `frames/beat_<id>.png`: init frames aprobados (o reusados desde cache).  
* `clips/beat_<id>.mp4`: clips Veo (8s).  
* `timeline.json`: timeline consecutiva de beats + mapping a VO (referencial).  
* `rough_cut.mp4`: concatenación de beats usando **solo 4s útiles por clip**.

---

## **3) Fase 0 — Ingest & QC (validación de inputs)**

**Objetivo:** asegurar consistencia y preparar el run.

**Lógica:**

1. Validar existencia y formato de `script.txt`, `voiceover.mp3`, `style_bible_LOCKED`.  
2. Calcular hashes (`script_hash`, `audio_hash`, `bible_hash`) y guardarlos en `run_manifest.json`.  
3. Leer constraints de Biblia y cargar configuración hard-locks + forbidden vocab + QA rules.  
4. (Opcional) Crear `vo_map.json` con forced-alignment **solo para referencia/QC**:  
   * Sirve para saber “qué parte del guion corresponde a qué ventana de audio”.  
   * **No** se usa para microajustar duración de clips Veo (Veo siempre 8s).

**Salida:**

* `run_manifest.json`  
* (Opcional) `vo_map.json`  
* `_INGEST_DONE.json`

---

## **4) Fase 1 — Planning (Beat-Sheet + ClipPlan)**

**Objetivo:** definir **qué beat va dónde** y **qué clip se pretende** antes de generar nada.

### **4.1 Beat-Sheet (estructura, no “texto creativo”)**

Cada beat define (en enums/IDs):

* `beat_id`, `sequence_index`  
* `verb`: EXPECTATION | TRACE | UNLOCK  
* `state`: LOCKED | NOISY | CLEAN | VERIFIED | UNLOCKED  
* `layer`: Blueprint | Evidence | Micro  
* `intensity`: L1 | L2 | L3  
* `shot_archetype`: 1..12 (cerrado)  
* `node_type_base`: GATE | FILTER | LEDGER  
* `node_role`: subtipo interno (ampliable sin romper node_type_base)  
* `amber_allowed`: bool (solo si verb=UNLOCK e intensity=L3)

El beat-sheet puede usar labels internas (como enums), pero **nunca** deben filtrarse al prompt con vocab prohibido.

### **4.2 ClipPlan (obligatorio antes de frames)**

Cada beat genera un `clip_plan` con:

* `action_intent` (una sola acción, coherente con arquetipo y layer)  
* `motion_profile` (qué se mueve vs qué queda estable)  
* `camera_behavior` (mínimo; “clarity-first”)  
* `constraints` (hard locks + cosas a evitar en ese beat)

**Hard rule:** si no existe `clip_plan` → **no se genera init frame**.

### **4.3 Política de duración (importante para montaje)**

* `veo_duration_s = 8` (siempre).  
* `usable_cut_s = 4` (default).  
* Cada beat define un `edit_window` recomendado dentro del clip de 8s.  
  * Default: usar una ventana estable (ej. del segundo 2 al 6), salvo que QA/heurística diga otra.

**Resultado esperado:**  
El rough cut será **más largo que el VO** (ej. VO 10 min → rough cut ~20 min). Esto es correcto: la **edición posterior** hace el conform.

**Salidas:**

* `beat_sheet.jsonl`  
* `clip_plan.jsonl`  
* `_PLANNING_DONE.json`

---

## **5) Fase 2 — Prompts (Prompt Pack + Sanitizer)**

**Objetivo:** producir prompts **técnicos y seguros** para generación, con intención clara.

### **5.1 Prompt Pack (dos prompts por beat, ambos saneados)**

Por cada beat:

* `prompt_init_frame` (Pass A): mundo limpio, sin evento.  
* `prompt_clip` (Pass B): agrega **una sola acción** (la del `clip_plan`).

### **5.2 Prompt Sanitizer (enforcement)**

El sanitizer corre SIEMPRE y hace:

1. **Bloqueo + reescritura** de vocabulario prohibido (noir/blueprint/UI/HUD/trace/unlock/verified/route/etc.).  
2. Inserta hard-locks obligatorios:  
   * NO-HUMANS positivo + negativo  
   * ANTI-TEXT/ANTI-MARKINGS positivo + negativo  
3. Inserta restricciones por layer:  
   * Evidence: still life anónimo, sin narrativa humana/detective  
   * Micro: sistema cerrado (sin leaks/pouring/puddles)  
4. Verifica amber:  
   * si `amber_allowed=false` → fuerza “0 amber”  
   * si `amber_allowed=true` → usa plantilla amber payoff (sellado, sin partículas)

**Salida:**

* `prompt_pack.jsonl`  
* `_PROMPTS_DONE.json`

---

## **6) Fase 3 — Init Frames (Generate/Reuse)**

**Objetivo:** obtener 1 init frame por beat (default), con **máximo reuso** para ahorrar costo.

### **6.1 Reuso / Caché (optimización)**

Orden de búsqueda:

1. **Cache por `beat_id`** (si el beat ya pasó QA en este run o run previo con mismos hashes).  
2. **Frame Library global (cross-beat / cross-episodio)** por `frame_signature`:  
   * Debe incluir intención, no solo “look”.  
   * Recomendado: `layer + intensity + shot_archetype + node_type_base + node_role + action_intent_category + amber_allowed`

**Compatibility check (hard):**  
solo se reusa si el frame contiene/permite ejecutar el `action_intent` del clip.

### **6.2 Generación (si no hay reuso)**

Generar imagen con `prompt_init_frame` (ya saneado).  
Luego correr QA.

### **6.3 QA (frames)**

FAIL → rerender (máx 3) si aparece cualquiera:

* humanos / manos / siluetas / figurines  
* texto / logos / QR / marcas / grabados / emboss  
* más de una idea por frame  
* top-left sucio

**Salidas:**

* `frames/*.png`  
* `_FRAMES_DONE.json`

---

## **7) Fase 4 — Clips (Veo 3.1)**

**Objetivo:** generar clips de 8 segundos a partir de init frame + `prompt_clip`.

### **7.1 Request**

Cada clip request incluye:

* `duration_s = 8`  
* `image_start = URL(init frame)`  
* `prompt = prompt_clip` (ya saneado)  
* (Opcional) parámetros globales (fps/aspect ratio)

Importante: el `prompt_clip` existe desde Planning/Prompts.  
No se “descubre” después de generar fotos.

### **7.2 QA (clips)**

FAIL → rerender (máx 3) si aparece cualquiera:

* humanos / texto / markings  
* amber fuera de UNLOCK/L3  
* amber como fuego/partículas/sparks  
* fluido fuera del sistema (leaks/pouring/puddles)  
* morphing/distorción que rompa lectura  
* más de una idea

### **7.3 Selección del “usable cut” (4s dentro de 8s)**

Una vez aprobado:

* asignar `edit_window` recomendado (default estable, p.ej. 2s–6s).  
* guardar en `timeline.json` para el montaje.

**Salidas:**

* `clips/*.mp4`  
* `qc_report.json` (incluye intentos, fails, chosen edit_window)  
* `_CLIPS_DONE.json`

---

## **8) Fase 5 — Assembly (Rough Cut + Timeline)**

**Objetivo:** construir un **montaje consecutivo** en el orden correcto, aunque no cierre con el largo del VO.

### **8.1 Montaje consecutivo (la regla clave que faltaba)**

1. Ordenar beats por `sequence_index`.  
2. Para cada beat:  
   * tomar el clip de 8s  
   * recortar solo el `edit_window` (default 4s)  
   * concatenar al final del anterior (sin gaps)  
3. Exportar `rough_cut.mp4`.

### **8.2 Audio (guía, no “sync final”)**

* Insertar `voiceover.mp3` como **guide track** iniciando en t=0.  
* Aceptar que el rough cut **no coincida** en duración con el VO (probablemente será más largo).

### **8.3 Timeline metadata (para edición posterior)**

Exportar `timeline.json` con:

* `sequence_index`, `beat_id`  
* `clip_path`  
* `clip_in_s`, `clip_out_s` (4s usados)  
* `vo_span_ref` (opcional: referencia a qué parte del guion/VO cubre ese beat)  
* notas QA / rerenders

**Salidas:**

* `rough_cut.mp4`  
* `timeline.json`  
* `_ASSEMBLY_DONE.json`

---

## **9) Fuera de alcance (pero previsto): “Editorial Conform”**

El conform final para igualar duración VO (acelerar, cortar, duplicar, time-remap, etc.) se define después.  
Este pipeline entrega **orden correcto + consistencia + material usable** y deja el “match exacto” a la etapa editorial.

---

## **10) Resumen técnico (actualizado)**

| Fase | Input principal | Motor/Lógica | Output principal |
| ----- | ----- | ----- | ----- |
| 0. Ingest & QC | Script + Audio + Biblia LOCKED | Validación + (opcional) vo_map | `run_manifest.json`, `vo_map.json` |
| 1. Planning | Inputs | Beat-Sheet + ClipPlan | `beat_sheet.jsonl`, `clip_plan.jsonl` |
| 2. Prompts | Beat/Clip Plan + Biblia | Prompt Pack + Sanitizer | `prompt_pack.jsonl` |
| 3. Init Frames | Prompts | Reuse/Generate + QA | `frames/*.png` |
| 4. Clips | Init Frames + Clip prompts | Veo 3.1 (8s) + QA + edit_window | `clips/*.mp4`, `qc_report.json` |
| 5. Assembly | Clips + VO | Concatenación 4s/beat + guide VO | `rough_cut.mp4`, `timeline.json` |

---

## **(Anexo) Decisiones operativas ya cerradas**

* QA enforcement automático, 3 rerenders máximo, luego manual.  
* Clip prompt/intención definida **antes** de generar init frame.  
* Veo 8s fijo; montaje usa 4s útiles por clip por defecto.  
* No assets pack; sí caché por beat_id y reuse cross-beat/cross-episodio con firma + compatibility check.
