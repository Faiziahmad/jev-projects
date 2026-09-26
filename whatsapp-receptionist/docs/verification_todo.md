# Verification TODO

The workflow was built against the n8n 2.40 node source and tested end to end on
n8n 2.40.7 (npm install), with **mocked** Anthropic, Twilio, Google Calendar and Google
Sheets APIs behind a local intercepting proxy. Every path passed in that setup: FAQ,
booking, reschedule, cancel, handoff and staff commands, emergency, low confidence,
opt-out, media, reminders with YES confirmation, and signature rejection.

The items below could **not** be checked without real accounts. Tick them off before
the first client goes live.

## Must verify

- [ ] **Real Twilio signature.** The Code node follows Twilio's documented algorithm
      (URL + sorted POST params, HMAC-SHA1, base64), but it was only tested against
      `scripts/send_test_message.py`, which uses the same algorithm. Send one real
      sandbox message. If execution stops at *Verify & Normalize* with no output,
      `TWILIO_WEBHOOK_URL` doesn't match the console URL exactly (scheme, host, path,
      trailing slash).
- [ ] **Inbound payload fields.** The workflow reads `From`, `Body`, `ProfileName`,
      `NumMedia` and `MessageSid`. Confirm a real sandbox execution has them under
      `$json.body` in the *Twilio Webhook* node.
- [ ] **Reminder template path.** Set `TWILIO_REMINDER_CONTENT_SID` to an approved
      utility template and confirm Twilio accepts `ContentSid` +
      `ContentVariables` `{"1": name, "2": day, "3": time}`. This path wasn't exercised.
- [ ] **Free-text delivery outside the 24h window.** Check whether sandbox reminders
      and staff alerts arrive when the recipient hasn't messaged in the last 24h
      (Twilio error 63016 if not).
- [ ] **Real Claude (Haiku 4.5) behaviour.** The mock returned scripted replies. Check:
  - [ ] the classifier returns clean JSON (no prose around it)
  - [ ] the booking agent copies slot codes exactly (`YYYY-MM-DDTHH:mm`)
  - [ ] it reads the booking back and waits for a clear "yes" before calling a tool
        (run test 5 in the setup guide several times)
  - [ ] it adds `[HANDOFF]` when it should, and only then
  - [ ] prompt-injection attempts are deflected
- [ ] **Real Google Calendar.**
  - [ ] An invented slot is rejected with a 400. The workflow sends `Invalid date`;
        the mock rejected it, real Google is expected to.
  - [ ] All-day events block the whole day
  - [ ] The ✅ title update and the "Reminder sent" description update work
- [ ] **Real Google Sheets.** Appends land in `Leads` and `Opt-outs` with the headers
      from the setup guide (`useAppend` mode).
- [ ] **Google OAuth refresh.** Once the consent screen is published (not *Testing*),
      the credentials still work after 7+ days.
- [ ] **UI import.** Import the JSON through the n8n UI (tested via CLI only) and confirm
      each red node just needs its credential selected.
- [ ] **Docker image.** Run `docker compose up` with `n8nio/n8n:2.40.7` (tested with the
      npm package, not the image). Confirm the Code nodes can use `require('crypto')`
      and `$env`. If a future n8n version drops the internal task runner, move
      `NODE_FUNCTION_ALLOW_BUILTIN=crypto` to a separate runners container.

## Should confirm before quoting clients

- [ ] Twilio + Meta WhatsApp per-message fees for the clinic's country
- [ ] Anthropic prices (Haiku 4.5: $1 / $5 per MTok input/output at time of writing)
- [ ] Real per-message token usage: check a few executions and adjust the
      $0.003–0.006/message estimate in `setup_guide.md` and `pricing.md`
- [ ] Whether Anthropic prompt caching (option on the model nodes) saves anything. The
      prompts include the current time near the top and may be below Haiku's minimum
      cacheable length, so it's left off by default.

## Known limitations (by design, documented in the setup guide)

- Chat state (pause, context, rate-limit counters) uses workflow static data. Under bursts
  of simultaneous messages, writes can overwrite each other, so the rate limit is soft
  (≈2× the setting). Upgrade path: Redis or n8n Data Tables.
- Simple Memory is in-process and clears after 1h idle or a restart.
- One calendar, fixed-length slots; no practice-management software integration.
- Not HIPAA/GDPR-ready out of the box.
