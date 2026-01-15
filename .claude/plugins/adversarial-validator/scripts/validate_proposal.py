#!/usr/bin/env python3
"""
Adversarial Validation Runner for Design Proposals

Implements the five-stage protocol programmatically for integration
with automated pipelines and pre-commit hooks.

Usage:
    python3 validate_proposal.py <proposal_file>
    python3 validate_proposal.py --help
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    """Issue severity levels with clear action requirements."""
    BLOCKING = "blocking"   # Must fix before merge/deploy
    HIGH = "high"           # Should fix before merge
    MEDIUM = "medium"       # Fix within sprint
    SUGGESTION = "suggestion"  # Consider for future


class Verdict(Enum):
    """Validation verdicts."""
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REVISE_AND_RESUBMIT = "revise_and_resubmit"
    BLOCKED = "blocked"


@dataclass
class Issue:
    """A single validation issue with full context."""
    severity: Severity
    title: str
    location: str
    evidence: str
    impact: str
    principle_violated: str
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "title": self.title,
            "location": self.location,
            "evidence": self.evidence,
            "impact": self.impact,
            "principle_violated": self.principle_violated,
            "remediation": self.remediation,
        }


@dataclass
class ValidationResult:
    """Complete validation result with all findings."""
    verdict: Verdict
    issues: list[Issue] = field(default_factory=list)
    unanswered_questions: list[str] = field(default_factory=list)
    steel_man_summary: str = ""
    pre_mortem_findings: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    confidence_justification: str = ""

    @property
    def blocking_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.BLOCKING)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.MEDIUM)

    @property
    def suggestion_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.SUGGESTION)

    @property
    def is_approved(self) -> bool:
        return self.verdict in [Verdict.APPROVED, Verdict.APPROVED_WITH_CONDITIONS]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "counts": {
                "blocking": self.blocking_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "suggestion": self.suggestion_count,
            },
            "confidence": self.confidence,
            "confidence_justification": self.confidence_justification,
            "steel_man_summary": self.steel_man_summary,
            "pre_mortem_findings": self.pre_mortem_findings,
            "issues": [i.to_dict() for i in self.issues],
            "unanswered_questions": self.unanswered_questions,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def determine_verdict(issues: list[Issue]) -> Verdict:
    """Determine verdict based on issue severities."""
    severities = [i.severity for i in issues]

    if Severity.BLOCKING in severities:
        return Verdict.BLOCKED
    elif severities.count(Severity.HIGH) >= 3:
        return Verdict.REVISE_AND_RESUBMIT
    elif Severity.HIGH in severities:
        return Verdict.APPROVED_WITH_CONDITIONS
    elif Severity.MEDIUM in severities:
        return Verdict.APPROVED_WITH_CONDITIONS
    else:
        return Verdict.APPROVED


# Pre-mortem prompt templates for different failure scenarios
PRE_MORTEM_PROMPTS = [
    "It is six months from now. This has failed catastrophically in production. What went wrong?",
    "A security researcher just published a CVE for this system. What did they find?",
    "The on-call engineer was paged at 3 AM. What caused the outage?",
    "This became a case study of what NOT to do. Why?",
    "A customer is demanding a refund due to data loss. What happened?",
    "The new hire asked 'why is this so complicated?' What's the answer?",
    "The system fell over during Black Friday traffic. What wasn't scaled?",
    "An audit found compliance violations. What was missed?",
]

# Socratic question categories with example templates
SOCRATIC_CATEGORIES = {
    "clarifying": [
        "What is the intended behavior when {edge_case}?",
        "What does 'success' look like for this component?",
        "Who are the actual users and what are their workflows?",
        "What are the hard requirements vs. nice-to-haves?",
    ],
    "assumptions": [
        "What assumptions does this make about {dependency}?",
        "What if {assumption} turns out to be wrong?",
        "What implicit constraints are built into this design?",
        "What external factors could invalidate this approach?",
    ],
    "evidence": [
        "What tests validate this handles {scenario}?",
        "What load testing supports this scaling claim?",
        "How was this approach validated before proposing?",
        "What data supports this design decision?",
    ],
    "perspectives": [
        "How would a {role}-focused reviewer analyze this?",
        "What would a malicious actor try to exploit?",
        "How would the on-call engineer debug this at 3 AM?",
        "How would a new team member understand this code?",
    ],
    "implications": [
        "If {assumption} fails, what cascades?",
        "What depends on this behaving correctly?",
        "If we need to change this later, how hard is it?",
        "What's the blast radius when this fails?",
    ],
    "meta": [
        "What is the most important question we haven't asked?",
        "What are we afraid to bring up about this design?",
        "What would make us reject this approach entirely?",
        "What's the worst case scenario we're ignoring?",
    ],
}

# Constitutional principles for grounding critiques
CONSTITUTIONAL_PRINCIPLES = {
    "security_first": {
        "name": "Security First",
        "question": "How could a malicious actor abuse this?",
        "description": "Prioritize identifying vulnerabilities that could be exploited.",
    },
    "production_readiness": {
        "name": "Production Readiness",
        "question": "What happens at 10x load? At 3 AM? With bad input?",
        "description": "Evaluate behavior under real-world conditions, not just happy paths.",
    },
    "failure_mode_awareness": {
        "name": "Failure Mode Awareness",
        "question": "When this fails, what's the blast radius?",
        "description": "Systems fail. Good systems fail gracefully.",
    },
    "maintainability": {
        "name": "Maintainability Over Cleverness",
        "question": "Would a new team member understand this in 6 months?",
        "description": "Future developers must understand and modify this code.",
    },
    "evidence_based": {
        "name": "Evidence-Based Criticism",
        "question": "Can I prove this is a problem?",
        "description": "Every criticism must cite specific code/design and explain concrete impact.",
    },
    "constructive_intent": {
        "name": "Constructive Intent",
        "question": "Does this criticism help ship better software?",
        "description": "Criticism must improve outcomes, not just find faults.",
    },
    "calibrated_severity": {
        "name": "Calibrated Severity",
        "question": "Is this severity accurate, or am I overreacting?",
        "description": "Match criticism intensity to actual risk and impact.",
    },
    "intellectual_honesty": {
        "name": "Intellectual Honesty",
        "question": "Am I certain, or am I guessing?",
        "description": "Acknowledge uncertainty and distinguish confidence levels.",
    },
}


def format_report(result: ValidationResult, proposal_name: str = "Proposal") -> str:
    """Format validation result as markdown report."""
    lines = [
        f"## Validation Report: {proposal_name}",
        "",
        "### Executive Summary",
        f"- **Verdict**: {result.verdict.value.upper().replace('_', ' ')}",
        f"- **Blocking Issues**: {result.blocking_count}",
        f"- **High Severity**: {result.high_count}",
        f"- **Medium Severity**: {result.medium_count}",
        f"- **Suggestions**: {result.suggestion_count}",
        f"- **Confidence Level**: {result.confidence} - {result.confidence_justification}",
        "",
    ]

    if result.steel_man_summary:
        lines.extend([
            "### What Works Well",
            result.steel_man_summary,
            "",
        ])

    if result.pre_mortem_findings:
        lines.extend([
            "### Pre-Mortem Findings",
            "",
        ])
        for finding in result.pre_mortem_findings:
            lines.append(f"- {finding}")
        lines.append("")

    if result.issues:
        lines.extend([
            "### Issues",
            "",
        ])

        for issue in result.issues:
            severity_icon = {
                Severity.BLOCKING: "BLOCKING",
                Severity.HIGH: "HIGH",
                Severity.MEDIUM: "MEDIUM",
                Severity.SUGGESTION: "SUGGESTION",
            }[issue.severity]

            lines.extend([
                f"#### {severity_icon}: {issue.title}",
                f"- **Location**: {issue.location}",
                f"- **Evidence**: {issue.evidence}",
                f"- **Impact**: {issue.impact}",
                f"- **Principle Violated**: {issue.principle_violated}",
                f"- **Remediation**: {issue.remediation}",
                "",
            ])

    if result.unanswered_questions:
        lines.extend([
            "### Unanswered Questions",
            "",
        ])
        for q in result.unanswered_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)


def print_usage():
    """Print usage information."""
    print("""
