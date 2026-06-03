import httpx

from config.settings import settings, logger

_MAX_CV_CHARS = 3000
_MAX_JOB_CHARS = 2000

_ADVICE_PROMPT = """Eres un experto en reclutamiento y optimización de CVs para sistemas ATS.
Analiza en detalle el CV y la oferta laboral. Da consejos concretos, accionables y específicos.
Menciona SIEMPRE elementos reales del CV y de la oferta. Nunca des consejos genéricos.
No inventes datos que no estén en el CV.

Responde ÚNICAMENTE con este formato Markdown, sin texto antes ni después:

## Compatibilidad general

**Nivel:** [Alto / Medio / Bajo]

[3-4 oraciones explicando los puntos fuertes y las debilidades del perfil para esta oferta concreta. Sé directo.]

## Palabras clave ATS — inclúyelas en tu CV

**Habilidades técnicas:** [términos técnicos exactos de la oferta que faltan o deben reforzarse]
**Herramientas y tecnologías:** [software, plataformas, frameworks mencionados en la oferta]
**Metodologías:** [procesos, frameworks de trabajo, certificaciones requeridas]
**Soft skills:** [competencias blandas que la oferta menciona explícitamente]

## Ajustes recomendados por sección

### Perfil profesional
[Indica frases concretas que cambiar, términos de la oferta que incorporar y qué eliminar por irrelevante]

### Experiencia laboral
[Para cada puesto del CV: qué logros reformular con métricas, qué verbos de acción usar, qué responsabilidades resaltar según la oferta]

### Habilidades
[Qué agregar, reorganizar o eliminar de la sección de habilidades según los requisitos de la oferta]

### Otras secciones
[Sugerencias puntuales para educación, certificaciones, proyectos o idiomas si son relevantes para la oferta]

## Fortalezas a destacar

[Lista de 4-6 puntos específicos del CV que encajan directamente con la oferta y cómo presentarlos de forma más impactante]

## Brechas y estrategia para compensarlas

[Para cada brecha: qué requisito falta, por qué es importante en esta oferta y cómo compensarlo de forma honesta sin inventar datos]"""

_CV_GENERATION_PROMPT = """Eres un experto redactor de CVs profesionales. Genera un CV en Markdown basándote EXCLUSIVAMENTE en el CV del candidato, optimizándolo para la oferta indicada.

Reglas estrictas:
- NO inventes experiencias, empresas, fechas ni habilidades que no estén en el CV original
- SÍ reformula logros usando el vocabulario y las palabras clave de la oferta
- SÍ reorganiza y prioriza la información según lo que más valora la oferta
- SÍ reescribe el perfil profesional orientado directamente a la oferta

Usa EXACTAMENTE esta estructura Markdown, sin texto antes ni después:

# [Nombre Completo]

**[Cargo objetivo alineado con la oferta]** | [email] | [teléfono] | [ciudad, país]

---

## Perfil Profesional

[3-4 oraciones que conecten la experiencia del candidato con los requisitos de la oferta. Usa palabras clave de la oferta.]

---

## Experiencia

### [Cargo] — [Empresa] · [Ciudad] *(inicio – fin)*

- [Logro reformulado con métricas si existen en el CV original]
- [Responsabilidad relevante para la oferta, en lenguaje de la oferta]

---

## Habilidades

**[Categoría]:** skill1, skill2, skill3

---

## Educación

**[Título]** — [Universidad] *(inicio – fin)*

---

## Idiomas

- **[Idioma]:** [Nivel]"""


def _llm_request_params() -> tuple[str, dict[str, str], str]:
    """Retorna (url, headers, model) según el proveedor LLM configurado."""
    if settings.LLM_PROVIDER == "ollama":
        return (
            f"{settings.OLLAMA_HOST}/v1/chat/completions",
            {"Content-Type": "application/json"},
            settings.OLLAMA_MODEL,
        )
    return (
        settings.OPENROUTER_URL,
        {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        settings.OPENROUTER_MODEL,
    )


async def _call_llm(system_prompt: str, user_message: str) -> str:
    """Realiza una llamada al proveedor LLM configurado y retorna el contenido del mensaje.

    Args:
        system_prompt: Instrucciones de sistema para el modelo.
        user_message: Mensaje del usuario con los datos a procesar.

    Returns:
        Contenido de texto de la respuesta del modelo.

    Raises:
        RuntimeError: Si la respuesta está vacía.
    """
    url, headers, model = _llm_request_params()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    content = (response.json()["choices"][0]["message"]["content"] or "").strip()
    if not content:
        raise RuntimeError("El LLM retornó una respuesta vacía.")
    return content


async def generate_cv_advice(cv_content: str, job_description: str) -> str:
    """Genera consejos para optimizar el CV del candidato para una oferta laboral.

    Args:
        cv_content: Contenido del CV base en Markdown.
        job_description: Texto limpio de la oferta laboral.

    Returns:
        String con los consejos en formato Markdown.
    """
    logger.info(
        f"BL > generate_cv_advice() - Llamando {settings.LLM_PROVIDER} | model={settings.OLLAMA_MODEL if settings.LLM_PROVIDER == 'ollama' else settings.OPENROUTER_MODEL}"
    )

    user_message = (
        f"CV del candidato:\n{cv_content[:_MAX_CV_CHARS]}\n\n"
        f"Oferta laboral:\n{job_description[:_MAX_JOB_CHARS]}\n\n"
        "Analiza el CV frente a la oferta y proporciona los consejos en el formato indicado."
    )

    result = await _call_llm(_ADVICE_PROMPT, user_message)
    logger.info(f"BL > generate_cv_advice() - Consejos generados | chars={len(result)}")
    return result


async def generate_markdown_cv(cv_content: str, job_description: str) -> str:
    """Genera un CV en Markdown optimizado para la oferta, basado en el CV original.

    Args:
        cv_content: Contenido del CV base en Markdown.
        job_description: Texto limpio de la oferta laboral.

    Returns:
        String con el CV en formato Markdown.
    """
    logger.info(
        f"BL > generate_markdown_cv() - Llamando {settings.LLM_PROVIDER} | model={settings.OLLAMA_MODEL if settings.LLM_PROVIDER == 'ollama' else settings.OPENROUTER_MODEL}"
    )

    user_message = (
        f"CV del candidato:\n{cv_content[:_MAX_CV_CHARS]}\n\n"
        f"Oferta laboral:\n{job_description[:_MAX_JOB_CHARS]}\n\n"
        "Genera el CV en Markdown optimizado para esta oferta."
    )

    result = await _call_llm(_CV_GENERATION_PROMPT, user_message)
    logger.info(f"BL > generate_markdown_cv() - CV generado | chars={len(result)}")
    return result
