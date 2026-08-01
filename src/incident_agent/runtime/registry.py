"""Registered tool definitions for the isolated runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from incident_agent.genai.contracts import ToolRisk
from incident_agent.runtime.contracts import (
    RuntimeToolResult,
)


RUNTIME_VERSION = "isolated-tool-runtime-v1"


ToolHandler = Callable[
    [dict[str, str], bool],
    RuntimeToolResult,
]


@dataclass(frozen=True)
class RuntimeToolDefinition:
    """One registered runtime tool."""

    tool_name: str
    risk: ToolRisk
    required_arguments: tuple[str, ...]
    timeout_seconds: float
    maximum_attempts: int
    dry_run_required: bool
    handler: ToolHandler


def inspect_incident_telemetry(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return deterministic synthetic incident telemetry."""

    return RuntimeToolResult(
        tool_name="inspect_incident_telemetry",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "window": "last_15_minutes",
            "http_5xx_rate": 0.17,
            "token_validation_error_rate": 0.13,
            "latency_p95_ms": 2310,
            "source": "synthetic_tutorial_telemetry",
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="inspect-telemetry-v1",
    )


def inspect_service_health(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return deterministic synthetic service-health data."""

    return RuntimeToolResult(
        tool_name="inspect_service_health",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "health": "degraded",
            "healthy_instances": 7,
            "unhealthy_instances": 2,
            "source": "synthetic_tutorial_health",
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="inspect-health-v1",
    )


def inspect_deployment_history(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return deterministic synthetic deployment history."""

    return RuntimeToolResult(
        tool_name="inspect_deployment_history",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "latest_version": "4.3.2",
            "previous_version": "4.3.1",
            "latest_deployment_age_minutes": 12,
            "source": "synthetic_tutorial_deployments",
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="inspect-deployment-v1",
    )


def inspect_identity_configuration(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return non-secret synthetic identity configuration."""

    return RuntimeToolResult(
        tool_name="inspect_identity_configuration",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "issuer_configuration": "configured",
            "audience_configuration": "configured",
            "signing_key_status": "metadata_refresh_pending",
            "secrets_returned": False,
            "source": "synthetic_tutorial_identity",
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="inspect-identity-v1",
    )


def restart_service_dry_run(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return a restart plan without performing a restart."""

    return RuntimeToolResult(
        tool_name="restart_service",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "planned_action": "rolling_restart",
            "estimated_instance_count": 9,
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="restart-dry-run-v1",
    )


def rollback_deployment_dry_run(
    arguments: dict[str, str],
    dry_run: bool,
) -> RuntimeToolResult:
    """Return a rollback plan without performing a rollback."""

    return RuntimeToolResult(
        tool_name="rollback_deployment",
        data={
            "service": arguments["service"],
            "environment": arguments["environment"],
            "target_version": arguments["target_version"],
            "planned_action": "deployment_rollback",
            "dry_run": dry_run,
        },
        side_effects_performed=False,
        handler_version="rollback-dry-run-v1",
    )


RUNTIME_TOOLS: dict[str, RuntimeToolDefinition] = {
    "inspect_incident_telemetry": RuntimeToolDefinition(
        tool_name="inspect_incident_telemetry",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        timeout_seconds=2.0,
        maximum_attempts=2,
        dry_run_required=False,
        handler=inspect_incident_telemetry,
    ),
    "inspect_service_health": RuntimeToolDefinition(
        tool_name="inspect_service_health",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        timeout_seconds=2.0,
        maximum_attempts=2,
        dry_run_required=False,
        handler=inspect_service_health,
    ),
    "inspect_deployment_history": RuntimeToolDefinition(
        tool_name="inspect_deployment_history",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        timeout_seconds=2.0,
        maximum_attempts=2,
        dry_run_required=False,
        handler=inspect_deployment_history,
    ),
    "inspect_identity_configuration": RuntimeToolDefinition(
        tool_name="inspect_identity_configuration",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        timeout_seconds=2.0,
        maximum_attempts=1,
        dry_run_required=False,
        handler=inspect_identity_configuration,
    ),
    "restart_service": RuntimeToolDefinition(
        tool_name="restart_service",
        risk=ToolRisk.MUTATING,
        required_arguments=(
            "service",
            "environment",
        ),
        timeout_seconds=2.0,
        maximum_attempts=1,
        dry_run_required=True,
        handler=restart_service_dry_run,
    ),
    "rollback_deployment": RuntimeToolDefinition(
        tool_name="rollback_deployment",
        risk=ToolRisk.HIGH_IMPACT,
        required_arguments=(
            "service",
            "environment",
            "target_version",
        ),
        timeout_seconds=2.0,
        maximum_attempts=1,
        dry_run_required=True,
        handler=rollback_deployment_dry_run,
    ),
}
