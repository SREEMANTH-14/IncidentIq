import logging
from collections.abc import Callable
from typing import Any

from app.schemas.agent_messages import ToolExecutionResult, ToolExecutionStatus

logger = logging.getLogger("IncidentIQ.Tools.DevOpsTools")


ToolFunction = Callable[..., ToolExecutionResult]


def _clean_required_text(value: str, field_name: str) -> str:
    """
    Cleans and validates required text input for mocked DevOps tools.

    This protects tools from receiving empty service names, environments,
    tool names, or messages.
    """

    cleaned_value = value.strip()

    if not cleaned_value:
        raise ValueError(f"{field_name} cannot be empty.")

    return cleaned_value


def _build_success_result(
    tool_name: str,
    message: str,
    output: dict[str, str],
) -> ToolExecutionResult:
    """
    Builds a successful ToolExecutionResult contract.

    All mocked DevOps tools return this Pydantic contract so the
    Remediation Agent receives predictable structured output.
    """

    result = ToolExecutionResult(
        tool_name=tool_name,
        status=ToolExecutionStatus.SUCCESS,
        message=message,
        output=output,
    )

    return result


def _build_failed_result(
    tool_name: str,
    message: str,
    output: dict[str, str] | None = None,
) -> ToolExecutionResult:
    """
    Builds a failed ToolExecutionResult contract.

    This is used when tool execution fails due to validation or unexpected
    runtime errors.
    """

    if output is None:
        result_output: dict[str, str] = {}
    else:
        result_output = output

    result = ToolExecutionResult(
        tool_name=tool_name,
        status=ToolExecutionStatus.FAILED,
        message=message,
        output=result_output,
    )

    return result


def _build_skipped_result(
    tool_name: str,
    message: str,
    output: dict[str, str] | None = None,
) -> ToolExecutionResult:
    """
    Builds a skipped ToolExecutionResult contract.

    This is useful when the Remediation Agent decides that a requested action
    should not be automated.
    """

    if output is None:
        result_output: dict[str, str] = {}
    else:
        result_output = output

    result = ToolExecutionResult(
        tool_name=tool_name,
        status=ToolExecutionStatus.SKIPPED,
        message=message,
        output=result_output,
    )

    return result


def check_service_health(service: str, environment: str) -> ToolExecutionResult:
    """
    Mocked DevOps tool: check_service_health.

    Purpose:
    Checks the mocked health status of the affected service.

    This does not call a real monitoring system. It returns deterministic
    mock output for a stable assessment demo.
    """

    tool_name = "check_service_health"
    cleaned_service = _clean_required_text(service, "service")
    cleaned_environment = _clean_required_text(environment, "environment")

    logger.info(
        "Mock tool invoked: %s service=%s environment=%s",
        tool_name,
        cleaned_service,
        cleaned_environment,
    )

    output = {
        "service": cleaned_service,
        "environment": cleaned_environment,
        "health_status": "degraded",
        "latency_status": "above_threshold",
        "error_rate_status": "elevated",
        "mocked": "true",
    }

    message = (
        f"Mock health check completed for {cleaned_service} "
        f"in {cleaned_environment}. Service is degraded."
    )

    result = _build_success_result(
        tool_name=tool_name,
        message=message,
        output=output,
    )

    return result


def restart_service(service: str, environment: str) -> ToolExecutionResult:
    """
    Mocked DevOps tool: restart_service.

    Purpose:
    Pretends to restart the affected service.

    """

    tool_name = "restart_service"
    cleaned_service = _clean_required_text(service, "service")
    cleaned_environment = _clean_required_text(environment, "environment")

    logger.info(
        "Mock tool invoked: %s service=%s environment=%s",
        tool_name,
        cleaned_service,
        cleaned_environment,
    )

    output = {
        "service": cleaned_service,
        "environment": cleaned_environment,
        "restart_status": "completed",
        "restart_strategy": "rolling_restart",
        "mocked": "true",
    }

    message = (
        f"Mock rolling restart completed for {cleaned_service} "
        f"in {cleaned_environment}."
    )

    result = _build_success_result(
        tool_name=tool_name,
        message=message,
        output=output,
    )

    return result


