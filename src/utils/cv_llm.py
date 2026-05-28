from loguru import logger
from ollama import AsyncClient


_MAX_CV_CHARS = 2500
_MAX_JOB_CHARS = 1000

_SYSTEM_PROMPT = """Eres un experto en redacción de CVs. Genera un CV profesional en Markdown, optimizado para la oferta laboral.

Usa EXACTAMENTE esta estructura:

# [Nombre Completo]

**[Cargo objetivo]** | [email] | [teléfono] | [ciudad, país]

---

## Perfil Profesional

[2-3 oraciones que destaquen lo más relevante para esta oferta concreta]

---

## Experiencia

### [Cargo] — [Empresa] · [Ciudad] *(inicio – fin)*

- [Logro o responsabilidad]
- [Logro o responsabilidad]

---

## Habilidades

**[Categoría]:** skill1, skill2, skill3

---

## Educación

**[Título]** — [Universidad] *(inicio – fin)*

---

## Idiomas

- **[Idioma]:** [Nivel]

Reglas:
- Extrae TODA la información del CV del candidato
- Optimiza ÚNICAMENTE el "Perfil Profesional" para la oferta
- NO inventes datos que no estén en el CV
- Responde SOLO con el Markdown, sin texto adicional antes ni después"""


async def generate_markdown_cv(
    cv_content: str,
    job_description: str,
    model: str,
    host: str,
) -> str:
    """Genera un CV en formato Markdown optimizado para una oferta laboral.

    Args:
        cv_content: Contenido del CV base en Markdown.
        job_description: Texto limpio de la oferta laboral.
        model: Nombre del modelo Ollama a usar.
        host: URL del servidor Ollama.

    Returns:
        String con el CV en formato Markdown.

    Raises:
        RuntimeError: Si el LLM no retorna contenido válido.
    """
    logger.info(f"BL > generate_markdown_cv() - Llamando Ollama | model={model}")

    client = AsyncClient(host=host)
    user_message = (
        f"CV del candidato:\n{cv_content[:_MAX_CV_CHARS]}\n\n"
        f"Oferta laboral:\n{job_description[:_MAX_JOB_CHARS]}\n\n"
        "Genera el CV en Markdown optimizado para esta oferta."
    )

    response = await client.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    result = (response.message.content or "").strip()
    if not result:
        raise RuntimeError("El LLM retornó una respuesta vacía.")

    logger.info(f"BL > generate_markdown_cv() - CV generado | chars={len(result)}")
    return result
