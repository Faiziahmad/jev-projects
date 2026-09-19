# Jev Project Ideas

TypeSafe Jev — System One model. Typed decisions, calibrated probabilities, no hallucinations.
API: POST https://api.typesafe.ai/v1/systemone | Model: jev-latest | $0.042/M input tokens, output free
SDK: pip install typesafe-sdk

---

## Queue (build in order)

### 1. jeval — LLM Output Evaluator [DONE ✓]
Replace LLM-as-judge with Jev. 100x cheaper, no self-serving bias.
- Input: prompt + LLM_response + rubric
- Output: calibrated scores per criterion (relevance, completeness, safety, tone, instruction-follow)
- CLI tool + promptfoo/braintrust adapter
- Constraint: factual accuracy needs ground truth in state
- Scope: ~200 lines Python, weekend build

### 2. agentd — AI Agent Runtime Kernel [ ]
Control plane for any LLM agent. Jev handles all control decisions, LLM handles generation only.
- Every tool call → Jev: allow/deny/ask_human
- Every LLM output → Jev: quality score / on-task / loop detected
- Every step → Jev: which model tier? (haiku/sonnet/opus)
- Works with Claude Code, AutoGPT, any framework
- Cost: $0.01/day to govern a 24/7 agent

### 3. jev-fsm — Probabilistic State Machine Runtime [DONE ✓]
States + transitions defined by you. Jev evaluates which transition fires.
- Returns probability distribution over valid next states
- Every transition auditable with calibrated confidence
- Use: compliance workflows, support escalation, agent lifecycle, insurance claims
- Replaces brittle if/else rule trees

### 4. jev-trace — Observability for Jev Decisions [ ]
Distributed tracing + analytics for all Jev calls across your stack.
- Log: state hash, questions, probabilities, action taken, outcome
- Dashboard: drift detection, question definition performance, threshold tuning
- Feedback loop: optimize question wording from real outcome data
- "Datadog for AI decisions"

### 5. jev-budget — LLM Model Router [ ]
Before every LLM call, Jev picks the cheapest model that can handle the task.
- Returns: {use: haiku, confidence: 0.84} vs sonnet vs opus
- Middleware for any LLM client
- Saves 60-80% LLM spend on easy tasks
- Self-funding: saves more than it costs

### 6. SOC Triage Engine [DONE ✓]
Real-time SIEM/IDS alert triage for security operations.
- Every alert → Jev: true_positive_probability / severity / asset_category / action
- Auto-close false positives, auto-page critical, route mid-confidence to L1
- $40/day to triage 1M alerts
- Replaces L1 analyst for boring triage work

### 7. jev-vote — Ensemble Decision System [ ]
High-stakes decisions: run same state through N differently-framed question sets.
- Aggregate probability distributions → consensus with uncertainty quantification
- If spread > threshold → HUMAN_REVIEW
- Use: medical triage, legal routing, financial risk gates

### 8. Browser Extension — Real-time Content Classifier [ ]
Jev classifies every page in background (JS → API, 70ms).
- News: credibility tier / manipulation score / source bias
- Job posting: ghosting risk / salary transparency
- Product: review authenticity / price fairness
- LinkedIn: hiring signal quality
- Privacy: Jev never stores content

### 9. jevops — Agentic Pentesting Control Plane [DONE ✓]
Jev as brain of recon/exploit pipeline.
- Every scan finding → Jev: critical / interesting / noise / already-known
- Routes to: which tool, wordlist, payload category
- Gates dangerous actions before execution
- Detects dead-end loops, redirects budget
- 10,000 routing decisions = $0.04

---

## Already Built (don't rebuild)
- toolgate — MCP/tool call gating
- swarmrouter — multi-agent task router
- jevegis — LLM guardrails (prompt injection, PII)
- trustgate — content moderation
- spendbrake — basic budget control
- jev-review — PR review gate
- RAG reranking — document relevance scoring
- heist-one, typesafe-chess, typesafe-mario — games

---

## Notes
- Question types: Choice (up to 255 options), Score (ordered levels), Noul (yes/no probability)
- Parallel questions in one call = same latency for 1 or 20 questions
- RLCD training = calibrated probabilities, not RLHF
