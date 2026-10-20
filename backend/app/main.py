"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import update
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import guides, llm_config, research
from app.config import Settings, get_settings
from app.db.models import ResearchRunRow, utcnow
from app.errors import error_body, install_error_handlers
from app.logging_setup import configure_logging
from app.security.csrf import CSRFMiddleware
from app.seed.loader import upsert_seed_guides
from app.services.llm.base import LLMError
from app.state import AppState, build_state

logger = logging.getLogger("atlas")


async def _mark_interrupted_runs(state: AppState) -> None:
    async with state.db.session() as session:
        await session.execute(
            update(ResearchRunRow)
            .where(ResearchRunRow.status.in_(["queued", "running"]))
            .values(
                status="failed",
                error_code="interrupted",
                error_message="Research was interrupted by a server restart. Retry to run it again.",
                finished_at=utcnow(),
            )
        )
        await session.commit()


async def _purge_loop(state: AppState) -> None:
    while True:
        await asyncio.sleep(300)
        await state.sessions.purge_expired()


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/api/session"):
            response.headers["Cache-Control"] = "no-store"
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        state = build_state(settings)
        app.state.atlas = state
        if settings.auto_create_tables:
            await state.db.create_all()
        seeded = await upsert_seed_guides(state.db)
        await _mark_interrupted_runs(state)
        logger.info(
            "Integration Atlas ready: %d seed guides, default LLM %s, search %s",
            seeded,
            "configured" if settings.default_llm_configured else "not configured",
            "configured" if settings.search_configured else "not configured",
        )
        purge = asyncio.create_task(_purge_loop(state))
        try:
            yield
        finally:
            purge.cancel()
            for task in list(state.tasks):
                task.cancel()
            with contextlib.suppress(Exception):
                await asyncio.gather(*state.tasks, return_exceptions=True)
            await state.db.dispose()

    app = FastAPI(
        title="Integration Atlas API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)

    @app.exception_handler(LLMError)
    async def _llm_error(_: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.http_status)

    app.add_middleware(CSRFMiddleware, allowed_origins=settings.allowed_origins)
    app.add_middleware(SecurityHeaders)

    app.include_router(llm_config.router)
    app.include_router(research.router)
    app.include_router(guides.router)

    @app.get("/api/health", tags=["meta"])
    async def health() -> dict:
        return {
            "status": "ok",
            "default_llm_configured": settings.default_llm_configured,
            "search_configured": settings.search_configured,
        }

    return app


app = create_app()
