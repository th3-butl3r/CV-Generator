# Frontend — Plan de Fases de Implementación

- **Date**: 2026-05-23
- **Status**: Proposed
- **Scope**: `src/web/` y `src/web/templates/`

---

## Estado actual

Un único archivo `src/web/index.html` implementa la pantalla completa: formulario de entrada
(URL de oferta + upload de CV `.md`), envío a `POST /api/v1/comparativa/` via `fetch`, y
panel de resultado que muestra `json.message` + volcado JSON crudo.

El resultado que devuelve el backend hoy tiene forma mínima:

```json
{
  "job_url": "https://...",
  "cv_filename": "mi-cv.md",
  "status": "pending",
  "message": "Comparativa recibida. Lógica de análisis pendiente de implementar."
}
```

Una vez que el backend implemente el pipeline real (spec `00`), `ComparativaResponse`
tendrá un campo `result` con `match_score`, `summary`, `strengths`, `skill_gaps` y
`recommendations`. El frontend debe estar listo para consumir esa estructura.

---

## Endpoint de referencia

| Campo | Valor |
|---|---|
| URL | `POST /api/v1/comparativa/` |
| Content-Type | `multipart/form-data` |
| Campo `job_url` | `string` (form field) |
| Campo `cv_file` | archivo `.md` (upload) |
| Respuesta OK (`200`) | `ComparativaResponse` (ver abajo) |
| Error HTTP | `{ "detail": "<mensaje>" }` con códigos 400, 413, 422 |

### ComparativaResponse enriquecida (target del backend)

```json
{
  "job_url": "https://...",
  "cv_filename": "mi-cv.md",
  "status": "completed",
  "message": "Resumen ejecutivo del análisis",
  "result": {
    "match_score": 78,
    "summary": "...",
    "strengths": ["..."],
    "skill_gaps": [
      { "skill": "Docker", "present_in_cv": false, "relevance": "alta" }
    ],
    "recommendations": ["..."]
  }
}
```

El campo `result` es `null` cuando `status === "error"`. El frontend debe manejar ambos
casos sin romper.

---

## Paleta y variables CSS existentes

Definidas en el `:root` de `index.html` — se deben reutilizar en todos los archivos nuevos
sin modificarlas ni duplicarlas (excepto en hojas de estilo de templates de CV, que tienen
sus propias necesidades de impresión).

| Variable | Valor | Uso |
|---|---|---|
| `--bg` | `#0f1117` | Fondo de página |
| `--surface` | `#1a1d27` | Cards y paneles |
| `--surface-hover` | `#21263a` | Estados hover |
| `--border` | `#2d3148` | Bordes y separadores |
| `--accent` | `#6c63ff` | Acciones primarias, énfasis |
| `--accent-hover` | `#5a52e0` | Hover de acento |
| `--text` | `#e2e4f0` | Texto principal |
| `--muted` | `#7b7f9e` | Texto secundario, labels |
| `--success` | `#4ade80` | Estados positivos |
| `--error` | `#f87171` | Estados de error |
| `--radius` | `12px` | Radio de bordes de card |

---

## Principios de diseño para este proyecto

1. **Dark theme canónico**: fondo oscuro (`--bg`) con superficies elevadas (`--surface`).
2. **Sin frameworks externos**: vanilla HTML5 + CSS3 + JS. No añadir librerías CDN.
3. **Responsive mínimo**: breakpoints en `768px` (tablet) y `1024px` (desktop).
4. **Print styles en templates CV**: cada template necesita `@media print` que oculte
   navegación y exponga el contenido limpio para PDF.
5. **Accesibilidad básica**: `<label for>`, `aria-live` en paneles de resultado dinámico,
   contraste suficiente sobre `--bg`.

---

## Fase 1 — Mejorar el panel de resultado (urgente, sin dependencia de backend)

**Objetivo**: reemplazar el volcado JSON crudo por una UI estructurada que presente
`match_score`, `strengths`, `skill_gaps` y `recommendations` de forma legible.

La fase se puede desarrollar ahora usando datos mockeados — el contrato de
`ComparativaResponse` ya está definido en la spec del backend.

### Cambios en `src/web/index.html`

#### 1.1 — Score visual con medidor circular (CSS puro)

Reemplazar `<pre id="resultJson">` por un bloque de resultado rico:

