# Manual Server Startup Guide

Este documento contiene las instrucciones para levantar manualmente todos los servicios del Cockpit y poder ver los logs en tiempo real.

## Pre-requisitos

Asegúrate de estar en el directorio raíz del proyecto:
```bash
cd /home/roiky/Espacio/FinanceVideoPlatform
```

## Paso 1: Activar Virtual Environment y Cargar Variables

```bash
source venv/bin/activate
source load_env.sh
```

**Verificar que las variables se cargaron:**
```bash
echo $GEMINI_API_KEY | cut -c1-20
echo $AGENT_MODEL
```

Deberías ver tu API key (primeros 20 caracteres) y el modelo configurado (`gemini-2.5-flash`).

---



---

## Paso 2: Iniciar Backend API (Terminal 2)

**Puerto:** 8000

```bash
python -m src.server.app
```

**Logs esperados:**
- `Starting API Server. DB Path: /home/roiky/Espacio/FinanceVideoPlatform/pipeline.db`
- `INFO: Uvicorn running on http://0.0.0.0:8000`

**Verificar:**
```bash
curl http://localhost:8000/
```

Debería retornar: `{"status":"ok","service":"FinanceVideoPlatform API"}`

---

## Paso 3: Iniciar Frontend UI (Terminal 3)

**Puerto:** 3000

```bash
cd src/ui
yarn dev
```

**Logs esperados:**
- `▲ Next.js 16.1.4 (Turbopack)`
- `- Local: http://localhost:3000`
- `✓ Ready in XXXms`

**Verificar:**
Abre en el navegador: `http://localhost:3000`

---

## Resumen de Servicios

| Servicio | Puerto | URL | Terminal |
|----------|--------|-----|----------|

| Backend API | 8000 | http://localhost:8000 | Terminal 2 |
| Frontend UI | 3000 | http://localhost:3000 | Terminal 3 |

---

## Debugging: Ver Variables de Entorno en el Backend

Para verificar que el backend tiene acceso a las variables de entorno, puedes agregar temporalmente este código en `src/server/app.py`:

```python
@app.get("/debug/env")
def debug_env():
    return {
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "NOT SET")[:20] + "...",
        "AGENT_MODEL": os.environ.get("AGENT_MODEL", "NOT SET"),
        "AGENT_MOCK_MODE": os.environ.get("AGENT_MOCK_MODE", "NOT SET"),
    }
```

Luego visita: `http://localhost:8000/debug/env`

---

## Troubleshooting

### Error: "Address already in use"
```bash
# Matar procesos en puertos específicos
fuser -k 8000/tcp
fuser -k 8050/tcp
fuser -k 3000/tcp
```

### Error: Variables de entorno no cargadas
```bash
# Verificar que .env existe
cat .env | grep GEMINI

# Recargar variables
export $(cat .env | grep -v '^#' | xargs)
```

### Error: "[MOCK_RESPONSE]" en prompts
Esto indica que `GEMINI_API_KEY` no está disponible en el proceso del backend. Verifica:
1. Que ejecutaste `export $(cat .env | grep -v '^#' | xargs)` antes de iniciar el backend
2. Que el backend se inició desde la misma terminal donde exportaste las variables
3. Que la API key es válida: `echo $GEMINI_API_KEY`

---

## Detener Todos los Servicios

```bash
# Opción 1: Ctrl+C en cada terminal

# Opción 2: Matar todos los procesos
pkill -f uvicorn
pkill -f "next dev"
fuser -k 8000/tcp
fuser -k 8050/tcp
fuser -k 3000/tcp
```

---

## Notas Importantes

- **Orden de inicio**: Puedes iniciar los servicios en cualquier orden, pero es recomendable: Alignment Gateway → Backend → Frontend
- **Logs en tiempo real**: Todos los logs aparecerán directamente en la terminal donde iniciaste cada servicio
- **Hot Reload**: El frontend tiene hot reload automático. El backend requiere reinicio manual para cambios en el código.
