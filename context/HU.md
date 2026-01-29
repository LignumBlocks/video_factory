# FinanceVideoPlatform — User Stories (HU) Backlog
LOCKED: Clean Score Jump

Este documento define el backlog de Historias de Usuario (HU) para guiar al agente de programación.

---

## EPIC 0 — Foundation: Run Orchestrator + Manifests

### HU-0.1 — Registrar una corrida reproducible
Como sistema, quiero registrar una corrida reproducible para asegurar trazabilidad.

**Criterios de aceptación**
- Genera `run_manifest.json` con hashes de inputs.
- Guarda estado de fase y checkpoints `_PHASE_DONE.json`.

---

## EPIC 1 — Planning: BeatSheet + ClipPlan

### HU-1.1 — Generar BeatSheet estructurado
Como sistema, quiero generar `beat_sheet.jsonl` con enums válidos y constraints LOCKED.

**Criterios de aceptación**
- verb ∈ {EXPECTATION, TRACE, UNLOCK}
- state ∈ {LOCKED, NOISY, CLEAN, VERIFIED, UNLOCKED}
- layer ∈ {Blueprint, Evidence, Micro}
- intensity ∈ {L1, L2, L3}
- shot_archetype ∈ [1..12]
- amber_allowed solo si UNLOCK + L3

---

### HU-1.2 — Generar ClipPlan obligatorio antes de frames
Como sistema, quiero generar `clip_plan.jsonl` antes de cualquier frame.

**Criterios de aceptación**
- Si falta ClipPlan → pipeline falla (no FrameGen permitido).
- Cada beat tiene una sola `action_intent`.

---

## EPIC 2 — Prompts + Sanitizer

### HU-2.1 — Generar PromptPack por beat
Como sistema, quiero producir prompts Pass A/B saneados.

**Criterios de aceptación**
- `prompt_init_frame` (mundo limpio)
- `prompt_clip` (una sola acción)
- `negative_prompt` obligatorio

---

### HU-2.2 — PromptSanitizer obligatorio
Como sistema, quiero bloquear vocab prohibido e inyectar hard locks.

**Criterios de aceptación**
- Bloquea noir/UI/HUD/trace/unlock/etc.
- Inyecta NO-HUMANS + ANTI-TEXT siempre
- Enforce amber solo en UNLOCK/L3
- Enforce closed-system (no leaks/pouring/puddles)

---

## EPIC 3 — Cache + Reuse

### HU-3.1 — Cache por beat_id
Como sistema, quiero reusar frames/clips aprobados.

**Criterios de aceptación**
- Beat aprobado → guardado en cache
- Re-run con mismos hashes → no regenera

---

### HU-3.2 — Frame reuse cross-beat
Como sistema, quiero reusar frames por signature con compatibility check.

**Criterios de aceptación**
- frame_signature incluye intención (`action_intent_category`)
- No reuse si no soporta el clip

---

## EPIC 4 — QA Enforcement

### HU-4.1 — QA frames con rerenders automáticos
Como sistema, quiero validar frames con FAIL → rerender.

**Criterios de aceptación**
- Detecta humans/text/markings/top-left dirty
- Max 3 intentos → needs_manual_prompt

---

### HU-4.2 — QA clips con rerenders automáticos
Como sistema, quiero validar clips antes de assembly.

**Criterios de aceptación**
- Fail si amber fuera de UNLOCK/L3
- Fail si sparks/fire/leaks/pouring/puddles
- Fail si morphing ilegible

---

## EPIC 5 — Generation

### HU-5.1 — Init frames solo si no hay reuse
Como sistema, quiero generar frames solo si no existen en cache.

**Criterios de aceptación**
- Nunca generar sin ClipPlan
- Siempre usar PromptSanitizer

---

### HU-5.2 — Clips Veo 3.1 con intención definida desde planning
Como sistema, quiero generar clips de 8s con prompt definido desde el inicio.

**Criterios de aceptación**
- duration_s=8 fijo
- prompt_clip viene del planning, no post-foto

---

## EPIC 6 — Assembly

### HU-6.1 — Rough cut consecutivo usando 4s útiles
Como sistema, quiero concatenar clips recortados por beat.

**Criterios de aceptación**
- edit_window default 2–6
- concat sin gaps por sequence_index
- output: rough_cut.mp4

---

### HU-6.2 — Export timeline.json
Como sistema, quiero exportar metadata para edición posterior.

**Criterios de aceptación**
- timeline incluye clip_in/out, beat_id, notas QA
- VO es guide track (no sync final)

---
