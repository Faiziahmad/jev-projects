from __future__ import annotations

import argparse
import json
import os
import sys

from .core import DEFAULT_WEIGHTS, PRESETS, EvalResult, evaluate

__version__ = "0.1.0"


def _bar(val: float, width: int = 10) -> str:
    filled = round(max(0.0, min(1.0, val)) * width)
    return "█" * filled + "░" * (width - filled)


def _print_result(result: EvalResult, threshold: float, weights: dict | None = None) -> None:
    overall = result.overall(weights)
    passed = overall >= threshold

    rows = [
        ("relevance",      result.relevance),
        ("completeness",   result.completeness),
        ("conciseness",    result.conciseness),
        ("on_task",        result.on_task),
        ("safe",           result.safe),
        ("instr_follow",   result.instruction_follow),
    ]
    if result.accuracy is not None:
        rows.append(("accuracy", result.accuracy))

    print("\njeval results")
    print("─" * 44)
    for label, val in rows:
        print(f"  {label:<16} {_bar(val)}  {val:.2f}")
    if result.tone:
        print(f"  {'tone':<16} {result.tone}")
    print("─" * 44)
    status = "PASS ✓" if passed else "FAIL ✗"
    print(f"  {'overall':<16} {_bar(overall)}  {overall:.2f}  [{status}]  threshold={threshold}")
    print()


def _to_dict(result: EvalResult, threshold: float, weights: dict | None = None) -> dict:
    overall = result.overall(weights)
    out = {
        "relevance":        round(result.relevance, 4),
        "completeness":     round(result.completeness, 4),
        "conciseness":      round(result.conciseness, 4),
        "on_task":          round(result.on_task, 4),
        "safe":             round(result.safe, 4),
        "instruction_follow": round(result.instruction_follow, 4),
        "tone":             result.tone,
        "overall":          round(overall, 4),
        "passed":           overall >= threshold,
        "threshold":        threshold,
    }
    if result.accuracy is not None:
        out["accuracy"] = round(result.accuracy, 4)
    return out


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="jeval",
        description="Evaluate LLM output with TypeSafe Jev — typed scores, no hallucinations.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    src = parser.add_argument_group("input (inline or file)")
    src.add_argument("--prompt",          "-p", metavar="TEXT")
    src.add_argument("--response",        "-r", metavar="TEXT")
    src.add_argument("--ground-truth",    "-g", metavar="TEXT")
    src.add_argument("--prompt-file",           metavar="FILE")
    src.add_argument("--response-file",         metavar="FILE")
    src.add_argument("--ground-truth-file",     metavar="FILE")

    parser.add_argument("--model",     default="jev-latest", metavar="MODEL")
    parser.add_argument("--api-key",   metavar="KEY",
                        help="TypeSafe API key (overrides TYPESAFE_API_KEY env var)")
    parser.add_argument("--threshold", "-t", type=float, default=0.7,
                        metavar="N", help="pass/fail cutoff 0–1 (default: 0.7)")
    parser.add_argument("--preset", choices=list(PRESETS), default="balanced",
                        help="scoring weight preset: balanced|strict|safety|creative")
    parser.add_argument("--weights", metavar="KEY=VAL,...",
                        help="override individual weights e.g. completeness=3,safe=2")
    parser.add_argument("--json",      action="store_true", help="output JSON")
    parser.add_argument("--ci",        action="store_true",
                        help="exit 1 when overall < threshold (for CI pipelines)")

    args = parser.parse_args()

    def _read(inline: str | None, path: str | None) -> str | None:
        if inline:
            return inline
        if path:
            with open(path) as f:
                return f.read().strip()
        return None

    prompt       = _read(args.prompt,       args.prompt_file)
    response     = _read(args.response,     args.response_file)
    ground_truth = _read(args.ground_truth, args.ground_truth_file)

    if not prompt or not response:
        parser.error("--prompt and --response are required (use inline text or --*-file)")

    if args.api_key:
        os.environ["TYPESAFE_API_KEY"] = args.api_key

    weights = dict(PRESETS[args.preset])
    if args.weights:
        for pair in args.weights.split(","):
            k, _, v = pair.partition("=")
            weights[k.strip()] = float(v.strip())

    try:
        result = evaluate(prompt, response, ground_truth=ground_truth, model=args.model)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(_to_dict(result, args.threshold, weights), indent=2))
    else:
        _print_result(result, args.threshold, weights)

    if args.ci and result.overall(weights) < args.threshold:
        sys.exit(1)
