# Documento de Alineación y Auditoría — Antigravity (versión existente) vs Clean Score Jump (LOCKED)

## 1) Objetivo
Necesitamos alinear tu versión actual de Antigravity (la que tú tienes en tu repo) con el estándar definitivo del proyecto Clean Score Jump, sin destruir tu arquitectura ni reescribir tu flujo agéntico.

Este documento no es “hazlo todo de nuevo”. Es:
- Auditar qué tienes hoy.
- Mapear discrepancias contra el estándar.
- Aplicar parches mínimos para que tu versión quede compatible.

## 2) Contexto (cambio mayor respecto a tu versión antigua)
En la versión final del proyecto, se eliminaron (o quedaron prohibidos) varios supuestos típicos:

- **NO se usa maniquí ni assets humanos.**
- **Hard lock: NO HUMANS** (ni personas, ni manos, ni siluetas, ni maniquíes, ni figurines).
- **NO texto generado por IA** (ni UI, ni labels, ni números, ni símbolos).
- Todo texto va en post.
- El estilo visual final es un sistema abstracto (tres mundos), no un “lab literal”, no un “personaje”.

Esto implica que si tu Antigravity tiene un flujo basado en *character anchor / mannequin references / single character lock*, eso debe quedar **desactivado o aislado**, pero no borrado (solo *legacy-compatible / off-by-default*).

## 3) Norte del proyecto (innegociable)
> “Tu score es una escalera de bandas y el banco toma una foto. El juego es preparar la foto.”

La imagen no compite con el VO: lo acompaña con mecánica visual simple y recompensa.

## 4) HARD REQUIREMENTS (bloqueo duro)

### 4.1 Hard locks visuales
- **NO HUMANS:** people/person/human/silhouette/hands/mannequin/figurine/statue/clothing.
- **NO TEXT / NO MARKINGS:** letras/números/símbolos/logos/QR/barcodes/inscripciones/seriales/UI.
- **Paleta bloqueada:** Carbon / Graphite / Smoke / Off-white.
- **Tungsten amber SOLO en L3** (payoff) y solo como “glow sellado detrás de vidrio esmerilado”.
- **Prohibidos:** cyan/blue glow, red/green accents, neon, RGB.
- **Sistema cerrado:** no leaks / puddles / pouring / drips.

### 4.2 Contrato A / B / ANIM (producción)
Cada shot se define como:
- **A:** START still
- **B:** END still (si hay cambio mecánico)
- **ANIM:** transición

**Reference Binding rule (hard):**
- Si hay cambio mecánico, **B debe generarse usando A como referencia** (image-to-image / init_image).
- **B solo puede diferir por 1 cambio visible** (*one-action rule*).

**A-only exception:**
- Si el shot es solo movimiento de cámara sin cambio de sistema, se permite “A-only” (sin B).

### 4.3 Stills vs Camera (hard)
- **A/B (stills):** prohibidas palabras de cámara/movimiento (zoom, pan, dolly, push-in, parallax, lens, etc.).
- **ANIM:** sí puede llevar cámara, pero disciplinada (slow push-in, settle).

### 4.4 Forbidden-vocab lint (hard)
Debe haber lint que bloquee vocab que dispara UI/texto/humano/estética errónea.

Ejemplos:
`blueprint, diagram, UI, HUD, label, trace, unlock, verified, route, noir, detective, QR, barcode, etc.`

> La lista canónica debe vivir en `QCManager`.

## 5) Estilo visual final (3 mundos + mix)

**Sistema final (mix):**
- **Filament Network:** 25–35%
- **Artifact Still-Life:** 40–55% (props whitelist: tarjeta blanca, sobre sellado, placa de vidrio, etc.)
- **Sealed Mechanics:** 15–25% (micro-mecánica sellada: shutter / latch / choke)

**Composición fija:**
- Hero node ligeramente debajo del centro
- Top-left quiet
- Máximo 3 capas de profundidad
- Una idea por frame

