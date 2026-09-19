from __future__ import annotations

import argparse
import json
import sys

import os

from .pipeline import process_alert, process_batch
from .triage import SEVERITY_LEVELS, _ACTIONS

__version__ = "0.1.0"


def _severity_color(severity: str) -> str:
    colors = {
        "info":     "\033[90m",
        "low":      "\033[32m",
        "medium":   "\033[33m",
        "high":     "\033[91m",
        "critical": "\033[31m",
    }
    reset = "\033[0m"
    return f"{colors.get(severity, '')}{severity.upper()}{reset}"


def _action_icon(action: str) -> str:
    icons = {
        "auto_close":         "✓ AUTO-CLOSE",
        "l1_investigate":     "→ L1",
        "l2_escalate":        "↑ L2",
        "l3_page":            "⚡ L3 PAGE",
        "immediate_response": "🚨 IMMEDIATE",
    }
    return icons.get(action, action)


def _print_result(result) -> None:
    t = result.triage
    print(f"\n{'─'*52}")
    print(f"  Alert:    {result.alert_id}")
    print(f"  TP Prob:  {'█' * round(t.true_positive_prob * 20):<20} {t.true_positive_prob:.2f}")
    print(f"  Severity: {_severity_color(t.severity)}")
    print(f"  Category: {t.category}")
    print(f"  Action:   {_action_icon(t.action)}")
    if t.notes:
        print(f"  Note:     {t.notes}")
    if result.lifecycle:
        print(f"  Path:     {result.lifecycle.summary()}")
    print(f"  Final:    {result.final_state}")
    print(f"{'─'*52}")


def cmd_alert(args: argparse.Namespace) -> None:
    if args.alert:
        alert = json.loads(args.alert)
    elif args.alert_file:
        with open(args.alert_file) as f:
            alert = json.load(f)
    else:
        print("error: --alert JSON or --alert-file FILE required", file=sys.stderr)
        sys.exit(2)

    result = process_alert(
        alert,
        model=args.model,
        run_lifecycle_fsm=not args.triage_only,
        auto_close_threshold=args.auto_close_threshold,
        auto_page_threshold=args.auto_page_threshold,
        confidence_threshold=args.confidence_threshold,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result)


def cmd_batch(args: argparse.Namespace) -> None:
    with open(args.file) as f:
        alerts = json.load(f)

    results = process_batch(
        alerts,
        model=args.model,
        run_lifecycle_fsm=not args.triage_only,
        auto_close_threshold=args.auto_close_threshold,
        auto_page_threshold=args.auto_page_threshold,
        confidence_threshold=args.confidence_threshold,
    )

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        action_counts: dict[str, int] = {}
        for r in results:
            action_counts[r.triage.action] = action_counts.get(r.triage.action, 0) + 1
            _print_result(r)

        print(f"\nBatch summary ({len(results)} alerts):")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {_action_icon(action):<25} {count}")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Run built-in simulation alerts to verify the pipeline."""
    sim_alerts = [
        {
            "alert_id": "SIM-001",
            "source": "crowdstrike",
            "rule": "Successful login from known corporate IP",
            "severity_raw": "low",
            "host": "LAPTOP-01",
            "user": "alice",
            "context": {"ip": "10.0.0.5", "known_ip": True, "time": "09:15", "business_hours": True},
        },
        {
            "alert_id": "SIM-002",
            "source": "sentinel",
            "rule": "Ransomware file extension changes detected",
            "severity_raw": "critical",
            "host": "FILESERVER-01",
            "user": "SYSTEM",
            "indicators": [".locked", ".encrypted", "ransom_note.txt", "vssadmin delete shadows"],
            "context": {"files_renamed": 4200, "shadow_copies_deleted": True},
        },
        {
            "alert_id": "SIM-003",
            "source": "splunk",
            "rule": "Multiple failed SSH logins",
            "severity_raw": "medium",
            "host": "WEB-01",
            "user": "root",
            "indicators": ["failed_auth x 847", "source_ip: 185.220.101.42"],
            "context": {"attempts_per_minute": 120, "source_country": "RU"},
        },
        {
            "alert_id": "SIM-004",
            "source": "dlp",
            "rule": "Large file upload to personal cloud storage",
            "severity_raw": "high",
            "host": "WORKSTATION-07",
            "user": "bob",
            "indicators": ["dropbox.com", "4.2GB upload", "resignation_letter.docx"],
            "context": {"user_gave_notice": True, "upload_outside_hours": True},
        },
        {
            "alert_id": "SIM-005",
            "source": "ids",
            "rule": "PsExec lateral movement to admin share",
            "severity_raw": "high",
            "host": "WORKSTATION-04",
            "user": "jsmith",
            "indicators": ["psexec.exe", "admin$", "WORKSTATION-07", "WORKSTATION-09"],
            "context": {"user_role": "developer", "is_admin": False, "peer_behavior": "unusual"},
        },
    ]

    print(f"Running simulation with {len(sim_alerts)} alerts...\n")
    results = process_batch(
        sim_alerts,
        model=args.model,
        run_lifecycle_fsm=not args.triage_only,
    )

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            _print_result(r)


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="jev-soc",
        description="SOC alert triage powered by TypeSafe Jev",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--model", default="jev-latest")
    shared.add_argument("--api-key", metavar="KEY",
                        help="TypeSafe API key (overrides TYPESAFE_API_KEY env var)")
    shared.add_argument("--triage-only", action="store_true",
                        help="Skip lifecycle FSM, triage pass only")
    shared.add_argument("--auto-close-threshold", type=float, default=0.15)
    shared.add_argument("--auto-page-threshold",  type=float, default=0.90)
    shared.add_argument("--confidence-threshold",  type=float, default=0.55)
    shared.add_argument("--json", action="store_true")

    p = sub.add_parser("alert", parents=[shared], help="Triage a single alert")
    p.add_argument("--alert",      metavar="JSON")
    p.add_argument("--alert-file", metavar="FILE")

    p = sub.add_parser("batch", parents=[shared], help="Triage a JSON array of alerts")
    p.add_argument("file", metavar="ALERTS.json")

    p = sub.add_parser("simulate", parents=[shared], help="Run built-in simulation")

    args = parser.parse_args()

    dispatch = {"alert": cmd_alert, "batch": cmd_batch, "simulate": cmd_simulate}
    if hasattr(args, "api_key") and args.api_key:
        os.environ["TYPESAFE_API_KEY"] = args.api_key
    try:
        dispatch[args.command](args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
