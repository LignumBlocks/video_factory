# BIBLIA DE ESTILO VISUAL — HINTSLY LAB
**Versión FINAL — LOCK ABSOLUTO**

> Este documento define el sistema visual oficial de Hintsly Lab.  
> **Todo lo que no esté explícitamente permitido aquí está prohibido.**  
> No es una guía inspiracional: es un **contrato operativo** entre storytelling, generación visual y QC.

---

## 0. Principio Rector
Hintsly Lab comunica **conceptos abstractos complejos sin texto ni UI**, usando **metáfora física**, **geometría simple** y **un único personaje constante**.

El estilo no depende de ilustradores ni gustos: depende de **reglas cerradas**.

---

## 1. Los 3 Mandamientos Inquebrantables
Si una imagen rompe **uno solo**, queda **automáticamente descartada**.

### 1.1 CERO TEXTO / CERO UI
- Prohibido: letras, números, símbolos, %, $, gráficos, barras, gauges, dashboards, pantallas, ventanas, HUDs.
- Prohibido: iconografía tipo UI (checkmarks, alerts, sliders, panels).
- **Toda información se comunica por física:** tamaño, peso, cantidad, distancia, caída, bloqueo, altura.

### 1.2 SINGLE CHARACTER LOCK
- Existe **un solo personaje** en todo el universo visual.
- Prohibido: segundo maniquí, siluetas humanas, multitudes, reflejos humanos.
- Prohibido: manos flotantes (si hay mano, hay brazo y torso).

### 1.3 NO LABORATORIO LITERAL
“Hintsly Lab” es mentalidad, no lugar físico.
- Prohibido: batas, microscopios, tubos de ensayo, pizarras, laboratorios.
- Permitido: metáforas de **ingeniería abstracta**, construcción, sistemas físicos simples.

---

## 2. El Personaje Oficial (Mannequin)

### 2.1 Identidad
- **Masculino**, adulto.
- Maniquí, no humano realista.
- Cabeza calva, **totalmente lisa**.
- **Sin orejas, sin ojos, sin nariz, sin boca**.

### 2.2 Cuerpo
- Proporciones humanas realistas pero **suaves**.
- **Prohibido**: musculatura marcada, abs, pectorales, anatomía explícita.
- El cuerpo debe leerse como **maniquí**, no atleta.

### 2.3 Vestuario (LOCK)
- **Bodysuit de cuello alto (turtleneck)**, visible y evidente.
- Sin costuras visibles, sin bolsillos, sin accesorios.
- Color fijo: **Bodysuit Grey `#6F767F`**.

### 2.4 Piel (LOCK)
- Piel cálida clara:
  - Base: `#E9DDCF`
  - Sombra de forma: `#D9CBBE`
- La piel **solo aparece en cabeza y manos**.

### 2.5 Calzado (LOCK)
- Slip-on simple, integrado al bodysuit.
- Mismo color del bodysuit (`#6F767F`).
- Prohibido: botas, cordones, suelas gruesas.

### 2.6 Reference Asset Rule
- El **asset master** del maniquí es la **única fuente de identidad**.
- El asset **NO define pose, cámara, iluminación ni paleta**.
- Las poses se definen **solo por prompt/storyboard**.

---

## 3. Paleta Cromática — LOCK FINAL

### 3.1 Base Neutra
- **Background (Technical White):** `#F8FAFC`
- **Floor Plane:** `#E6E8EC`
- **Structure / Anchor:** `#3B4047`
- **Bodysuit:** `#6F767F`

### 3.2 Acentos de Evento (UNO POR FRAME)
- **Evento Negativo (Peligro / Costo / Riesgo):** `#B23A48` (Rojo)
- **Evento Positivo (Clean / Checkpoint):** `#2F7D66` (Verde)

**Regla dura:**
- Nunca rojo y verde juntos.
- Si aparece un acento, ocupa **< 8% del frame**.

### 3.3 Prohibiciones
- Prohibido: teal, petrol, azules, beiges adicionales.
- Si aparece un color fuera del lock → **FAIL inmediato**.

---

## 4. Estilo Visual

