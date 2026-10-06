# AETA — Autonomous End-to-End Real Estate Transaction Agent

Blueprint for an Indian real estate client: compliance checklist, technical architecture, build cost, monthly running cost and timeline.

Step-by-step work breakdown, stack pricing and per-component running cost: see [PROJECT_PLAN.md](./PROJECT_PLAN.md).

> All prices are estimates (Oct 2026, ₹1 ≈ $0.0114 / $1 ≈ ₹88). Verify vendor pricing before quoting a client — WhatsApp, telephony and voice-AI rates change often.

---

## 1. Compliance checklist (India)

| Area | Law / Rule | Applies to |
|---|---|---|
| Data privacy | **DPDP Act 2023 + DPDP Rules 2025** (phased rollout) | Consent notice, purpose limitation, erasure, breach reporting, consent records |
| Telemarketing | **TRAI TCCCPR 2018** + amendments | DND scrubbing; promotional calls from **140-series**, service/transactional from **160-series**; unregistered 10-digit telemarketing → disconnection |
| SMS | **DLT registration** | Headers + templates (only if SMS is used) |
| Real estate ads | **RERA Act 2016** + state rules | RERA project number on every ad (MahaRERA: QR code too); **agent RERA registration** per operating state |
| Advertising | **Consumer Protection Act 2019**, CCPA Misleading Ads Guidelines 2022, Dark Patterns Guidelines 2023 | Ad copy, AI visuals, no fake urgency/scarcity |
| Ad standards | **ASCI Code** (incl. real-estate guidelines) | Price claims, disclaimers |
| IT | **IT Act 2000 / IT Rules 2021** | Platform obligations, reasonable security practices |
| AML | **PMLA 2002** | Real estate agents are reporting entities — buyer KYC above threshold |
| NRI buyers | **FEMA** | Foreign/NRI purchases and remittances |
| Platforms | **Meta Advertising Policies** (lead ads, housing), **WhatsApp Business & Commerce Policy** | Ad approval, 24h messaging window, opt-in, template approval |

---

## 2. Architecture

```
                 ┌────────────── ORCHESTRATOR (event-driven) ──────────────┐
                 │  FastAPI/Node API  +  Queue (Redis/BullMQ or Celery)    │
                 │  Workflow state machine per Supplier / Property / Lead  │
                 └───┬────────────┬──────────────┬───────────────┬─────────┘
                     │            │              │               │
   PHASE 1           │  PHASE 2   │   PHASE 3    │    PHASE 4    │
 ┌──────────────┐ ┌──▼─────────┐ ┌▼────────────┐ ┌▼─────────────┐
 │ WhatsApp     │ │ Creative   │ │ Meta leadgen│ │ Negotiation  │
 │ Cloud API    │ │ generator  │ │ webhook     │ │ engine       │
 │ (webhook in) │ │ + Meta     │ │ → dialer    │ │ (rules, not  │
 │ → extractor  │ │ Marketing  │ │ → Voice AI  │ │  LLM) + Cal  │
 │ (LLM vision) │ │ API        │ │             │ │ + handoff    │
 └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ └──────┬───────┘
        └───────────────┴────── Postgres + pgvector ─────┘
                         S3/R2 (media) · Admin dashboard
```

### Phase 1 — Supplier ingestion

- **Channel:** WhatsApp Cloud API (direct) or a BSP (Gupshup / Interakt / AiSensy) for easier template management.
- **Pipeline:** webhook → download media (`media_id`) → S3 → classify (PDF / image / floor plan / rate sheet / link) → extract:
  - PDF: `pdfplumber` text layer + page images → vision LLM
  - Images/scans: vision LLM (handles Hindi/English brochures)
  - Links: Playwright fetch → extraction
- → Pydantic/Zod schema validation → CRM upsert with `status = pending_review` (human approves before going live).

```json
{
  "project_name": "", "developer": "", "rera_no": "",
  "location": {"city": "", "locality": "", "lat": null, "lng": null},
  "configurations": [{"type": "3BHK", "carpet_sqft": 0, "price_min": 0, "price_max": 0}],
  "price_per_sqft": 0, "amenities": [], "possession_date": "",
  "commission_pct": 0, "payment_plan": "",
  "source_refs": [{"field": "price_min", "file": "s3://...", "page": 3}],
  "missing_fields": []
}
```

- `source_refs` enforces **strict factuality**: the voice agent only states fields that have a source.
- `missing_fields` drives the 24h follow-up cron (WhatsApp template, max 3 nudges).
- Normalise Lakh/Crore notation to INR integers.
- Models: a strong vision model for extraction, a small fast model for classification/routing.

### Phase 2 — Creatives and Meta ads

- **Copy:** LLM generates ~5 headlines × 5 primary texts × 3 descriptions per property, in English / Hinglish / Hindi. Generated only from the DB record; a fact-check pass diffs every number against the DB.
- **Visuals:** use the developer's real renders + templated overlays (price-from, locality, RERA no., CTA) via Templated / Bannerbear / own Sharp or Pillow engine. AI only for backgrounds and layout variants — never fake the building.
- **Meta Marketing API:**

