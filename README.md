# FinanceVideoPlatform (VideoFactory)

Sistema de generación de videos financieros automatizados.

## Instalación

1.  **Clonar repositorio**:
    ```bash
    git clone <repo_url>
    cd FinanceVideoPlatform
    ```

2.  **Configurar entorno virtual**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Variables de entorno**:
    Copiar `.env.example` a `.env` y configurar las credenciales necesarias (Kie.ai, etc).

## Uso CLI

El sistema incluye un wrapper `videofactory` para facilitar la ejecución.

### Crear un nuevo RUN
Valida los inputs y prepara la estructura de directorios.

```bash
./videofactory create-run --script <path> --voiceover <path> --bible <path>
```

### Ejecutar un RUN existente
Retoma la ejecución del pipeline para un ID dado.

```bash
./videofactory execute-run --run-id <run_id>
```

### Ayuda
Para ver todos los comandos disponibles:
```bash
./videofactory --help
```

## Estructura de Directorios

- `src/`: Código fuente del paquete `videofactory`.
    - `orchestrator.py`: Lógica principal del pipeline.
    - `foundation/`: Validadores y modelos base.
- `runs/`: Directorio de salida local (gitignored) para artefactos de cada ejecución.
- `tests/`: Tests unitarios y de integración (pytest).
- `logs/`: Logs de ejecución.

## Ejecución de Tests

Para correr la suite de pruebas:

```bash
pytest
```
