# Hito 1 — Tickets de implementación (RUN Skeleton + Preflight + Manifest + Logging + CLI)

> Objetivo del hito: cerrar una base **reproducible** (RUN) con manifiesto, validación, logging y CLI.  
> Resultado esperado: puedes crear un RUN y ejecutarlo sin UI y con artefactos auditables.

---

## T-001 — Estructura de repositorio + convenciones

**Objetivo:** base limpia para el proyecto.

### Requerimientos
- Python 3.11+ (o versión acordada, pero fija en config)
- `src/` o `videofactory/` como paquete
- `runs/` como output local (gitignored)
- `tests/` con pytest
- `pyproject.toml` (poetry o uv/pip-tools, pero definido)

### Entregables
- `.gitignore` incluyendo `runs/`, `.env`, `*.mp4`, `*.wav`, etc.
- `README.md` mínimo con:
  - instalación
  - comandos CLI
  - estructura de RUN

### Definition of Done
- `pytest` corre (aunque sea con 1 test dummy)
- `videofactory --help` funciona

---

## T-002 — Generación de `run_id` + estructura de carpetas RUN

**Objetivo:** crear una corrida con layout fijo.

### Especificación de `run_id` (recomendado)
Formato: `YYYYMMDD_HHMMSS_<shortHash>`  
`shortHash` = SHA256 de (`script_hash + audio_hash + bible_hash`) recortado a 8 chars.

### Layout obligatorio
```
runs/<run_id>/
  inputs/
    script.txt
    voiceover.mp3
    style_bible_LOCKED.md
  work/
    beats/
    prompts/
    frames/
    clips/
    qc/
    assembly/
  outputs/
  logs/
  run_manifest.json
  preflight_report.json
```

### Reglas
- Copiar inputs a `inputs/` (no trabajar sobre rutas externas)
- Crear carpetas vacías aunque no se usen aún

### Criterios de Aceptación (AC)
- Al crear RUN, todas las carpetas existen
- Inputs copiados y preservados

### Tests
- Unit: crear run en temp dir y validar folders
- Unit: si input path no existe → error claro

---

## T-003 — Hashing de inputs + metadata en `run_manifest.json`

**Objetivo:** reproducibilidad.

### `run_manifest.json` mínimo (schema v1)
```json
{
  "schema_version": "1.0",
  "run_id": "20260209_101530_ab12cd34",
  "created_at": "2026-02-09T10:15:30-05:00",
  "status": "CREATED",
  "app": {
    "name": "videofactory",
    "version": "0.1.0",
    "git_commit": "abcdef1"
  },
  "paths": {
    "run_root": "runs/<run_id>",
    "inputs_dir": "...",
    "work_dir": "...",
    "outputs_dir": "..."
  },
  "inputs": {
    "script": {"filename":"script.txt","sha256":"...","bytes":1234},
    "voiceover": {"filename":"voiceover.mp3","sha256":"...","bytes":98765,"duration_s":12.34},
    "style_bible": {"filename":"style_bible_LOCKED.md","sha256":"...","bytes":4567,"locked": true}
  },
  "steps": []
}
```

### Requerimientos técnicos
- SHA256 por archivo
- Duración de audio (recomendación: `ffprobe` vía subprocess o librería equivalente)
- Detectar `locked` buscando substring `"LOCKED"` en la biblia

### Criterios de Aceptación (AC)
- Manifest existe al crear RUN
- Hashes correctos (test con fixture)

### Tests
- Unit: hash de archivo conocido
- Unit: bible locked detection

---

## T-004 — Preflight Validator (genera `preflight_report.json` y actualiza manifest)

**Objetivo:** no correr basura.

### Preflight checks (obligatorios)
- `script` no vacío
- `voiceover` `duration_s` > 0
- `style_bible` `locked == true`
- Extensiones permitidas:
  - script: `.txt` `.md`
  - audio: `.mp3` `.wav`
  - bible: `.md` `.txt`

### Output: `preflight_report.json`
```json
{
  "run_id":"...",
  "passed": true,
  "checks": [
    {"name":"script_non_empty","passed":true,"detail":""},
    {"name":"voiceover_duration","passed":true,"detail":"duration_s=12.34"},
    {"name":"bible_locked","passed":true,"detail":"found LOCKED marker"}
  ]
}
```

### Actualización del manifest
- `status` pasa a:
  - `READY` si `passed=true`
  - `FAILED_PREFLIGHT` si `passed=false`
- Agregar step entry:
```json
{"step":"PREFLIGHT","status":"SUCCESS","started_at":"...","ended_at":"...","artifacts":["preflight_report.json"]}
```

### Criterios de Aceptación (AC)
- Si falla → no ejecuta nada más
- Reporte y manifest siempre se escriben

### Tests
- Integration: run con bible sin “LOCKED” → `FAILED_PREFLIGHT`

---

## T-005 — Sistema de logging por RUN (archivo + consola)

**Objetivo:** trazabilidad.

### Requerimientos
- Log file: `runs/<run_id>/logs/run.log`
- Log format: timestamp, level, run_id, step, message
- Nivel configurable (`INFO` default)

### Criterios de Aceptación (AC)
- Cada comando CLI escribe en `run.log`
- Errores quedan registrados

---

## T-006 — CLI `videofactory` (create-run / execute-run)

**Objetivo:** interfaz única.

### Comandos
1) `videofactory create-run --script PATH --voiceover PATH --bible PATH`
   - crea estructura
   - copia inputs
   - crea manifest
   - ejecuta preflight automáticamente
   - imprime `run_id` y status

2) `videofactory execute-run --run-id RUN_ID`
   - carga manifest
   - verifica `status == READY`
   - ejecuta pipeline (por ahora: solo preflight + “placeholders” de steps siguientes)
   - actualiza manifest

### Placeholders de steps (solo registro)
- BEAT_SEGMENTER (PENDING)
- VISUAL_PLANNER (PENDING)
- PROMPT_PACK (PENDING)
- GENERATION (PENDING)
- QC (PENDING)
- ASSEMBLY (PENDING)

### Criterios de Aceptación (AC)
- `--help` completo
- Errores claros si `run_id` no existe

### Tests
- CLI smoke test (si aplica)
- Unit: parse args

---

## T-007 — “Step Runner” mínimo (estado y registro)

**Objetivo:** base para el pipeline real.

### Diseño
- `Step` interface:
  - `name`
  - `run(context) -> StepResult`
- `StepResult`:
  - `status: SUCCESS|FAIL|SKIPPED`
  - `artifacts: [paths]`
  - `error: optional`

### Criterios de Aceptación (AC)
- `execute-run` recorre steps (aunque sean stubs)
- Cada step actualiza `manifest.steps[]`

---

## Entregable final del Hito 1 (Definition of Done global)
✅ Crear RUN + preflight + manifest + logging + CLI  
✅ `execute-run` deja el pipeline “con rieles” (stubs listos)  
✅ Artefactos producidos y auditables por RUN

---
