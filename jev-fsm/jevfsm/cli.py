from __future__ import annotations

import argparse
import json
import os
import sys

from .config import load_yaml, validate_yaml
from .core import JevFSM, StepResult

__version__ = "0.1.0"


def _print_step(result: StepResult, step_num: int = 1) -> None:
    status = ""
    if result.guard_failed:
        status = "  [GUARD FAILED]"
    elif result.paused:
        status = "  [LOW CONFIDENCE — paused]"

    print(f"\nStep {step_num}: {result.from_state} → {result.next_state}  "
          f"confidence={result.confidence:.2f}{status}")
    print("  Probabilities:")
    for state, prob in sorted(result.probabilities.items(), key=lambda x: -x[1]):
        bar = "█" * round(prob * 20)
        print(f"    {state:<20} {bar:<20} {prob:.3f}")


def cmd_validate(args: argparse.Namespace) -> None:
    errors = validate_yaml(args.config)
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("✓ Config valid")


def cmd_viz(args: argparse.Namespace) -> None:
    fsm = load_yaml(args.config)
    print(fsm.viz())


def cmd_step(args: argparse.Namespace) -> None:
    fsm = load_yaml(args.config)

    context: dict = {}
    if args.context:
        context = json.loads(args.context)
    elif args.context_file:
        with open(args.context_file) as f:
            context = json.load(f)

    result = fsm.step(
        current=args.from_state,
        context=context,
        confidence_threshold=args.confidence_threshold,
    )

    if args.json:
        out = {
            "from_state": result.from_state,
            "next_state": result.next_state,
            "confidence": round(result.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in result.probabilities.items()},
            "paused": result.paused,
            "guard_failed": result.guard_failed,
        }
        print(json.dumps(out, indent=2))
    else:
        _print_step(result)


def cmd_run(args: argparse.Namespace) -> None:
    fsm = load_yaml(args.config)

    base_context: dict = {}
    if args.context:
        base_context = json.loads(args.context)
    elif args.context_file:
        with open(args.context_file) as f:
            base_context = json.load(f)

    step_num = 0

    def context_fn(state: str, trail) -> dict:
        return {**base_context, "step": len(trail.steps), "current_state": state}

    def on_pause(result: StepResult) -> None:
        reason = "guard failed" if result.guard_failed else f"confidence {result.confidence:.2f} below threshold"
        print(f"\n⚠ Paused at '{result.from_state}': {reason}")
        return None

    trail = fsm.run(
        start=args.start,
        context_fn=context_fn,
        max_steps=args.max_steps,
        confidence_threshold=args.confidence_threshold,
        on_pause=on_pause,
    )

    if args.json:
        out = {
            "path": trail.states_visited(),
            "steps": [
                {
                    "from": s.from_state,
                    "to": s.next_state,
                    "confidence": round(s.confidence, 4),
                    "probabilities": {k: round(v, 4) for k, v in s.probabilities.items()},
                    "paused": s.paused,
                    "guard_failed": s.guard_failed,
                }
                for s in trail.steps
            ],
            "summary": trail.summary(),
        }
        print(json.dumps(out, indent=2))
    else:
        for i, step in enumerate(trail.steps, 1):
            _print_step(step, step_num=i)
        print(f"\nSummary: {trail.summary()}")


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="jev-fsm",
        description="Probabilistic state machine powered by TypeSafe Jev",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    parser.add_argument("--api-key", metavar="KEY",
                        help="TypeSafe API key (overrides TYPESAFE_API_KEY env var)")

    # validate
    p = sub.add_parser("validate", help="Validate a YAML config")
    p.add_argument("config", metavar="CONFIG.yaml")

    # viz
    p = sub.add_parser("viz", help="Print state graph")
    p.add_argument("config", metavar="CONFIG.yaml")

    # step
    p = sub.add_parser("step", help="Run a single FSM step")
    p.add_argument("config", metavar="CONFIG.yaml")
    p.add_argument("--from", dest="from_state", required=True, metavar="STATE")
    p.add_argument("--context", metavar="JSON")
    p.add_argument("--context-file", metavar="FILE")
    p.add_argument("--confidence-threshold", type=float, default=None)
    p.add_argument("--json", action="store_true")

    # run
    p = sub.add_parser("run", help="Run FSM autonomously from start state")
    p.add_argument("config", metavar="CONFIG.yaml")
    p.add_argument("--start", required=True, metavar="STATE")
    p.add_argument("--context", metavar="JSON")
    p.add_argument("--context-file", metavar="FILE")
    p.add_argument("--max-steps", type=int, default=20)
    p.add_argument("--confidence-threshold", type=float, default=None)
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    dispatch = {
        "validate": cmd_validate,
        "viz": cmd_viz,
        "step": cmd_step,
        "run": cmd_run,
    }

    if args.api_key:
        os.environ["TYPESAFE_API_KEY"] = args.api_key

    try:
        dispatch[args.command](args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