```
Campaign (objective=OUTCOME_LEADS)
 └─ AdSet (geo radius, placements, budget, optimization_goal=LEAD_GENERATION)
     └─ Ad (creative + lead_gen_form_id)
LeadGen Form: name, phone (prefill), budget, timeline, location,
              + custom consent checkbox + privacy policy URL
```

- Prerequisites: Business verification, System User token, app review for `ads_management`, `leads_retrieval`, `pages_manage_ads` (1–3 weeks).
- Nightly insights pull (CPL, CTR) → pause losers, generate new variants.

### Phase 3 — Lead → AI call in under 60 s

```
Meta leadgen webhook (verify X-Hub-Signature-256)
 → GET /{leadgen_id} → normalise +91 phone, dedupe, DND/consent check
 → priority call job → telephony API originates call
 → audio stream (WebSocket) ↔ voice agent pipeline
 → post-call: transcript, extracted fields, score → CRM → next action
```

| Layer | India-friendly options |
|---|---|
| Telephony | **Exotel**, Plivo, Ozonetel, Knowlarity (Twilio has limited Indian outbound) |
| Voice platform (fast path) | **Bolna** (Exotel-native), Vapi, Retell + SIP |
| Voice framework (custom) | Pipecat, LiveKit Agents |
| STT | **Sarvam Saarika**, Deepgram Nova-3 (Hindi / multilingual), Google Chirp — must handle Hinglish |
| LLM | Fast tool-calling model per turn; stronger model for summaries |
| TTS | **Sarvam Bulbul**, ElevenLabs Flash, Cartesia |

**Latency budget (< 1 s per turn):** VAD end-of-speech ~200 ms + STT ~150 ms + LLM first token ~300 ms + TTS first audio ~150 ms + network ~100 ms. Stream everything, speak on first sentence, support barge-in.

**Agent tools:**

```
get_property_facts(property_id, fields[])   # source-backed DB values only
search_properties(budget, location, config) # pgvector + SQL filters
update_lead(intent, budget, timeline, financing, objections[])
book_visit(lead_id, slot)                   # Google Calendar / Cal.com
evaluate_offer(property_id, amount)         # Phase 4
transfer_to_human(reason)                   # SIP REFER / warm transfer
```

- Post-call: LLM → structured BANT + score 0–100 + next action.
- No answer: retry ladder +10 min → +2 h → next day → WhatsApp template.

### Phase 4 — Negotiation and closing

**The LLM never sees floor price.** It only calls `evaluate_offer`:

```python
def evaluate_offer(property_id, offer):
    p = pricing[property_id]                 # floor, target, step, max_rounds
    if offer >= p.target:
        return {"decision": "accept"}
    if offer < p.floor:
        return {"decision": "counter", "amount": next_counter(p, offer)}
    if current_round(property_id) >= p.max_rounds:
        return {"decision": "escalate_human"}
    return {"decision": "counter", "amount": concession_curve(p, offer)}
```

- Deterministic, auditable, injection-proof. Non-price levers (payment plan, parking, floor rise, PLC waiver) are configured per project.
- **Token / EOI:** Razorpay or Cashfree payment link on WhatsApp → payment webhook → CRM.
- **Site visit:** calendar booking + WhatsApp reminder template.
- **Handoff:** auto-generated deal brief PDF (buyer profile, negotiation log, objections, agreed terms, transcript link) → human agent via WhatsApp/CRM, or live warm transfer.

### Data model

```
suppliers(id, name, phone, type, status, last_followup_at)
properties(id, supplier_id, data jsonb, embedding vector, status, verified_by)
media(id, property_id, s3_key, kind, page)
campaigns(id, property_id, meta_campaign_id, metrics jsonb)
leads(id, campaign_id, meta_lead_id, phone, consent_ts, consent_text, score, stage)
calls(id, lead_id, provider_call_id, recording_key, transcript, summary jsonb)
negotiations(id, lead_id, property_id, round, offer, decision, ts)
appointments(id, lead_id, slot, calendar_event_id)
```

### Security hardening

| Surface | Control |
|---|---|
| Broker PDFs/messages (indirect prompt injection) | Schema-only extraction; untrusted text never enters voice-agent system prompt; human review gate |
| Caller social engineering | Floor price not in LLM context |
| Meta / WhatsApp webhooks | HMAC signature verification, replay window, idempotency on `leadgen_id` / message id |
| Lead-form abuse (dialer as harassment tool) | Phone validation, per-number/per-IP rate limits, max calls/day |
| Telephony toll fraud | +91-only allowlist, daily spend caps |
| PII | Encryption at rest, signed URLs for recordings, retention policy, audit log |

---

## 3. Build timeline

