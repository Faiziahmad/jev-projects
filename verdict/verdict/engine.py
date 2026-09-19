from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from typesafe_sdk import Noul, Score, TypeSafeClient

_LOGIC_RUBRIC = [
    "Completely illogical — fallacies, contradictions, or nonsense",
    "Weak logic — some reasoning but significant gaps",
    "Moderate logic — reasonable but not airtight",
    "Strong logical argument — well structured and sound",
    "Airtight — watertight reasoning, no logical flaws",
]

_EVIDENCE_RUBRIC = [
    "Ignores available evidence entirely",
    "Barely references any evidence",
    "Uses some evidence but misses key points",
    "Strong use of evidence — well cited and relevant",
    "Masterful — uses all key evidence precisely and compellingly",
]

_PERSUASION_RUBRIC = [
    "Not persuasive at all — may even hurt their case",
    "Slightly persuasive to an impartial observer",
    "Moderately persuasive — makes a fair point",
    "Very persuasive — likely to move a jury",
    "Extremely compelling — hard to counter",
]


@dataclass
class ArgumentResult:
    role: str                  # "prosecution" | "defense"
    argument: str
    logic: float               # 0-1
    evidence: float            # 0-1
    persuasion: float          # 0-1
    relevant: float            # 0-1 (noul)
    guilty_prob: float         # 0-1 — updated probability after this argument
    guilty_delta: float        # change from previous
    round_num: int


@dataclass
class GameState:
    case: dict
    model: str = "jev-latest"
    max_rounds: int = 6
    win_threshold: float = 0.85
    guilty_prob: float = 0.50
    round_num: int = 0
    history: list[ArgumentResult] = field(default_factory=list)
    winner: Optional[str] = None
    finished: bool = False

    def current_role(self) -> str:
        return "prosecution" if self.round_num % 2 == 0 else "defense"

    def score_argument(self, argument: str) -> ArgumentResult:
        client = TypeSafeClient(model=self.model)
        role = self.current_role()

        state = {
            "case_title":  self.case["title"],
            "charge":      self.case["charge"],
            "defendant":   self.case["defendant"],
            "facts":       self.case["facts"],
            "evidence":    self.case["evidence"],
            "trial_history": [
                {
                    "round":    h.round_num,
                    "role":     h.role,
                    "argument": h.argument,
                }
                for h in self.history
            ],
            "current_role":     role,
            "current_argument": argument,
        }

        answers = client.system_one(
            state=state,
            questions={
                "logic": Score(
                    instructions=f"Rate the logical soundness of the {role}'s argument",
                    criteria=_LOGIC_RUBRIC,
                ),
                "evidence": Score(
                    instructions=f"How well does the {role} use the available case evidence?",
                    criteria=_EVIDENCE_RUBRIC,
                ),
                "persuasion": Score(
                    instructions=f"How persuasive is the {role}'s argument to an impartial jury?",
                    criteria=_PERSUASION_RUBRIC,
                ),
                "relevant": Noul(
                    instructions="This argument is relevant to the charges and case facts"
                ),
                "guilty_now": Noul(
                    instructions=(
                        "Based on ALL arguments made so far in this trial — including the current one — "
                        "the defendant is guilty of the stated charges"
                    )
                ),
            },
        ).answers

        def norm(score: float, levels: int = 5) -> float:
            return score / (levels - 1)

        logic      = norm(answers["logic"].score)
        evidence   = norm(answers["evidence"].score)
        persuasion = norm(answers["persuasion"].score)
        relevant   = answers["relevant"].noul
        guilty     = answers["guilty_now"].noul
        delta      = guilty - self.guilty_prob

        result = ArgumentResult(
            role=role,
            argument=argument,
            logic=logic,
            evidence=evidence,
            persuasion=persuasion,
            relevant=relevant,
            guilty_prob=guilty,
            guilty_delta=delta,
            round_num=self.round_num,
        )

        self.guilty_prob = guilty
        self.history.append(result)
        self.round_num += 1

        # check win conditions
        if guilty >= self.win_threshold:
            self.winner = "prosecution"
            self.finished = True
        elif guilty <= (1 - self.win_threshold):
            self.winner = "defense"
            self.finished = True
        elif self.round_num >= self.max_rounds * 2:
            self.winner = "prosecution" if guilty > 0.5 else "defense"
            self.finished = True

        return result
