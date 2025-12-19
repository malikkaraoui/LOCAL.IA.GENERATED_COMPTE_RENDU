"""Point d'entrée principal de l'API FastAPI."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.api.routes import reports, health, auth, branding, llm

# Créer l'application
app = FastAPI(
    title=settings.APP_NAME,
    description="API de génération de rapports RH avec LLM",
    version="2.0.1",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix=settings.API_PREFIX, tags=["health"])
app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["auth"])
app.include_router(reports.router, prefix=settings.API_PREFIX, tags=["reports"])
app.include_router(branding.router, prefix=settings.API_PREFIX, tags=["branding"])
app.include_router(llm.router, prefix=settings.API_PREFIX, tags=["llm"])


def _configure_logging() -> None:
    """Configure un logging simple (stdout) pour l'API.

    Les logs détaillés runtime sont redirigés vers /tmp/backend.log par scripts/start-all.sh.
    """
    level_name = (getattr(settings, "LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@app.get("/")
async def root():
    """Page d'accueil de l'API."""
    return {
        "message": "RapportIA API",
        "version": "2.0.1",
        "docs": f"{settings.API_PREFIX}/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Gestion globale des erreurs."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn

    _configure_logging()
    
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=(getattr(settings, "LOG_LEVEL", "info") or "info").lower(),
        access_log=True,
    )
