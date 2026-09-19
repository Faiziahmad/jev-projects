from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from typesafe_sdk import Choice, Noul, TypeSafeClient


@dataclass
class State:
    name: str
    description: str = ""
    terminal: bool = False


@dataclass
class Transition:
    from_state: str
    to_states: list[str]
    instructions: str = ""
    guard_instructions: Optional[str] = None
    guard_threshold: float = 0.5


@dataclass
class StepResult:
    from_state: str
    next_state: str
    confidence: float
    probabilities: dict[str, float]
    context: dict
    paused: bool = False        # True when confidence < threshold
    guard_failed: bool = False  # True when guard Noul rejected transition
    raw: Any = field(default=None, repr=False)


@dataclass
class AuditTrail:
    steps: list[StepResult] = field(default_factory=list)

    def append(self, result: StepResult) -> None:
        self.steps.append(result)

    def last(self) -> Optional[StepResult]:
        return self.steps[-1] if self.steps else None

    def states_visited(self) -> list[str]:
        if not self.steps:
            return []
        return [self.steps[0].from_state] + [s.next_state for s in self.steps]

    def summary(self) -> str:
        path = " → ".join(self.states_visited())
        avg_conf = sum(s.confidence for s in self.steps) / len(self.steps) if self.steps else 0
        return f"{path}  (avg confidence: {avg_conf:.2f})"


class FSMError(Exception):
    pass


class JevFSM:
    def __init__(
        self,
        model: str = "jev-latest",
        confidence_threshold: float = 0.0,
        strict: bool = False,
    ) -> None:
        self._model = model
        self._confidence_threshold = confidence_threshold
        self._strict = strict  # if True, raise on low confidence instead of pausing
        self._states: dict[str, State] = {}
        self._transitions: dict[str, Transition] = {}
        self._client: Optional[TypeSafeClient] = None

    @property
    def _jev(self) -> TypeSafeClient:
        if self._client is None:
            self._client = TypeSafeClient(model=self._model)
        return self._client

    # ── definition API ────────────────────────────────────────────────────────

    def state(
        self,
        name: str,
        description: str = "",
        terminal: bool = False,
    ) -> "JevFSM":
        self._states[name] = State(name=name, description=description, terminal=terminal)
        return self

    def transition(
        self,
        from_state: str,
        to: list[str],
        instructions: str = "",
        guard: Optional[str] = None,
        guard_threshold: float = 0.5,
    ) -> "JevFSM":
        self._transitions[from_state] = Transition(
            from_state=from_state,
            to_states=to,
            instructions=instructions,
            guard_instructions=guard,
            guard_threshold=guard_threshold,
        )
        return self

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name in self._transitions:
            if name not in self._states:
                errors.append(f"transition from unknown state '{name}'")
            for to in self._transitions[name].to_states:
                if to not in self._states:
                    errors.append(f"transition to unknown state '{to}'")
        non_terminal_no_transition = [
            n for n, s in self._states.items()
            if not s.terminal and n not in self._transitions
        ]
        for name in non_terminal_no_transition:
            errors.append(f"non-terminal state '{name}' has no outgoing transitions")
        return errors

    # ── runtime ───────────────────────────────────────────────────────────────

    def step(
        self,
        current: str,
        context: dict,
        confidence_threshold: Optional[float] = None,
    ) -> StepResult:
        threshold = confidence_threshold if confidence_threshold is not None else self._confidence_threshold

        if current not in self._states:
            raise FSMError(f"unknown state '{current}'")

        state = self._states[current]
        if state.terminal:
            raise FSMError(f"state '{current}' is terminal — cannot step further")

        if current not in self._transitions:
            raise FSMError(f"no transition defined from state '{current}'")

        trans = self._transitions[current]

        # build state description for context
        state_descriptions = {
            name: self._states[name].description
            for name in trans.to_states
            if name in self._states
        }

        jev_state: dict = {
            "current_state": current,
            "current_state_description": state.description,
            "context": context,
            "possible_next_states": state_descriptions,
        }

        instructions = trans.instructions or (
            f"Based on the current state '{current}' and the provided context, "
            "which state should the workflow transition to next?"
        )

        questions: dict = {
            "next_state": Choice(
                instructions=instructions,
                criteria={
                    name: self._states[name].description or name
                    for name in trans.to_states
                },
            )
        }

        if trans.guard_instructions:
            questions["guard"] = Noul(instructions=trans.guard_instructions)

        answers = self._jev.system_one(state=jev_state, questions=questions).answers

        next_ans = answers["next_state"]
        next_state = next_ans.choice
        confidence = next_ans.confidence
        probabilities = dict(next_ans.probabilities)

        guard_failed = False
        if trans.guard_instructions:
            guard_prob = answers["guard"].noul
            if guard_prob < trans.guard_threshold:
                guard_failed = True

        paused = not guard_failed and confidence < threshold
        if self._strict and (paused or guard_failed):
            reason = "guard failed" if guard_failed else f"confidence {confidence:.2f} < {threshold}"
            raise FSMError(f"transition from '{current}' blocked: {reason}")

        return StepResult(
            from_state=current,
            next_state=next_state,
            confidence=confidence,
            probabilities=probabilities,
            context=context,
            paused=paused,
            guard_failed=guard_failed,
            raw=answers,
        )

    def run(
        self,
        start: str,
        context_fn: Callable[[str, AuditTrail], dict],
        max_steps: int = 20,
        confidence_threshold: Optional[float] = None,
        on_pause: Optional[Callable[[StepResult], Optional[str]]] = None,
    ) -> AuditTrail:
        trail = AuditTrail()
        current = start

        for _ in range(max_steps):
            if current not in self._states:
                raise FSMError(f"unknown state '{current}'")
            if self._states[current].terminal:
                break

            context = context_fn(current, trail)
            result = self.step(current, context, confidence_threshold=confidence_threshold)
            trail.append(result)

            if result.guard_failed or result.paused:
                if on_pause:
                    override = on_pause(result)
                    if override and override in self._states:
                        current = override
                        continue
                break

            current = result.next_state

        return trail

    # ── introspection ─────────────────────────────────────────────────────────

    def viz(self) -> str:
        lines = ["States:"]
        for name, s in self._states.items():
            tag = " [terminal]" if s.terminal else ""
            desc = f" — {s.description}" if s.description else ""
            lines.append(f"  {name}{tag}{desc}")
        lines.append("\nTransitions:")
        for from_s, trans in self._transitions.items():
            arrow = " → ".join(trans.to_states)
            lines.append(f"  {from_s} → [{arrow}]")
            if trans.guard_instructions:
                lines.append(f"    guard: {trans.guard_instructions}")
        return "\n".join(lines)
