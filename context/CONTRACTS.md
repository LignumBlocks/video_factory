# FinanceVideoPlatform — Data Contracts & Enforcement Rules
**LOCKED: Clean Score Jump**

Este documento define los JSON schemas y reglas técnicas obligatorias.

---

## 1. RunManifest (`run_manifest.json`)

```json
{
  "run_id": "uuid",
  "created_at": "ISO8601",
  "inputs": {
    "script_hash": "sha256",
    "audio_hash": "sha256",
    "bible_hash": "sha256",
    "paths": {
      "script": "script.txt",
      "audio": "voiceover.mp3",
      "bible": "STYLE_BIBLE_LOCKED.md"
    }
  },
  "config": {
    "veo_duration_s": 8,
    "usable_cut_s": 4,
    "max_rerenders": 3
  },
  "status": {
    "phase": "PLANNING",
    "state": "RUNNING"
  }
}

2. BeatSheet (beat_sheet.jsonl)

1 línea por beat:

{
  "beat_id": "B0001",
  "sequence_index": 1,

  "verb": "EXPECTATION",
  "state": "LOCKED",

  "layer": "Blueprint",
  "intensity": "L2",

  "shot_archetype": 7,

  "node_type_base": "GATE",
  "node_role": "THRESHOLD",

  "amber_allowed": false,

  "vo_summary": "One sentence VO meaning",
  "vo_span_ref": {
    "start_ms": 12000,
    "end_ms": 16500
  }
}

Enums obligatorios

verb ∈ {EXPECTATION, TRACE, UNLOCK}

state ∈ {LOCKED, NOISY, CLEAN, VERIFIED, UNLOCKED}

layer ∈ {Blueprint, Evidence, Micro}

intensity ∈ {L1, L2, L3}

shot_archetype ∈ [1..12]

node_type_base ∈ {GATE, FILTER, LEDGER}

3. ClipPlan (clip_plan.jsonl)

Hard rule:

Sin ClipPlan → no se genera init frame.

{
  "beat_id": "B0001",

  "action_intent": "Gate clicks from locked to engaged",
  "action_intent_category": "GATE_CLICK",

  "motion_profile": "Only ring moves, background stable",
  "camera_behavior": "Locked camera",

  "constraints": {
    "no_humans": true,
    "no_text": true,
    "no_markings": true,
    "closed_system_only": true,
    "amber_allowed": false
  }
}

4. PromptPack (prompt_pack.jsonl)

{
  "beat_id": "B0001",

  "prompt_init_frame": "SANITIZED PROMPT A",
  "prompt_clip": "SANITIZED PROMPT B",

  "negative_prompt": "NO HUMANS, NO TEXT, NO MARKINGS",

  "sanitizer_report": {
    "blocked_terms_found": ["hud", "trace"],
    "rewrites_applied": true
  }
}

5. PromptSanitizer Rules (Mandatory)
Forbidden vocab (prompt positivo)

Bloquear + reescribir:

- blueprint
- noir
- evidence room
- detective
- ui / hud
- trace / unlock / verified / route
- overlay / label / text

Hard injections

Siempre incluir:

- NO HUMANS (positivo + negativo)
- ANTI TEXT / ANTI MARKINGS
- Blank surfaces

Amber enforcement

- amber_allowed=false → 0 amber
- amber_allowed=true → tungsten amber only, no sparks/fire

Closed system enforcement

Eliminar acciones tipo:

- pour
- spill
- puddle
- leak

One idea rule
 Si prompt contiene >1 acción → recortar a solo action_intent

6. Cache & Reuse Policy
Beat Cache (obligatorio)

Key:

  beat_cache_key = hash(inputs + beat_id + clip_plan)

Si existe aprobado → reusar frame/clip.

-------------------------------------------------
Frame Library Global (cross-beat)

Key:

frame_signature =
 layer + intensity + shot_archetype +
 node_type_base + node_role +
 action_intent_category + amber_allowed

Compatibility Check (hard)

No reusar si el frame no soporta la acción del clip.

7. QA Enforcement Specs
QA Frames FAIL si:

- humanos / manos / siluetas
- texto / logos / símbolos
- markings / emboss / decals
- top-left sucio
- más de una idea

QA Clips FAIL si:

- cualquier fail frame aparece en el clip
- amber fuera de UNLOCK/L3
- sparks/fire/particles
- leaks/pouring/puddles
- morphing ilegible
- más de una acción

Retries:

- max 3 → manual

8. Assembly Contract

- Veo clips siempre 8s
- Se usa edit_window de 4s (default 2–6)
- Concatena sin gaps por sequence_index
- VO es guide track
- Rough cut será más largo que VO

Timeline mínimo:

{
  "sequence_index": 1,
  "beat_id": "B0001",
  "clip_path": "clips/beat_B0001.mp4",
  "clip_in_s": 2.0,
  "clip_out_s": 6.0,
  "notes": "Passed QA on attempt 2"
}
