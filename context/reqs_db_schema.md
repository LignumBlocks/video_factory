# Requisito Funcional: Esquema de Base de Datos (SQLite)

## Objetivo
Reemplazar Airtable con una base de datos local ligera (SQLite) que almacene tanto el **Lineamiento de Producción** (qué se generó) como la **Capa de Decisión** (qué aprobó el humano).

## Principios de Diseño
1.  **Inmutabilidad de Artefactos:** Si el pipeline genera un archivo, se crea un registro. Nunca se sobrescribe.
2.  **Mutabilidad de Estado:** El humano cambia flags (`selected`, `qc_status`), no los datos del asset.
3.  **Relacional:** Un Shot tiene muchos Assets. Un Run tiene muchos Shots.

## Esquema Propuesto

### 1. Table `runs`
Representa una ejecución del pipeline (versión).
- `run_id` (PK, Text): e.g., "E2E_TEST"
- `version` (Integer): e.g., 1
- `created_at` (Datetime)

### 2. Table `shots`
El contenedor abstracto (el "Plan").
- `shot_id` (PK, Text): e.g., "S001"
- `run_id` (FK)
- `script_text` (Text)
- `intent` (Text)
- `duration_s` (Float)
- `status` (Text): 'PLANNED', 'IN_PROGRESS', 'DONE', 'FLAGGED'

### 3. Table `assets`
La tabla central (Vertical Asset Stream).
- `asset_id` (PK, UUID)
- `shot_id` (FK)
- `type` (Text): 'PROMPT', 'IMAGE_START', 'IMAGE_END', 'CLIP'
- `role` (Text): 'ref', 'start', 'end' (para diferenciar imágenes A/B)
- `path` (Text): Ruta absoluta local (`/exports/...`)
- `url` (Text, Nullable): URL pública si existe (para compartir)
- `metadata` (JSON):
    - Seed, Prompt Text, Model Name, Generation Params.
- `created_at` (Datetime)

### 4. Table `decisions` (La Capa Humana)
Separamos la decisión del asset para limpiar la lógica.
- `shot_id` (FK)
- `asset_type` (Text): 'CLIP', 'IMAGE_START', etc.
- `selected_asset_id` (FK -> assets.asset_id): El "Ganador" actual.
- `qc_notes` (Text): Comentarios del humano.
- `updated_at` (Datetime)

*Nota: Alternativamente, `is_selected` puede ser una columna en `assets` para simplificar queries (MVP).*

## Flujo de Datos
1.  **Pipeline:** Inserta en `runs`, `shots`, `assets`.
2.  **Pipeline:** Marca `selected=True` al último generado por defecto (o gestiona tabla `decisions`).
3.  **UI:** Lee `shots` + `assets` (filtrando por `selected` para la vista principal).
4.  **UI:** Actualiza `decisions` cuando el usuario elige una versión anterior.
