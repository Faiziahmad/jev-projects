# Pricing and Packaging

**Offer:** WhatsApp AI Receptionist for dental clinics
**Price:** **$500 one-time setup + $50/month** care plan

Clinics understand this framing: *less than one missed new-patient booking a month.*
A single new patient is typically worth several hundred dollars in first-year revenue to
a dental practice, so the bot pays for itself if it catches one after-hours enquiry a month.

---

## What's included

### Setup: $500 (one-time)

Delivered in **5–7 business days** from receiving the intake form and account access.

| Included | Details |
|---|---|
| Discovery call (30 min) | Hours, services, booking rules, handoff contacts, tone |
| FAQ build | Up to **25 FAQs** written with the clinic from the seed list, reviewed and approved by them |
| Receptionist configuration | Clinic profile, opening hours, services, appointment length, cancellation policy, emergency wording |
| Google Calendar integration | Connected to **one** existing appointment calendar; live free-slot booking, reschedule and cancel |
| Lead log | Google Sheet with every conversation logged (Leads + Opt-outs tabs) |
| Human handoff | Staff alerts on WhatsApp plus reply/resume commands; staff walkthrough |
| 24h reminders | Reminder with one-tap YES confirmation (✅ marked in the calendar) |
| WhatsApp number go-live | Twilio sender registration support and the reminder template submitted for Meta approval |
| Hosting setup | Private n8n instance on the clinic's (or your) server, HTTPS, backups enabled |
| Testing | Full 19-point test script run on the live number |
| Handover | 30-min training call for front desk + 1-page cheat sheet |
| 14-day hypercare | Prompt/FAQ tweaks and fixes during the first two weeks, no extra charge |

### Care plan: $50/month

| Included | Details |
|---|---|
| Monitoring | Weekly check of executions, errors and delivery failures; fixes applied |
| Content updates | Up to **5 FAQ/price/hours changes per month** (reply within 2 business days) |
| Holiday and schedule changes | Closures and seasonal hours kept up to date |
| Platform maintenance | n8n security updates tested on a staging copy before rollout; credential renewals |
| Monthly report | Messages handled, bookings, reschedules, cancellations, handoffs, confirmation rate (from the Leads sheet) |
| Prompt tuning | Review of 20 random conversations a month; wording improved where the bot was unclear |
| Support | Email/WhatsApp support, business hours, next-business-day response |

Minimum term: **3 months**, then month-to-month with 30 days' notice. Clinics can cancel
any time after that and keep their sheet and calendar data. The workflow export is
handed over on request.

---

## Usage costs (paid by the clinic, billed directly)

Keep these on the clinic's own accounts. It keeps your margin clean and avoids you being
the billing middleman.

| Service | Typical monthly cost for one clinic* | Notes |
|---|---|---|
| Anthropic API (Claude Haiku 4.5) | **$2–8** | ≈ $0.003–0.006 per patient message |
| Twilio + Meta WhatsApp fees | **$10–40** | Depends on country, volume and template usage; check Twilio's WhatsApp pricing page |
| Server (VPS) | **$6–12** | One small VPS per clinic; can be your server if you bundle hosting |
| Google Workspace / Calendar / Sheets | $0 | Uses their existing account |

\*Assumes roughly 500–1,500 patient messages a month. Estimates, not quotes: confirm
current prices before sending a proposal.

**Alternative: all-inclusive $89/month.** You pay usage and hosting and bill a flat fee.
Only offer this once you know a clinic's volume, and cap it (for example, up to 2,000
messages a month).

---

## Add-ons (quote separately)

| Add-on | Price guide |
|---|---|
| Extra calendar / dentist / chair (per calendar) | $150 setup + $15/mo |
| Second language fully localized (FAQ + messages) | $150 |
| Extra FAQ block (+25 questions) | $100 |
| Staff alert template (alerts outside the 24h window) | $50 |
| Instagram DM / website chat widget using the same brain | from $300 |
| Practice-management integration (Dentrix, Open Dental, Dentally…) | custom quote, from $800 |
| Monthly review requests (post-visit Google review ask) | $150 setup + $20/mo |
| Additional change requests beyond 5/month | $40 each or $60/hour |

---

## Not included

- Medical or dental content decisions (the clinic approves all FAQ answers)
- Legal or compliance advice (HIPAA/GDPR); the clinic is responsible for BAAs/DPAs with vendors
- Meta Business verification delays, or rejection of the clinic's display name
- Usage fees (Twilio, Meta, Anthropic, hosting) unless on the all-inclusive plan
- Changes to how patients are triaged clinically (emergency wording is agreed at setup)

---

## Positioning and sales notes

- **Lead with outcomes:** "answers every WhatsApp in seconds, 24/7", "books straight into
  your calendar", "hands tricky chats to your team", "cuts no-shows with confirmations".
- **Handle the main objection, "Will it say something wrong?":** it only answers from
  their approved FAQ, never gives medical advice, always reads back bookings before
  confirming, and hands over to a human when unsure. Show the test script.
- **Proof:** the 2-minute demo video (`docs/demo_script.md`) plus a live demo on the
  sandbox from your phone during the call.
- **Pilot option** for hesitant clinics: $250 setup, a 30-day pilot on the care plan,
  and the remaining $250 due if they keep it.
- **Upsell path:** month 2 → reminders and reviews; month 3 → second calendar or
  Instagram.

---

## Client intake form (send after they sign)

1. Clinic legal name and the display name on WhatsApp
2. Address, main phone number, website
3. Opening hours per weekday, lunch breaks, and holidays for the next 3 months
4. Services the bot may book, and the default appointment length
5. Services the bot should **not** book (always hand to staff)
6. Prices you're happy to share publicly, and insurance plans accepted
7. Cancellation policy wording
8. Emergency instructions (clinic phone, after-hours line, local emergency number)
9. Staff member(s) for handoff alerts: name and WhatsApp number
10. Google account that owns the appointment calendar (and who can grant access)
11. Phone number to register for WhatsApp (not currently on the WhatsApp app), and Meta
    Business Manager access
12. Languages patients commonly use
13. Anything the bot must never say