Adversarial Validator - The Judge

Usage:
    python3 validate_proposal.py <proposal_file>
    python3 validate_proposal.py --list-principles
    python3 validate_proposal.py --list-questions
    python3 validate_proposal.py --help

Options:
    --list-principles   List all constitutional principles
    --list-questions    List socratic question categories
    --help              Show this help message

The proposal file should contain the design/architecture to validate.
Output is a structured validation report in markdown format.
""")


def list_principles():
    """Print all constitutional principles."""
    print("\n=== Constitutional Principles for Adversarial Validation ===\n")
    for key, principle in CONSTITUTIONAL_PRINCIPLES.items():
        print(f"### {principle['name']}")
        print(f"    Key Question: {principle['question']}")
        print(f"    Description: {principle['description']}")
        print()


def list_questions():
    """Print all socratic question categories."""
    print("\n=== Socratic Question Categories ===\n")
    for category, questions in SOCRATIC_CATEGORIES.items():
        print(f"### {category.replace('_', ' ').title()}")
        for q in questions:
            print(f"    - {q}")
        print()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    arg = sys.argv[1]

    if arg in ("--help", "-h"):
        print_usage()
        sys.exit(0)
    elif arg == "--list-principles":
        list_principles()
        sys.exit(0)
    elif arg == "--list-questions":
        list_questions()
        sys.exit(0)

    # File argument
    proposal_path = Path(arg)
    if not proposal_path.exists():
        print(f"Error: File not found: {proposal_path}")
        sys.exit(1)

    print(f"Adversarial Validator - The Judge")
    print(f"Analyzing: {proposal_path}")
    print()
    print("This script provides data structures and utilities for validation.")
    print("For full LLM-powered analysis, invoke the skill directly:")
    print()
    print("    @adversarial-validator review the following proposal:")
    print(f"    [contents of {proposal_path}]")
    print()

    # Show available resources
    print("Available resources:")
    print(f"  - {len(CONSTITUTIONAL_PRINCIPLES)} constitutional principles (--list-principles)")
    print(f"  - {len(SOCRATIC_CATEGORIES)} socratic question categories (--list-questions)")
    print(f"  - {len(PRE_MORTEM_PROMPTS)} pre-mortem prompt templates")


if __name__ == "__main__":
    main()
