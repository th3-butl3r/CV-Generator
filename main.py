from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.api.router import api_router

app = FastAPI(
    title="CV Generator",
    description="API de comparativa entre oferta laboral y CV.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory="src/web"), name="static")


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    """Sirve la interfaz gráfica principal."""
    logger.info("BL > root() - Sirviendo frontend")
    return FileResponse("src/web/index.html")
