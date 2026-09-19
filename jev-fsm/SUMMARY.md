# jev-fsm

Probabilistic state machine powered by TypeSafe Jev. Every transition is a Jev Choice decision with calibrated confidence and full audit trail. Replaces brittle if/else workflow rules.

## Status
Working. CLI ships. Programmatic API done. YAML configs portable.

## Usage

### CLI
```bash
pip install -e .
export TYPESAFE_API_KEY=...

jev-fsm validate pentest.yaml                  # validate config
jev-fsm viz pentest.yaml                       # print state graph
jev-fsm step pentest.yaml --from recon --context '{"findings": "..."}'
jev-fsm run pentest.yaml --start recon --context '{"target": "..."}' --max-steps 10
jev-fsm run pentest.yaml --start recon --context '{}' --json   # structured output for CI
```

### Programmatic API
```python
from jevfsm import JevFSM

fsm = JevFSM(confidence_threshold=0.6)
fsm.state("recon", description="Passive info gathering")
fsm.state("scanning", description="Active port scan")
fsm.state("done", terminal=True)
fsm.transition("recon", to=["scanning", "done"])
fsm.transition("scanning", to=["done"])

result = fsm.step("recon", context={"findings": "port 80 open"})
print(result.next_state, result.confidence)

# full autonomous run
trail = fsm.run("recon", context_fn=lambda s, h: get_context(s), max_steps=10)
print(trail.summary())
```

### YAML config
```yaml
name: my-workflow
model: jev-latest
confidence_threshold: 0.60

states:
  intake:
    description: New item received
  processing:
    description: Active handling
  done:
    terminal: true

transitions:
  intake:
    to: [processing, done]
    instructions: Should we process this or skip?
    guard: This item passes basic validation
  processing:
    to: [done]
```

## QA Results
| Test | Result |
|---|---|
| Config validation | ✓ |
| State graph viz | ✓ |
| Recon → scanning (strong signal) | ✓ confidence=0.99 |
| Recon → done (no findings, low confidence) | ✓ paused at 0.34 |
| Scan → exploit (vulns found) | ✓ confidence=0.61 |
| Terminal state raises FSMError | ✓ |
| Billing ticket → billing team (confidence=1.00) | ✓ |
| Full pentest run with guard block | ✓ guard stopped unauthorized exploit |

## Key Behaviors
- `step()` always returns — never blocks, caller decides on low confidence
- Guard (Noul) can block transitions regardless of confidence — authorization gates
- Full probability distribution stored every step — complete audit trail
- `run()` with `on_pause` callback for human-in-the-loop
- YAML first — share workflows without code

## Ship targets (next)
- [ ] Web UI — visual state graph, live step-through with context input
- [ ] jev-soc — SOC alert triage built ON TOP of jev-fsm
- [ ] GitHub Action integration

## Files
```
jev-fsm/
├── jevfsm/
│   ├── __init__.py
│   ├── core.py      JevFSM, State, Transition, StepResult, AuditTrail
│   ├── config.py    from_dict(), load_yaml()
│   └── cli.py       validate / viz / step / run
├── examples/
│   ├── pentest.yaml
│   └── support-escalation.yaml
└── pyproject.toml
```