def scale_deployment(
    service: str,
    environment: str,
    replicas: int = 3,
) -> ToolExecutionResult:
    """
    Mocked DevOps tool: scale_deployment.

    Purpose:
    Pretends to scale a Kubernetes/OpenShift deployment to a target
    replica count.
    """

    tool_name = "scale_deployment"
    cleaned_service = _clean_required_text(service, "service")
    cleaned_environment = _clean_required_text(environment, "environment")

    try:
        replica_count = int(replicas)
    except (TypeError, ValueError) as error:
        raise ValueError("replicas must be a valid integer.") from error

    if replica_count < 1:
        raise ValueError("replicas must be greater than or equal to 1.")

    if replica_count > 20:
        raise ValueError("replicas cannot be greater than 20 in mock mode.")

    logger.info(
        "Mock tool invoked: %s service=%s environment=%s replicas=%s",
        tool_name,
        cleaned_service,
        cleaned_environment,
        replica_count,
    )

    output = {
        "service": cleaned_service,
        "environment": cleaned_environment,
        "replicas": str(replica_count),
        "scale_status": "completed",
        "mocked": "true",
    }

    message = (
        f"Mock scaled {cleaned_service} in {cleaned_environment} "
        f"to {replica_count} replicas."
    )

    result = _build_success_result(
        tool_name=tool_name,
        message=message,
        output=output,
    )

    return result


def rollback_deployment(
    service: str,
    environment: str,
    target_version: str = "previous-stable",
) -> ToolExecutionResult:
    """
    Mocked DevOps tool: rollback_deployment.

    Purpose:
    Pretends to roll back a deployment to a previous stable version.

    In real production systems, this is often risky. Later, the Remediation
    Agent can decide whether to execute or mark this for human approval.
    """

    tool_name = "rollback_deployment"
    cleaned_service = _clean_required_text(service, "service")
    cleaned_environment = _clean_required_text(environment, "environment")
    cleaned_target_version = _clean_required_text(target_version, "target_version")

    logger.info(
        "Mock tool invoked: %s service=%s environment=%s target_version=%s",
        tool_name,
        cleaned_service,
        cleaned_environment,
        cleaned_target_version,
    )

    output = {
        "service": cleaned_service,
        "environment": cleaned_environment,
        "target_version": cleaned_target_version,
        "rollback_status": "completed",
        "mocked": "true",
    }

    message = (
        f"Mock rollback completed for {cleaned_service} in "
        f"{cleaned_environment} to version {cleaned_target_version}."
    )

    result = _build_success_result(
        tool_name=tool_name,
        message=message,
        output=output,
    )

    return result


def notify_oncall(
    service: str,
    environment: str,
    severity: str,
    message: str,
) -> ToolExecutionResult:
    """
    Mocked DevOps tool: notify_oncall.

    Purpose:
    Pretends to notify the on-call engineer through Slack, PagerDuty,
    email, or another incident management tool.
    """

    tool_name = "notify_oncall"
    cleaned_service = _clean_required_text(service, "service")
    cleaned_environment = _clean_required_text(environment, "environment")
    cleaned_severity = _clean_required_text(severity, "severity")
    cleaned_message = _clean_required_text(message, "message")

    logger.info(
        "Mock tool invoked: %s service=%s environment=%s severity=%s",
        tool_name,
        cleaned_service,
        cleaned_environment,
        cleaned_severity,
    )

    output = {
        "service": cleaned_service,
        "environment": cleaned_environment,
        "severity": cleaned_severity,
        "notification_channel": "mock_pagerduty_and_slack",
        "notification_status": "sent",
        "mocked": "true",
    }

    result_message = (
        f"Mock on-call notification sent for {cleaned_service} "
        f"in {cleaned_environment} with severity {cleaned_severity}. "
        f"Notification message: {cleaned_message}"
    )

    result = _build_success_result(
        tool_name=tool_name,
        message=result_message,
        output=output,
    )

    return result


