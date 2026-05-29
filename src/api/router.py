from fastapi import APIRouter

from api.endpoints.comparativa import router as comparativa_router
from api.endpoints.cv import router as cv_router

api_router = APIRouter()

api_router.include_router(comparativa_router, prefix="/comparativa", tags=["Comparativa"])
api_router.include_router(cv_router, prefix="/cv", tags=["CV"])
