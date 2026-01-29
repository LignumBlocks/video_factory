# TICKETS_IMPLEMENTATION.md
FinanceVideoPlatform — Implementation Tickets
LOCKED: Clean Score Jump

Este documento traduce el backlog HU a tickets técnicos atómicos, listos para ejecutar por un agente de programación.
Reglas globales: QA enforcement, 3 rerenders, no generar frames sin ClipPlan, Veo=8s, montaje usa 4s.

---

## EPIC 0 — Foundation: Run Orchestrator + Manifests

### T-0.1 — Project skeleton + config loader
**Objetivo:** estructura base del repo + carga de config.
**Tareas**
- Crear estructura `/src`, `/configs`, `/artifacts`, `/logs`.
- Definir `config.yaml` (paths, max_rerenders=3, veo_duration=8, usable_cut=4).
- Loader con overrides por env vars.
**DoD**
- Ejecuta `python -m app --help` y muestra config efectiva.

### T-0.2 — Input validator (script/audio/bible)
**Objetivo:** validar entradas obligatorias.
**Tareas**
- Validar existencia y extensiones: `.txt`, `.mp3`, `.md`/`.txt`.
- Validar tamaños razonables (audio > 0).
- Validar “Bible locked id” (string/fecha) si aplica.
**DoD**
- Inputs inválidos → error claro y exit code ≠ 0.

### T-0.3 — Hashing service (sha256)
**Objetivo:** reproducibilidad.
**Tareas**
- Implementar `hash_file(path) -> sha256`.
- Escribir hashes en memoria del run.
**DoD**
- Mismo archivo → mismo hash; cambios mínimos → hash distinto.

### T-0.4 — RunManifest writer
**Objetivo:** escribir `run_manifest.json`.
**Tareas**
- Generar `run_id` (uuid).
- Guardar hashes + paths + config.
- Guardar `status.phase/state`.
**DoD**
- Se crea `artifacts/<run_id>/run_manifest.json`.

### T-0.5 — Phase checkpoint writer
**Objetivo:** checkpoint por fase.
**Tareas**
- Helper `write_checkpoint(phase_name)`.
- Estructura `artifacts/<run_id>/_PHASE_DONE.json`.
**DoD**
- Cada fase termina con checkpoint escrito.

### T-0.6 — RunOrchestrator (state machine)
**Objetivo:** controlar el pipeline.
**Tareas**
- Definir fases: INGEST, PLANNING, PROMPTS, FRAMES, CLIPS, ASSEMBLY.
- Manejar errores y reintentos.
- Actualizar `run_manifest.status`.
**DoD**
- Pipeline corre de punta a punta con stubs.

---

## EPIC 1 — Planning: BeatSheet + ClipPlan

### T-1.1 — Enums + validators (BeatSheet)
**Objetivo:** validación estricta de BeatSheet.
**Tareas**
- Enums: verb/state/layer/intensity/node_type_base.
- Validar `shot_archetype` ∈ [1..12].
- Validar `amber_allowed`: solo (UNLOCK && L3).
**DoD**
- `validate_beat_row(row)` retorna lista de errores; vacío si OK.

### T-1.2 — BeatSheet schema + writer (jsonl)
**Objetivo:** generar `beat_sheet.jsonl`.
**Tareas**
- Definir schema mínimo por beat.
- Writer JSONL (1 objeto por línea).
**DoD**
- Archivo JSONL válido y parseable.

### T-1.3 — BeatPlanner MVP (heurístico simple)
**Objetivo:** generar beats sin “creatividad libre”.
**Tareas**
- Tomar script y segmentar en chunks (frases o ~N palabras).
- Asignar `sequence_index` incremental.
- Asignar `verb` por patrón E→T→U por sección.
- Asignar `intensity` (L1/L2/L3) según sección (hook/explicación/payoff).
- Asignar `layer` con target mix (warning-only).
**DoD**
- Produce ~X beats para un script de prueba.

### T-1.4 — ClipPlan schema + writer (jsonl)
**Objetivo:** contrato “intención antes de frames”.
**Tareas**
- Definir schema ClipPlan.
- Writer `clip_plan.jsonl`.
**DoD**
- Cada beat_id tiene un ClipPlan asociado.

### T-1.5 — ClipPlan generator (action_intent_category)
**Objetivo:** catálogo mínimo de acciones.
**Tareas**
- Definir catálogo categories (ej: GATE_CLICK, FILTER_WASH, LEDGER_IMPRINT, SNAPSHOT, STAIR_STEP, THROTTLE, BREATH).
- Mapear `shot_archetype` → category default.
- Generar `action_intent` 1 acción (string corto).
**DoD**
- 100% beats tienen 1 action_intent coherente.