def get_mocked_devops_tools() -> dict[str, ToolFunction]:
    """
    Returns the mocked DevOps tool registry.

    The Remediation Agent will use this registry to invoke tools by name.
    """

    tools: dict[str, ToolFunction] = {
        "check_service_health": check_service_health,
        "restart_service": restart_service,
        "scale_deployment": scale_deployment,
        "rollback_deployment": rollback_deployment,
        "notify_oncall": notify_oncall,
    }

    return tools


def get_mocked_devops_tool_names() -> list[str]:
    """
    Returns the available mocked DevOps tool names.

    This is useful for logging, debugging, tests, and documentation.
    """

    tools = get_mocked_devops_tools()
    tool_names = list(tools.keys())

    return tool_names


def execute_mocked_devops_tool(
    tool_name: str,
    tool_arguments: dict[str, Any],
) -> ToolExecutionResult:
    """
    Executes a mocked DevOps tool by name.

    This function gives the Remediation Agent one safe entry point for
    invoking all mocked tools.

    Example:
    execute_mocked_devops_tool(
        tool_name="scale_deployment",
        tool_arguments={
            "service": "checkout-service",
            "environment": "production",
            "replicas": 3,
        },
    )
    """

    cleaned_tool_name = _clean_required_text(tool_name, "tool_name")
    tool_registry = get_mocked_devops_tools()

    tool_function = tool_registry.get(cleaned_tool_name)

    if tool_function is None:
        logger.warning("Unknown mocked DevOps tool requested: %s", cleaned_tool_name)

        result = _build_failed_result(
            tool_name=cleaned_tool_name,
            message=f"Unknown mocked DevOps tool: {cleaned_tool_name}.",
            output={
                "available_tools": ", ".join(get_mocked_devops_tool_names()),
                "mocked": "true",
            },
        )

        return result

    try:
        result = tool_function(**tool_arguments)
    except ValueError as error:
        logger.warning(
            "Mocked DevOps tool validation failed: tool=%s error=%s",
            cleaned_tool_name,
            str(error),
        )

        result = _build_failed_result(
            tool_name=cleaned_tool_name,
            message=str(error),
            output={"mocked": "true"},
        )

        return result
    except TypeError as error:
        logger.warning(
            "Mocked DevOps tool argument mismatch: tool=%s error=%s",
            cleaned_tool_name,
            str(error),
        )

        result = _build_failed_result(
            tool_name=cleaned_tool_name,
            message=f"Invalid arguments for tool {cleaned_tool_name}: {str(error)}",
            output={"mocked": "true"},
        )

        return result
    except Exception as error:
        logger.exception(
            "Unexpected mocked DevOps tool failure: tool=%s",
            cleaned_tool_name,
        )

        result = _build_failed_result(
            tool_name=cleaned_tool_name,
            message=f"Unexpected tool failure: {str(error)}",
            output={"mocked": "true"},
        )

        return result

    return result


def skip_mocked_devops_tool(
    tool_name: str,
    reason: str,
) -> ToolExecutionResult:
    """
    Returns a skipped tool result when the Remediation Agent decides that
    a tool should not be executed automatically.

    This is useful for risky actions that need human approval.
    """

    cleaned_tool_name = _clean_required_text(tool_name, "tool_name")
    cleaned_reason = _clean_required_text(reason, "reason")

    logger.info(
        "Mock tool skipped: tool=%s reason=%s",
        cleaned_tool_name,
        cleaned_reason,
    )

    result = _build_skipped_result(
        tool_name=cleaned_tool_name,
        message=cleaned_reason,
        output={"mocked": "true"},
    )

    return result