### 4.1 Render
- **Flat solid colors**.
- **Lineless 100%** (sin outlines, strokes).
- Sin gradientes, blur, glow, grain, noise, texturas.

### 4.2 Sombras
- **Form shadow:** tono más oscuro del mismo material (plano).
- **Contact shadow:** un solo óvalo bajo los pies.
  - Color único: `#3B4047`.
  - Prohibido multi-tono o sombras largas.

---

## 5. Cámara y Composición

### 5.1 Modos
- **CALMA:** plano medio o general, frontal o ligeramente oblicuo, estable.
- **DRAMA:** ángulos bajos/altos, mayor profundidad, escorzo moderado.
  - Foreshortening máx: **1.5×**.
  - **Prohibido tilt** (horizonte siempre nivelado).

### 5.2 Cadencia (DRAMA vs CALMA)
- El DRAMA **no es el default automático**: debe obedecer al storytelling.
- Objetivo operativo del video: **50–60% de tomas en DRAMA** para aportar profundidad, viveza y tensión visual.

#### 5.2.1 Tipos de DRAMA (formal)
- **DRAMA SUAVE:** profundidad y energía sin agresividad.
  - Ángulo leve (low/high sutil), encuadre medio, escorzo leve.
  - Mantiene alta legibilidad.
- **DRAMA FUERTE:** impacto y tensión.
  - Low/high angle marcado o close-up, escorzo moderado (≤ 1.5×), masas grandes y riesgo físico.
  - Se usa en beats clave (hook, riesgo, caída, decisión).

#### 5.2.2 Guardrails anti-fatiga
- Evitar rachas largas: **máximo 3 tomas seguidas** en DRAMA (suave o fuerte).
- Insertar CALMA después de un DRAMA FUERTE para recuperar legibilidad.

#### 5.2.3 Regla del Hook (0–10s)
- Los **primeros 0–10 segundos** del video son **DRAMA casi siempre**.
- Preferencia: DRAMA FUERTE si el beat lo permite sin romper legibilidad.

### 5.3 Regla de Escala
- Maniquí visible:
  - CALMA ≥ **30%** del alto del frame.
  - DRAMA ≥ **22%**.

### 5.3 Espacio
- Formato: **16:9 (1920×1080)**.
- Mantener **30–40% de espacio negativo**.
- Máximo **2 props** (dominante + secundario).

---

## 6. Vocabulario Visual (Metáforas)

- **Valor / Costo:** pucks (discos).
- **Mucho costo:** muchos pucks cayendo.
- **Poco costo:** pocos pucks.
- **Sistema:** contenedor, slot, bloque.
- **Portal A (Placa):** forma sólida orgánica adherida.
- **Portal B (Recorte):** hueco orgánico negativo.
- **Peligro:** caída, acumulación, bloqueo.

Prohibido: rieles, medidores, paneles, botones.

---

## 7. Hook A/B (Props Only)

- Permitido **solo sin maniquí**.
- Dos carriles **independientes**, sin canal ni puente.
- Separados por espacio vacío.
- Fuga siempre en **pucks**, nunca bandas.

---

## 8. Safe Area (Postproducción)

- Texto/disclaimers solo en **post**.
- Safe area recomendado: **tercio inferior derecho**.
- Durante generación puede haber elementos detrás, pero no ocuparlo.

---

## 9. QC Gate — HARD

### 9.1 QC Automático (pre-render)
- No texto / no UI.
- Un solo personaje.
- Paleta lock.
- Un solo acento.
- Máx 2 props.
- Sin outlines/gradientes.

### 9.2 QC Manual (post-render)
- Identidad del maniquí intacta.
- Turtleneck visible.
- Sin orejas ni rasgos.
- Sin props fantasmas.
- Lectura clara en <0.5s.

**Si falla cualquier punto → DESCARTAR.**

---

## 10. Autoridad de Overrides

- **Story & Art Director** tiene autoridad final.
- Toda excepción debe estar marcada explícitamente por **BIT**.

---

## 11. Cierre

Esta Biblia está **cerrada**.

No se modifica por gusto, referencia externa ni output de modelo.
Si algo no encaja, **se ajusta el prompt o se descarta la imagen**, no la Biblia.

**Hintsly Lab funciona porque es consistente.**

