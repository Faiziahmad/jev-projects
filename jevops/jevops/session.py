from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .classify import ClassifiedFinding, classify_paths, classify_ports, classify_vulns, route_next
from .parsers import parse


@dataclass
class Session:
    target: str
    session_file: str
    model: str = "jev-latest"
    findings: list[ClassifiedFinding] = field(default_factory=list)
    raw_findings: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_tool_output(self, content: str, tool: str) -> list[ClassifiedFinding]:
        raw = parse(content, tool)
        if not raw:
            return []

        self.raw_findings.extend(raw)

        finding_type = raw[0].get("type", "port")
        if tool == "nmap" or finding_type == "port":
            classified = classify_ports(raw, target=self.target, model=self.model)
        elif tool in ("ffuf", "gobuster") or finding_type == "path":
            classified = classify_paths(raw, target=self.target, model=self.model)
        elif tool == "wpscan" or finding_type == "vulnerability":
            classified = classify_vulns(raw, target=self.target, model=self.model)
        else:
            classified = classify_ports(raw, target=self.target, model=self.model)

        self.findings.extend(classified)
        self._save()
        return classified

    def route(self) -> dict:
        result = route_next(self.findings, target=self.target, model=self.model)
        self._save()
        return result

    def report(self) -> list[dict]:
        return [f.to_dict() for f in sorted(self.findings, key=lambda x: -x.interest)]

    def _save(self) -> None:
        data = {
            "target":     self.target,
            "model":      self.model,
            "created_at": self.created_at,
            "findings":   [f.to_dict() for f in self.findings],
        }
        with open(self.session_file, "w") as fp:
            json.dump(data, fp, indent=2)

    @classmethod
    def load(cls, session_file: str, model: str = "jev-latest") -> "Session":
        with open(session_file) as fp:
            data = json.load(fp)
        session = cls(
            target=data.get("target", ""),
            session_file=session_file,
            model=model,
            created_at=data.get("created_at", time.time()),
        )
        # rebuild ClassifiedFinding objects from saved dicts
        for f in data.get("findings", []):
            cls_data = f.pop("classification", {})
            cf = ClassifiedFinding(
                finding=f,
                tier=cls_data.get("tier", "info"),
                interest=cls_data.get("interest", 0.0),
                primary=cls_data.get("primary", ""),
                action=cls_data.get("action", ""),
                action_confidence=cls_data.get("action_confidence", 0.0),
                exploitable=cls_data.get("exploitable", 0.0),
                notes=cls_data.get("notes", ""),
            )
            session.findings.append(cf)
        return session

    @classmethod
    def create(cls, target: str, session_file: str, model: str = "jev-latest") -> "Session":
        session = cls(target=target, session_file=session_file, model=model)
        session._save()
        return session
