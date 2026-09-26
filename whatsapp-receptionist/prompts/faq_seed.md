# FAQ Seed — Dental Clinic

**For the clinic:** these are the 20 questions patients ask most often on WhatsApp.
The receptionist answers **only** from what's written here, so accuracy matters more
than style.

How to customize:

1. Replace every value marked **`[CUSTOMIZE]`** with your clinic's real details.
   The example values belong to a fictional practice, *Bright Smile Dental*.
2. Delete any answer that doesn't apply rather than leaving it vague. If a question
   isn't covered, the bot says so and offers to connect the patient with your team.
   That's the safe behaviour.
3. Keep answers short, 1–3 sentences each. Everything in this block is sent to the AI
   on every FAQ reply, so shorter answers are cheaper and faster.
4. Never put medical advice here (for example "take ibuprofen for pain"). Say "please
   book an appointment" or "call us" instead.
5. After editing, rebuild the workflow with `python3 scripts/build_workflow.py`, or paste
   the block into the **Clinic Profile** node in n8n (the `FAQ` constant).

Only the text between the `BEGIN:faq` and `END:faq` markers is sent to the AI. Remove
the `[CUSTOMIZE]` tags when you fill in real values. The build script warns you if any
are left.

---

<!-- BEGIN:faq -->
Q: What are your opening hours?
A: Monday to Friday 8:30am–6:00pm, Saturday 9:00am–1:00pm. Closed Sundays and public holidays. [CUSTOMIZE]

Q: Where are you located and is there parking?
A: 2140 Maple Avenue, Suite 200, Springfield, above the Riverside Pharmacy. Free patient parking behind the building; the entrance is on Oak Street. [CUSTOMIZE]

Q: Are you accepting new patients?
A: Yes, we welcome new patients of all ages, including children from their first tooth. [CUSTOMIZE]

Q: How much is a check-up and cleaning?
A: New patient exam, X-rays and cleaning: $180. Returning patient check-up and cleaning: $120. Exact fees are confirmed at your visit if extra treatment is needed. [CUSTOMIZE]

Q: Do you accept my insurance?
A: We are in-network with Delta Dental, Cigna, MetLife and Aetna PPO plans, and we can submit claims to most other PPO plans. We don't accept HMO/DMO plans. Send us your insurer's name and our team will confirm your coverage. [CUSTOMIZE]

Q: What if I don't have insurance?
A: We offer the Bright Smile Membership Plan: $29/month covers two cleanings and exams a year, X-rays, and 15% off other treatment. [CUSTOMIZE]

Q: What payment methods do you take?
A: Cash, all major credit and debit cards, HSA/FSA cards, and CareCredit financing for treatment over $500. Payment is due at the time of the visit. [CUSTOMIZE]

Q: Do you handle dental emergencies?
A: Yes. We keep same-day emergency slots on weekdays. For severe pain, swelling, or a broken or knocked-out tooth, call us right away at (555) 010-2040. If you have trouble breathing or swallowing, or swelling spreading to your eye or neck, call 911 or go to the nearest emergency room. [CUSTOMIZE]

Q: What services do you offer?
A: Check-ups and cleanings, fillings, root canals, crowns and bridges, extractions including wisdom teeth, dental implants, Invisalign clear aligners, teeth whitening, and children's dentistry. [CUSTOMIZE]

Q: How much does teeth whitening cost?
A: In-office whitening is $450 (about 90 minutes). Take-home custom trays with gel are $295. A quick check-up first confirms whitening is right for you. [CUSTOMIZE]

Q: Do you offer Invisalign or braces?
A: We offer Invisalign clear aligners. Treatment usually ranges from $3,800 to $5,800 depending on complexity, with monthly payment plans available. The first consultation is free. We don't offer traditional metal braces. [CUSTOMIZE]

Q: Do you do dental implants?
A: Yes. A single implant with crown typically costs $3,500–$4,500, confirmed after a consultation with a 3D scan ($95, credited toward treatment if you go ahead). [CUSTOMIZE]

Q: Do you see children?
A: Yes, we see children from their first tooth or first birthday. Kids' check-ups are relaxed and fun, and a parent or guardian must attend with anyone under 18. [CUSTOMIZE]

Q: What should I bring to my first appointment?
A: A photo ID, your insurance card if you have one, a list of any medications you take, and please arrive 10 minutes early to complete a short health form. [CUSTOMIZE]

Q: How long does an appointment take?
A: A check-up and cleaning takes about 45–60 minutes. New patient visits take about 60–75 minutes. The team will tell you if a treatment needs longer. [CUSTOMIZE]

Q: What is your cancellation policy?
A: Please give us at least 24 hours' notice to cancel or reschedule. Missed appointments or cancellations with less notice may be charged a $50 fee. [CUSTOMIZE]

Q: I'm nervous about the dentist. Can you help?
A: Absolutely, many of our patients feel the same. Let us know when you book and we'll allow extra time and go at your pace. We also offer nitrous oxide ("laughing gas") for many treatments. [CUSTOMIZE]

Q: Is the clinic wheelchair accessible?
A: Yes. There is an elevator from the parking lot entrance and step-free access to all treatment rooms. [CUSTOMIZE]

Q: Do you speak languages other than English?
A: Yes, our team also speaks Spanish and Mandarin. Just let us know your preference when you book. [CUSTOMIZE]

Q: How do I get my dental records or X-rays sent to another dentist?
A: Our team will need your written consent. Reply "records" and we'll connect you with a team member, or email records@brightsmiledental.example with your full name and date of birth. [CUSTOMIZE]
<!-- END:faq -->
