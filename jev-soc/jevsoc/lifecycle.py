from __future__ import annotations

from jevfsm import JevFSM, AuditTrail

from .triage import TriageResult


def build_alert_fsm(model: str = "jev-latest", confidence_threshold: float = 0.55) -> JevFSM:
    fsm = JevFSM(model=model, confidence_threshold=confidence_threshold)

    fsm.state("new",           description="Alert received, awaiting triage")
    fsm.state("triaging",      description="Initial triage in progress")
    fsm.state("investigating", description="Analyst actively investigating")
    fsm.state("escalated",     description="Escalated to senior analyst or incident commander")
    fsm.state("contained",     description="Threat contained, verifying clean state")
    fsm.state("resolved",      terminal=True)
    fsm.state("false_positive", terminal=True)

    fsm.transition(
        "new",
        to=["triaging", "false_positive"],
        instructions="Based on initial alert data, should we triage this or close as false positive?",
    )
    fsm.transition(
        "triaging",
        to=["investigating", "escalated", "false_positive"],
        instructions=(
            "Based on triage findings, severity, and true positive probability, "
            "should we investigate, escalate directly, or close as false positive?"
        ),
    )
    fsm.transition(
        "investigating",
        to=["escalated", "contained", "false_positive", "resolved"],
        instructions=(
            "Based on investigation findings, should we escalate, contain, "
            "close as false positive, or mark resolved?"
        ),
    )
    fsm.transition(
        "escalated",
        to=["contained", "resolved", "false_positive"],
        instructions="Based on escalation response, should we contain, resolve, or close as false positive?",
        guard="There is sufficient evidence to justify continued escalation",
        guard_threshold=0.4,
    )
    fsm.transition(
        "contained",
        to=["resolved"],
        instructions="Is the threat fully contained and safe to mark resolved?",
    )

    return fsm


def run_lifecycle(
    triage: TriageResult,
    alert: dict,
    model: str = "jev-latest",
    confidence_threshold: float = 0.55,
    max_steps: int = 8,
) -> AuditTrail:
    fsm = build_alert_fsm(model=model, confidence_threshold=confidence_threshold)

    base_context = {
        "alert": alert,
        "triage_summary": {
            "true_positive_prob": triage.true_positive_prob,
            "severity": triage.severity,
            "category": triage.category,
            "initial_action": triage.action,
        },
    }

    def context_fn(state: str, trail: AuditTrail) -> dict:
        return {
            **base_context,
            "current_state": state,
            "steps_taken": len(trail.steps),
            "previous_states": trail.states_visited(),
        }

    return fsm.run(
        start="new",
        context_fn=context_fn,
        max_steps=max_steps,
        confidence_threshold=confidence_threshold,
    )
