# Security Review: Estado inicial del proyecto

- **Date**: 2026-05-23
- **Status**: Completed
- **Branch**: `development`
- **Scope**: `main.py`, `src/config/settings.py`, `src/api/endpoints/comparativa.py`, `src/api/router.py`, `src/services/comparativa.py`, `pyproject.toml`

---

## Resultado

No se encontraron vulnerabilidades de seguridad con alta confianza (≥ 8/10) en esta revisión.

---

## Candidatos evaluados

| # | Hallazgo | Categoría | Confianza inicial | Disposición |
|---|---|---|---|---|
| 1 | `UnicodeDecodeError` en uploads no-UTF-8 | Input validation | 3/10 | Excluido — genera 500 genérico sin filtración de información |
| 2 | `job_url` reflejado en la respuesta | XSS reflejado potencial | 2/10 | Excluido — el frontend usa `.textContent`, no `innerHTML` |
| 3 | `cv_filename` reflejado en la respuesta | Path traversal / reflected input | 2/10 | Excluido — el filename nunca toca el filesystem |
| 4 | OpenAPI `/docs` expuesto sin autenticación | Information disclosure | 8/10 → 2/10 tras filtro FP | Excluido — API pública sin autenticación; deshabilitar docs es una medida de hardening, no un fix a una cadena de explotación concreta |
| 5 | `BACKEND_CORS_ORIGINS` declarado pero nunca aplicado como middleware | CORS misconfiguration | 4/10 | Excluido — no hay sesión ni auth que robar |
| 6 | `KeyError` en startup si falta `.env` | Error handling | 2/10 | Excluido — solo ocurre en server-side, no es activable remotamente |

---

## Detalle de hallazgos

### Hallazgo 1 — UnicodeDecodeError en archivo no-UTF-8
**Archivo:** `src/api/endpoints/comparativa.py`, línea 74

`content.decode("utf-8")` se llama sin `try/except`. Un archivo `.md` con bytes no-UTF-8 lanza `UnicodeDecodeError`. FastAPI lo captura y devuelve `{"detail": "Internal Server Error"}` sin stack trace. No hay filtración de información. Cae dentro de DOS/fiabilidad — excluido.

---

### Hallazgo 2 — `job_url` reflejado en la respuesta
**Archivo:** `src/schemas/comparativa.py` línea 7, `src/api/endpoints/comparativa.py` líneas 55–78

El campo `job_url` se valida con `HttpUrl(url)` pero el string original sin normalizar es el que se almacena en `ComparativaResponse.job_url: str` y se serializa de vuelta al cliente. En el frontend, todos los campos de la respuesta se insertan via `.textContent` — nunca `innerHTML`. XSS reflejado no es posible con la implementación actual.

---

### Hallazgo 3 — `cv_filename` reflejado en la respuesta
**Archivo:** `src/api/endpoints/comparativa.py`, líneas 57–62

`filename.endswith(".md")` permite nombres como `../../etc/passwd.md`. El filename se refleja como `cv_filename` en el JSON de respuesta. Sin embargo, el filename nunca se usa en ninguna operación de filesystem (confirmado por búsqueda exhaustiva — sin `open()`, `os.path.join`, `shutil` o `aiofiles` en el codebase). Path traversal no es posible. XSS no es posible por el uso de `.textContent`.

---

### Hallazgo 4 — OpenAPI `/docs` expuesto sin autenticación
**Archivo:** `main.py`, líneas 7–11

FastAPI expone `/docs`, `/redoc` y `/openapi.json` por defecto al no pasar `docs_url=None`. Confianza inicial de 8/10, pero tras el filtro de falsos positivos bajó a 2/10. Razones:
- La API es pública e intencionalmente sin autenticación — la UI es de acceso libre.
- Un atacante no obtiene nada de `/openapi.json` que no pueda obtener cargando `index.html` o enviando una request y leyendo la respuesta.
- No hay endpoints privilegiados, auth que bypassear, ni datos sensibles en el schema.
- Deshabilitar los docs en producción es una medida de hardening (best practice), no la solución a una cadena de explotación concreta. Cubierto por la regla de exclusión #6.

---

### Hallazgo 5 — `BACKEND_CORS_ORIGINS` declarado pero no aplicado
**Archivo:** `src/config/settings.py`, línea 23; `main.py` (sin `CORSMiddleware`)

El campo existe en `BaseConfig` pero `CORSMiddleware` nunca se registra con `app.add_middleware()`. Sin embargo, dado que no hay sesiones, cookies de autenticación ni tokens CSRF, un bypass de CORS no tiene privilegio que escalar. No es explotable en el estado actual.

---

### Hallazgo 6 — `KeyError` en startup si `.env` está incompleto
**Archivo:** `src/config/settings.py`, líneas 15, 24–25

`env_file["ENVIRONMENT"]` y `env_file[f"{ENVIRONMENT}_JINA_AI"]` se evalúan en el cuerpo de la clase (tiempo de importación). Si faltan esas keys, se lanza un `KeyError` al arrancar el servidor. El mensaje de error (nombre de la key faltante) solo es visible en los logs del servidor, nunca en la respuesta HTTP. No activable remotamente.

---

## Observaciones para futuras revisiones

Cuando se implemente el pipeline real (Fases 4–6 del `spec/01_backend_fases_implementacion.md`), revisar:

- **SSRF**: `fetch_job_description(url)` recibirá una URL controlada por el usuario y hará una request HTTP a ella (vía Jina AI Reader). Aunque Jina actúa como intermediario, verificar que la key de Jina no permita redirecciones a URLs internas.
- **Prompt injection**: el contenido del CV Markdown (controlado por el usuario) se inyectará directamente en el prompt del LLM. Aunque está excluido per policy, documentar para futura revisión.
- **Información sensible en logs**: cuando `analyze_cv_match` esté implementado, asegurar que el contenido del CV y el job description no se logueen completos.
