from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health_router, incidents_router, process_router,metrics_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.core.logging_middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """
    It creates required directories during startup.
    """

    active_settings = get_settings()
    active_settings.create_required_directories()

    yield


settings = get_settings()
configure_logging(settings=settings)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "IncidentIQ is an AI-powered DevOps incident triage and remediation assistant using FastAPI, LangGraph, RAG, ChromaDB, and mocked DevOps tools."
    ),
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health_router, tags=["Health"])
app.include_router(process_router, tags=["Process"])
app.include_router(incidents_router, tags=["Incidents"])
app.include_router(metrics_router, tags=["Metrics"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
