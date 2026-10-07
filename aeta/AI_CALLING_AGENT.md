# AETA — AI Calling Agent Only (single-agent scope)

Scoped-down option: deliver **only the AI calling agent** (Phase 3 of [BLUEPRINT.md](./BLUEPRINT.md)) for one client. Meta lead form → AI call within 60 s → qualify → book site visit → hand off to a human. No WhatsApp ingestion (Phase 1), no ad automation (Phase 2), no negotiation engine (Phase 4).

> Estimates as of Oct 2026, $1 ≈ ₹88. Same day rates and unit costs as [PROJECT_PLAN.md](./PROJECT_PLAN.md). Confirm vendor rates (Exotel, Sarvam, Bolna, WhatsApp) before quoting.

## What is included

| Included | Not included |
|---|---|
| Meta Lead Ads webhook → instant AI call | Broker/developer outreach & WhatsApp data extraction |
| Hindi / English / Hinglish voice agent answering from the property database | AI ad creatives and campaign publishing |
| Qualification: intent, budget, timeline, financing, location | Price negotiation engine, payment links |
| Retry ladder, DND/consent check, spend caps | |
| Site-visit booking on the agent's calendar + WhatsApp reminders | |
| Warm transfer / summary handoff to the human agent | |
| Dashboard: leads, calls, recordings, transcripts, scores | |
| Property data via admin form + CSV upload | |

## Build: step-by-step cost (8 weeks)

#### S0 — Discovery & design

| # | Step | Lead | Backend | Frontend | QA/DevOps | Person-days | Cost |
|---|---|---|---|---|---|---|---|
| 0.1 | Requirement workshop: call script, qualification rules, KPIs | 3 |  |  |  | 3 | ₹36,000 |
| 0.2 | Architecture, data model, API contracts | 2 | 1 |  |  | 3 | ₹31,000 |
| 0.3 | Conversation design: Hindi/English/Hinglish script, objection bank | 2 | 2 |  |  | 4 | ₹38,000 |
| 0.4 | Dashboard wireframes |  |  | 2 |  | 2 | ₹12,000 |
| 0.5 | Consent text + compliance checklist | 1 |  |  |  | 1 | ₹12,000 |
| 0.6 | Cloud accounts, CI/CD, staging/prod |  |  |  | 3 | 3 | ₹18,000 |
| | **Stage total** | | | | | **16** | **₹1,47,000** |

#### S1 — Accounts & approvals (parallel)

| # | Step | Lead | Backend | Frontend | QA/DevOps | Person-days | Cost |
|---|---|---|---|---|---|---|---|
| 1.1 | Meta app review (leads_retrieval only) | 2 |  |  |  | 2 | ₹24,000 |
| 1.2 | WhatsApp account + reminder templates |  | 1 |  |  | 1 | ₹7,000 |
| 1.3 | Telephony account, KYC, 160-series number |  | 1 |  |  | 1 | ₹7,000 |
| | **Stage total** | | | | | **4** | **₹38,000** |

#### S2 — AI calling agent build

| # | Step | Lead | Backend | Frontend | QA/DevOps | Person-days | Cost |
|---|---|---|---|---|---|---|---|
| 2.1 | Meta leadgen webhook, HMAC verify, dedupe, lead store |  | 4 |  |  | 4 | ₹28,000 |
| 2.2 | Lead form with consent checkbox | 1 |  |  |  | 1 | ₹12,000 |
| 2.3 | Dialer: queue, retry ladder, DND/consent check, spend caps |  | 5 |  |  | 5 | ₹35,000 |
| 2.4 | Voice pipeline + STT/TTS benchmarking on Hinglish | 8 | 4 |  |  | 12 | ₹1,24,000 |
| 2.5 | Agent tools: property facts, search, update lead, book visit | 3 | 3 |  |  | 6 | ₹57,000 |
| 2.6 | Post-call summary, BANT extraction, lead scoring | 2 |  |  |  | 2 | ₹24,000 |
| 2.7 | Calendar booking + WhatsApp reminders |  | 3 |  |  | 3 | ₹21,000 |
| 2.8 | Property data entry: admin form + CSV upload (replaces Phase 1) |  | 2 | 3 |  | 5 | ₹32,000 |
| 2.9 | Dashboard: leads, calls, recordings, transcripts |  |  | 10 |  | 10 | ₹60,000 |
| 2.10 | QA: 200+ test calls, latency tests, UAT with 50 live leads |  |  |  | 5 | 5 | ₹30,000 |
| | **Stage total** | | | | | **53** | **₹4,23,000** |

#### S3 — Hardening & launch

| # | Step | Lead | Backend | Frontend | QA/DevOps | Person-days | Cost |
|---|---|---|---|---|---|---|---|
| 3.1 | Security review (webhooks, toll fraud, PII) | 2 |  |  |  | 2 | ₹24,000 |
| 3.2 | Load test |  | 1 |  | 2 | 3 | ₹19,000 |
| 3.3 | Monitoring, alerting, runbook |  |  |  | 2 | 2 | ₹12,000 |
| 3.4 | Voice tuning on real transcripts | 4 |  |  |  | 4 | ₹48,000 |
| 3.5 | Go-live + 1 week hypercare | 1 | 1 | 1 | 1 | 4 | ₹31,000 |
| | **Stage total** | | | | | **15** | **₹1,34,000** |

