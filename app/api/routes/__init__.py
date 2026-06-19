from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.process import router as process_router
from app.api.routes.metrics import router as metrics_router

__all__ = [
    "health_router",
    "incidents_router",
    "process_router",
    "metrics_router",
]