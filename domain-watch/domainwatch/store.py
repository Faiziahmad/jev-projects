"""Keeps last week's snapshot per domain so the report can say what changed."""
from __future__ import annotations

import json
import os
from typing import Optional


class Store:
    def __init__(self, path: str = "state"):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def _file(self, domain: str) -> str:
        return os.path.join(self.path, domain.replace("/", "_") + ".json")

    def last(self, domain: str) -> Optional[dict]:
        try:
            with open(self._file(domain)) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save(self, snap: dict, prev: Optional[dict] = None) -> None:
        # a failed lookup this week keeps last week's value, so next week's comparison stays fair
        keep = dict(snap)
        for k in ("web_addresses", "lookalikes", "mx", "ns", "spf", "dmarc"):
            if keep.get(k) is None and prev and prev.get(k) is not None:
                keep[k] = prev[k]
        tmp = self._file(snap["domain"]) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(keep, f, indent=2, sort_keys=True)
        os.replace(tmp, self._file(snap["domain"]))