### T-1.6 — Hard rule: block FrameGen if no ClipPlan
**Objetivo:** enforcement.
**Tareas**
- Gate en pipeline: si falta ClipPlan para un beat → fail inmediato.
**DoD**
- FrameGen no corre sin ClipPlan.

### T-1.7 — Mix tracker (warning-only)
**Objetivo:** medir mix B/E/M por episodio.
**Tareas**
- Contador de beats por layer.
- Warning si sale de rangos target.
**DoD**
- `mix_report` en logs; no bloquea el run.

---

## EPIC 2 — Prompts + PromptSanitizer

### T-2.1 — Prompt templates (init frame / clip)
**Objetivo:** plantillas deterministas.
**Tareas**
- Template base por `layer` + `shot_archetype`.
- `prompt_init_frame`: mundo limpio sin acción.
- `prompt_clip`: una acción desde ClipPlan.
**DoD**
- Para un beat dado, templates generan output consistente.

### T-2.2 — Forbidden vocab list + matcher (exact + fuzzy)
**Objetivo:** detectar vocab prohibido.
**Tareas**
- Lista forbidden (tokens + frases).
- Matching case-insensitive.
- Fuzzy básico (variantes: ui/hud, routing/route, verified/verify).
**DoD**
- `scan_forbidden(text)` retorna hallazgos.

### T-2.3 — PromptSanitizer (rewrite + inject)
**Objetivo:** producir prompt final seguro.
**Tareas**
- Reescribir/remover términos prohibidos.
- Inyectar hard locks (NO HUMANS, NO TEXT, NO MARKINGS).
- Enforce closed-system (bloquear spill/pour/leak/puddle).
- Enforce amber: si no permitido, remover warm/amber/glow.
**DoD**
- Siempre produce `prompt_*_sanitized` + `negative_prompt` + `sanitizer_report`.

### T-2.4 — One-idea enforcer
**Objetivo:** evitar prompts con múltiples acciones.
**Tareas**
- Si detecta múltiples verbos/acciones, reducir a `action_intent`.
**DoD**
- `prompt_clip` resultante expresa 1 acción.

### T-2.5 — PromptPack writer (jsonl)
**Objetivo:** guardar `prompt_pack.jsonl`.
**Tareas**
- Un record por beat: init/clip/negative/sanitizer_report.
**DoD**
- Archivo generado y validado.

---

## EPIC 3 — Cache + Reuse

### T-3.1 — Filesystem layout por run
**Objetivo:** estructura consistente.
**Tareas**
- `artifacts/<run_id>/{frames,clips,logs}`
- Nombres `beat_<id>.png`, `beat_<id>.mp4`.
**DoD**
- Se crean carpetas al iniciar run.

### T-3.2 — Beat cache key builder
**Objetivo:** cache determinista por beat.
**Tareas**
- `beat_cache_key = hash(script_hash,audio_hash,bible_hash,beat_id,beat_row,clip_plan_row)`
**DoD**
- Llaves estables; cambia si cambia intención.

### T-3.3 — Beat cache store/lookup
**Objetivo:** reuso por beat_id.
**Tareas**
- Index local (json/sqlite) con key→paths.
- Solo guardar si QA aprobado.
**DoD**
- Re-run reusa sin regenerar.

### T-3.4 — Frame signature builder (cross-beat)
**Objetivo:** reuso inteligente.
**Tareas**
- signature: layer+intensity+archetype+node_type+node_role+action_category+amber_allowed.
**DoD**
- `frame_signature(beat)` estable.

### T-3.5 — Frame library index (global)
**Objetivo:** reuso cross-episodio.
**Tareas**
- Index persistente (sqlite/json).
- Insertar frames aprobados con metadata.
**DoD**
- Se puede consultar por signature y retornar candidatos.

### T-3.6 — Compatibility check (hard)
**Objetivo:** no reusar frames incompatibles.
**Tareas**
- Validación por metadata: archetype/category must match.
- Hook para checks futuros (vision/OCR).
**DoD**
- Nunca reusa si category ≠.

---

## EPIC 4 — QA Enforcement

### T-4.1 — QA rules engine (framework)
**Objetivo:** motor de reglas.
**Tareas**
- `Rule`: id, description, severity, apply().
- `QAResult`: pass/fail + reasons.
**DoD**
- Se pueden registrar reglas y correr sobre un artefacto.

