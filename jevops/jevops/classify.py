from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

_INTEREST_RUBRIC = [
    "No attack value — standard/expected service",
    "Low interest — worth noting but low priority",
    "Moderate interest — investigate after higher priorities",
    "High value — strong attack surface, prioritise",
    "Critical — immediate high-value target",
]

_PORT_VECTORS = {
    "web":      "HTTP/HTTPS web application (80, 443, 8080, 8443)",
    "ssh":      "SSH remote access (22)",
    "smb":      "SMB/Windows file sharing (445, 139)",
    "database": "Database service (3306, 5432, 1433, 27017, 6379)",
    "rdp":      "Remote desktop (3389)",
    "ftp":      "FTP file transfer (21)",
    "mail":     "Mail service (25, 110, 143, 587)",
    "other":    "Other / uncommon service",
}

_PORT_NEXT_TOOLS = {
    "ffuf":     "Web directory fuzzing with ffuf",
    "gobuster": "Directory/DNS busting with gobuster",
    "hydra":    "Credential brute-force with hydra",
    "burp":     "Manual web testing with Burp Suite",
    "nse":      "Nmap NSE scripts for deeper service enumeration",
    "wpscan":   "WordPress scan with wpscan",
    "manual":   "Manual investigation — no automated tool fits",
    "skip":     "Skip — not worth pursuing",
}

_PATH_TIERS = {
    "admin":    "Admin panel, management interface, control page",
    "api":      "API endpoint — REST, GraphQL, SOAP",
    "backup":   "Backup file, archive, old version (.bak, .zip, .tar)",
    "config":   "Config file, .env, credentials, secrets",
    "upload":   "File upload endpoint",
    "git":      ".git, .svn or other version control exposure",
    "auth":     "Login, register, password reset, OAuth endpoint",
    "standard": "Standard page — not high value",
}

_PATH_ACTIONS = {
    "investigate": "Open in browser / Burp and investigate manually",
    "fuzz_deeper": "Run additional fuzzing on this path",
    "download":    "Download and inspect the file/resource",
    "skip":        "Skip — low value",
}

_VULN_EFFORTS = {
    "trivial":         "Public exploit, one-click, no skill needed",
    "moderate":        "Some configuration or conditions required",
    "complex":         "Skilled attacker, specific conditions",
    "needs_research":  "No public exploit, research needed",
}

_SEVERITY_RUBRIC = [
    "Informational — no direct risk",
    "Low — minor risk",
    "Medium — notable risk, investigate",
    "High — significant risk, exploit likely",
    "Critical — severe, immediate action",
]


@dataclass
class ClassifiedFinding:
    finding: dict
    tier: str          # critical / high / medium / low / info
    interest: float    # 0-1
    primary: str       # main classification label
    action: str        # recommended next action/tool
    action_confidence: float
    exploitable: float = 0.0
    notes: str = ""
    raw_answers: Any = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            **self.finding,
            "classification": {
                "tier":             self.tier,
                "interest":         round(self.interest, 3),
                "primary":          self.primary,
                "action":           self.action,
                "action_confidence": round(self.action_confidence, 3),
                "exploitable":      round(self.exploitable, 3),
                "notes":            self.notes,
            },
        }


def _interest_to_tier(score: float) -> str:
    if score >= 0.85:  return "critical"
    if score >= 0.65:  return "high"
    if score >= 0.40:  return "medium"
    if score >= 0.20:  return "low"
    return "info"


def classify_ports(
    findings: list[dict],
    target: str = "",
    model: str = "jev-latest",
) -> list[ClassifiedFinding]:
    if not findings:
        return []

    client = TypeSafeClient(model=model)
    state = {
        "target": target,
        "task": "You are a penetration tester. Classify each open port/service finding.",
        "findings": [f["raw"] for f in findings],
    }

    questions: dict = {}
    for i, f in enumerate(findings):
        questions[f"f{i}_interest"] = Score(
            instructions=f"Finding {i}: '{f['raw']}' — how interesting is this for attack?",
            criteria=_INTEREST_RUBRIC,
        )
        questions[f"f{i}_vector"] = Choice(
            instructions=f"Finding {i}: '{f['raw']}' — primary attack vector?",
            criteria=_PORT_VECTORS,
        )
        questions[f"f{i}_next"] = Choice(
            instructions=f"Finding {i}: '{f['raw']}' — best next tool to enumerate this?",
            criteria=_PORT_NEXT_TOOLS,
        )

    answers = client.system_one(state=state, questions=questions).answers

    results = []
    for i, f in enumerate(findings):
        interest = answers[f"f{i}_interest"].score / (len(_INTEREST_RUBRIC) - 1)
        vector   = answers[f"f{i}_vector"].choice
        next_tool = answers[f"f{i}_next"].choice
        next_conf = answers[f"f{i}_next"].confidence

        results.append(ClassifiedFinding(
            finding=f,
            tier=_interest_to_tier(interest),
            interest=interest,
            primary=vector,
            action=next_tool,
            action_confidence=next_conf,
        ))

    return sorted(results, key=lambda x: -x.interest)


