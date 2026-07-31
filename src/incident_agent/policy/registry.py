"""Versioned deterministic tool-policy registry."""

from __future__ import annotations

from incident_agent.genai.contracts import ToolRisk
from incident_agent.policy.contracts import ToolPolicy


POLICY_VERSION = "deterministic-policy-v1"


TOOL_POLICIES: dict[str, ToolPolicy] = {
    "inspect_incident_telemetry": ToolPolicy(
        tool_name="inspect_incident_telemetry",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        allowed_roles=(
            "incident_responder",
            "production_operator",
            "incident_commander",
        ),
        allowed_environments=(
            "staging",
            "production",
        ),
        minimum_citations=1,
        requires_human_approval=False,
        required_approval_roles=(),
    ),
    "inspect_service_health": ToolPolicy(
        tool_name="inspect_service_health",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        allowed_roles=(
            "support_engineer",
            "incident_responder",
            "production_operator",
            "incident_commander",
        ),
        allowed_environments=(
            "development",
            "staging",
            "production",
        ),
        minimum_citations=1,
        requires_human_approval=False,
        required_approval_roles=(),
    ),
    "inspect_deployment_history": ToolPolicy(
        tool_name="inspect_deployment_history",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        allowed_roles=(
            "incident_responder",
            "production_operator",
            "incident_commander",
        ),
        allowed_environments=(
            "staging",
            "production",
        ),
        minimum_citations=1,
        requires_human_approval=False,
        required_approval_roles=(),
    ),
    "inspect_identity_configuration": ToolPolicy(
        tool_name="inspect_identity_configuration",
        risk=ToolRisk.READ_ONLY,
        required_arguments=(
            "service",
            "environment",
        ),
        allowed_roles=(
            "production_operator",
            "incident_commander",
            "security_reviewer",
        ),
        allowed_environments=(
            "staging",
            "production",
        ),
        minimum_citations=2,
        requires_human_approval=False,
        required_approval_roles=(),
    ),
    "restart_service": ToolPolicy(
        tool_name="restart_service",
        risk=ToolRisk.MUTATING,
        required_arguments=(
            "service",
            "environment",
        ),
        allowed_roles=(
            "production_operator",
            "incident_commander",
        ),
        allowed_environments=(
            "staging",
            "production",
        ),
        minimum_citations=2,
        requires_human_approval=True,
        required_approval_roles=(
            "incident_commander",
        ),
    ),
    "rollback_deployment": ToolPolicy(
        tool_name="rollback_deployment",
        risk=ToolRisk.HIGH_IMPACT,
        required_arguments=(
            "service",
            "environment",
            "target_version",
        ),
        allowed_roles=(
            "production_operator",
            "incident_commander",
        ),
        allowed_environments=(
            "staging",
            "production",
        ),
        minimum_citations=3,
        requires_human_approval=True,
        required_approval_roles=(
            "incident_commander",
            "production_operator",
        ),
    ),
}