### T-4.2 — Frame QA (MVP)
**Objetivo:** gates para init frames.
**Tareas**
- MVP sin visión: usar “signal” (si la API devuelve flags) o manual placeholder.
- Interface preparada para añadir CV luego.
**DoD**
- QA produce PASS/FAIL y reasons.

### T-4.3 — Clip QA (MVP)
**Objetivo:** gates para clips.
**Tareas**
- MVP: validar metadata + heurísticas (duración, params).
- Interface para sample frames luego.
**DoD**
- QA produce PASS/FAIL.

### T-4.4 — Retry controller (frames & clips)
**Objetivo:** enforcement automático.
**Tareas**
- 3 intentos max.
- Si falla, marcar beat como `needs_manual_prompt`.
**DoD**
- Se observa rerender loop y escalamiento.

### T-4.5 — QC report writer
**Objetivo:** `qc_report.json`.
**Tareas**
- Guardar intentos, reasons, decisiones de edit_window.
**DoD**
- Report consolidado al final del run.

---

## EPIC 5 — Generation: Init Frames + Clips (Veo)

### T-5.1 — FrameGen adapter (API wrapper)
**Objetivo:** wrapper de generación de imágenes.
**Tareas**
- `generate_frame(prompt, negative, seed?) -> image_path`.
- Manejo de errores + retries.
**DoD**
- Produce un png válido (o stub en dev).

### T-5.2 — Frame generation loop per beat
**Objetivo:** reusar o generar.
**Tareas**
- Si beat cache hit → reusar.
- Else si library hit + compatible → reusar.
- Else generar + QA + store.
**DoD**
- Se observan hits de cache en logs.

### T-5.3 — Veo adapter (API wrapper)
**Objetivo:** wrapper de video.
**Tareas**
- `generate_clip(init_image_url, prompt, duration=8) -> mp4_path`.
**DoD**
- Produce mp4 válido (o stub).

### T-5.4 — Clip generation loop per beat
**Objetivo:** generar clips con intención previa.
**Tareas**
- Asegurar `prompt_clip` existe antes.
- Generar clip → QA → store.
**DoD**
- No hay clips generados sin prompt_clip.

### T-5.5 — Edit window selector (default)
**Objetivo:** escoger 4s útiles.
**Tareas**
- Default: 2–6.
- Permitir override por archetype.
**DoD**
- `edit_window` escrito en timeline y qc_report.

---

## EPIC 6 — Assembly

### T-6.1 — Clip trimmer (ffmpeg)
**Objetivo:** recortar 4s.
**Tareas**
- Trim mp4 por clip_in/out.
- Mantener fps y audio track (si existe) o remover audio del clip.
**DoD**
- Output trims reproducibles.

### T-6.2 — Concat builder (ffmpeg)
**Objetivo:** montaje consecutivo.
**Tareas**
- Concatenar trims por sequence_index.
- Sin gaps.
**DoD**
- rough_cut.mp4 generado.

### T-6.3 — VO guide track mux
**Objetivo:** VO como guía.
**Tareas**
- Insertar voiceover.mp3 desde t=0.
- No intentar sync perfecto.
**DoD**
- rough_cut.mp4 contiene VO track.

### T-6.4 — Timeline exporter
**Objetivo:** `timeline.json`.
**Tareas**
- Export por beat: clip_path, clip_in/out, notes.
**DoD**
- timeline.json válido y consistente con rough_cut.

---

## EPIC 7 — Dev UX / Observability

### T-7.1 — Logging estándar por fase
**Objetivo:** debug fácil.
**Tareas**
- Logger con run_id y beat_id.
- Archivos por fase en `logs/`.
**DoD**
- Logs claros de cache hits, retries, fails.

### T-7.2 — CLI runner
**Objetivo:** correr pipeline desde terminal.
**Tareas**
- `run --script ... --audio ... --bible ...`
- Flags: `--dry-run`, `--stubs-only`, `--from-phase`.
**DoD**
- Se puede reanudar desde fase.

### T-7.3 — Determinism hooks
**Objetivo:** reproducibilidad.
**Tareas**
- Semillas/ids por beat en manifest.
- Capturar versiones de modelos/APIs.
**DoD**
- run_manifest contiene versions.

---

## Suggested Execution Order (para el agente)
1) T-0.x (Orchestrator + manifest)
2) T-1.1–T-1.6 (BeatSheet + ClipPlan + hard rule)
3) T-2.1–T-2.5 (Templates + Sanitizer)
4) T-6.1–T-6.4 (Assembly con stubs)
5) T-3.x (Cache + reuse)
6) T-5.x (Adapters reales)
7) T-4.x (QA real)
8) T-7.x (CLI + observabilidad)

---