```html
<!-- Dentro de #result, después de #resultMsg -->
<div id="resultDetail" style="display:none">

  <!-- Score -->
  <div class="score-ring" id="scoreRing" role="meter" aria-label="Match score">
    <svg viewBox="0 0 44 44" aria-hidden="true">
      <circle class="track" cx="22" cy="22" r="18"/>
      <circle class="fill"  cx="22" cy="22" r="18" id="scoreArc"/>
    </svg>
    <span id="scoreValue" class="score-value"></span>
  </div>

  <!-- Fortalezas -->
  <section class="result-section" id="sectionStrengths">
    <h3 class="section-title">Fortalezas</h3>
    <ul id="listStrengths" class="tag-list"></ul>
  </section>

  <!-- Brechas de habilidades -->
  <section class="result-section" id="sectionGaps">
    <h3 class="section-title">Brechas de habilidades</h3>
    <ul id="listGaps" class="gap-list"></ul>
  </section>

  <!-- Recomendaciones -->
  <section class="result-section" id="sectionRecs">
    <h3 class="section-title">Recomendaciones</h3>
    <ol id="listRecs" class="rec-list"></ol>
  </section>

</div>
```

El SVG del score usa `stroke-dasharray` / `stroke-dashoffset` calculados en JS a partir de
`match_score` (0–100). La circunferencia del círculo de r=18 es `≈ 113.1`.

```js
// Calcular arco para el score ring
function setScoreArc(score) {
  const CIRCUMFERENCE = 2 * Math.PI * 18; // ≈ 113.1
  const offset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE;
  const arc = document.getElementById('scoreArc');
  arc.style.strokeDasharray  = CIRCUMFERENCE;
  arc.style.strokeDashoffset = offset;
  // Color dinámico según score
  arc.style.stroke = score >= 70 ? 'var(--success)'
                   : score >= 45 ? '#facc15'   // amarillo warning
                   : 'var(--error)';
}
```

#### 1.2 — Función `showResult` actualizada

```js
function showResult(type, title, message, data) {
  result.className = type;
  result.style.display = 'block';
  result.setAttribute('aria-live', 'polite');
  resultTitle.textContent = title;
  resultMsg.textContent   = message;

  const detail = document.getElementById('resultDetail');

  if (data?.result) {
    const r = data.result;
    detail.style.display = 'block';
    document.getElementById('scoreValue').textContent = r.match_score + '%';
    setScoreArc(r.match_score);
    populateList('listStrengths', r.strengths, 'tag');
    populateGaps('listGaps', r.skill_gaps);
    populateList('listRecs',      r.recommendations, 'rec');
  } else {
    detail.style.display = 'none';
  }
}

function populateList(id, items, cssClass) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  (items || []).forEach(text => {
    const li = document.createElement('li');
    li.className = cssClass;
    li.textContent = text;
    el.appendChild(li);
  });
}

function populateGaps(id, gaps) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  (gaps || []).forEach(g => {
    const li = document.createElement('li');
    li.className = 'gap-item';
    li.dataset.relevance = g.relevance;
    li.innerHTML = `<span class="gap-skill">${g.skill}</span>
                    <span class="gap-status ${g.present_in_cv ? 'ok' : 'missing'}">
                      ${g.present_in_cv ? 'Presente' : 'Faltante'}
                    </span>
                    <span class="gap-relevance">${g.relevance}</span>`;
    el.appendChild(li);
  });
}
```

#### 1.3 — Backward compatibility

Mientras el backend retorne `status: "pending"` y `result: null`, `#resultDetail` permanece
oculto y solo se muestra `resultMsg` con el mensaje de texto. No hay cambio observable para
el usuario hasta que el backend esté listo.

---

## Fase 2 — Generador de CV (nueva página)

**Objetivo**: permitir al usuario rellenar un formulario y descargar un CV generado en
PDF/HTML usando uno de los templates disponibles en `src/web/templates/`.

Esta fase depende de definir el endpoint de generación de CV en el backend. **No implementar
hasta confirmar el contrato del endpoint.**

### Preguntas que deben resolverse antes de empezar

1. ¿Qué endpoint expone el backend para la generación? URL, método HTTP y schema de entrada.
2. ¿El CV se genera server-side (el backend devuelve HTML/PDF) o client-side (JS renderiza
   un template en el browser)?
3. ¿Cuántos templates hay previstos? ¿Tienen nombre/identificador definido?
4. ¿El usuario puede previsualizar el CV antes de descargarlo?

### Estructura de archivos prevista (pendiente de confirmación)

```
src/web/
├── index.html              # Pantalla actual: comparativa CV-oferta
├── cv-generator.html       # (Fase 2) Formulario de generación de CV
└── templates/
    ├── base-template.css   # Variables y reset comunes a todos los templates
    ├── classic.html        # Template clásico (una columna)
    └── modern.html         # Template moderno (dos columnas)
```

### Campos del formulario de CV (borrador)

Los campos se derivan del contenido habitual de un CV en Markdown. Confirmar con el schema
del backend antes de implementar.

