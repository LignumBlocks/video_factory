# Requisito Funcional: Integración Pipeline -> DB

## Objetivo
Conectar el `Orchestrator` existente con la nueva base de datos SQLite, reemplazando (o complementando) el módulo `SyncManager` actual.

## Componentes

### 1. `DatabaseManager` (Reemplazo de SyncManager)
Una clase Python en `src/database_manager.py`.
- `__init__(db_path)`: Conecta a SQLite.
- `register_run(run_id, version)`: Crea entrada en tabla `runs`.
- `register_shot(shot_spec)`: Crea/Actualiza tabla `shots`.
- `register_asset(asset_type, local_path, metadata)`: Inserta en `assets`.
    - **Lógica Automática:** Al insertar, marca `is_selected=True` y pone `is_selected=False` a los anteriores de ese shot/tipo.

### 2. Modificación de `Orchestrator`
- Eliminar dependencias de `AirtableClient`.
- Instanciar `DatabaseManager`.
- Llamar a métodos de registro en los puntos clave (fin de Planning, fin de Prompts, fin de Images, fin de Clips).

### 3. Migración (Backfill)
- Script `one_off_migrate.py`.
- Debe leer los archivos JSONL existentes (`shot_spec.jsonl`, `_IMAGES_DONE.json`, etc.) de `exports/` y poblar la base de datos inicial para no perder el trabajo de `E2E_TEST`.

## Beneficio Inmediato
El pipeline corre 100% local, sin dependencia de internet (Airtable API) y con latencia cero en la actualización de estados.
