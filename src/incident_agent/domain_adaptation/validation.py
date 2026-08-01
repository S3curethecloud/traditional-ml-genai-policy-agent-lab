"""Deterministic validation of domain adaptation packs."""

from __future__ import annotations

from incident_agent.domain_adaptation.contracts import (
    DomainPack,
    PackFinding,
    PackValidationResult,
    PackValidationStatus,
)


def _unique(values: tuple[str, ...]) -> bool:
    return len(values) == len(set(values))


def validate_domain_pack(
    pack: DomainPack,
    policy: dict,
) -> PackValidationResult:
    findings: list[PackFinding] = []

    def record(
        rule_id: str,
        passed: bool,
        detail: str,
    ) -> None:
        findings.append(
            PackFinding(
                rule_id=rule_id,
                passed=passed,
                detail=detail,
            )
        )

    record(
        "PLATFORM-CONTRACT",
        pack.platform_contract_version
        == policy["platform_contract_version"],
        "Domain pack must target the current platform contract.",
    )

    allowed_capabilities = set(
        policy["allowed_capabilities"]
    )
    actual_capabilities = set(
        pack.supported_capabilities
    )

    record(
        "CAPABILITY-ALLOWLIST",
        actual_capabilities <= allowed_capabilities,
        "Domain capabilities must remain inside the platform allowlist.",
    )

    record(
        "CAPABILITY-UNIQUENESS",
        _unique(pack.supported_capabilities),
        "Domain capabilities must be unique.",
    )

    category_ids = tuple(
        item.category_id
        for item in pack.incident_categories
    )

    record(
        "MINIMUM-TAXONOMY",
        len(category_ids)
        >= policy[
            "minimum_required_incident_categories"
        ],
        "Domain must define the minimum incident taxonomy.",
    )

    record(
        "TAXONOMY-UNIQUENESS",
        _unique(category_ids),
        "Incident category IDs must be unique.",
    )

    source_ids = tuple(
        item.source_id
        for item in pack.evidence_sources
    )

    record(
        "MINIMUM-EVIDENCE-SOURCES",
        len(source_ids)
        >= policy[
            "minimum_required_evidence_sources"
        ],
        "Domain must define sufficient evidence sources.",
    )

    record(
        "EVIDENCE-SOURCE-UNIQUENESS",
        _unique(source_ids),
        "Evidence source IDs must be unique.",
    )

    record(
        "TENANT-SCOPED-EVIDENCE",
        all(
            source.tenant_scoped
            for source in pack.evidence_sources
        ),
        "Every domain evidence source must be tenant scoped.",
    )

    tool_names = tuple(
        item.tool_name
        for item in pack.tools
    )

    record(
        "TOOL-UNIQUENESS",
        _unique(tool_names),
        "Tool names must be unique within a domain pack.",
    )

    allowed_risks = set(
        policy["allowed_tool_risks"]
    )

    record(
        "TOOL-RISK-ALLOWLIST",
        all(
            tool.risk in allowed_risks
            for tool in pack.tools
        ),
        "Tool risk levels must be platform recognized.",
    )

    allowed_environments = set(
        policy["allowed_environments"]
    )

    record(
        "TOOL-ENVIRONMENT-ALLOWLIST",
        all(
            set(tool.allowed_environments)
            <= allowed_environments
            for tool in pack.tools
        ),
        "Tool environments must be platform recognized.",
    )

    record(
        "MUTATING-TOOL-APPROVAL",
        all(
            not tool.mutating
            or tool.required_approval
            for tool in pack.tools
        ),
        "Every mutating tool must require approval.",
    )

    record(
        "POLICY-NO-EXPANSION",
        pack.may_narrow_platform_policy
        and not pack.may_expand_platform_policy,
        "Domain policy may narrow but cannot expand platform policy.",
    )

    record(
        "CROSS-TENANT-DENIAL",
        pack.tenant_isolation_required
        and pack.deny_cross_tenant_access,
        "Tenant isolation and cross-tenant denial are required.",
    )

    record(
        "PRODUCTION-MUTATION-DENIAL",
        pack.deny_unapproved_production_mutation,
        "Unapproved production mutation must remain denied.",
    )

    record(
        "NO-DIRECT-GENAI-EXECUTION",
        pack.deny_direct_genai_tool_execution,
        "Direct GenAI-to-tool execution must remain denied.",
    )

    record(
        "MINIMUM-EVALUATION-CASES",
        len(pack.required_evaluation_cases)
        >= policy["minimum_evaluation_cases"],
        "Domain must define sufficient evaluation cases.",
    )

    record(
        "EVALUATION-CASE-UNIQUENESS",
        _unique(pack.required_evaluation_cases),
        "Evaluation case IDs must be unique.",
    )

    record(
        "FULL-EVALUATION-PASS-RATE",
        pack.minimum_pass_rate_percentage == 100.0,
        "Adaptation evaluation requires a 100 percent pass rate.",
    )

    record(
        "NO-AUTOMATIC-ACTIVATION",
        not pack.automatic_activation,
        "Domain pack activation cannot be automatic.",
    )

    record(
        "PRODUCTION-HUMAN-APPROVAL",
        pack.production_activation_requires_human_approval,
        "Production activation requires human approval.",
    )

    boundary_safe = not any(
        (
            pack.domain_pack_can_execute_tools,
            pack.domain_pack_can_modify_platform_policy,
            pack.domain_pack_can_approve_exceptions,
            pack.domain_pack_can_activate_itself,
        )
    )

    record(
        "AUTHORITY-BOUNDARY",
        boundary_safe,
        "Domain pack cannot execute, mutate policy, approve exceptions, or activate itself.",
    )

    status = (
        PackValidationStatus.VALID
        if all(item.passed for item in findings)
        else PackValidationStatus.INVALID
    )

    return PackValidationResult(
        pack_id=pack.pack_id,
        status=status,
        findings=tuple(findings),
        digest=pack.digest,
    )