| Campo | Tipo HTML | Notas |
|---|---|---|
| Nombre completo | `<input type="text">` | required |
| Título profesional | `<input type="text">` | |
| Email | `<input type="email">` | required |
| Teléfono | `<input type="tel">` | |
| LinkedIn / URL | `<input type="url">` | |
| Resumen profesional | `<textarea>` | max ~500 chars |
| Experiencia laboral | bloque repetible | empresa, cargo, fechas, descripción |
| Educación | bloque repetible | institución, título, año |
| Habilidades | input de tags | lista separada por comas |
| Template a usar | `<select>` o radio cards | opciones: classic, modern, ... |

### Notas de UX para Fase 2

- Los bloques repetibles (experiencia, educación) se añaden/eliminan dinámicamente con JS
  sin recarga de página.
- Mostrar un panel de previsualización en tiempo real si el backend soporta render
  server-side, o aplicar el template CSS directamente en el browser.
- El botón de descarga dispara la petición al backend y recibe el PDF o abre el HTML en
  una nueva pestaña para que el usuario imprima (Ctrl+P → Guardar como PDF).

---

## Fase 3 — Templates de CV (HTML + CSS)

**Objetivo**: crear los archivos de template en `src/web/templates/` que el backend Jinja2
(o el browser directamente) puede usar para renderizar el CV con los datos del usuario.

### Estructura de un template

Cada template es un archivo HTML autocontenido con:

- Variables Jinja2 para los datos del usuario: `{{ name }}`, `{{ email }}`, etc.
- Estilos `@media print` que ocultan cabeceras del browser y ajustan márgenes para A4.
- Clases CSS semánticas: `.cv-header`, `.cv-section`, `.cv-entry`, `.cv-skills`.
- Sin dependencias externas (no Google Fonts CDN hasta que se apruebe).

### Template clásico (`classic.html`) — estructura mínima

```
┌─────────────────────────────────┐
│  Nombre │ Título                │  ← .cv-header (una columna)
│  email · tel · linkedin         │
├─────────────────────────────────┤
│  Resumen profesional            │  ← .cv-section
├─────────────────────────────────┤
│  Experiencia laboral            │  ← .cv-section
│    Empresa · Cargo · Fechas     │  ← .cv-entry
│    descripción                  │
├─────────────────────────────────┤
│  Educación                      │  ← .cv-section
├─────────────────────────────────┤
│  Habilidades                    │  ← .cv-section .cv-skills
└─────────────────────────────────┘
```

### Template moderno (`modern.html`) — estructura mínima

```
┌──────────────┬──────────────────┐
│  .cv-sidebar │  .cv-main        │
│  foto        │  Resumen         │
│  contacto    │  Experiencia     │
│  habilidades │  Educación       │
└──────────────┴──────────────────┘
```

Implementar con CSS Grid: `grid-template-columns: 280px 1fr`.

### Print styles obligatorios en cada template

```css
@media print {
  /* Eliminar fondo oscuro para ahorro de tinta */
  body { background: #fff; color: #000; }

  /* Evitar cortes de página dentro de una entrada */
  .cv-entry { page-break-inside: avoid; }

  /* Ocultar elementos no imprimibles */
  .no-print { display: none !important; }

  /* Márgenes A4 estándar */
  @page { margin: 20mm 15mm; }
}
```

---

## Fase 4 — Navegación y estructura multi-página

**Objetivo**: una vez que existan dos páginas (`index.html` y `cv-generator.html`), añadir
navegación consistente.

### Opciones

**Opción A — Header compartido inline** (más simple, sin build step):
Repetir el mismo bloque `<header>` / `<nav>` en cada HTML. Mantenimiento manual.

**Opción B — Web Components o `<template>` tag**:
Definir el nav en un fragment e inyectarlo con JS. Más mantenible pero añade complejidad.

Recomendación: **Opción A** hasta que haya tres o más páginas.

### Navegación prevista

```html
<nav class="site-nav" aria-label="Navegación principal">
  <a href="/index.html"         class="nav-link">Comparativa</a>
  <a href="/cv-generator.html"  class="nav-link">Generar CV</a>
</nav>
```

El backend FastAPI sirve los archivos estáticos desde `src/web/` — confirmar que la ruta
base es correcta antes de implementar los `href`.

---

## Dependencias entre fases

```
Fase 1  ──►  Sin dependencias externas. Empieza ahora.
Fase 2  ──►  Requiere: confirmar endpoint de generación de CV en backend.
Fase 3  ──►  Requiere: decidir si render es server-side (Jinja2) o client-side.
Fase 4  ──►  Requiere: Fase 2 completada (necesita segunda página para que el nav tenga sentido).
```

---

## Archivos afectados por fase

| Fase | Archivos a crear/modificar |
|---|---|
| 1 | `src/web/index.html` (modificar) |
| 2 | `src/web/cv-generator.html` (crear) |
| 3 | `src/web/templates/classic.html` (crear), `src/web/templates/modern.html` (crear), `src/web/templates/base-template.css` (crear) |
| 4 | `src/web/index.html` (añadir nav), `src/web/cv-generator.html` (añadir nav) |
