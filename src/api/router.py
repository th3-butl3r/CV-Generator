from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api.endpoints.comparativa import router as comparativa_router
from api.endpoints.cv import router as cv_router
from config.settings import settings

api_router = APIRouter()

api_router.include_router(comparativa_router, prefix="/comparativa", tags=["Comparativa"])
api_router.include_router(cv_router, prefix="/cv", tags=["CV"])


@api_router.get("/config", tags=["Config"], summary="Configuración pública de la app")
async def get_config() -> JSONResponse:
    """Devuelve la configuración no sensible necesaria para el frontend.

    Returns:
        JSONResponse con el proveedor LLM activo.
    """
    return JSONResponse(content={"llm_provider": settings.LLM_PROVIDER})
