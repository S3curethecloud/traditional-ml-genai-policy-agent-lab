"""Controlled simulated deployment runtime."""

from __future__ import annotations

from incident_agent.deployment.authorization import (
    authorize_deployment,
)
from incident_agent.deployment.contracts import (
    DeploymentApproval,
    DeploymentAuditEvent,
    DeploymentDecision,
    DeploymentEnvironment,
    DeploymentIdentity,
    DeploymentManifest,
    DeploymentOutcome,
    DeploymentStatus,
    EnvironmentConfiguration,
    RuntimeState,
)
from incident_agent.deployment.drift import (
    detect_runtime_drift,
)
from incident_agent.deployment.loading import (
    configuration_sha256,
)


DEPLOYMENT_RUNTIME_VERSION = "deployment-runtime-v1"


class SimulatedDeploymentRuntime:
    """In-memory deployment runtime with no external effects."""

    def __init__(self) -> None:
        self._states: dict[
            DeploymentEnvironment,
            RuntimeState,
        ] = {}

    def deploy(
        self,
        root,
        identity: DeploymentIdentity,
        manifest: DeploymentManifest,
        configuration: EnvironmentConfiguration,
        approval: DeploymentApproval | None = None,
        health_passed: bool = True,
        readiness_passed: bool = True,
    ) -> DeploymentOutcome:
        """Authorize and simulate a deployment."""

        events: list[DeploymentAuditEvent] = []

        def record(
            event_type: str,
            detail: str,
            evidence: tuple[str, ...] = (),
        ) -> None:
            events.append(
                DeploymentAuditEvent(
                    sequence=len(events) + 1,
                    event_type=event_type,
                    release_id=manifest.release_id,
                    environment=(
                        configuration.environment.value
                    ),
                    actor_id=identity.subject_id,
                    detail=detail,
                    evidence_references=evidence,
                )
            )

        record(
            "deployment_requested",
            "Deployment request received.",
            (
                manifest.image_digest,
                manifest.source_revision,
            ),
        )

        authorization = authorize_deployment(
            root=root,
            identity=identity,
            manifest=manifest,
            configuration=configuration,
            approval=approval,
        )

        record(
            "deployment_authorized",
            (
                "Deployment authorization evaluated: "
                f"{authorization.decision.value}."
            ),
            tuple(
                check.check_name
                for check in authorization.checks
                if check.passed
            ),
        )

        if authorization.decision is not DeploymentDecision.ALLOW:
            record(
                "deployment_blocked",
                "Deployment did not pass preflight.",
                authorization.reasons,
            )

            return DeploymentOutcome(
                release_id=manifest.release_id,
                environment=configuration.environment,
                status=DeploymentStatus.BLOCKED,
                authorization_decision=(
                    authorization.decision
                ),
                runtime_state=None,
                drift_report=None,
                audit_events=tuple(events),
                rollback_performed=False,
                production_side_effects_performed=False,
                authority_boundary=(
                    "The simulated runtime may apply an "
                    "authorized deployment state. It cannot "
                    "bypass deployment authorization or "
                    "perform real infrastructure changes."
                ),
            )

        record(
            "preflight_passed",
            "All deployment preflight checks passed.",
        )

        runtime_state = RuntimeState(
            environment=configuration.environment,
            release_id=manifest.release_id,
            image_digest=manifest.image_digest,
            source_revision=manifest.source_revision,
            replica_count=configuration.replica_count,
            configuration_sha256=(
                configuration_sha256(configuration)
            ),
            deployed_by=identity.subject_id,
            healthy=health_passed,
            ready=readiness_passed,
        )

        self._states[
            configuration.environment
        ] = runtime_state

        record(
            "deployment_applied",
            "Desired runtime state applied in memory.",
            (runtime_state.configuration_sha256,),
        )

        if not health_passed or not readiness_passed:
            record(
                "deployment_health_failed",
                "Health or readiness validation failed.",
            )

            self._states.pop(
                configuration.environment,
                None,
            )

            record(
                "deployment_rolled_back",
                "Simulated runtime state removed.",
                (manifest.rollback_plan_path,),
            )

            return DeploymentOutcome(
                release_id=manifest.release_id,
                environment=configuration.environment,
                status=DeploymentStatus.ROLLED_BACK,
                authorization_decision=(
                    authorization.decision
                ),
                runtime_state=None,
                drift_report=None,
                audit_events=tuple(events),
                rollback_performed=True,
                production_side_effects_performed=False,
                authority_boundary=(
                    "The simulated runtime may apply and "
                    "remove in-memory state only."
                ),
            )

        drift = detect_runtime_drift(
            manifest=manifest,
            configuration=configuration,
            runtime_state=runtime_state,
        )

        record(
            "deployment_verified",
            "Health, readiness, and drift checks passed.",
            (drift.status.value,),
        )

        return DeploymentOutcome(
            release_id=manifest.release_id,
            environment=configuration.environment,
            status=DeploymentStatus.HEALTHY,
            authorization_decision=(
                authorization.decision
            ),
            runtime_state=runtime_state,
            drift_report=drift,
            audit_events=tuple(events),
            rollback_performed=False,
            production_side_effects_performed=False,
            authority_boundary=(
                "The simulated runtime may apply an "
                "authorized in-memory state. It cannot "
                "perform real infrastructure changes."
            ),
        )

    def current_state(
        self,
        environment: DeploymentEnvironment,
    ) -> RuntimeState | None:
        """Return the current simulated runtime state."""

        return self._states.get(environment)

    def rollback(
        self,
        environment: DeploymentEnvironment,
    ) -> bool:
        """Remove current simulated state."""

        return self._states.pop(
            environment,
            None,
        ) is not None
