from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

SEVERITY_LEVELS = ["info", "low", "medium", "high", "critical"]

_SEVERITY_RUBRIC = [
    "Informational — no immediate risk, log only",
    "Low — minor risk, monitor but no urgent action",
    "Medium — moderate risk, investigate within hours",
    "High — significant risk, investigate within 30 minutes",
    "Critical — immediate threat, respond now",
]

_CATEGORIES = {
    "malware":           "Malware execution, ransomware, trojan, or virus activity",
    "phishing":          "Phishing attempt, credential harvesting, or social engineering",
    "brute_force":       "Repeated failed authentication or password spraying",
    "data_exfiltration": "Large or unusual data transfer to external destination",
    "lateral_movement":  "Attacker moving between systems inside the network",
    "insider_threat":    "Unusual behavior from a legitimate user account",
    "recon":             "Scanning, enumeration, or reconnaissance activity",
    "privilege_escalation": "Attempt to gain elevated privileges",
    "c2":                "Command and control communication detected",
    "other":             "Does not fit the above categories",
}

_ACTIONS = {
    "auto_close":          "Clearly a false positive — close without human review",
    "l1_investigate":      "Route to L1 analyst for basic investigation",
    "l2_escalate":         "Escalate to L2 security engineer for deep investigation",
    "l3_page":             "Page L3 / incident commander immediately",
    "immediate_response":  "Critical active threat — trigger incident response now",
}


@dataclass
class TriageResult:
    alert_id: str
    true_positive_prob: float
    severity: str
    severity_score: float
    category: str
    action: str
    action_confidence: float
    action_probabilities: dict[str, float]
    auto_actioned: bool
    notes: str = ""
    raw: Any = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "true_positive_prob": round(self.true_positive_prob, 4),
            "severity": self.severity,
            "severity_score": round(self.severity_score, 4),
            "category": self.category,
            "action": self.action,
            "action_confidence": round(self.action_confidence, 4),
            "action_probabilities": {k: round(v, 4) for k, v in self.action_probabilities.items()},
            "auto_actioned": self.auto_actioned,
            "notes": self.notes,
        }


def _severity_label(score: float) -> str:
    idx = min(int(round(score)), len(SEVERITY_LEVELS) - 1)
    return SEVERITY_LEVELS[idx]


def triage_alert(
    alert: dict,
    alert_id: Optional[str] = None,
    model: str = "jev-latest",
    auto_close_threshold: float = 0.15,
    auto_page_threshold: float = 0.90,
) -> TriageResult:
    client = TypeSafeClient(model=model)
    aid = alert_id or alert.get("alert_id", "unknown")

    state = {
        "alert": alert,
        "task": (
            "You are a SOC analyst. Evaluate this security alert and answer each question "
            "based on the alert data, indicators, context, and source system."
        ),
    }

    answers = client.system_one(
        state=state,
        questions={
            "true_positive": Noul(
                instructions=(
                    "This alert represents a real security threat or malicious activity, "
                    "not a false positive or benign event"
                )
            ),
            "severity": Score(
                instructions="Rate the severity of this security alert",
                criteria=_SEVERITY_RUBRIC,
            ),
            "category": Choice(
                instructions="What type of security threat does this alert represent?",
                criteria=_CATEGORIES,
            ),
            "action": Choice(
                instructions=(
                    "What is the correct immediate action for this alert? "
                    "Consider the true positive probability, severity, and category."
                ),
                criteria=_ACTIONS,
            ),
        },
    ).answers

    tp_prob = answers["true_positive"].noul
    sev_score = answers["severity"].score
    severity = _severity_label(sev_score)
    category = answers["category"].choice
    action = answers["action"].choice
    action_conf = answers["action"].confidence
    action_probs = dict(answers["action"].probabilities)

    # override action on extreme signals
    auto_actioned = False
    notes = ""
    if tp_prob < auto_close_threshold:
        action = "auto_close"
        auto_actioned = True
        notes = f"Auto-closed: true positive probability {tp_prob:.2f} below threshold {auto_close_threshold}"
    elif tp_prob >= auto_page_threshold and severity == "critical":
        action = "immediate_response"
        auto_actioned = True
        notes = f"Auto-paged: tp_prob={tp_prob:.2f}, severity=critical"

    return TriageResult(
        alert_id=aid,
        true_positive_prob=tp_prob,
        severity=severity,
        severity_score=sev_score,
        category=category,
        action=action,
        action_confidence=action_conf,
        action_probabilities=action_probs,
        auto_actioned=auto_actioned,
        notes=notes,
        raw=answers,
    )
