# WhatsApp AI Receptionist for Dental Clinics (n8n template)

A deployable n8n workflow that answers a dental clinic's WhatsApp 24/7. It answers FAQs,
books, reschedules and cancels appointments in Google Calendar, logs every conversation
to Google Sheets, hands chats to a human when needed, and sends 24h reminders with
one-tap confirmation.

Built for resale as a **$500 setup + $50/month** service (see `docs/pricing.md`).

## What's in here

| Path | What |
|---|---|
| `workflows/whatsapp_receptionist.json` | Importable n8n workflow (tested on n8n 2.40.7) |
| `prompts/system_prompt.md` | Receptionist and classifier prompts with guardrails |
| `prompts/faq_seed.md` | 20 dental FAQs to customize per clinic |
| `docs/setup_guide.md` | Docker install, Twilio, Google OAuth, testing and go-live checklists |
| `docs/demo_script.md` | 2-minute portfolio/demo video script |
| `docs/pricing.md` | Packaging, inclusions, add-ons, client intake form |
| `docker-compose.yml`, `Caddyfile`, `.env.example` | n8n + Postgres + automatic HTTPS |
| `scripts/build_workflow.py` | Regenerates the workflow JSON from the prompt files (per-clinic builds) |
| `scripts/send_test_message.py` | Sends signed fake Twilio webhooks for testing without a phone |

## How it works

```
Twilio webhook ─> Ack (empty TwiML) ─> Clinic Profile ─> Verify & Normalize (signature, rate limit)
   ├─ staff number ──────> Handle Staff Command (#reply / #resume / #pause / #status)
   ├─ chat paused ───────> Forward to Staff (no AI call)
   ├─ STOP/START/media ──> Canned Reply (+ Opt-outs tab)
   └─ patient ─> Classify Intent (Claude Haiku, JSON) ─> Route by Intent
                   ├─ faq ─────────────> FAQ Agent
                   ├─ booking/reschedule/confirm ─> Get Upcoming Events ─> Prepare Booking Context
                   │                        ├─ confirm ─> Mark ✅ in calendar
                   │                        └─ Booking Agent + create/reschedule/cancel tools
                   └─ handoff/emergency/low confidence ─> Start Handoff (pause + alert staff)
Every Hour ─> Get Appointments in 24h ─> Get Opt-outs ─> Build Reminders ─> stamp "Reminder sent"
All replies ─> Outbox ─> Send WhatsApp (Twilio API) + Log Lead to Sheet
```

### Guardrails enforced in code (not just the prompt)

- The booking tools take a **slot code** that is looked up in freshly computed free slots,
  so the AI can't double-book or invent a time.
- Reschedule and cancel can only target appointments carrying **the sender's own**
  WhatsApp number.
- The patient's phone number comes from Twilio, never from the model.
- A paused (handed-off) chat never reaches the AI.
- Twilio request signatures are verified; a per-number rate limit caps AI spend.

## Quick start

```bash
cp .env.example .env && nano .env
docker compose up -d
```

Then follow `docs/setup_guide.md` from step 2.

## Rebuilding the workflow for a client

```bash
python3 scripts/build_workflow.py --faq clients/acme/faq.md --out clients/acme/workflow.json
```

Clinic settings (hours, services, messages) are in the `PROFILE` dict at the top of the
script, and in the **Clinic Profile** node once imported.
