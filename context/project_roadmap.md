# Roadmap: Transición a Custom UI "Cockpit"

## Fase A: Cimientos de Datos (Local DB)
1.  **Diseño DB:** Implementar esquema SQLite (`reqs_db_schema.md`).
2.  **Manager:** Crear `DatabaseManager` en Python.
3.  **Integración:** Conectar `Orchestrator` a `DatabaseManager`.
4.  **Migración:** Script para importar `E2E_TEST` existente a SQLite.
5.  *Hito:* Pipeline corre y llena el `.db` localmente.

## Fase B: Backend Server
1.  **API Setup:** Crear servidor FastAPI en `src/server/app.py`.
2.  **Endpoints:** Implementar lectura de Tree (`/runs/{id}/shots`).
3.  **Static Serving:** Exponer carpeta `exports/` como estática.
4.  *Hito:* Puedes ver JSON del pipeline en `localhost:8000/docs`.

## Fase C: Frontend "Cockpit"
1.  **Scaffold:** Crear proyecto Next.js en `src/ui`.
2.  **Componentes:** ShotCard, AssetPlayer, Timeline.
3.  **Conexión:** Hookear UI con API FastAPI.
4.  **Lógica Selected:** Implementar botones "Make Hero".
5.  *Hito:* Puedes ver, reproducir y seleccionar clips en el navegador.

## Fase D: Control Total (Futuro)
1.  **Regeneración:** Botones en UI que disparen `Orchestrator` re-runs.
2.  **Edición:** Editar texto de Prompt en UI y re-generar.
