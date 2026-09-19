from __future__ import annotations

import argparse
import sys
import time

from .cases import CASES, DEFAULT_CASE
from .engine import ArgumentResult, GameState

# ── terminal colors ───────────────────────────────────────────────────────────
_R = "\033[0m"
_BOLD = "\033[1m"
_RED  = "\033[31m"
_GRN  = "\033[32m"
_YLW  = "\033[33m"
_CYN  = "\033[36m"
_GRY  = "\033[90m"
_PROS = "\033[91m"   # prosecution — red
_DEF  = "\033[94m"   # defense — blue

WIDTH = 62


def _hr(char: str = "═") -> str:
    return char * WIDTH


def _bar(val: float, width: int = 20) -> str:
    filled = round(max(0.0, min(1.0, val)) * width)
    empty  = width - filled
    return f"{_RED}{'█' * filled}{_GRN}{'█' * empty}{_R}"


def _score_bar(val: float, width: int = 10) -> str:
    filled = round(max(0.0, min(1.0, val)) * width)
    return "█" * filled + "░" * (width - filled)


def _clear() -> None:
    print("\033[2J\033[H", end="")


def _print_header(state: GameState) -> None:
    print(f"\n{_BOLD}{_hr()}{_R}")
    print(f"  {_BOLD}VERDICT{_R} — AI Courtroom Judge")
    print(f"  {_hr('-')}")
    print(f"  Case:      {_BOLD}{state.case['title']}{_R}")
    print(f"  Charge:    {state.case['charge']}")
    print(f"  Defendant: {state.case['defendant']}")
    print(f"  {_hr('-')}")
    print(f"  Model: TypeSafe Jev  |  Rounds: {state.round_num // 2}/{state.max_rounds}  |  Win threshold: {state.win_threshold:.0%}")
    print(_hr())


def _print_facts(state: GameState) -> None:
    print(f"\n  {_BOLD}CASE FACTS:{_R}")
    for i, fact in enumerate(state.case["facts"], 1):
        print(f"  {_GRY}{i}.{_R} {fact}")
    print(f"\n  {_BOLD}EVIDENCE:{_R}")
    for ev in state.case["evidence"]:
        print(f"  {_GRY}•{_R} {ev}")
    print()


def _print_meter(state: GameState) -> None:
    gp = state.guilty_prob
    label = f"{gp:.0%}"

    if gp >= 0.75:
        verdict_hint = f"{_RED}Leaning GUILTY{_R}"
    elif gp <= 0.25:
        verdict_hint = f"{_GRN}Leaning NOT GUILTY{_R}"
    else:
        verdict_hint = f"{_YLW}CONTESTED{_R}"

    print(f"\n  {_BOLD}Guilty probability:{_R}  {_bar(gp)}  {_BOLD}{label}{_R}  {verdict_hint}")
    print(f"  {'NOT GUILTY':>10}{'':>18}{'GUILTY'}")
    print()


def _print_result(result: ArgumentResult) -> None:
    role_label = f"{_PROS}PROSECUTION{_R}" if result.role == "prosecution" else f"{_DEF}DEFENSE{_R}"
    delta_str  = f"+{result.guilty_delta:+.2f}" if result.role == "prosecution" else f"{result.guilty_delta:+.2f}"
    delta_col  = _RED if result.guilty_delta > 0 else _GRN

    print(f"\n  {_hr('-')}")
    print(f"  Jev scores [{role_label}] argument:")
    print(f"  {_hr('-')}")
    print(f"  Logic       {_score_bar(result.logic)}  {result.logic:.2f}")
    print(f"  Evidence    {_score_bar(result.evidence)}  {result.evidence:.2f}")
    print(f"  Persuasion  {_score_bar(result.persuasion)}  {result.persuasion:.2f}")
    print(f"  Relevant    {_score_bar(result.relevant)}  {result.relevant:.2f}")
    print(f"  {_hr('-')}")
    print(f"  Guilty Δ    {delta_col}{delta_str}{_R}  →  {result.guilty_prob:.2f}")
    print()


