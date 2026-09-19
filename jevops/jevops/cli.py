from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from .classify import classify_paths, classify_ports, classify_vulns, route_next, ClassifiedFinding
from .parsers import parse
from .session import Session

__version__ = "0.1.0"

_TIER_COLORS = {
    "critical": "\033[31m",
    "high":     "\033[91m",
    "medium":   "\033[33m",
    "low":      "\033[32m",
    "info":     "\033[90m",
}
_RESET = "\033[0m"


def _tier_label(tier: str) -> str:
    return f"{_TIER_COLORS.get(tier, '')}{tier.upper():<8}{_RESET}"


def _bar(val: float, width: int = 10) -> str:
    filled = round(max(0.0, min(1.0, val)) * width)
    return "█" * filled + "░" * (width - filled)


def _print_findings(findings: list[ClassifiedFinding], title: str = "Results") -> None:
    print(f"\n{title} ({len(findings)} findings)")
    print("─" * 60)
    for f in findings:
        raw = f.finding.get("raw", "")[:45]
        print(
            f"  {_tier_label(f.tier)}  {_bar(f.interest)}  {f.interest:.2f}  "
            f"{f.primary:<20}  → {f.action}"
        )
        print(f"            {raw}")
    print()


def _read(path: Optional[str]) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    with open(path) as f:
        return f.read()


def cmd_nmap(args: argparse.Namespace) -> None:
    content = _read(args.file)
    raw = parse(content, "nmap")
    if not raw:
        print("No open ports found.")
        return
    findings = classify_ports(raw, target=args.target or "", model=args.model)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        _print_findings(findings, "nmap — Port Classification")


def cmd_paths(args: argparse.Namespace) -> None:
    content = _read(args.file)
    tool = args.format or ("ffuf" if args.file and args.file.endswith(".json") else "gobuster")
    raw = parse(content, tool)
    if not raw:
        print("No paths found.")
        return
    findings = classify_paths(raw, target=args.target or "", model=args.model)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        _print_findings(findings, f"{tool} — Path Classification")


def cmd_wpscan(args: argparse.Namespace) -> None:
    content = _read(args.file)
    raw = parse(content, "wpscan")
    if not raw:
        print("No wpscan findings.")
        return
    findings = classify_vulns(raw, target=args.target or "", model=args.model)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        _print_findings(findings, "wpscan — Vulnerability Classification")


def cmd_session_start(args: argparse.Namespace) -> None:
    session = Session.create(
        target=args.target,
        session_file=args.session,
        model=args.model,
    )
    print(f"Session started: {args.session}")
    print(f"Target: {args.target}")


def cmd_session_add(args: argparse.Namespace) -> None:
    session = Session.load(args.session, model=args.model)
    content = _read(args.file)
    findings = session.add_tool_output(content, args.tool)
    print(f"Added {len(findings)} classified findings from {args.tool}.")
    if not args.json:
        _print_findings(findings, f"{args.tool} findings")
    else:
        print(json.dumps([f.to_dict() for f in findings], indent=2))


def cmd_session_route(args: argparse.Namespace) -> None:
    session = Session.load(args.session, model=args.model)
    result = session.route()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nNext phase:  {result['next_phase']}")
        print(f"Confidence:  {_bar(result['next_confidence'])}  {result['next_confidence']:.2f}")
        print(f"Info OK:     {result['info_sufficient']:.2f}")
        print(f"Need human:  {result['needs_human']:.2f}")
        print("\nProbability breakdown:")
        for phase, prob in sorted(result["next_probs"].items(), key=lambda x: -x[1]):
            print(f"  {phase:<20} {_bar(prob)}  {prob:.3f}")
        print()


def cmd_session_report(args: argparse.Namespace) -> None:
    session = Session.load(args.session, model=args.model)
    report = session.report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_findings(session.findings, f"Session Report — {session.target}")


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="jevops",
        description="Pentest findings classifier powered by TypeSafe Jev",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--model",   default="jev-latest")
    shared.add_argument("--target",  default="", metavar="HOST")
    shared.add_argument("--json",    action="store_true")
    shared.add_argument("--api-key", metavar="KEY",
                        help="TypeSafe API key (overrides TYPESAFE_API_KEY env var)")

    sub = parser.add_subparsers(dest="command", required=True)

    # nmap
    p = sub.add_parser("nmap", parents=[shared], help="Classify nmap output")
    p.add_argument("file", nargs="?", default="-", metavar="SCAN.xml")

    # paths
    p = sub.add_parser("paths", parents=[shared], help="Classify ffuf/gobuster output")
    p.add_argument("file", nargs="?", default="-", metavar="OUTPUT")
    p.add_argument("--format", choices=["ffuf", "gobuster"], default=None)

    # wpscan
    p = sub.add_parser("wpscan", parents=[shared], help="Classify wpscan output")
    p.add_argument("file", nargs="?", default="-", metavar="OUTPUT.json")

    # session
    sess = sub.add_parser("session", help="Manage a campaign session")
    sess_sub = sess.add_subparsers(dest="subcommand", required=True)

    p = sess_sub.add_parser("start", help="Start a new session")
    p.add_argument("--target", required=True)
    p.add_argument("--session", default="session.json")
    p.add_argument("--model", default="jev-latest")

    p = sess_sub.add_parser("add", help="Add tool output to session")
    p.add_argument("--tool", required=True, choices=["nmap", "ffuf", "gobuster", "wpscan"])
    p.add_argument("--file", required=True)
    p.add_argument("--session", default="session.json")
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--json", action="store_true")

    p = sess_sub.add_parser("route", help="Get next phase recommendation")
    p.add_argument("--session", default="session.json")
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--json", action="store_true")

    p = sess_sub.add_parser("report", help="Full ranked findings report")
    p.add_argument("--session", default="session.json")
    p.add_argument("--model", default="jev-latest")
    p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    dispatch = {
        "nmap":    cmd_nmap,
        "paths":   cmd_paths,
        "wpscan":  cmd_wpscan,
    }

    if hasattr(args, "api_key") and args.api_key:
        os.environ["TYPESAFE_API_KEY"] = args.api_key

    try:
        if args.command == "session":
            sess_dispatch = {
                "start":  cmd_session_start,
                "add":    cmd_session_add,
                "route":  cmd_session_route,
                "report": cmd_session_report,
            }
            sess_dispatch[args.subcommand](args)
        else:
            dispatch[args.command](args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
