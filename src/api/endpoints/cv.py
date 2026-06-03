import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import HttpUrl, ValidationError

from config.settings import logger
from services.cv_generator import CVAdvisorService, CVGeneratorService

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
AVAILABLE_TEMPLATES = {"clasico", "moderno"}
_INTERNAL_ERROR_MSG = "No se pudo procesar la solicitud. Por favor, inténtalo de nuevo."


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


async def _read_cv_file(cv_file: UploadFile) -> str:
    """Valida y lee el contenido de un archivo CV en Markdown.

    Args:
        cv_file: Archivo subido por el usuario.

    Returns:
        Contenido del archivo como string.

    Raises:
        HTTPException: Si el archivo es inválido, vacío o demasiado grande.
    """
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

    return content.decode("utf-8")


@router.post(
    "/generate", summary="Analizar CV vs oferta y generar consejos de optimización"
)
async def analyze_cv(
    job_url: str = Form(..., description="URL de la oferta laboral"),
    cv_file: UploadFile = File(..., description="CV base en formato Markdown"),
) -> JSONResponse:
    """Recibe una URL de oferta y un CV en Markdown, devuelve consejos de optimización.

    Args:
        job_url: URL de la oferta laboral.
        cv_file: Archivo `.md` con el CV base del candidato.

    Returns:
        JSONResponse con los consejos en formato Markdown.
    """
    logger.info(f"BL > analyze_cv() - Solicitud recibida | job_url={job_url}")
    _validate_url(job_url)
    cv_text = await _read_cv_file(cv_file)

    try:
        advice = await CVAdvisorService.analyze(job_url=job_url, cv_content=cv_text)
    except ValueError as exc:
        logger.warning(f"BL > analyze_cv() - URL rechazada | {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"BL > analyze_cv() - Error en pipeline | {exc}")
        raise HTTPException(status_code=500, detail=_INTERNAL_ERROR_MSG)

    logger.info("BL > analyze_cv() - Consejos entregados al cliente")
    return JSONResponse(content={"advice": advice})


@router.post("/pdf", summary="Generar CV en PDF optimizado para una oferta")
async def generate_cv_pdf(
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
    """
    logger.info(
        f"BL > generate_cv_pdf() - Solicitud recibida | job_url={job_url} | template={template}"
    )
    _validate_url(job_url)

    if template not in AVAILABLE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Plantilla '{template}' no disponible. Opciones: {', '.join(AVAILABLE_TEMPLATES)}",
        )

    cv_text = await _read_cv_file(cv_file)

    try:
        pdf_bytes = await CVGeneratorService.generate(
            job_url=job_url,
            cv_content=cv_text,
            template_name=template,
        )
    except ValueError as exc:
        logger.warning(f"BL > generate_cv_pdf() - URL rechazada | {exc}")
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"BL > generate_cv_pdf() - Error en pipeline | {exc}")
        raise HTTPException(status_code=500, detail=_INTERNAL_ERROR_MSG)

    logger.info("BL > generate_cv_pdf() - PDF entregado al cliente")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=cv_optimizado.pdf"},
    )
