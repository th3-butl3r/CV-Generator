import httpx
from config.settings import logger


async def fetch_job_description(url: str, api_key: str, timeout: int = 15) -> str:
    """Obtiene el texto limpio de una oferta laboral usando la Jina AI Reader API.

    Args:
        url: URL pública de la oferta laboral.
        api_key: Bearer token de Jina AI.
        timeout: Segundos antes de lanzar TimeoutException.

    Returns:
        Texto Markdown limpio con el contenido de la oferta.

    Raises:
        ValueError: Si ocurre timeout, error HTTP, o la respuesta está vacía.
    """
    jina_url = f"https://r.jina.ai/{url}"
    logger.info(f"BL > fetch_job_description() - Fetching job description | url={url}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(
                jina_url,
                headers={"Authorization": f"Bearer {api_key}"},
            )

            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ValueError(f"Timeout al obtener la oferta laboral: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"Error HTTP {exc.response.status_code} al obtener la oferta laboral"
            ) from exc

    text = response.text.strip()
    if not text:
        raise ValueError("La respuesta de Jina AI está vacía")

    logger.info(f"BL > fetch_job_description() - Texto obtenido | chars={len(text)}")
    return text
