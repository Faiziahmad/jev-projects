from __future__ import annotations

from typing import Any

from .core import JevFSM


def from_dict(data: dict[str, Any]) -> JevFSM:
    model = data.get("model", "jev-latest")
    threshold = float(data.get("confidence_threshold", 0.0))
    strict = bool(data.get("strict", False))

    fsm = JevFSM(model=model, confidence_threshold=threshold, strict=strict)

    states = data.get("states", {})
    for name, cfg in states.items():
        cfg = cfg or {}
        fsm.state(
            name=name,
            description=cfg.get("description", ""),
            terminal=bool(cfg.get("terminal", False)),
        )

    transitions = data.get("transitions", {})
    for from_state, cfg in transitions.items():
        cfg = cfg or {}
        to = cfg.get("to", [])
        if isinstance(to, str):
            to = [to]
        fsm.transition(
            from_state=from_state,
            to=to,
            instructions=cfg.get("instructions", ""),
            guard=cfg.get("guard"),
            guard_threshold=float(cfg.get("guard_threshold", 0.5)),
        )

    return fsm


def load_yaml(path: str) -> JevFSM:
    try:
        import yaml
    except ImportError as e:
        raise ImportError("pip install pyyaml to use YAML configs") from e

    with open(path) as f:
        data = yaml.safe_load(f)

    return from_dict(data)


def validate_yaml(path: str) -> list[str]:
    fsm = load_yaml(path)
    return fsm.validate()
