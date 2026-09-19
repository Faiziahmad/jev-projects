# jev-fsm Blueprint

## Problem
Workflow automation uses rigid if/else rules. Rules break on edge cases, can't express uncertainty, and have no audit trail showing WHY a transition fired.

## Solution
A state machine where every transition is decided by Jev — calibrated probabilities, typed choices, full audit trail. "Should I move from scanning → exploitation?" is a Jev Choice question.

---

## Core Concepts

### State
A named node. Can be terminal (no outgoing transitions).

### Transition
Allowed edges FROM a state. Carries:
- `to`: list of allowed next states
- `instructions`: what Jev should consider when choosing
- Optional `guard`: a Noul question that must pass (>= threshold) before the transition runs

### StepResult
What you get back from one FSM step:
- `next_state`: chosen state
- `confidence`: Jev's confidence in that choice
- `probabilities`: full distribution over all options
- `guard_passed`: bool (if guard was defined)
- `context`: the input that drove the decision

### AuditTrail
Ordered list of StepResult. Full replay of every decision with its confidence.

---

## API Design

```python
from jevfsm import JevFSM

fsm = JevFSM()

# Define states
fsm.state("recon",       description="Passive information gathering")
fsm.state("scanning",    description="Active port and service scanning")
fsm.state("exploitation",description="Attempting to exploit vulnerabilities")
fsm.state("post_exploit",description="Post-exploitation, pivoting, persistence")
fsm.state("done",        terminal=True)

# Define transitions
fsm.transition("recon",        to=["scanning", "done"])
fsm.transition("scanning",     to=["exploitation", "recon", "done"])
fsm.transition("exploitation", to=["post_exploit", "scanning", "done"])
fsm.transition("post_exploit", to=["done"])

# Single step
result = fsm.step(
    current="recon",
    context={"findings": "ports 22,80,443 open", "target": "10.0.0.1"}
)
print(result.next_state, result.confidence)

# Full autonomous run (context_fn called each step)
history = fsm.run(
    start="recon",
    context_fn=lambda state, history: collect_context(state),
    max_steps=20,
    confidence_threshold=0.6  # pause for human if below
)
```

### YAML Config (portable, shareable workflows)
```yaml
name: pentest-workflow
model: jev-latest
confidence_threshold: 0.65

states:
  recon:
    description: Passive information gathering about the target
  scanning:
    description: Active scanning of ports, services, and vulnerabilities
  exploitation:
    description: Attempting exploitation of discovered vulnerabilities
  post_exploit:
    description: Post-exploitation activities
  done:
    terminal: true

transitions:
  recon:
    to: [scanning, done]
    instructions: Based on recon findings, what is the next engagement phase?
  scanning:
    to: [exploitation, recon, done]
    instructions: Based on scan results, should we exploit, gather more info, or stop?
  exploitation:
    to: [post_exploit, scanning, done]
  post_exploit:
    to: [done]
```

### CLI
```bash
jev-fsm validate pentest.yaml          # validate config
jev-fsm viz pentest.yaml               # print state graph (ASCII)
jev-fsm step pentest.yaml --from recon --context context.json
jev-fsm run pentest.yaml --start recon --context context.json --max-steps 10
```

---

## File Structure
```
jev-fsm/
├── BLUEPRINT.md
├── SUMMARY.md
├── pyproject.toml
└── jevfsm/
    ├── __init__.py
    ├── core.py      JevFSM, State, Transition, StepResult, AuditTrail
    ├── config.py    load_yaml(), validate_config()
    └── cli.py       validate / viz / step / run commands
```

---

## QA Test Cases (planned)
1. Linear FSM — A → B → C, no choices
2. Branching FSM — context drives different paths
3. Loop detection — FSM can return to prior state
4. Terminal state — step() on terminal raises cleanly
5. Guard threshold — low-confidence step pauses, doesn't auto-transition
6. YAML round-trip — load config, run, same behavior as programmatic
7. Pentest workflow — real recon context, verify sensible transitions
8. Audit trail — history records every step with full probabilities

---

## Key Design Decisions
- `step()` always returns StepResult even if paused — caller decides what to do
- Probabilities stored for every step — full replay possible
- YAML first — makes workflows shareable without code
- No implicit self-loops — must be declared explicitly
- `confidence_threshold` is advisory by default, hard-stop only with `strict=True`
