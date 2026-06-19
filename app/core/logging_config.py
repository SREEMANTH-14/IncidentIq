import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import ConfigSettings, get_settings
from app.core.trace import get_trace_id

STANDARD_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonLogFormatter(logging.Formatter):
    """
    Formats application logs as structured JSON.

    Each log line includes:
    - timestamp
    - level
    - logger
    - message
    - trace_id
    - module
    - function
    - line
    - any extra fields passed through logger.info(..., extra={...})
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Converts a Python LogRecord into a JSON string.
        """

        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": get_trace_id(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        extra_fields = self._extract_extra_fields(record=record)

        for key, value in extra_fields.items():
            log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)

    def _extract_extra_fields(self, record: logging.LogRecord) -> dict[str, Any]:
        """
        Extracts custom logging fields passed through the extra parameter.

        Example:
        logger.info("Request completed", extra={"status_code": 200})
        """

        extra_fields: dict[str, Any] = {}

        for key, value in record.__dict__.items():
            if key in STANDARD_LOG_RECORD_FIELDS:
                continue

            if key.startswith("_"):
                continue

            extra_fields[key] = value

        return extra_fields


def configure_logging(settings: ConfigSettings | None = None) -> None:
    """
    Configures application logging.

    JSON logs are enabled when ENABLE_JSON_LOGS=true.
    Plain logs are used when ENABLE_JSON_LOGS=false.
    """

    if settings is None:
        active_settings = get_settings()
    else:
        active_settings = settings

    log_level = getattr(logging, active_settings.log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)

    if active_settings.enable_json_logs:
        formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger.info(
        "Logging configured",
        extra={
            "app_name": active_settings.app_name,
            "app_env": active_settings.app_env,
            "json_logs_enabled": active_settings.enable_json_logs,
            "log_level": active_settings.log_level,
        },
    )
