import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import asr, benchmark, session, story, tts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    for sub in ("audio", "sessions"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    Path("./stories").mkdir(parents=True, exist_ok=True)
    logger.info("VoxQuest-AI backend started. Data dir: %s", data_dir.resolve())
    yield
    logger.info("VoxQuest-AI backend shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="VoxQuest-AI",
        description="Voice-first AI Assistant RPG Backend",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(asr.router)
    app.include_router(tts.router)
    app.include_router(story.router)
    app.include_router(benchmark.router)
    app.include_router(session.router)

    audio_dir = Path(settings.data_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok",
            "service": "VoxQuest-AI",
            "version": "1.0.0",
            "llm_provider": settings.llm_provider,
            "tts_engine": settings.tts_engine,
            "whisper_model": settings.whisper_model_size,
        }

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "path": str(request.url.path)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "path": str(request.url.path)},
        )

    return app


app = create_app()
