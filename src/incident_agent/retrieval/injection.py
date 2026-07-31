"""Heuristic prompt-injection inspection for retrieved text."""

from __future__ import annotations

import re


INJECTION_PATTERNS: tuple[
    tuple[str, re.Pattern[str]],
    ...
] = (
    (
        "ignore_previous_instructions",
        re.compile(
            r"\bignore\s+(all\s+)?previous\s+instructions\b",
            re.IGNORECASE,
        ),
    ),
    (
        "authorization_claim",
        re.compile(
            r"\byou\s+are\s+authorized\b",
            re.IGNORECASE,
        ),
    ),
    (
        "restricted_data_disclosure",
        re.compile(
            r"\bdisclose\s+every\s+restricted\s+document\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unapproved_production_action",
        re.compile(
            r"\brestart\s+production\b",
            re.IGNORECASE,
        ),
    ),
)


def detect_prompt_injection(
    content: str,
) -> tuple[str, ...]:
    """Return detected prompt-injection marker IDs."""

    return tuple(
        marker
        for marker, pattern in INJECTION_PATTERNS
        if pattern.search(content)
    )
