"""Security control catalogue mapped to published cost factors.

Each control is an investable lever whose effect is anchored to IBM's *Cost of a Data
Breach* cost amplifiers and mitigators. Applying a control reduces the estimated
operational breach cost (and, for some, the annual breach likelihood). This turns the
what-if simulator into a concrete, defensible business case instead of a vibe.

The reductions are marginal improvements relative to the modelled baseline posture and
are illustrative reference points drawn from the report's published deltas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    key: str
    name: str
    description: str
    cost_reduction: float  # fractional reduction in operational breach cost
    frequency_reduction: float = 0.0  # fractional reduction in annual breach likelihood


CONTROL_CATALOG: dict[str, Control] = {
    "security_ai_automation": Control(
        key="security_ai_automation",
        name="Security AI & automation",
        description="Extensive use of AI/automation in detection and response — IBM's "
        "single largest cost mitigator.",
        cost_reduction=0.18,
        frequency_reduction=0.05,
    ),
    "ir_team_and_plan": Control(
        key="ir_team_and_plan",
        name="IR team + tested plan",
        description="A dedicated incident-response team with a regularly tested plan.",
        cost_reduction=0.12,
        frequency_reduction=0.03,
    ),
    "encryption": Control(
        key="encryption",
        name="Extensive encryption",
        description="Encryption of data at rest and in transit across the estate.",
        cost_reduction=0.10,
    ),
    "devsecops": Control(
        key="devsecops",
        name="DevSecOps",
        description="Security integrated into the software delivery lifecycle.",
        cost_reduction=0.08,
        frequency_reduction=0.04,
    ),
    "identity_mfa": Control(
        key="identity_mfa",
        name="Identity & access (MFA)",
        description="Strong IAM with multi-factor authentication enforced.",
        cost_reduction=0.07,
        frequency_reduction=0.06,
    ),
    "employee_training": Control(
        key="employee_training",
        name="Employee security training",
        description="Regular awareness training reducing human-error breaches.",
        cost_reduction=0.06,
        frequency_reduction=0.05,
    ),
    "threat_intel": Control(
        key="threat_intel",
        name="Threat intelligence",
        description="Proactive threat intelligence shortening detection time.",
        cost_reduction=0.05,
        frequency_reduction=0.02,
    ),
}


def cost_reduction_factor(control_keys: list[str]) -> float:
    """Combined multiplicative cost factor for a set of controls (0–1, lower = cheaper)."""
    factor = 1.0
    for key in control_keys:
        control = CONTROL_CATALOG.get(key)
        if control is not None:
            factor *= 1.0 - control.cost_reduction
    return factor


def frequency_reduction_factor(control_keys: list[str]) -> float:
    """Combined multiplicative frequency factor for a set of controls (0–1)."""
    factor = 1.0
    for key in control_keys:
        control = CONTROL_CATALOG.get(key)
        if control is not None:
            factor *= 1.0 - control.frequency_reduction
    return factor
