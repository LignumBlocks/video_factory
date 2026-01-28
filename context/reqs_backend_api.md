# Requisito Funcional: Backend API

## Objetivo
Proveer una interfaz HTTP (REST) simple para que la GUI interactúe con la base de datos y el sistema de archivos local.

## Stack Sugerido
- **Framework:** FastAPI (Python) - Rápido, tipado, fácil de integrar con el código existente del pipeline.
- **Run:** `uvicorn` local.

## Endpoints Clave

### 1. Lectura del Pipeline
- `GET /api/runs`: Lista ejecuciones disponibles.
- `GET /api/runs/{run_id}/shots`: Retorna la estructura jerárquica completa.
    - Debe retornar Shots con sus Assets anidados.
    - Debe incluir flags de `selected` para que el UI sepa qué pintar.

### 2. Gestión de Assets
- `GET /api/assets/{asset_id}/file`: Sirve el archivo local (imagen/video).
    - Necesario porque el navegador no puede cargar `file://` locales por seguridad.
- `PATCH /api/assets/{asset_id}`: Actualiza metadatos mutables.
    - Body: `{ "is_selected": true, "qc_status": "REJECTED" }`
    - **Lógica de Negocio:** Si marcas `is_selected=true`, el backend debe desmarcar (false) a los hermanos del mismo tipo en ese shot.

### 3. Acciones de Pipeline (Fase 2)
- `POST /api/shots/{shot_id}/regenerate`: Dispara la re-generación (Prompts/Imagen/Video).
    - Llama a métodos de `Orchestrator` en background.

## Estructura de Respuesta (Ejemplo JSON)
```json
[
  {
    "shot_id": "S001",
    "status": "DONE",
    "planning": { "intent": "Door opens..." },
    "active_clip": {
        "url": "/api/assets/123/file",
        "id": "123"
    },
    "history": {
        "prompts": [...],
        "images": [...],
        "clips": [...]
    }
  }
]
```
