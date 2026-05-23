from fastapi import APIRouter

from api.endpoints.comparativa import router as comparativa_router

api_router = APIRouter()

api_router.include_router(comparativa_router, prefix="/comparativa", tags=["Comparativa"])
