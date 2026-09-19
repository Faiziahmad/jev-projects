# jeval

LLM output evaluator powered by TypeSafe Jev. Replaces LLM-as-judge with typed calibrated scores — 100x cheaper, no self-serving bias, no hallucinated verdicts.

## What it does
Takes a prompt + LLM response (+ optional ground truth) and returns scored dimensions:
- relevance, completeness, conciseness, on_task, safe, instruction_follow, accuracy, tone

## Status
Working. CLI ships. Weighted scoring done (presets: balanced / strict / safety / creative).

## Usage
```bash
pip install -e .
export TYPESAFE_API_KEY=...

jeval --prompt "..." --response "..."
jeval --prompt "..." --response "..." --preset strict
jeval --prompt "..." --response "..." --weights "completeness=3,safe=2"
jeval --prompt-file p.txt --response-file r.txt --json --ci
```

## Ship targets (next)
- [ ] VS Code extension — eval panel inside editor, highlight low-scoring responses inline
- [ ] Web app — paste prompt + response, see live scores, compare A vs B side by side
- [ ] GitHub Action — `uses: jeval-action@v1`, fails PR if eval drops below threshold
- [ ] promptfoo adapter — drop-in evaluator for existing eval pipelines
- [ ] Jupyter widget — for notebook-based eval workflows

## Files
```
jeval/
├── jeval/
│   ├── __init__.py
│   ├── core.py      evaluate(), EvalResult, presets, weights
│   └── cli.py       CLI entry point
└── pyproject.toml
```

## Key design decisions
- Score normalized 0–1 (Jev returns 0 to N-1, divide by N-1)
- Weighted overall: presets or per-key overrides via CLI
- Noul = raw probability, Score = normalized, Choice = string label
- `raw` field stores answer objects for downstream tooling
