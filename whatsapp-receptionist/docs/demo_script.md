# Demo Video Script: "The Receptionist That Never Sleeps" (2:00)

**Goal:** show a clinic owner, in two minutes, that the bot answers questions, books,
reschedules and knows when to hand over to a human, and that everything lands in their
calendar and spreadsheet.

**Audience:** dental clinic owners and practice managers. Not technical, and they care
about missed calls and front-desk workload.

---

## Setup before recording

- **Screen layout (1920×1080):** phone mirror on the left (about 40% width; use
  scrcpy for Android or QuickTime for iPhone). On the right, Google Calendar (week view)
  stacked over the Leads sheet. Keep n8n hidden until the 1:40 cutaway.
- **Two phones:** "Patient" (your phone, joined to the sandbox) and "Staff" (second phone
  on the table, notifications on, visible to camera or mirrored).
- **Pre-seed the calendar** with 3–4 realistic appointments so it doesn't look empty. Have
  one existing appointment for the patient phone on **Thursday 10:00**
  (`Jordan Lee – Check-up and cleaning`, description `WhatsApp: +<patient phone>`) so the
  reschedule has something to move.
- Clear the Leads sheet except the header row. Set the WhatsApp profile name to "Jordan".
- Rename the sandbox chat contact to **"Bright Smile Dental"** so the chat header looks
  real.
- Do a full dry run. AI replies vary slightly between runs, so record the phone once,
  then record the voiceover to match what actually appeared.
- Typing speed: paste messages from a notes app so there's no typo-fixing on camera.

---

## Script

| Time | Screen | Voiceover |
|---|---|---|
| **0:00–0:10** | Title card: *"Your front desk closes at 6. Your patients don't."* Then cut to the phone showing 9:47 PM. | "It's 9:47 on a Tuesday night. Your front desk went home hours ago, but patients are still reaching for their phones." |
| **0:10–0:30** | **FAQ.** Type: `Hi! Do you take Delta Dental, and how much is a cleaning?` Bot replies within a few seconds with in-network insurers and the cleaning prices, then "Would you like me to find you an appointment?" | "This is Bright Smile Dental's WhatsApp receptionist. It answers from the clinic's own FAQ, with real prices and real insurers, in seconds. It never guesses: if it doesn't know, it says so and offers a person." |
| **0:30–0:58** | **Booking.** Type: `Yes please, a cleaning next Monday morning`. Bot offers 3 Monday times. Type: `9:30 works. It's Jordan Lee`. Bot reads back *Jordan Lee, check-up and cleaning, Monday 28 Sep at 9:30. Shall I book this?* Type `Yes`. Bot: "You're booked ✅ …". **Cut right:** the new event appears in Google Calendar, and a `Booked` row appears in the sheet (highlight it). | "It only offers times that are actually free in your Google Calendar. And before it books anything, it reads the details back and waits for a clear yes, so there are no surprise bookings. There it is: in your calendar, and logged in your spreadsheet with the patient's number and status." |
| **0:58–1:18** | **Reschedule.** Type: `Actually, can I move my Thursday appointment to Friday afternoon?` Bot confirms which appointment and offers Friday slots. Type `2pm please`, then `Yes`. **Cut right:** the Thursday 10:00 event jumps to Friday 14:00; the sheet shows `Rescheduled`. | "Rescheduling works the same way. It finds the patient's own appointment, and only theirs, and moves it. No phone tag, no voicemail." |
| **1:18–1:40** | **Human handoff.** Type: `I was charged twice for my last visit, can I talk to someone?` Bot: "I've passed your message to our team and a staff member will reply here shortly…" **Cut to the staff phone:** 🙋 alert with the patient's name, number and message. Staff types `#reply +1555… Hi Jordan, it's Dana from billing. I've found the duplicate and refunded it.` **Cut to the patient phone:** Dana's message arrives. | "Billing, complaints, anything clinical: the bot knows its limits. It hands the chat to your team instantly and stops talking, so staff take over right inside WhatsApp. If a patient describes an emergency, it tells them to call you immediately and flags it as urgent." |
| **1:40–1:52** | Quick cutaway: the n8n workflow canvas (zoom out, slow pan), then the phone showing yesterday's reminder: *"Hi Jordan, this is a reminder of your appointment… Reply YES to confirm"*, then `YES` and the ✅ appearing on the calendar event. | "Every appointment also gets a reminder 24 hours before. Patients confirm with one tap, and your calendar shows who's confirmed. Fewer no-shows, less chasing." |
| **1:52–2:00** | End card: *"WhatsApp AI Receptionist for dental clinics. Live in one week. [Your name] · [email / booking link]"* | "Answer every patient, 24/7, without adding staff. I set it up in about a week. Book a 15-minute call and I'll show it running on your own calendar." |

**Word count:** about 300 words of voiceover, a comfortable pace for 2:00. If you run
long, cut the reminder cutaway (1:40–1:52) first.

---

## Recording tips

- Record the screen at 30 fps with the cursor hidden. Zoom in (1.3–1.5×) on the phone
  while typing and on the calendar/sheet when rows appear.
- Add a soft "pop" sound when the calendar event appears. It's the moment owners remember.
- Keep the n8n canvas on screen for under 5 seconds. Owners buy outcomes, not nodes. Keep
  a longer technical walkthrough as a separate video for agency or technical buyers.
- Captions on. Many people watch portfolio videos muted.
- Use the fictional clinic name. Never record with a real clinic's patient data.

## Variants

- **30-second social cut:** 0:00–0:10 hook → 0:30–0:58 booking → end card.
- **Localized cut:** send the FAQ question in Spanish. The bot answers in Spanish (see the
  language rule in `prompts/system_prompt.md`). This is strong for clinics in bilingual
  areas.
