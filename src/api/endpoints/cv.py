import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import HttpUrl, ValidationError

from config.settings import logger
from services.cv_generator import CVGeneratorService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
AVAILABLE_TEMPLATES = {"clasico", "moderno"}
_INTERNAL_ERROR_MSG = "No se pudo generar el CV. Por favor, inténtalo de nuevo."


def _validate_url(url: str) -> None:
    """Valida que la URL sea HTTP/HTTPS válida.

    Args:
        url: String con la URL a validar.

    Raises:
        HTTPException: Si la URL no es válida.
    """
    try:
        HttpUrl(url)
    except ValidationError:
        raise HTTPException(
            status_code=422, detail="La URL de la oferta laboral no es válida."
        )


@router.post("/generate", summary="Generar CV en PDF optimizado para una oferta")
async def generate_cv(
    job_url: str = Form(..., description="URL de la oferta laboral"),
    cv_file: UploadFile = File(..., description="CV base en formato Markdown"),
    template: str = Form("clasico", description="Nombre de la plantilla a usar"),
) -> StreamingResponse:
    """Recibe una URL de oferta y un CV en Markdown, devuelve un PDF optimizado.

    Args:
        job_url: URL de la oferta laboral.
        cv_file: Archivo `.md` con el CV base del candidato.
        template: Nombre de la plantilla HTML a usar.

    Returns:
        StreamingResponse con el PDF generado para descarga.

    Raises:
        HTTPException: Si los inputs son inválidos o el pipeline falla.
    """
    logger.info(
        f"BL > generate_cv() - Solicitud recibida | job_url={job_url} | template={template}"
    )

    _validate_url(job_url)

    if template not in AVAILABLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Plantilla '{template}' no disponible. Opciones: {', '.join(AVAILABLE_TEMPLATES)}",
        )

    filename = cv_file.filename or ""
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .md")

    content = await cv_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail="El archivo supera el límite de 5 MB."
        )

    cv_text = content.decode("utf-8")

    try:
        pdf_bytes = await CVGeneratorService.generate(
            job_url=job_url,
            cv_content=cv_text,
            template_name=template,
        )
    except Exception as exc:
        logger.error(f"BL > generate_cv() - Error en pipeline | {exc}")
        raise HTTPException(status_code=500, detail=_INTERNAL_ERROR_MSG)

    logger.info("BL > generate_cv() - PDF entregado al cliente")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cv_optimizado.pdf"},
    )