### Build cost summary

| Item | Low | High |
|---|---|---|
| Direct engineering (88 person-days) | ₹7,42,000 | ₹7,42,000 |
| PM, code review, bug-fix buffer (30%) | ₹2,22,600 | ₹2,22,600 |
| Infra, API credits, test calls | ₹40,000 | ₹75,000 |
| Telephony setup (KYC, 160-series number, deposit) | ₹10,000 | ₹30,000 |
| WhatsApp account / templates | ₹0 | ₹15,000 |
| Legal: consent text, privacy policy | ₹30,000 | ₹75,000 |
| Contingency (~10%) | ₹1,00,000 | ₹1,20,000 |
| **Total** | **≈ ₹11.4 lakh** (~$13k) | **≈ ₹12.8 lakh** (~$14.5k) |

| Week | Stage |
|---|---|
| 1–2 | S0 Discovery & design · S1 approvals in parallel |
| 3–6 | S2 Build (two 2-week sprints) — gate: 50 live leads called |
| 7–8 | S3 Hardening, voice tuning, go-live |

**Lean variant — ≈ ₹3–5 lakh, 3–4 weeks:** managed voice platform (Bolna / Vapi) configured instead of a custom pipeline, a Google Sheet or the client's existing CRM instead of a custom dashboard, BSP dashboard for WhatsApp reminders. Less control over voice quality and higher per-minute cost.

## Monthly running cost (one AI agent)

Assumes ~1,000 leads/month, ≈ 3.4 billable minutes per lead (≈ 3,400 min), managed voice at ₹5/min.

| Component | Monthly |
|---|---|
| Voice — telephony | ₹2,700 |
| Voice — speech-to-text | ₹1,700 |
| Voice — LLM turns (Claude Haiku 4.5) | ₹2,000 |
| Voice — text-to-speech | ₹2,700 |
| Voice — platform fee | ₹7,900 |
| *Voice subtotal* | *₹17,000* |
| WhatsApp visit reminders | ₹2,500 |
| LLM post-call summaries (Claude Sonnet 5.5) | ₹2,000 |
| Cloud (small compute, Postgres, storage for recordings) | ₹6,000 |
| SaaS (number rental, monitoring, domain) | ₹5,000 |
| **Platform cost** | **₹32,500** |
| Maintenance retainer (part-time dev, ~4 days/month) | ₹25,000 |
| **Total / month** | **≈ ₹57,500** (~$650) |

Usage scales linearly: every extra 1,000 leads adds ≈ ₹20,000 (voice + WhatsApp + LLM). Self-hosted voice (₹2.7/min) cuts the voice line from ₹17,000 to ≈ ₹9,200.

## Capacity of "1 agent"

An AI agent is billed per minute, not per seat — "1 agent" means **1 concurrent call line**.

| | One concurrent line |
|---|---|
| Calling window (9 am – 9 pm) | 720 line-minutes/day |
| Usable at ~60% utilisation | ≈ 430 min/day ≈ 13,000 min/month |
| Leads it can handle | ≈ 3,500/month |
| Risk | Leads that arrive together queue up and miss the 60-second call target |

**Recommendation:** configure **2–3 concurrent lines** for the same price. Per-minute cost does not change; only number rental adds ~₹1,000–2,000/month. That keeps the 60-second response even during ad-spike hours.

## Comparison with a human telecaller

| | Human telecaller | AI calling agent |
|---|---|---|
| Monthly cost | ₹28,000–35,000 (salary ₹18–25k + seat, phone, PF) | ≈ ₹57,500 incl. maintenance (≈ ₹32,500 platform only) |
| Calls per day | 100–120 dials, office hours | Limited only by line count and calling window |
| Speed to lead | Minutes to hours | < 60 seconds, every lead |
| Consistency | Varies by person and mood | Same script and qualification every call; full transcript + recording |
| Attrition / training | High churn, re-training | None |

At ~1,000 leads/month the AI costs about the same as 1.5–2 telecallers, but responds instantly and records every conversation. Above ~2,000 leads/month it becomes clearly cheaper than the 3–4 people needed for the same volume.

## Suggested pricing to the client

| Model | Price | Notes |
|---|---|---|
| One-time custom build | ₹14–16 lakh setup + ₹60–75k/month | Cost + ~25–35% margin; client owns the deployment |
| Productised / SaaS (reuse across clients) | ₹1.5–2.5 lakh setup + ₹40–60k/month platform fee + ₹7–8 per call-minute | Build once, sell many; margin comes from usage and platform fee |

The SaaS model makes sense if you plan to sell this to more than one builder or broker. The ₹11–13 lakh build cost is recovered after about 4–6 clients.
