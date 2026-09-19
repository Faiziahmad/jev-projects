from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .triage import TriageResult, triage_alert
from .lifecycle import run_lifecycle
from jevfsm import AuditTrail


@dataclass
class SOCResult:
    alert_id: str
    triage: TriageResult
    lifecycle: Optional[AuditTrail] = None
    final_state: str = ""
    skipped_lifecycle: bool = False
    skip_reason: str = ""

    def to_dict(self) -> dict:
        out = {
            "alert_id": self.alert_id,
            "triage": self.triage.to_dict(),
            "final_state": self.final_state,
            "skipped_lifecycle": self.skipped_lifecycle,
        }
        if self.skip_reason:
            out["skip_reason"] = self.skip_reason
        if self.lifecycle:
            out["lifecycle_path"] = self.lifecycle.states_visited()
            out["lifecycle_summary"] = self.lifecycle.summary()
            out["lifecycle_steps"] = [
                {
                    "from": s.from_state,
                    "to": s.next_state,
                    "confidence": round(s.confidence, 4),
                }
                for s in self.lifecycle.steps
            ]
        return out


def process_alert(
    alert: dict,
    model: str = "jev-latest",
    run_lifecycle_fsm: bool = True,
    auto_close_threshold: float = 0.15,
    auto_page_threshold: float = 0.90,
    confidence_threshold: float = 0.55,
) -> SOCResult:
    alert_id = alert.get("alert_id", "unknown")

    triage = triage_alert(
        alert,
        alert_id=alert_id,
        model=model,
        auto_close_threshold=auto_close_threshold,
        auto_page_threshold=auto_page_threshold,
    )

    # auto-actioned alerts skip the lifecycle FSM
    if triage.auto_actioned or not run_lifecycle_fsm:
        reason = triage.notes if triage.auto_actioned else "lifecycle disabled"
        return SOCResult(
            alert_id=alert_id,
            triage=triage,
            final_state=triage.action,
            skipped_lifecycle=True,
            skip_reason=reason,
        )

    trail = run_lifecycle(
        triage=triage,
        alert=alert,
        model=model,
        confidence_threshold=confidence_threshold,
    )

    last = trail.last()
    final = last.next_state if last else "triaging"

    return SOCResult(
        alert_id=alert_id,
        triage=triage,
        lifecycle=trail,
        final_state=final,
    )


def process_batch(
    alerts: list[dict],
    model: str = "jev-latest",
    **kwargs,
) -> list[SOCResult]:
    results = []
    for alert in alerts:
        result = process_alert(alert, model=model, **kwargs)
        results.append(result)
    return results
