# FinanceVideoPlatform — Architecture Spec
**LOCKED: Clean Score Jump (01172026)**

Este documento define la arquitectura de software del sistema.
Su objetivo es guiar implementación sin interpretación creativa.

---

## 1. Objetivo del sistema

Dado:

- `script.txt` (voiceover script locked)
- `voiceover.mp3` (audio final)
- `STYLE_BIBLE_LOCKED.md` (Clean Score Jump)

El sistema produce:

- `rough_cut.mp4` (montaje consecutivo)
- `timeline.json` (metadata editorial)
- artefactos reproducibles (beats, prompts, QA, cache)

Con:

- QA enforcement automático
- Clip intention definida antes de generar frames
- Veo 3.1 clips fijos de 8s
- Uso real de ~4s por clip
- Caché por beat + reuse cross-beat

---

## 2. Hard Constraints (LOCKED Rules)

Estos son FAIL automáticos:

- No humans (manos/siluetas/personas)
- No text / no markings / blank surfaces
- Amber solo en UNLOCK + L3
- Sistema cerrado (no leaks/pouring/puddles)
- QA enforcement: FAIL → rerender (max 3)
- Shot archetypes cerrados (1–12)

---

## 3. Pipeline General

Flujo:

Ingest & QC
↓
Planning (BeatSheet + ClipPlan)
↓
Prompts (Sanitize)
↓
Init Frames (Reuse/Generate)
↓
Clips (Veo 3.1)
↓
Assembly (Rough Cut + Timeline)


Regla central:

> No se genera ningún frame si no existe ClipPlan.

---

## 4. Componentes del Sistema (Services)

### 4.1 IngestService

Responsabilidad:

- Validar inputs
- Hashes y run manifest
- (Opcional) forced-alignment solo como referencia

Outputs:

- `run_manifest.json`
- `vo_map.json` (opcional)

---

### 4.2 BeatPlanner

Genera:

- `BeatSheet`
- `ClipPlan`

Nunca genera prompts finales.

---

### 4.3 PromptService

Genera:

- `prompt_init_frame` (Pass A)
- `prompt_clip` (Pass B)

Aplica PromptSanitizer obligatorio.

---

### 4.4 AssetReuseService

Optimización de costo:

- Cache por beat_id
- Reuse cross-beat vía frame_signature
- Compatibility check hard

---

### 4.5 FrameGenService

Genera init frames si no hay reuse.

QA enforcement:

- FAIL → rerender (max 3)

Outputs:

- `frames/*.png`

---

### 4.6 ClipGenService

Genera clips Veo:

- duración fija 8s
- QA enforcement clips
- define edit_window usable (~4s)

Outputs:

- `clips/*.mp4`

---

### 4.7 AssemblyService

Construye Rough Cut:

- clips concatenados consecutivamente
- recorte edit_window
- VO como guide track

Outputs:

- `rough_cut.mp4`
- `timeline.json`

---

### 4.8 RunOrchestrator

Controla:

- orden de fases
- reintentos
- checkpoints `_PHASE_DONE.json`

---

## 5. Montaje y duración

- Veo produce clips de 8s
- Solo se usan ~4s por beat
- Rough Cut será más largo que VO
- Edición posterior hace conform final

---

## 6. Orden recomendado de implementación

1. RunOrchestrator + manifests
2. PromptSanitizer + QA skeleton
3. BeatPlanner + ClipPlan
4. FrameGen + Cache
5. ClipGen + edit_window
6. Assembly + timeline export
7. Frame Library global reuse

---