def classify_paths(
    findings: list[dict],
    target: str = "",
    model: str = "jev-latest",
) -> list[ClassifiedFinding]:
    if not findings:
        return []

    client = TypeSafeClient(model=model)
    state = {
        "target": target,
        "task": "You are a penetration tester. Classify each discovered web path.",
        "findings": [f["raw"] for f in findings],
    }

    questions: dict = {}
    for i, f in enumerate(findings):
        questions[f"f{i}_juicy"] = Noul(
            instructions=f"Path {i}: '{f['raw']}' — this path is likely to contain sensitive data, admin access, or an exploitable function"
        )
        questions[f"f{i}_tier"] = Choice(
            instructions=f"Path {i}: '{f['raw']}' — what type of resource is this?",
            criteria=_PATH_TIERS,
        )
        questions[f"f{i}_action"] = Choice(
            instructions=f"Path {i}: '{f['raw']}' — recommended next action?",
            criteria=_PATH_ACTIONS,
        )

    answers = client.system_one(state=state, questions=questions).answers

    results = []
    for i, f in enumerate(findings):
        juicy     = answers[f"f{i}_juicy"].noul
        tier_name = answers[f"f{i}_tier"].choice
        action    = answers[f"f{i}_action"].choice
        action_c  = answers[f"f{i}_action"].confidence

        results.append(ClassifiedFinding(
            finding=f,
            tier=_interest_to_tier(juicy),
            interest=juicy,
            primary=tier_name,
            action=action,
            action_confidence=action_c,
            exploitable=juicy,
        ))

    return sorted(results, key=lambda x: -x.interest)


def classify_vulns(
    findings: list[dict],
    target: str = "",
    model: str = "jev-latest",
) -> list[ClassifiedFinding]:
    if not findings:
        return []

    client = TypeSafeClient(model=model)
    state = {
        "target": target,
        "task": "You are a penetration tester. Classify each vulnerability finding.",
        "findings": [f["raw"] for f in findings],
    }

    questions: dict = {}
    for i, f in enumerate(findings):
        questions[f"f{i}_exploitable"] = Noul(
            instructions=f"Vuln {i}: '{f['raw']}' — this vulnerability is likely exploitable in a real engagement"
        )
        questions[f"f{i}_severity"] = Score(
            instructions=f"Vuln {i}: '{f['raw']}' — severity?",
            criteria=_SEVERITY_RUBRIC,
        )
        questions[f"f{i}_effort"] = Choice(
            instructions=f"Vuln {i}: '{f['raw']}' — how much effort to exploit?",
            criteria=_VULN_EFFORTS,
        )

    answers = client.system_one(state=state, questions=questions).answers

    results = []
    for i, f in enumerate(findings):
        exploitable = answers[f"f{i}_exploitable"].noul
        sev_score   = answers[f"f{i}_severity"].score / (len(_SEVERITY_RUBRIC) - 1)
        effort      = answers[f"f{i}_effort"].choice
        effort_conf = answers[f"f{i}_effort"].confidence

        results.append(ClassifiedFinding(
            finding=f,
            tier=_interest_to_tier(sev_score),
            interest=sev_score,
            primary=effort,
            action="exploit" if exploitable > 0.6 else "research",
            action_confidence=effort_conf,
            exploitable=exploitable,
        ))

    return sorted(results, key=lambda x: -x.exploitable)


def route_next(
    all_findings: list[ClassifiedFinding],
    target: str = "",
    model: str = "jev-latest",
) -> dict:
    """Given all classified findings so far, decide what to do next."""
    client = TypeSafeClient(model=model)

    summary = [
        {"tier": f.tier, "action": f.action, "primary": f.primary,
         "interest": round(f.interest, 2), "raw": f.finding.get("raw", "")}
        for f in all_findings
    ]

    state = {
        "target": target,
        "task": "You are a penetration test lead. Given all findings so far, decide next steps.",
        "findings_summary": summary,
        "high_value_count": sum(1 for f in all_findings if f.tier in ("critical", "high")),
        "total_findings": len(all_findings),
    }

    answers = client.system_one(
        state=state,
        questions={
            "next_phase": Choice(
                instructions="What should the next phase of this engagement focus on?",
                criteria={
                    "web_enum":     "Enumerate web application further (ffuf, gobuster, burp)",
                    "exploitation": "Move to exploitation of identified vulnerabilities",
                    "cred_attack":  "Attempt credential attacks (hydra) on identified services",
                    "pivoting":     "Pivot to other discovered hosts or services",
                    "reporting":    "Enough findings — move to reporting",
                    "more_recon":   "Need more reconnaissance before proceeding",
                },
            ),
            "confidence_ok": Noul(
                instructions="We have enough information to proceed to the next phase confidently"
            ),
            "human_review": Noul(
                instructions="A human should review the findings before proceeding to the next phase"
            ),
        },
    ).answers

    return {
        "next_phase":      answers["next_phase"].choice,
        "next_confidence": answers["next_phase"].confidence,
        "next_probs":      dict(answers["next_phase"].probabilities),
        "info_sufficient": answers["confidence_ok"].noul,
        "needs_human":     answers["human_review"].noul,
    }
