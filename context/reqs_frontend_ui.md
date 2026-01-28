# Requisito Funcional: Frontend GUI ("The Cockpit")

## Objetivo
Visualizar el "Vertical Asset Stream" de forma humana, siguiendo los principios de `gui.md`.

## Stack Sugerido
- **Framework:** Next.js (React) o Vite + React.
- **Estilos:** TailwindCSS (Dark Mode por defecto, colores vibrantes como "Cyberpunk Financial").
- **Estado:** React Query (para sincronizar con API).

## Vistas Principales

### 1. Panel de Control (Shot Master View)
Es la "Capa 1" del diseño.
- **Layout:** Grid de tarjetas o Lista Rica.
- **Elemento por fila:** 1 Shot.
- **Componentes:**
    - **Thumbnail:** El `Clip` seleccionado (si existe) o la `Image` seleccionada. Si mueve el mouse, reproduce preview.
    - **Header:** Shot ID + Intent (texto corto).
    - **Traffic Light:** Status de QC (Verde/Rojo/Gris).
    - **Actions:** Botón "Detail" y "Regen".

### 2. Inspector de Shot (Detail View)
Es la "Capa 2" (Árbol). Se abre al hacer click en un Shot.
- **Layout:** Horizontal Swimlane o Árbol Vertical.
- **Secciones:**
    - **Planning:** Bloque de texto estático (Script).
    - **Prompt:** Muestra el prompt activo. Click para ver historial de versiones.
    - **Assets:** Muestra `Start` y `End` images.
        - **Feature Clave:** "Version Carousel". Flechas < > para cambiar entre versiones de imagen generadas.
    - **Clip:** Reproductor de video grande.

### 3. Interacciones Clave
- **"Make Hero":** Botón en cualquier asset del historial para promoverlo a `Selected`.
    - Al hacer click, la UI se actualiza inmediatamente y el backend guarda el cambio.
- **QC Toggle:** Botón "Approve / Reject" rápido en cada asset.

## Mockup Mental
Imagine un editor de video no-lineal (tipo Premiere) pero simplificado, donde cada "clip" en el timeline es un contenedor profundo de versiones.