| Milestone | Duration | Notes |
|---|---|---|
| Setup & approvals (parallel) | 1–3 weeks | Meta business verification + app review, WABA + templates, 140/160 series numbers, RERA agent registration |
| **MVP — Phase 3** (webhook → AI call → qualify → book visit) | 4 weeks | First revenue-generating piece |
| Phase 1 — WhatsApp ingestion + review dashboard | 3 weeks | |
| Phase 2 — creatives + campaign automation | 3–4 weeks | |
| Phase 4 — negotiation engine, payments, handoff | 2–3 weeks | |
| Hardening, QA, load test, Hindi/Hinglish voice tuning | 2 weeks | Tuning continues after launch |
| **Total** | **~14–16 weeks (3.5–4 months)** with a team of 3 | |
| Lean path | ~10–12 weeks | Managed platforms (Bolna/Vapi, BSP, n8n for glue); less control, higher per-minute cost |

---

## 4. Making cost (one-time)

### Team (India rates)

| Role | Monthly | 4 months |
|---|---|---|
| Tech lead / backend + AI (senior) | ₹2,00,000 | ₹8,00,000 |
| Backend / voice-telephony dev | ₹1,20,000 | ₹4,80,000 |
| Frontend dev (dashboard) | ₹1,00,000 | ₹4,00,000 |
| QA + DevOps (part-time) | ₹60,000 | ₹2,40,000 |
| **Team subtotal** | **₹4,80,000** | **₹19,20,000** |

### Other one-time

| Item | Cost |
|---|---|
| Dev/staging infra, API credits, test calls & voice evals | ₹75,000 – ₹1,50,000 |
| WhatsApp BSP onboarding, number setup, templates | ₹0 – ₹25,000 |
| Telephony setup (140/160 series, deposits) | ₹10,000 – ₹50,000 |
| RERA agent registration (per state, company) | ₹25,000 – ₹1,00,000 |
| Legal: privacy policy, consent text, DPDP review | ₹50,000 – ₹1,50,000 |
| Security pentest before go-live (in-house: ₹0) | ₹0 – ₹1,50,000 |
| Contingency (~10%) | ₹2,00,000 |

### Total build cost

| Option | Cost | Time |
|---|---|---|
| **Lean** — 2 devs + managed platforms | **₹8 – 12 lakh** (~$9–14k) | 10–12 weeks |
| **Standard** — in-house team of 3–4 (above) | **₹23 – 28 lakh** (~$26–32k) | 14–16 weeks |
| **Agency / outsourced** | **₹30 – 50 lakh** (~$34–57k) | 12–20 weeks |

---

## 5. Running cost (per month)

### Unit costs used

| Item | Unit cost |
|---|---|
| AI voice all-in (telephony + STT + LLM + TTS) | ~₹5 / min (range ₹3–8) |
| WhatsApp marketing template | ~₹0.80–0.90 / msg |
| WhatsApp utility template | ~₹0.12–0.15 / msg |
| WhatsApp replies inside 24h user window | free |
| LLM extraction per property | ~₹20–50 |
| Payment gateway (token amounts) | ~2% per transaction |

Call model per lead: ~1.8 dial attempts, ~60% connect, ~4 min per connected call, plus a ~5 min follow-up/negotiation call for ~15% of leads.

### Scenarios (excluding Meta ad spend)

| Cost head | Small — 1,000 leads/mo | Medium — 5,000 leads/mo | Large — 20,000 leads/mo |
|---|---|---|---|
| AI voice calls | ₹17,000 | ₹85,000 | ₹3,40,000 |
| WhatsApp (leads + suppliers) | ₹5,000 | ₹20,000 | ₹80,000 |
| LLM (extraction, copy, summaries) | ₹5,000 | ₹15,000 | ₹50,000 |
| Cloud infra (AWS/GCP Mumbai, DB, storage, recordings) | ₹12,000 | ₹30,000 | ₹80,000 |
| SaaS (BSP plan, telephony rental, creative engine, monitoring) | ₹10,000 | ₹20,000 | ₹40,000 |
| Maintenance / on-call dev | ₹60,000 | ₹1,00,000 | ₹2,00,000 |
| **Total / month** | **≈ ₹1.1 lakh** (~$1.25k) | **≈ ₹2.7 lakh** (~$3.1k) | **≈ ₹7.9 lakh** (~$9k) |
| **Cost per lead (ex-ads)** | ~₹110 | ~₹54 | ~₹40 |

### Meta ad spend (client budget, separate)

Indian real estate CPL is typically ₹150–600 (luxury: ₹500–1,500+).

| Scenario | Ad spend at ~₹400 CPL |
|---|---|
| 1,000 leads | ~₹4 lakh |
| 5,000 leads | ~₹20 lakh |
| 20,000 leads | ~₹80 lakh |

Ad spend dominates the budget — the AI system itself is typically **5–25%** of total monthly cost.

### Cost levers

- Self-hosting Pipecat/LiveKit + Sarvam STT/TTS instead of a managed voice platform cuts voice cost by ~30–50% at medium/large scale.
- Use utility templates and in-window free replies instead of marketing templates where policy allows.
- Prompt caching on the static system prompt and property facts reduces LLM cost.
- Store compressed (Opus) recordings with a retention policy to keep storage flat.
