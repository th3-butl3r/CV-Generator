import ipaddress
from urllib.parse import urlparse

import httpx
from config.settings import logger


def _block_private_hosts(url: str) -> None:
    """Rechaza URLs cuyo host sea una dirección IP privada, loopback o link-local.

    Protege contra SSRF: evita que se reenvíen peticiones a rangos internos
    (127.x, 10.x, 172.16-31.x, 192.168.x, 169.254.x, ::1, etc.).

    Args:
        url: URL a inspeccionar.

    Raises:
        ValueError: Si el host es una IP en rango privado/reservado.
    """
    hostname = urlparse(url).hostname or ""
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError(f"Host no permitido: {hostname}")
    except ValueError as exc:
        # Re-lanza solo si fue nuestra validación; ignora el error de parseo de dominio
        if "Host no permitido" in str(exc):
            raise


async def fetch_job_description(url: str, api_key: str, timeout: int = 15) -> str:
    """Obtiene el texto limpio de una oferta laboral usando la Jina AI Reader API.

    Args:
        url: URL pública de la oferta laboral.
        api_key: Bearer token de Jina AI.
        timeout: Segundos antes de lanzar TimeoutException.

    Returns:
        Texto Markdown limpio con el contenido de la oferta.

    Raises:
        ValueError: Si la URL apunta a un host privado, ocurre timeout, error HTTP,
            o la respuesta está vacía.
    """
    _block_private_hosts(url)
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