**Intensidad:**
- L1 ~40% (quiet)
- L2 ~40%
- L3 ≤20% (solo aquí amber)

## 6) Front-end y gates humanos (Airtable es base)
Airtable es el panel donde el equipo ve:
- Previews de A/B antes de clips
- Previews de clips antes de assembly

**Gates:**
- No clips si `IMAGES_APPROVED` no está abierto.
- No assembly si `CLIPS_APPROVED` no está abierto.

## 7) Hosting obligatorio para attachments (AssetStore)
Airtable attachments requieren URL accesible.

Por eso el pipeline usa un **AssetStore S3-compatible con signed URLs**.

## 8) Proveedor de generación (Kie.ai)
- Imágenes: **NanoBananaPro**
- Video: **Veo 3.1**

Todo se gestiona vía **Kie.ai**, configurable por **env vars**, sin hardcode.

## 9) Perfil de costo (default de pruebas)
Para pruebas:
- Imágenes **16:9 1K** (1024×576 o lo más cercano soportado)
- **Veo 3.1 FAST**
- Siempre **16:9**

## 10) Verificación strict (una sola verdad)
Debe existir un verificador estricto (CI-friendly):
- Sin mocks
- Exit 0/1
- Preflight (keys / deps)
- Kie real A→B bound + clip
- Asset upload real (3 assets)
- Airtable record + attachments + transición de estados

Además existe onboarding:
- `.env.template`
- `setup_env_wizard.py`
- `README_RUN_VERIFY.md`

## 11) Lo que necesitamos de ti (auditoría sin romper tu sistema)

### 11.1 Entregable 1 — Reporte de alineación
Queremos que nos respondas con:
- Mapa del repo actual
- Entrypoint real del pipeline
- Módulos principales (planning / prompts / images / clips / assembly)
- Clients existentes (Airtable, provider, storage, QC)
- Estado de cumplimiento frente a hard requirements:
  - NO HUMANS
  - NO TEXT
  - Disciplina de paleta
  - Sistema sellado
  - Contrato A/B/ANIM + binding A→B
  - Stills vs camera enforcement
  - Forbidden-vocab lint
  - Gating Airtable + AssetStore + preflight REAL
  - Perfiles TEST / FINAL (1K + FAST)
- Dónde difieres (y por qué)
- Qué conservarías porque tu sistema es mejor
- Propuestas de mejora **sin reescribir**

> Tu flujo agéntico puede ser distinto (menos agentes, etc.) siempre que produzca los mismos outputs:
> **Shot manifest A/B/ANIM + QC + gates.**

### 11.2 Entregable 2 — Plan de parches mínimos
Plan en dos capas:
- **Compat layer:** mínimo imprescindible para correr el proyecto
- **Hardening layer:** después del primer dry run real (reintentos, logging, paginación Airtable, etc.)

### 11.3 Regla de no destrucción
- No borrar carpetas legacy; mover a `legacy/` si hace falta.
- No eliminar tu flujo agéntico; solo asegurar salida compatible.

## 12) Preguntas concretas para tu Antigravity
Responde explícitamente:

1. ¿Tu sistema genera A/B/ANIM por shot?
2. ¿B se genera con init_image/reference a A cuando hay cambio mecánico?
3. ¿Tienes stills-vs-camera lint (bloquear zoom/pan en A/B)?
4. ¿Tienes forbidden-vocab lint en prompt + negative + metadata con BLOCK?
5. ¿Hay QA codes canónicos y gates (QA_HUMAN, QA_TEXT, QA_AMBER_LEAK, etc.)?
6. ¿Airtable es source of truth o solo log?
7. ¿Cómo subes assets para attachments? ¿AssetStore o paths locales?
8. ¿En REAL bloquea si faltan creds de KIE / AIRTABLE / ASSET? (no mocks)
9. ¿Defaults de prueba en 1K + Veo FAST + 16:9?
10. ¿Existe `verify_live_production_readiness.py` strict + onboarding wizard?
11. ¿Tu flujo usa maniquí / character? Si sí, ¿está apagable por config?