def _print_verdict(state: GameState) -> None:
    print(f"\n{_BOLD}{_hr('═')}{_R}")
    print(f"  {_BOLD}⚖  FINAL VERDICT{_R}")
    print(_hr("─"))
    print(f"  Final guilty probability: {state.guilty_prob:.2f}")
    print()
    if state.winner == "prosecution":
        print(f"  {_RED}{_BOLD}GUILTY{_R}")
        print(f"  {_BOLD}Prosecution wins.{_R}")
    else:
        print(f"  {_GRN}{_BOLD}NOT GUILTY{_R}")
        print(f"  {_BOLD}Defense wins.{_R}")
    print(_hr("═"))
    print()

    if state.history:
        print(f"  {_BOLD}Argument history:{_R}")
        for h in state.history:
            r = f"{_PROS}PRO{_R}" if h.role == "prosecution" else f"{_DEF}DEF{_R}"
            print(f"  Round {h.round_num // 2 + 1} [{r}]  "
                  f"logic={h.logic:.2f}  ev={h.evidence:.2f}  "
                  f"pers={h.persuasion:.2f}  → guilty={h.guilty_prob:.2f}")
    print()


def _prompt_argument(role: str) -> str:
    color = _PROS if role == "prosecution" else _DEF
    print(f"  {color}{_BOLD}{role.upper()}{_R} — make your argument:")
    print(f"  {_GRY}(type your argument and press Enter){_R}\n")
    try:
        arg = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nGame ended.")
        sys.exit(0)
    return arg


def _thinking() -> None:
    print(f"\n  {_GRY}Jev is deliberating", end="", flush=True)
    for _ in range(3):
        time.sleep(0.4)
        print(".", end="", flush=True)
    print(f"{_R}\n")


def play(case_key: str = DEFAULT_CASE, model: str = "jev-latest",
         max_rounds: int = 6, win_threshold: float = 0.85,
         solo: bool = False) -> None:

    if case_key not in CASES:
        print(f"Unknown case '{case_key}'. Available: {list(CASES)}")
        sys.exit(1)

    state = GameState(
        case=CASES[case_key],
        model=model,
        max_rounds=max_rounds,
        win_threshold=win_threshold,
    )

    _clear()
    _print_header(state)
    _print_facts(state)
    _print_meter(state)

    print(f"  {_BOLD}HOW TO PLAY:{_R}")
    if solo:
        print(f"  You play both sides. Argue as {_PROS}PROSECUTION{_R} then {_DEF}DEFENSE{_R}.")
    else:
        print(f"  Player 1 = {_PROS}PROSECUTION{_R}  |  Player 2 = {_DEF}DEFENSE{_R}")
    print(f"  Push guilty probability above {win_threshold:.0%} to win (prosecution)")
    print(f"  or below {1-win_threshold:.0%} to win (defense).")
    print(f"  Jev is the only judge. No appeals.\n")
    input(f"  {_GRY}Press Enter to begin...{_R}")

    while not state.finished:
        _clear()
        _print_header(state)
        _print_meter(state)

        role = state.current_role()
        arg = _prompt_argument(role)
        if not arg:
            print("  Empty argument — Jev is not impressed.")
            continue

        _thinking()
        result = state.score_argument(arg)
        _print_result(result)
        _print_meter(state)

        if state.finished:
            break

        input(f"  {_GRY}Press Enter for next round...{_R}")

    _clear()
    _print_header(state)
    _print_verdict(state)


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="verdict",
        description="VERDICT — AI Courtroom Judge powered by TypeSafe Jev",
    )
    parser.add_argument(
        "--case", choices=list(CASES), default=DEFAULT_CASE,
        help=f"Case to play (default: {DEFAULT_CASE})",
    )
    parser.add_argument("--model", default="jev-latest")
    parser.add_argument("--rounds", type=int, default=6, help="Max rounds per side (default: 6)")
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="Win probability threshold (default: 0.85)")
    parser.add_argument("--solo", action="store_true",
                        help="Solo mode — you argue both sides")
    parser.add_argument("--list-cases", action="store_true", help="List available cases")

    args = parser.parse_args()

    if args.list_cases:
        print("Available cases:")
        for key, case in CASES.items():
            print(f"  {key:<12} {case['title']} — {case['charge']}")
        return

    play(
        case_key=args.case,
        model=args.model,
        max_rounds=args.rounds,
        win_threshold=args.threshold,
        solo=args.solo,
    )
