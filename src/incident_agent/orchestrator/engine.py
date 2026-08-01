"""Governed end-to-end agent orchestration."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from incident_agent.evaluation.ambiguity import (
    evaluate_ambiguity_pack,
    load_ambiguity_pack,
)
from incident_agent.genai.contracts import (
    SynthesisDisposition,
)
from incident_agent.genai.provider import (
    DeterministicTutorialProvider,
    SynthesisProvider,
)
from incident_agent.genai.service import (
    build_synthesis_request,
    synthesize_evidence,
)
from incident_agent.ml.inference import (
    IncidentClassifier,
)
from incident_agent.orchestrator.checkpoints import (
    InMemoryCheckpointStore,
    create_checkpoint,
)
from incident_agent.orchestrator.contracts import (
    StopReason,
    WorkflowEvent,
    WorkflowOutcome,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowStep,
)
from incident_agent.orchestrator.state import (
    WorkflowState,
)
from incident_agent.policy.contracts import (
    PolicyDecision,
    PolicyIdentity,
)
from incident_agent.policy.service import (
    build_policy_context,
    evaluate_synthesis_policy,
)
from incident_agent.retrieval.contracts import (
    RetrievalIdentity,
    RetrievalQuery,
    RetrievalScope,
)
from incident_agent.retrieval.engine import (
    retrieve_documents,
)
from incident_agent.retrieval.loader import (
    load_knowledge_corpus,
)
from incident_agent.retrieval.planning import (
    build_retrieval_query_text,
)
from incident_agent.runtime.contracts import (
    ExecutionStatus,
)
from incident_agent.runtime.engine import (
    IsolatedToolRuntime,
)
from incident_agent.runtime.service import (
    build_runtime_request,
    execute_authorized_request,
)


ORCHESTRATOR_VERSION = "governed-orchestrator-v1"


class GovernedAgentOrchestrator:
    """Coordinate components without absorbing their authority."""

    def __init__(
        self,
        knowledge_directory: Path,
        ambiguity_pack_path: Path,
        model_directory: Path,
        checkpoint_store: (
            InMemoryCheckpointStore | None
        ) = None,
        runtime: IsolatedToolRuntime | None = None,
        synthesis_provider: (
            SynthesisProvider | None
        ) = None,
    ) -> None:
        self._documents = load_knowledge_corpus(
            knowledge_directory
        )
        self._cases = load_ambiguity_pack(
            ambiguity_pack_path
        )
        self._classifier = IncidentClassifier.load(
            model_directory
        )
        self._checkpoint_store = (
            checkpoint_store
            or InMemoryCheckpointStore()
        )
        self._runtime = (
            runtime
            or IsolatedToolRuntime()
        )
        self._provider = (
            synthesis_provider
            or DeterministicTutorialProvider()
        )

    def run(
        self,
        request: WorkflowRequest,
        now_epoch_seconds: float,
    ) -> WorkflowOutcome:
        """Run one governed end-to-end workflow."""

        state = WorkflowState(request=request)

        self._record_event(
            state=state,
            step=WorkflowStep.RECEIVED,
            event_type="workflow_received",
            detail=(
                "Typed workflow request accepted by "
                "the orchestrator."
            ),
            evidence_references=(),
        )

        self._checkpoint(
            state=state,
            step=WorkflowStep.RECEIVED,
            payload={
                "case_id": request.case_id,
                "tenant_id":
                    request.request_tenant_id,
                "service": request.service,
                "environment": request.environment,
            },
            evidence_references=(),
        )

        try:
            self._evaluate_ambiguity(state)
            self._perform_retrieval(state)
            self._perform_synthesis(state)

            if (
                state.synthesis_response is not None
                and state.synthesis_response.disposition
                is SynthesisDisposition.ABSTAIN
            ):
                return self._stop(
                    state=state,
                    status=WorkflowStatus.DENIED,
                    final_step=WorkflowStep.DENIED,
                    stop_reason=(
                        StopReason
                        .SYNTHESIS_ABSTAINED
                    ),
                    detail=(
                        "Workflow stopped because synthesis "
                        "abstained."
                    ),
                )

            self._evaluate_policy(state)

            assert state.policy_evaluation is not None

            if (
                state.policy_evaluation.decision
                is PolicyDecision.DENY
            ):
                return self._stop(
                    state=state,
                    status=WorkflowStatus.DENIED,
                    final_step=WorkflowStep.DENIED,
                    stop_reason=StopReason.POLICY_DENIED,
                    detail=(
                        "Workflow stopped by deterministic "
                        "policy DENY."
                    ),
                )

            if (
                state.policy_evaluation.decision
                is PolicyDecision.ESCALATE
            ):
                return self._stop(
                    state=state,
                    status=WorkflowStatus.ESCALATED,
                    final_step=(
                        WorkflowStep
                        .HUMAN_ESCALATION_REQUIRED
                    ),
                    stop_reason=(
                        StopReason.POLICY_ESCALATED
                    ),
                    detail=(
                        "Workflow requires human escalation."
                    ),
                )

            self._execute_runtime(
                state=state,
                now_epoch_seconds=now_epoch_seconds,
            )

            assert state.runtime_record is not None

            if (
                state.runtime_record.status
                is ExecutionStatus.REJECTED
            ):
                return self._stop(
                    state=state,
                    status=WorkflowStatus.FAILED,
                    final_step=WorkflowStep.FAILED,
                    stop_reason=(
                        StopReason.RUNTIME_REJECTED
                    ),
                    detail=(
                        "Runtime rejected the authorized "
                        "request."
                    ),
                )

            if state.runtime_record.status in {
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMED_OUT,
            }:
                return self._stop(
                    state=state,
                    status=WorkflowStatus.FAILED,
                    final_step=WorkflowStep.FAILED,
                    stop_reason=(
                        StopReason.RUNTIME_FAILED
                    ),
                    detail=(
                        "Runtime execution failed or timed out."
                    ),
                )

            state.status = WorkflowStatus.COMPLETED
            state.current_step = WorkflowStep.COMPLETED

            self._record_event(
                state=state,
                step=WorkflowStep.COMPLETED,
                event_type="workflow_completed",
                detail=(
                    "Governed workflow completed."
                ),
                evidence_references=self._runtime_evidence(
                    state
                ),
            )

            self._checkpoint(
                state=state,
                step=WorkflowStep.COMPLETED,
                payload=self._final_state_payload(
                    state
                ),
                evidence_references=self._runtime_evidence(
                    state
                ),
            )

            return self._build_outcome(
                state=state,
                stop_reason=StopReason.NONE,
            )

        except Exception as exc:
            return self._stop(
                state=state,
                status=WorkflowStatus.FAILED,
                final_step=WorkflowStep.FAILED,
                stop_reason=StopReason.STEP_FAILURE,
                detail=(
                    "Workflow step failed safely: "
                    f"{type(exc).__name__}"
                ),
            )

    def _evaluate_ambiguity(
        self,
        state: WorkflowState,
    ) -> None:
        results = evaluate_ambiguity_pack(
            self._cases,
            self._classifier,
        )

        state.ambiguity_result = next(
            result
            for result in results
            if result.case_id == state.request.case_id
        )

        state.current_step = (
            WorkflowStep.AMBIGUITY_EVALUATED
        )

        evidence = (
            state.ambiguity_result.case_id,
            state.ambiguity_result
            .deterministic_category,
            state.ambiguity_result.ml_category,
        )

        self._record_event(
            state=state,
            step=state.current_step,
            event_type="ambiguity_evaluated",
            detail=(
                "Deterministic and ML evidence evaluated."
            ),
            evidence_references=evidence,
        )

        self._checkpoint(
            state=state,
            step=state.current_step,
            payload=asdict(
                state.ambiguity_result
            ),
            evidence_references=evidence,
        )

    def _perform_retrieval(
        self,
        state: WorkflowState,
    ) -> None:
        assert state.ambiguity_result is not None

        query_text = build_retrieval_query_text(
            state.ambiguity_result
        )

        state.retrieval_response = retrieve_documents(
            documents=self._documents,
            query=RetrievalQuery(
                query_text=query_text,
                identity=RetrievalIdentity(
                    user_id=(
                        state.request.identity.user_id
                    ),
                    tenant_id=(
                        state.request.identity.tenant_id
                    ),
                    roles=state.request.identity.roles,
                ),
                scope=RetrievalScope(
                    service=state.request.service,
                    environment=(
                        state.request.environment
                    ),
                ),
                maximum_results=(
                    state.request
                    .maximum_retrieval_results
                ),
            ),
        )

        state.current_step = (
            WorkflowStep.RETRIEVAL_COMPLETED
        )

        citations = tuple(
            result.citation
            for result
            in state.retrieval_response.results
        )

        self._record_event(
            state=state,
            step=state.current_step,
            event_type="retrieval_completed",
            detail=(
                "Permission-aware retrieval completed "
                "before GenAI synthesis."
            ),
            evidence_references=citations,
        )

        self._checkpoint(
            state=state,
            step=state.current_step,
            payload=asdict(
                state.retrieval_response
            ),
            evidence_references=citations,
        )

    def _perform_synthesis(
        self,
        state: WorkflowState,
    ) -> None:
        assert state.ambiguity_result is not None
        assert state.retrieval_response is not None

        synthesis_request = build_synthesis_request(
            ambiguity_result=(
                state.ambiguity_result
            ),
            retrieval_response=(
                state.retrieval_response
            ),
        )

        state.synthesis_response = (
            synthesize_evidence(
                request=synthesis_request,
                provider=self._provider,
            )
        )

        state.current_step = (
            WorkflowStep.SYNTHESIS_COMPLETED
        )

        citations = (
            state.synthesis_response.citations
        )

        self._record_event(
            state=state,
            step=state.current_step,
            event_type="synthesis_completed",
            detail=(
                "GenAI produced structured evidence "
                "synthesis and a typed recommendation."
            ),
            evidence_references=citations,
        )

        self._checkpoint(
            state=state,
            step=state.current_step,
            payload=state.synthesis_response.to_dict(),
            evidence_references=citations,
        )

    def _evaluate_policy(
        self,
        state: WorkflowState,
    ) -> None:
        assert state.ambiguity_result is not None
        assert state.retrieval_response is not None
        assert state.synthesis_response is not None

        policy_identity = PolicyIdentity(
            user_id=state.request.identity.user_id,
            tenant_id=(
                state.request.identity.tenant_id
            ),
            roles=state.request.identity.roles,
        )

        state.policy_context = build_policy_context(
            identity=policy_identity,
            request_tenant_id=(
                state.request.request_tenant_id
            ),
            service=state.request.service,
            environment=state.request.environment,
            ambiguity_result=(
                state.ambiguity_result
            ),
            retrieval_response=(
                state.retrieval_response
            ),
        )

        state.policy_evaluation = (
            evaluate_synthesis_policy(
                synthesis=(
                    state.synthesis_response
                ),
                context=state.policy_context,
            )
        )

        state.current_step = (
            WorkflowStep.POLICY_EVALUATED
        )

        reasons = tuple(
            reason.rule_id
            for reason
            in state.policy_evaluation.reasons
        )

        self._record_event(
            state=state,
            step=state.current_step,
            event_type="policy_evaluated",
            detail=(
                "Deterministic policy returned "
                f"{state.policy_evaluation.decision.value}."
            ),
            evidence_references=(
                state.policy_evaluation
                .request_fingerprint,
                *reasons,
            ),
        )

        self._checkpoint(
            state=state,
            step=state.current_step,
            payload=state.policy_evaluation.to_dict(),
            evidence_references=(
                state.policy_evaluation
                .request_fingerprint,
                *reasons,
            ),
        )

    def _execute_runtime(
        self,
        state: WorkflowState,
        now_epoch_seconds: float,
    ) -> None:
        assert state.synthesis_response is not None
        assert state.policy_context is not None
        assert state.policy_evaluation is not None
        assert (
            state.policy_evaluation.decision
            is PolicyDecision.ALLOW
        )

        policy_identity = PolicyIdentity(
            user_id=state.request.identity.user_id,
            tenant_id=(
                state.request.identity.tenant_id
            ),
            roles=state.request.identity.roles,
        )

        runtime_request = build_runtime_request(
            synthesis=state.synthesis_response,
            policy_evaluation=(
                state.policy_evaluation
            ),
            policy_identity=policy_identity,
            service=state.request.service,
            environment=state.request.environment,
            idempotency_key=(
                state.request.idempotency_key
            ),
            now_epoch_seconds=(
                state.request
                .created_at_epoch_seconds
            ),
            lifetime_seconds=60.0,
            dry_run=state.request.dry_run,
        )

        state.runtime_record = (
            execute_authorized_request(
                runtime=self._runtime,
                request=runtime_request,
                synthesis=(
                    state.synthesis_response
                ),
                policy_evaluation=(
                    state.policy_evaluation
                ),
                policy_context=(
                    state.policy_context
                ),
                now_epoch_seconds=(
                    now_epoch_seconds
                ),
            )
        )

        state.current_step = (
            WorkflowStep.RUNTIME_COMPLETED
        )

        evidence = self._runtime_evidence(state)

        self._record_event(
            state=state,
            step=state.current_step,
            event_type="runtime_completed",
            detail=(
                "Isolated runtime returned "
                f"{state.runtime_record.status.value}."
            ),
            evidence_references=evidence,
        )

        self._checkpoint(
            state=state,
            step=state.current_step,
            payload=state.runtime_record.to_dict(),
            evidence_references=evidence,
        )

    def _stop(
        self,
        state: WorkflowState,
        status: WorkflowStatus,
        final_step: WorkflowStep,
        stop_reason: StopReason,
        detail: str,
    ) -> WorkflowOutcome:
        state.status = status
        state.current_step = final_step

        self._record_event(
            state=state,
            step=final_step,
            event_type="workflow_stopped",
            detail=detail,
            evidence_references=(
                self._current_evidence(state)
            ),
        )

        self._checkpoint(
            state=state,
            step=final_step,
            payload=self._final_state_payload(
                state
            ),
            evidence_references=(
                self._current_evidence(state)
            ),
        )

        return self._build_outcome(
            state=state,
            stop_reason=stop_reason,
        )

    def _record_event(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        event_type: str,
        detail: str,
        evidence_references: tuple[str, ...],
    ) -> None:
        state.sequence += 1

        state.events.append(
            WorkflowEvent(
                sequence=state.sequence,
                step=step,
                event_type=event_type,
                trace_id=state.request.trace_id,
                workflow_id=(
                    state.request.workflow_id
                ),
                detail=detail,
                evidence_references=(
                    evidence_references
                ),
            )
        )

    def _checkpoint(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        payload: dict,
        evidence_references: tuple[str, ...],
    ) -> None:
        checkpoint = create_checkpoint(
            workflow_id=(
                state.request.workflow_id
            ),
            trace_id=state.request.trace_id,
            step=step,
            sequence=state.sequence,
            state_payload=payload,
            evidence_references=(
                evidence_references
            ),
        )

        self._checkpoint_store.append(
            checkpoint
        )

    def _current_evidence(
        self,
        state: WorkflowState,
    ) -> tuple[str, ...]:
        if state.policy_evaluation is not None:
            return (
                state.policy_evaluation
                .request_fingerprint,
                *(
                    reason.rule_id
                    for reason
                    in state.policy_evaluation.reasons
                ),
            )

        if state.synthesis_response is not None:
            return state.synthesis_response.citations

        if state.retrieval_response is not None:
            return tuple(
                result.citation
                for result
                in state.retrieval_response.results
            )

        if state.ambiguity_result is not None:
            return (
                state.ambiguity_result.case_id,
            )

        return ()

    def _runtime_evidence(
        self,
        state: WorkflowState,
    ) -> tuple[str, ...]:
        if state.runtime_record is None:
            return ()

        return (
            state.runtime_record
            .policy_fingerprint,
            state.runtime_record.status.value,
            *(
                event.event_type
                for event
                in state.runtime_record.audit_events
            ),
        )

    def _final_state_payload(
        self,
        state: WorkflowState,
    ) -> dict:
        return {
            "status": state.status.value,
            "current_step":
                state.current_step.value,
            "policy_decision": (
                state.policy_evaluation
                .decision.value
                if state.policy_evaluation
                else None
            ),
            "runtime_status": (
                state.runtime_record.status.value
                if state.runtime_record
                else None
            ),
        }

    def _build_outcome(
        self,
        state: WorkflowState,
        stop_reason: StopReason,
    ) -> WorkflowOutcome:
        recommendation = (
            state.synthesis_response
            .tool_recommendation
            if state.synthesis_response
            else None
        )

        return WorkflowOutcome(
            workflow_id=state.request.workflow_id,
            trace_id=state.request.trace_id,
            case_id=state.request.case_id,
            status=state.status,
            final_step=state.current_step,
            stop_reason=stop_reason,
            policy_decision=(
                state.policy_evaluation
                .decision.value
                if state.policy_evaluation
                else None
            ),
            recommended_tool=(
                recommendation.tool_name
                if recommendation
                else None
            ),
            runtime_status=(
                state.runtime_record.status.value
                if state.runtime_record
                else None
            ),
            checkpoints=(
                self._checkpoint_store
                .list_for_workflow(
                    state.request.workflow_id
                )
            ),
            events=tuple(state.events),
            authority_boundary=(
                "The orchestrator sequences governed "
                "components. It cannot bypass retrieval, "
                "policy, approval, or runtime controls."
            ),
            orchestrator_version=(
                ORCHESTRATOR_VERSION
            ),
        )
