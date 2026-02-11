# EPIC E1 — Agents Layer (Beats → ClipPlan → PromptPack)

> **Objetivo del EPIC:** implementar la “capa inteligente” (agentes) que transforma `script + bible (+ opcional vo_map)` en artefactos **estructurados y auditables**:  
> `beat_sheet.jsonl` → `clip_plan.jsonl` → `prompt_pack.jsonl`  
>
> **Regla:** estos agentes **no generan video**. Solo planean y preparan prompts con guardrails.

---

## Contexto y alcance

### Entradas (inputs) del EPIC
- `runs/<run_id>/inputs/script.txt` (o `.md`)
- `runs/<run_id>/inputs/style_bible_LOCKED.md`
- (Opcional) `runs/<run_id>/work/vo_map.json`

### Artefactos (outputs) del EPIC
- `runs/<run_id>/work/beats/beat_sheet.jsonl`
- `runs/<run_id>/work/beats/beat_sheet.meta.json` (opcional, recomendado)
- `runs/<run_id>/work/prompts/clip_plan.jsonl`
- `runs/<run_id>/work/prompts/prompt_pack.jsonl`
- `runs/<run_id>/work/prompts/prompt_sanitize_report.json` (recomendado)

### Restricciones no negociables
- **Shot Menu cerrado:** `shot_type` debe existir en el menú permitido (sin inventar).
- **Biblia LOCKED manda:** tokens, restricciones y estilo deben reflejarse en el prompt final.
- **Guardrails siempre presentes:** negativos obligatorios (no humans, no text, etc.).
- **Auditabilidad:** cada archivo incluye `run_id`, versiones y trazas mínimas.

---

## HU-101 — BeatSegmenterAgent: generar beats desde el guion

**Como** sistema  
**Quiero** convertir el guion en una lista de beats con intención y metadata  
**Para** alimentar planeación visual y timeline.

### Criterios de Aceptación (AC)
1) Se genera `beat_sheet.jsonl` con 1 beat por línea (JSONL válido).
2) Cada beat incluye:
   - `beat_id` (estable dentro del RUN)
   - `text` (texto del beat)
   - `intent` (resumen de intención)
   - `estimated_seconds` (float; aproximado)
   - `priority` (int; default 1)
3) No se “inventan” elementos visuales aquí; solo estructura narrativa.
4) Se registra el step en `run_manifest.json` como `BEAT_SEGMENTER`.

---

## HU-102 — VisualPlannerAgent: convertir beats → ClipPlan usando Shot Menu

**Como** sistema  
**Quiero** asignar a cada beat un `shot_type` permitido y parámetros visuales  
**Para** producir un plan visual consistente y cerrable.

### Criterios de Aceptación (AC)
1) Se genera `clip_plan.jsonl` con 1 línea por beat.
2) Cada línea incluye:
   - `beat_id`
   - `shot_type` (de Shot Menu)
   - `energy` (low|med|high)
   - `camera` (según biblia; default `locked`)
   - `duration_s` (según regla del sistema; fijo o por config)
   - `do_not_include` (lista con prohibiciones mínimas: humans, text)
   - `style_tokens` (extraídos/derivados de la biblia)
3) Si el agente propone un `shot_type` fuera del menú:
   - debe **fallar** el step con error `SHOT_MENU_VIOLATION`
4) Se registra el step en `run_manifest.json` como `VISUAL_PLANNER`.

---

## HU-103 — PromptBuilderAgent: generar prompts por beat (PromptPack)

**Como** sistema  
**Quiero** traducir `clip_plan` + biblia en prompts listos para generación  
**Para** producir clips sin ambigüedad y con estilo consistente.

### Criterios de Aceptación (AC)
1) Se genera `prompt_pack.jsonl` con 1 línea por beat.
2) Cada línea incluye:
   - `beat_id`
   - `model_target` (ej. `veo` o `init_frame_model`) — configurable
   - `prompt` (texto principal)
   - `negative_prompt` (guardrails)
   - `duration_s` (si aplica, para video)
   - `seed` (opcional; si se define política de seeds)
3) El prompt incorpora explícitamente:
   - tokens de estilo obligatorios (biblia)
   - shot_type traducido a instrucciones visuales
4) Se registra el step en `run_manifest.json` como `PROMPT_PACK`.

---

## HU-104 — PromptSanitizer: enforcement de guardrails + reporte

**Como** sistema  
**Quiero** sanitizar y normalizar prompts antes de generar contenido  
**Para** minimizar fallas de QC (texto/humanos/estilo roto) y evitar deriva.

### Criterios de Aceptación (AC)
1) El sanitizer:
   - agrega negativos obligatorios si faltan
   - elimina o reescribe frases que violen biblia/guardrails
   - normaliza formato (máximo de tokens, orden recomendado, etc.)
2) Produce `prompt_sanitize_report.json` con:
   - qué se cambió por beat
   - warnings y errores
3) Si detecta contradicción severa (ej. prompt pide texto):
   - debe marcar `status=FAIL` del step y detener EPIC E1.

---

## HU-105 — Trazabilidad y reproducibilidad de agentes

**Como** Owner/QA  
**Quiero** que cada agente deje evidencia de su decisión  
**Para** depurar y repetir resultados.

### Criterios de Aceptación (AC)
1) Cada artefacto (JSONL) incluye en cada línea:
   - `run_id`
   - `agent_version` (string)
   - `created_at`
2) `run_manifest.json` guarda:
   - input hashes
   - versiones de agentes
   - parámetros (temperature, model, etc. si aplica)
3) Se puede “replay” un RUN sin llamar a modelos (modo `--replay`):
   - si existen artefactos previos, se reusan y se valida schema

---
