import uuid
from contextvars import ContextVar, Token

trace_id_context: ContextVar[str | None] = ContextVar(
    "trace_id",
    default=None,
)


def create_trace_id() -> str:
    """
    Creates a new trace ID.

    UUID is used because it is unique and safe for request tracing.
    """

    trace_id = str(uuid.uuid4())
    return trace_id


def normalize_trace_id(trace_id: str | None) -> str:
    """
    Cleans and validates a trace ID.

    If the caller sends an empty or very short trace ID from Swagger,
    we generate a safe UUID instead.

    IncidentProcessResponse requires trace_id length >= 8.
    """

    if trace_id is None:
        return create_trace_id()

    cleaned_trace_id = trace_id.strip()

    if len(cleaned_trace_id) < 8:
        return create_trace_id()

    return cleaned_trace_id


def bind_trace_id(trace_id: str | None) -> tuple[str, Token[str | None]]:
    """
    Stores the active trace ID in context for the current request.

    Logging can read this context so every log line includes the same trace ID.
    """

    active_trace_id = normalize_trace_id(trace_id=trace_id)
    token = trace_id_context.set(active_trace_id)

    return active_trace_id, token


def reset_trace_id(token: Token[str | None]) -> None:
    """
    Resets the trace ID context after request completion.
    """

    trace_id_context.reset(token)


def get_trace_id() -> str:
    """
    Returns the current trace ID.

    If no trace ID exists, a new one is created and stored.
    """

    active_trace_id = trace_id_context.get()

    if active_trace_id is None:
        active_trace_id = create_trace_id()
        trace_id_context.set(active_trace_id)
        return active_trace_id

    if len(active_trace_id.strip()) < 8:
        active_trace_id = create_trace_id()
        trace_id_context.set(active_trace_id)
        return active_trace_id

    return active_trace_id
