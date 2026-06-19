import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.trace import bind_trace_id, reset_trace_id

logger = logging.getLogger("IncidentIQ.Core.RequestLoggingMiddleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request-level structured logging.

    It:
    - Reads X-Trace-Id from request headers.
    - Generates a trace ID when missing or invalid.
    - Stores trace ID in context.
    - Adds X-Trace-Id to response headers.
    - Logs request start and completion.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Runs for every HTTP request.
        """

        incoming_trace_id = request.headers.get("X-Trace-Id")
        active_trace_id, trace_token = bind_trace_id(trace_id=incoming_trace_id)

        start_time = time.perf_counter()

        logger.info(
            "HTTP request started",
            extra={
                "http_method": request.method,
                "path": request.url.path,
                "client_host": self._get_client_host(request=request),
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = self._calculate_duration_ms(start_time=start_time)

            self._record_http_metrics(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )

            logger.exception(
                "HTTP request failed",
                extra={
                    "http_method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "client_host": self._get_client_host(request=request),
                },
            )

            reset_trace_id(token=trace_token)
            raise

        duration_ms = self._calculate_duration_ms(start_time=start_time)
        response.headers["X-Trace-Id"] = active_trace_id

        self._record_http_metrics(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        logger.info(
            "HTTP request completed",
            extra={
                "http_method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_host": self._get_client_host(request=request),
            },
        )

        reset_trace_id(token=trace_token)

        return response

    def _calculate_duration_ms(self, start_time: float) -> float:
        """
        Calculates request duration in milliseconds.
        """

        duration_seconds = time.perf_counter() - start_time
        duration_ms = round(duration_seconds * 1000, 2)

        return duration_ms

    def _get_client_host(self, request: Request) -> str:
        """
        Safely reads client host from FastAPI request.
        """

        if request.client is None:
            return "unknown"

        return request.client.host
    
    def _record_http_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """
        Records HTTP metrics using a local import to avoid circular imports.
        """

        from app.services.metrics_service import application_metrics

        application_metrics.record_http_request(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
