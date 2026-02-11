# EPIC E0 — Fundaciones del sistema (RUN Skeleton)

> **Single Source of Truth (SoT)** para iniciar el proyecto con orden y reproducibilidad.  
> **Regla:** el equipo implementa exactamente lo que está aquí. Cualquier cosa fuera requiere **CR (Change Request)**.

---

## HU-001 — Crear una corrida RUN reproducible

**Como** Owner/PM  
**Quiero** iniciar una corrida (RUN) con un `run_id` único y estructura estándar de carpetas  
**Para** asegurar reproducibilidad, auditabilidad y orden.

### Criterios de Aceptación (AC)
1) Dado un input válido, se crea `runs/<run_id>/` con estructura estándar de carpetas.  
2) Se genera `run_manifest.json` inicial con:
   - `run_id`
   - timestamps
   - paths
   - hashes de inputs
   - versión app + git commit  
3) La creación de RUN **no ejecuta** el pipeline (solo prepara y valida).

---

## HU-002 — Preflight (validación) antes de correr

**Como** sistema  
**Quiero** validar que existen los 3 inputs obligatorios y son legibles  
**Para** evitar corridas rotas y “debug infinito”.

### Criterios de Aceptación (AC)
1) Si falta `script` o `voiceover` o `style_bible_LOCKED`, el RUN queda en estado `FAILED_PREFLIGHT` y no ejecuta nada más.  
2) Se genera `preflight_report.json` y se anota en `run_manifest.json`.  
3) Validaciones mínimas:
   - script no vacío  
   - audio duración > 0  
   - style bible contiene marcador **"LOCKED"** (string literal)

---

## HU-003 — CLI mínima para crear y correr RUNs

**Como** desarrollador  
**Quiero** un CLI con comandos `create-run` y `execute-run`  
**Para** probar el motor sin UI.

### Criterios de Aceptación (AC)
- `videofactory create-run --script ... --voiceover ... --bible ...` retorna `run_id` y paths.  
- `videofactory execute-run --run-id ...` ejecuta el pipeline (por ahora solo preflight + placeholders de steps).  
- Logs en consola **y** archivo por RUN.

---
