#!/usr/bin/env python3
"""Build workflows/whatsapp_receptionist.json from the prompt files.

The workflow JSON is generated so the prompts and FAQ only live in one place
(prompts/*.md) and every clinic build is reproducible.

    python3 scripts/build_workflow.py                      # default build
    python3 scripts/build_workflow.py --faq clients/acme/faq.md --out /tmp/acme.json

Standard library only. Node types and parameter names target n8n 2.x
(checked against n8n-nodes-base 2.40 / @n8n/n8n-nodes-langchain 2.40).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fixed namespace so node IDs stay stable between builds (clean git diffs).
NS = uuid.UUID("6f1c2a7e-4b8e-4f7a-9d0c-2d3b5e8a1c44")

# Default models. Haiku 4.5 is the cheapest current Claude model and is plenty for
# routing, FAQ answers and slot picking. Swap to "claude-sonnet-5" on the Booking
# Model only if a clinic needs more nuanced multi-step conversations.
CLASSIFIER_MODEL = "claude-haiku-4-5"
REPLY_MODEL = "claude-haiku-4-5"


def extract_block(text: str, name: str) -> str:
    m = re.search(rf"<!-- BEGIN:{name} -->\n(.*?)\n<!-- END:{name} -->", text, re.S)
    if not m:
        sys.exit(f"Block '{name}' not found")
    return m.group(1).strip()


def node_id(name: str) -> str:
    return str(uuid.uuid5(NS, name))


# ---------------------------------------------------------------------------
# Clinic profile (non-secret, per-clinic settings). Secrets and IDs live in env.
# ---------------------------------------------------------------------------
PROFILE = {
    "clinicName": "Bright Smile Dental",
    "address": "2140 Maple Avenue, Suite 200, Springfield",
    "phone": "(555) 010-2040",
    "defaultLanguage": "English",
    # Luxon weekday numbers: 1 = Monday ... 7 = Sunday. Each block is [open, close].
    "openingHours": {
        "1": [["08:30", "12:30"], ["13:30", "18:00"]],
        "2": [["08:30", "12:30"], ["13:30", "18:00"]],
        "3": [["08:30", "12:30"], ["13:30", "18:00"]],
        "4": [["08:30", "12:30"], ["13:30", "18:00"]],
        "5": [["08:30", "12:30"], ["13:30", "18:00"]],
        "6": [["09:00", "13:00"]],
        "7": [],
    },
    "appointmentMinutes": 30,
    "slotStepMinutes": 30,
    "minNoticeHours": 2,
    "bookingWindowDays": 10,
    "maxSlotsShown": 120,
    "services": [
        "Check-up and cleaning",
        "New patient exam",
        "Emergency / toothache visit",
        "Filling or crown consultation",
        "Teeth whitening consultation",
        "Invisalign consultation (free)",
        "Implant consultation",
        "Children's check-up",
    ],
    "cancelNoticeHours": 24,
    "cancellationPolicy": "Please give at least 24 hours' notice; late cancellations or missed visits may be charged a $50 fee.",
    # Classifier confidence below this goes straight to a human.
    "confidenceThreshold": 0.5,
    # A paused (handed-off) chat returns to the bot after this many hours of staff silence.
    "handoffAutoResumeHours": 12,
    # Max inbound messages per patient per hour before the bot stops answering (cost guard).
    "rateLimitPerHour": 20,
    "reminderHoursBefore": 24,
    "messages": {
        "handoff": "Thanks for your patience. I've passed your message to our team and a staff member will reply here shortly. For anything urgent, please call us on {clinicPhone}.",
        "emergency": "I'm sorry you're dealing with this. Please call us right now on {clinicPhone} so the team can help you straight away. If you have trouble breathing or swallowing, or swelling is spreading to your eye or neck, call your local emergency number immediately. I've also alerted our team.",
        "handoffAfterHours": "Thanks for your message. Our team is currently away, and a staff member will reply here as soon as we reopen ({openingHours}). If this is urgent, please call {clinicPhone}.",
        "unsupportedMedia": "Thanks! I can only read text messages at the moment. Could you type your question? If you need to send photos or documents, our team can help. Just reply \"team\".",
        "optOut": "You've been unsubscribed from appointment reminders. You can still message us here any time. Reply START to turn reminders back on.",
        "optIn": "Welcome back! Appointment reminders are switched on again.",
        "confirmThanks": "Thank you{firstName}! Your appointment on {when} is confirmed ✅ We look forward to seeing you. If anything changes, just reply here.",
        "reminder": "Hi {firstName}, this is a reminder of your appointment at {clinicName} on {when}. Reply YES to confirm or RESCHEDULE if you need to change it.",
        "fallback": "Sorry, I'm having trouble right now. I've asked a team member to reply to you here. For anything urgent, please call {clinicPhone}.",
    },
}

# ---------------------------------------------------------------------------
# Code node sources. Kept as plain JS strings; __PROFILE__/__PROMPTS__/__FAQ__ are
# replaced with JSON literals at build time.
# ---------------------------------------------------------------------------
JS_CLINIC_PROFILE = r"""// ⚙️ CLINIC PROFILE: the only node you need to edit per clinic.
// Secrets and IDs (Twilio, Google, staff number) live in environment variables.
// Prompts and FAQ are generated from prompts/*.md by scripts/build_workflow.py.
const PROFILE = __PROFILE__;
PROFILE.timezone = $env.GENERIC_TIMEZONE || 'America/New_York';

const PROMPTS = __PROMPTS__;

const FAQ = __FAQ__;

const trigger = $('Twilio Webhook').isExecuted ? 'webhook' : 'schedule';
const webhook = trigger === 'webhook' ? $('Twilio Webhook').first().json : {};

const dayNames = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const openingHoursText = Object.entries(PROFILE.openingHours)
  .map(([d, blocks]) => `${dayNames[d]} ${blocks.length ? blocks.map(b => b.join('-')).join(', ') : 'closed'}`)
  .join('; ');

return [{ json: { trigger, profile: { ...PROFILE, openingHoursText }, prompts: PROMPTS, faq: FAQ, webhook } }];
"""

JS_VERIFY = r"""// Verifies the Twilio signature, normalises the message, applies the per-number
// rate limit and decides which lane the message takes.
const crypto = require('crypto');
const ctx = $('Clinic Profile').first().json;
const P = ctx.profile;
const headers = ctx.webhook.headers || {};
const params = ctx.webhook.body || {};
const state = $getWorkflowStaticData('global');
state.chats = state.chats || {};
const now = Date.now();

// 1) Twilio request signature (https://www.twilio.com/docs/usage/webhooks/webhooks-security)
if (String($env.TWILIO_VALIDATE_SIGNATURE || 'true').toLowerCase() !== 'false') {
  const token = $env.TWILIO_AUTH_TOKEN;
  const url = $env.TWILIO_WEBHOOK_URL;
  if (!token || !url) {
    throw new Error('Set TWILIO_AUTH_TOKEN and TWILIO_WEBHOOK_URL (or TWILIO_VALIDATE_SIGNATURE=false for local testing only).');
  }
  const signed = url + Object.keys(params).sort().map(k => k + params[k]).join('');
  const expected = Buffer.from(crypto.createHmac('sha1', token).update(Buffer.from(signed, 'utf-8')).digest('base64'));
  const given = Buffer.from(String(headers['x-twilio-signature'] || ''));
  if (expected.length !== given.length || !crypto.timingSafeEqual(expected, given)) {
    return []; // not from Twilio: drop silently
  }
}

// 2) Normalise
const from = String(params.From || '');
if (!from.startsWith('whatsapp:')) return [];
const phone = from.slice('whatsapp:'.length).trim();
const text = String(params.Body || '').replace(/\u0000/g, '').trim().slice(0, 1000);
const numMedia = parseInt(params.NumMedia || '0', 10) || 0;
const profileName = String(params.ProfileName || '').slice(0, 80);
const staff = String($env.STAFF_WHATSAPP_NUMBER || '').replace('whatsapp:', '').trim();

// Housekeeping: forget idle chats after 60 days (opt-outs are kept).
for (const [k, v] of Object.entries(state.chats)) {
  if (!v.optedOut && now - (v.lastSeen || 0) > 60 * 86400e3) delete state.chats[k];
}

const base = { phone, text, numMedia, profileName, messageSid: params.MessageSid || '', receivedAt: new Date(now).toISOString() };

// 3) Staff commands
if (staff && phone === staff) {
  return [{ json: { ...base, lane: 'staff', mode: 'staff' } }];
}

// 4) Patient
const chat = state.chats[phone] = state.chats[phone] || { firstSeen: base.receivedAt };
chat.hits = (chat.hits || []).filter(t => now - t < 3600e3);
chat.hits.push(now);
if (chat.hits.length > P.rateLimitPerHour) return []; // cost guard: stop answering this number for a while
chat.lastSeen = now;
if (!chat.name && profileName) chat.name = profileName;

let mode = null;
const kw = text.toUpperCase().replace(/[^A-Z ]/g, '').trim();
if (['STOP', 'UNSUBSCRIBE', 'STOP REMINDERS'].includes(kw)) mode = 'optout';
else if (['START', 'SUBSCRIBE'].includes(kw) && chat.optedOut) mode = 'optin';
else if (chat.paused) {
  if (now - (chat.pausedAt || 0) > P.handoffAutoResumeHours * 3600e3) {
    chat.paused = false; // staff never picked it up: bot takes over again
  } else {
    mode = 'paused';
  }
}
if (!mode) {
  if (!text && numMedia > 0) mode = 'unsupported';
  else if (!text) return [];
  else mode = 'bot';
}

const contextFresh = now - (chat.contextAt || 0) < 24 * 3600e3;
const lane = { optout: 'canned', optin: 'canned', unsupported: 'canned', paused: 'paused', bot: 'bot' }[mode];
return [{ json: {
  ...base, lane, mode,
  name: chat.name || '',
  lastIntent: contextFresh ? (chat.lastIntent || 'none') : 'none',
  lastBotMessage: contextFresh ? (chat.lastBotMessage || '') : '',
} }];
"""

JS_STAFF = r"""// Staff commands, sent from STAFF_WHATSAPP_NUMBER to the clinic's WhatsApp number:
//   #reply +15551234567 Your message   -> sends your message to the patient
//   #resume +15551234567               -> hands the chat back to the bot
//   #pause +15551234567                -> stops the bot for that patient
//   #status                            -> lists chats currently with staff
const n = $('Verify & Normalize').first().json;
const state = $getWorkflowStaticData('global');
state.chats = state.chats || {};
const out = [];
const toStaff = body => out.push({ json: { to: n.phone, body } });
const HELP = 'Receptionist bot commands:\n#reply +15551234567 message\n#resume +15551234567\n#pause +15551234567\n#status';

const m = n.text.match(/^#(\w+)\s*(\+?[\d][\d\s()-]{5,}\d)?\s*([\s\S]*)$/);
if (!m) {
  toStaff(HELP);
} else {
  const cmd = m[1].toLowerCase();
  const target = m[2] ? '+' + m[2].replace(/\D/g, '') : null;
  const msg = (m[3] || '').trim();
  const chat = target ? (state.chats[target] = state.chats[target] || {}) : null;
  if (cmd === 'reply' && target && msg) {
    chat.paused = true;
    chat.pausedAt = Date.now(); // staff is active: extend the pause
    chat.contextAt = Date.now();
    chat.lastBotMessage = msg.slice(0, 300);
    out.push({ json: { to: target, body: msg, lead: { phone: target, name: chat.name || '', intent: 'handoff', status: 'Staff Replied', message: '' } } });
    toStaff(`✅ Sent to ${target}. Send #resume ${target} to hand back to the bot.`);
  } else if (cmd === 'resume' && target) {
    chat.paused = false;
    toStaff(`🤖 Bot resumed for ${target}.`);
  } else if (cmd === 'pause' && target) {
    chat.paused = true;
    chat.pausedAt = Date.now();
    chat.pauseReason = 'Paused by staff';
    toStaff(`⏸️ Bot paused for ${target}. Their messages will be forwarded to you.`);
  } else if (cmd === 'status') {
    const paused = Object.entries(state.chats).filter(([, c]) => c.paused);
    toStaff(paused.length
      ? 'Chats with staff:\n' + paused.map(([p, c]) => `• ${c.name || 'Unknown'} ${p}: ${c.pauseReason || ''}`).join('\n')
      : 'No chats are with staff right now. The bot is handling everything.');
  } else {
    toStaff(HELP);
  }
}
return out;
"""

JS_FORWARD = r"""// Chat is paused (handed off): forward the patient's message to staff, no AI call.
const n = $('Verify & Normalize').first().json;
const staff = String($env.STAFF_WHATSAPP_NUMBER || '').replace('whatsapp:', '').trim();
const who = n.name || n.profileName || 'Patient';
const text = n.text || (n.numMedia ? '[sent a photo/file, open Twilio console to view]' : '');
const lead = { phone: n.phone, name: who, intent: 'handoff', status: 'With Staff', message: text };
return [{ json: {
  to: staff,
  body: `💬 ${who} (${n.phone}):\n${text}\n\nReply: #reply ${n.phone} <message>\nHand back to bot: #resume ${n.phone}`,
  lead,
} }];
"""

JS_CANNED = r"""// Opt-out / opt-in / media-only messages: fixed replies, no AI call.
const n = $('Verify & Normalize').first().json;
const P = $('Clinic Profile').first().json.profile;
const state = $getWorkflowStaticData('global');
const chat = state.chats[n.phone];
let body, status, optChange = null;
if (n.mode === 'optout') { chat.optedOut = true; body = P.messages.optOut; status = 'Opted Out'; optChange = 'opt-out'; }
else if (n.mode === 'optin') { chat.optedOut = false; body = P.messages.optIn; status = 'Opted In'; optChange = 'opt-in'; }
else { body = P.messages.unsupportedMedia; status = 'Media Received'; }
// Opt-outs are also written to the "Opt-outs" sheet tab, which the reminder job reads.
const optRow = optChange
  ? { Timestamp: DateTime.now().setZone(P.timezone).toFormat('yyyy-MM-dd HH:mm:ss'), Phone: n.phone, Action: optChange }
  : null;
return [{ json: { to: n.phone, body, optRow, lead: { phone: n.phone, name: n.name, intent: n.mode, status, message: n.text || '[media]' } } }];
"""

JS_PARSE_INTENT = r"""// Parses the classifier JSON, applies the confidence threshold and builds the FAQ prompt.
const ctx = $('Clinic Profile').first().json;
const P = ctx.profile;
const n = $('Verify & Normalize').first().json;
const state = $getWorkflowStaticData('global');
const chat = state.chats[n.phone];

let c = {};
const raw = String($input.first().json.text || '');
try {
  const m = raw.match(/\{[\s\S]*\}/);
  c = JSON.parse(m ? m[0] : raw);
} catch (e) {
  c = { intent: 'other', confidence: 0, reason: 'classifier returned invalid JSON' };
}
const INTENTS = ['faq', 'booking', 'reschedule', 'cancel', 'confirm', 'handoff', 'emergency', 'other'];
const intent = INTENTS.includes(c.intent) ? c.intent : 'other';
let confidence = Number(c.confidence);
if (!Number.isFinite(confidence)) confidence = 0;

let route, handoffReason = '';
if (intent === 'emergency') { route = 'handoff'; handoffReason = 'Possible dental emergency'; }
else if (intent === 'handoff') { route = 'handoff'; handoffReason = 'Patient asked for a person, or needs staff: ' + String(c.reason || '').slice(0, 80); }
else if (confidence < P.confidenceThreshold) { route = 'handoff'; handoffReason = `Bot unsure what they need (confidence ${confidence.toFixed(2)})`; }
else route = { faq: 'faq', other: 'faq', booking: 'booking', reschedule: 'reschedule', cancel: 'reschedule', confirm: 'confirm' }[intent];

// "YES" replies to a reminder are checked against the calendar, whatever the classifier
// thought, unless the patient is in the middle of a booking conversation.
const bareYes = /^(yes|yes please|yep|yeah|y|ok|okay|confirm|confirmed|i confirm|si|sí|👍|✅)[\s.!]*$/iu.test(n.text.trim());
let confirmSource = intent === 'confirm' ? 'classifier' : '';
if (bareYes && route !== 'handoff' && !['booking', 'reschedule', 'cancel'].includes(n.lastIntent)) {
  route = 'confirm';
  confirmSource = 'reminderReply';
}

// A name the patient typed is better than their WhatsApp profile name.
const clean = s => String(s || '').replace(/[^\p{L}\p{M} .'-]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 40);
if (c.name && clean(c.name)) chat.name = clean(c.name);
chat.lastIntent = intent;

const now = DateTime.now().setZone(P.timezone);
const vars = {
  CLINIC_NAME: P.clinicName,
  CLINIC_ADDRESS: P.address,
  CLINIC_PHONE: P.phone,
  OPENING_HOURS: P.openingHoursText,
  TODAY: now.toFormat('cccc d LLLL yyyy'),
  NOW_TIME: now.toFormat('HH:mm'),
  TIMEZONE: P.timezone,
  DEFAULT_LANGUAGE: P.defaultLanguage,
  PATIENT_NAME: clean(chat.name || n.profileName) || 'unknown',
  FAQ: ctx.faq,
};
const fill = (tpl, v) => tpl.replace(/\{\{([A-Z_]+)\}\}/g, (m, k) => (v[k] !== undefined ? String(v[k]) : m));

return [{ json: {
  ...n,
  name: chat.name || n.profileName || '',
  intent, confidence, route, handoffReason, confirmSource,
  urgent: intent === 'emergency',
  classifierReason: String(c.reason || '').slice(0, 120),
  vars,
  faqPrompt: fill(ctx.prompts.core + '\n\n' + ctx.prompts.faq_mode, vars),
} }];
"""

JS_BOOKING_CONTEXT = r"""// Turns the next weeks of calendar events into (a) free slots and (b) this patient's
// own appointments, then builds the Booking Agent prompt. The booking tools can ONLY
// use slots/appointments computed here, so the AI cannot double-book or touch other
// patients' events.
const ctx = $('Clinic Profile').first().json;
const P = ctx.profile;
const n = $('Parse Intent').first().json;
const tz = P.timezone;
const now = DateTime.now().setZone(tz);
const KEY = "yyyy-MM-dd'T'HH:mm";

const events = $input.all().map(i => i.json).filter(e => e && e.id && e.status !== 'cancelled');

// Busy intervals (all-day events such as "Clinic closed" block the whole day).
const busy = [];
for (const e of events) {
  if (e.transparency === 'transparent') continue;
  let s, en;
  if (e.start && e.start.dateTime) { s = DateTime.fromISO(e.start.dateTime); en = DateTime.fromISO(e.end.dateTime); }
  else if (e.start && e.start.date) { s = DateTime.fromISO(e.start.date, { zone: tz }); en = DateTime.fromISO(e.end.date, { zone: tz }); }
  else continue;
  busy.push([s.toMillis(), en.toMillis()]);
}

// This patient's upcoming appointments, matched on the "WhatsApp: +number" line the bot writes.
const digits = n.phone.replace(/\D/g, '');
const appointments = {};
const apptLines = [];
for (const e of events) {
  const m = String(e.description || '').match(/WhatsApp:\s*\+?(\d{6,15})/i);
  if (!m || m[1] !== digits || !(e.start && e.start.dateTime)) continue;
  const s = DateTime.fromISO(e.start.dateTime).setZone(tz);
  if (s <= now) continue;
  const key = s.toFormat(KEY);
  appointments[key] = { id: e.id, summary: e.summary || 'Appointment', start: s.toISO(), label: s.toFormat("cccc d LLL 'at' HH:mm"),
    reminded: /Reminder sent/i.test(e.description || ''), confirmed: /^✅/.test(e.summary || '') };
  apptLines.push(`- ${key}: ${s.toFormat("cccc d LLL 'at' HH:mm")} (${e.summary || 'Appointment'})`);
}

// Free slots inside opening hours.
const dur = P.appointmentMinutes;
const earliest = now.plus({ hours: P.minNoticeHours });
const slots = {};
const slotLines = [];
let count = 0;
for (let d = 0; d < P.bookingWindowDays && count < P.maxSlotsShown; d++) {
  const day = now.startOf('day').plus({ days: d });
  const times = [];
  for (const [open, close] of (P.openingHours[String(day.weekday)] || [])) {
    const [oh, om] = open.split(':').map(Number);
    const [ch, cm] = close.split(':').map(Number);
    let t = day.set({ hour: oh, minute: om });
    const closeAt = day.set({ hour: ch, minute: cm });
    while (t.plus({ minutes: dur }) <= closeAt && count < P.maxSlotsShown) {
      const s = t.toMillis(), e = t.plus({ minutes: dur }).toMillis();
      if (t >= earliest && !busy.some(([bs, be]) => s < be && e > bs)) {
        slots[t.toFormat(KEY)] = { start: t.toISO(), end: t.plus({ minutes: dur }).toISO() };
        times.push(t.toFormat('HH:mm'));
        count++;
      }
      t = t.plus({ minutes: P.slotStepMinutes });
    }
  }
  if (times.length) slotLines.push(`${day.toFormat('yyyy-MM-dd (cccc d LLL)')}: ${times.join(', ')}`);
}

// Reminder confirmations: the patient's next appointment within 48h.
let route = n.route;
let confirmTarget = null;
if (route === 'confirm') {
  // A bare "yes" only confirms an appointment we actually sent a reminder for.
  const next = Object.values(appointments)
    .filter(a => DateTime.fromISO(a.start) < now.plus({ hours: 48 }) && !a.confirmed)
    .filter(a => n.confirmSource !== 'reminderReply' || a.reminded)
    .sort((a, b) => a.start.localeCompare(b.start))[0];
  if (next) confirmTarget = next;
  else route = 'booking'; // nothing to confirm: let the booking agent handle it
}

const TASKS = {
  booking: 'book a new appointment',
  reschedule: 'reschedule or cancel an existing appointment',
};
const vars = {
  ...n.vars,
  TASK: TASKS[route] || 'with their appointment',
  PATIENT_PHONE: n.phone,
  PATIENT_APPOINTMENTS: apptLines.length ? apptLines.join('\n') : '- none found under this WhatsApp number',
  SERVICES: P.services.map(s => '- ' + s).join('\n'),
  APPOINTMENT_MINUTES: dur,
  AVAILABLE_SLOTS: (slotLines.length ? slotLines.join('\n') : 'No free slots in the next ' + P.bookingWindowDays + ' days.')
    + '\nSlot code = date + "T" + time, e.g. ' + (Object.keys(slots)[0] || '2026-01-05T09:00'),
  CANCEL_NOTICE_HOURS: P.cancelNoticeHours,
  CANCELLATION_POLICY: P.cancellationPolicy,
};
const fill = (tpl, v) => tpl.replace(/\{\{([A-Z_]+)\}\}/g, (m, k) => (v[k] !== undefined ? String(v[k]) : m));

return [{ json: {
  ...n,
  route,
  confirmTarget,
  slots,
  appointments,
  bookingPrompt: fill(ctx.prompts.core + '\n\n' + ctx.prompts.booking_mode, vars),
} }];
"""

JS_FINALIZE = r"""// Cleans the agent reply, detects [HANDOFF], and works out what actually happened
// in the calendar from the agent's tool calls (for the lead sheet).
const P = $('Clinic Profile').first().json.profile;
const n = $('Parse Intent').first().json;
const state = $getWorkflowStaticData('global');
const chat = state.chats[n.phone];
const res = $input.first().json;

let reply = String(res.output || '').trim();
let handoff = /\[HANDOFF\]/i.test(reply);
reply = reply.replace(/\[HANDOFF\]/gi, '').replace(/\n{3,}/g, '\n\n').trim();

let status = n.route === 'faq' ? 'FAQ Answered' : 'In Progress';
let appointmentTime = '', eventId = '';
const fmt = iso => (iso ? DateTime.fromISO(iso).setZone(P.timezone).toFormat('yyyy-MM-dd HH:mm') : '');
for (const step of (res.intermediateSteps || [])) {
  const tool = String((step.action && step.action.tool) || '').toLowerCase();
  const input = (step.action && step.action.toolInput) || {};
  let obs = null;
  try { obs = JSON.parse(step.observation); } catch (e) { obs = null; }
  const first = Array.isArray(obs) ? obs[0] : obs;
  const ok = first && typeof first === 'object' && !first.error && (first.id || first.success);
  if (!ok) { status = 'Booking Error'; continue; }
  if (tool.includes('cancel')) {
    status = 'Cancelled';
    appointmentTime = String(input.appointment || '').replace('T', ' ');
  } else if (tool.includes('reschedule')) {
    status = 'Rescheduled'; eventId = first.id; appointmentTime = fmt(first.start && first.start.dateTime);
  } else if (tool.includes('create')) {
    status = 'Booked'; eventId = first.id; appointmentTime = fmt(first.start && first.start.dateTime);
  }
}

if (!reply) {
  // Agent failed or returned nothing: never leave the patient hanging.
  reply = P.messages.fallback.replace('{clinicPhone}', P.phone);
  handoff = true;
}

chat.contextAt = Date.now();
chat.lastBotMessage = reply.slice(0, 300);

return [{ json: {
  ...n,
  reply,
  needsHandoff: handoff,
  handoffReason: handoff ? (n.handoffReason || 'Bot could not resolve the request') : '',
  to: n.phone,
  body: reply,
  lead: { phone: n.phone, name: n.name, intent: n.intent, status, appointmentTime, eventId, message: n.text, confidence: n.confidence },
} }];
"""

JS_HANDOFF = r"""// Pauses the bot for this chat and alerts staff. Reached from the classifier
// (explicit request / emergency / low confidence) or from an agent's [HANDOFF].
const P = $('Clinic Profile').first().json.profile;
const n = $input.first().json;
const state = $getWorkflowStaticData('global');
const chat = state.chats[n.phone] = state.chats[n.phone] || {};
const staff = String($env.STAFF_WHATSAPP_NUMBER || '').replace('whatsapp:', '').trim();
const reason = n.handoffReason || 'Needs a team member';

chat.paused = true;
chat.pausedAt = Date.now();
chat.pauseReason = reason;
chat.contextAt = Date.now();

const tpl = n.urgent ? P.messages.emergency : P.messages.handoff;
const patientMsg = n.reply || tpl.replace('{clinicPhone}', P.phone).replace('{openingHours}', P.openingHoursText);
chat.lastBotMessage = patientMsg.slice(0, 300);

const who = n.name || n.profileName || 'Patient';
const out = [{ json: {
  to: n.phone,
  body: patientMsg,
  lead: { phone: n.phone, name: who, intent: n.intent || 'handoff', status: n.urgent ? 'URGENT Handoff' : 'Handoff', message: n.text, confidence: n.confidence, appointmentTime: '', eventId: '' },
} }];
if (staff) {
  out.push({ json: {
    to: staff,
    body: `${n.urgent ? '🚨 URGENT' : '🙋'} Handoff: ${who} (${n.phone})\nWhy: ${reason}\nThey said: "${String(n.text || '').slice(0, 300)}"\n\nReply: #reply ${n.phone} <message>\nHand back to bot: #resume ${n.phone}`,
  } });
}
return out;
"""

JS_CONFIRM = r"""// Patient confirmed attendance after a reminder.
const P = $('Clinic Profile').first().json.profile;
const b = $('Prepare Booking Context').first().json;
const state = $getWorkflowStaticData('global');
const chat = state.chats[b.phone];
const t = b.confirmTarget;
const first = (b.name || '').split(' ')[0];
const body = P.messages.confirmThanks
  .replace('{firstName}', first ? ', ' + first : '')
  .replace('{when}', t.label);
chat.contextAt = Date.now();
chat.lastIntent = 'confirm';
chat.lastBotMessage = body;
return [{ json: {
  to: b.phone,
  body,
  lead: { phone: b.phone, name: b.name, intent: 'confirm', status: 'Confirmed', appointmentTime: t.start.slice(0, 16).replace('T', ' '), eventId: t.id, message: b.text, confidence: b.confidence },
} }];
"""

JS_REMINDERS = r"""// Builds 24h reminders for appointments the bot can reach (a "WhatsApp: +number"
// line in the event description). State lives in the calendar and the sheet, not in
// workflow static data: each reminded event gets a "Reminder sent" line, and STOP
// requests are read from the Opt-outs tab.
const P = $('Clinic Profile').first().json.profile;

// Latest action per phone from the Opt-outs tab (columns: Timestamp, Phone, Action).
const optedOut = new Set();
const rows = $('Get Opt-outs').all().map(i => i.json).filter(r => r && r.Phone);
rows.sort((a, b) => String(a.Timestamp).localeCompare(String(b.Timestamp)));
for (const r of rows) {
  const phone = String(r.Phone).trim();
  if (String(r.Action).toLowerCase() === 'opt-out') optedOut.add(phone); else optedOut.delete(phone);
}

const contentSid = $env.TWILIO_REMINDER_CONTENT_SID || '';
const stamp = DateTime.now().setZone(P.timezone).toFormat('yyyy-MM-dd HH:mm');
const out = [];
for (const item of $('Get Appointments in 24h').all()) {
  const e = item.json;
  if (!e || !e.id || e.status === 'cancelled' || !(e.start && e.start.dateTime)) continue;
  const desc = String(e.description || '');
  const m = desc.match(/WhatsApp:\s*\+?(\d{6,15})/i);
  if (!m || /Reminder sent/i.test(desc)) continue;
  const phone = '+' + m[1];
  if (optedOut.has(phone)) continue;

  const start = DateTime.fromISO(e.start.dateTime).setZone(P.timezone);
  const name = String(e.summary || '').replace(/^✅\s*/, '').split(' – ')[0].trim();
  const firstName = name.split(' ')[0] || 'there';
  const day = start.toFormat('cccc d LLLL');
  const time = start.toFormat('h:mm a');
  const body = P.messages.reminder
    .replace('{firstName}', firstName)
    .replace('{clinicName}', P.clinicName)
    .replace('{when}', `${day} at ${time}`);

  out.push({ json: {
    to: phone,
    body,
    // Outside WhatsApp's 24h session window only approved templates are delivered.
    contentSid,
    contentVariables: contentSid ? { 1: firstName, 2: day, 3: time } : null,
    eventId: e.id,
    markedDescription: `${desc}\nReminder sent: ${stamp}`,
    lead: { phone, name: name || firstName, intent: 'reminder', status: 'Reminder Sent', appointmentTime: start.toFormat('yyyy-MM-dd HH:mm'), eventId: e.id, message: '' },
  } });
}
return out;
"""


JS_OUTBOX = r"""// Every outbound WhatsApp message passes through here: builds the Twilio API
// form body and completes the lead-sheet row.
const P = $('Clinic Profile').first().json.profile;
const from = String($env.TWILIO_WHATSAPP_NUMBER || '').replace('whatsapp:', '').trim();
const enc = o => Object.entries(o)
  .filter(([, v]) => v !== undefined && v !== null && v !== '')
  .map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v))
  .join('&');
const stamp = DateTime.now().setZone(P.timezone).toFormat('yyyy-MM-dd HH:mm:ss');

return $input.all().map(({ json: j }) => {
  const params = { From: 'whatsapp:' + from, To: 'whatsapp:' + j.to };
  if (j.contentSid) {
    params.ContentSid = j.contentSid;
    params.ContentVariables = JSON.stringify(j.contentVariables || {});
  } else {
    params.Body = String(j.body || '').slice(0, 1500);
  }
  const l = j.lead;
  return { json: {
    to: j.to || '',
    form: enc(params),
    lead: l ? {
      timestamp: stamp,
      phone: l.phone || j.to || '',
      name: l.name || '',
      intent: l.intent || '',
      status: l.status || '',
      appointmentTime: l.appointmentTime || '',
      eventId: l.eventId || '',
      message: l.message || '',
      reply: j.body || '',
      confidence: l.confidence === undefined || l.confidence === '' ? '' : Number(l.confidence).toFixed(2),
    } : null,
  } };
});
"""


# ---------------------------------------------------------------------------
# Node builders
# ---------------------------------------------------------------------------
nodes: list[dict] = []
connections: dict = {}


def add(name, type_, version, params, pos, **extra):
    node = {
        "parameters": params,
        "id": node_id(name),
        "name": name,
        "type": type_,
        "typeVersion": version,
        "position": list(pos),
    }
    node.update(extra)
    nodes.append(node)
    return name


def code(name, js, pos, mode="runOnceForAllItems", **extra):
    return add(name, "n8n-nodes-base.code", 2, {"mode": mode, "jsCode": js}, pos, **extra)


def link(src, dst, out_index=0, kind="main", in_index=0):
    outs = connections.setdefault(src, {}).setdefault(kind, [])
    while len(outs) <= out_index:
        outs.append([])
    outs[out_index].append({"node": dst, "type": kind, "index": in_index})


def cond(left, op_type, operation, right=None, cid=None):
    c = {
        "id": cid or str(uuid.uuid5(NS, f"{left}{operation}{right}")),
        "leftValue": left,
        "operator": {"type": op_type, "operation": operation},
    }
    if right is None:
        c["operator"]["singleValue"] = True
        c["rightValue"] = ""
    else:
        c["rightValue"] = right
    return c


def filter_value(*conditions):
    return {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": list(conditions),
        "combinator": "and",
    }


def switch_rules(field, values):
    return {
        "rules": {
            "values": [
                {
                    "conditions": filter_value(cond(f"={{{{ $json.{field} }}}}", "string", "equals", v)),
                    "renameOutput": True,
                    "outputKey": v,
                }
                for v in values
            ]
        },
        "options": {},
    }


def anthropic_model(name, pos, max_tokens, temperature):
    return add(
        name,
        "@n8n/n8n-nodes-langchain.lmChatAnthropic",
        1.6,
        {
            "model": {"__rl": True, "mode": "id", "value": REPLY_MODEL if "Classifier" not in name else CLASSIFIER_MODEL},
            "options": {"maxTokensToSample": max_tokens, "temperature": temperature},
        },
        pos,
        credentials={"anthropicApi": {"id": "REPLACE_WITH_YOUR_CREDENTIAL_ID", "name": "Anthropic account"}},
    )


def memory(name, pos):
    return add(
        name,
        "@n8n/n8n-nodes-langchain.memoryBufferWindow",
        1.4,
        {
            "sessionIdType": "customKey",
            "sessionKey": "={{ 'wa-' + $('Verify & Normalize').first().json.phone }}",
            "contextWindowLength": 8,
        },
        pos,
    )


CAL_CRED = {"googleCalendarOAuth2Api": {"id": "REPLACE_WITH_YOUR_CREDENTIAL_ID", "name": "Google Calendar account"}}
SHEETS_CRED = {"googleSheetsOAuth2Api": {"id": "REPLACE_WITH_YOUR_CREDENTIAL_ID", "name": "Google Sheets account"}}
TWILIO_CRED = {"twilioApi": {"id": "REPLACE_WITH_YOUR_CREDENTIAL_ID", "name": "Twilio account"}}
CALENDAR = {"__rl": True, "mode": "id", "value": "={{ $env.GOOGLE_CALENDAR_ID }}"}

SLOT_ARG = "$fromAI('slot', 'Slot code copied exactly from AVAILABLE SLOTS, format YYYY-MM-DDTHH:mm', 'string')"
NEW_SLOT_ARG = "$fromAI('new_slot', 'New slot code copied exactly from AVAILABLE SLOTS, format YYYY-MM-DDTHH:mm', 'string')"
APPT_ARG = "$fromAI('appointment', 'Code of the patient appointment from PATIENT CONTEXT, format YYYY-MM-DDTHH:mm', 'string')"
CTX = "$('Prepare Booking Context').first().json"


def build(faq_path: Path, prompt_path: Path) -> dict:
    prompt_md = prompt_path.read_text()
    faq_md = faq_path.read_text()
    prompts = {k: extract_block(prompt_md, k) for k in ("core", "faq_mode", "booking_mode", "classifier")}
    faq = extract_block(faq_md, "faq")
    leftover = faq.count("[CUSTOMIZE]")
    if leftover:
        print(f"note: FAQ still contains {leftover} [CUSTOMIZE] markers (fine for the template, not for a live clinic)", file=sys.stderr)
        faq = faq.replace(" [CUSTOMIZE]", "").replace("[CUSTOMIZE]", "")

    profile_js = (
        JS_CLINIC_PROFILE.replace("__PROFILE__", json.dumps(PROFILE, indent=2, ensure_ascii=False))
        .replace("__PROMPTS__", json.dumps(prompts, indent=2, ensure_ascii=False))
        .replace("__FAQ__", json.dumps(faq, ensure_ascii=False))
    )

    # ---- Triggers & shared entry -------------------------------------------
    add("Twilio Webhook", "n8n-nodes-base.webhook", 2.1,
        {"httpMethod": "POST", "path": "whatsapp-inbound", "responseMode": "responseNode", "options": {}},
        (-1520, 200), webhookId=str(uuid.uuid5(NS, "webhook")))
    add("Ack Twilio (empty TwiML)", "n8n-nodes-base.respondToWebhook", 1.5,
        {"respondWith": "text", "responseBody": "<Response></Response>",
         "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/xml"}]}}},
        (-1300, 200))
    add("Every Hour", "n8n-nodes-base.scheduleTrigger", 1.2,
        {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}}, (-1300, 760))
    code("Clinic Profile", profile_js, (-1080, 480))
    add("Route by Trigger", "n8n-nodes-base.switch", 3.4, switch_rules("trigger", ["webhook", "schedule"]), (-860, 480))
    link("Twilio Webhook", "Ack Twilio (empty TwiML)")
    link("Ack Twilio (empty TwiML)", "Clinic Profile")
    link("Every Hour", "Clinic Profile")
    link("Clinic Profile", "Route by Trigger")

    # ---- Inbound lanes -----------------------------------------------------
    code("Verify & Normalize", JS_VERIFY, (-640, 200))
    add("Route by Lane", "n8n-nodes-base.switch", 3.4, switch_rules("lane", ["staff", "paused", "canned", "bot"]), (-420, 200))
    link("Route by Trigger", "Verify & Normalize", 0)
    link("Verify & Normalize", "Route by Lane")

    code("Handle Staff Command", JS_STAFF, (-160, -360))
    code("Forward to Staff", JS_FORWARD, (-160, -200))
    code("Canned Reply", JS_CANNED, (-160, -40))
    link("Route by Lane", "Handle Staff Command", 0)
    link("Route by Lane", "Forward to Staff", 1)
    link("Route by Lane", "Canned Reply", 2)
    add("Is Opt Change?", "n8n-nodes-base.filter", 2.2,
        {"conditions": filter_value(cond("={{ !!$json.optRow }}", "boolean", "true")), "options": {}},
        (100, -40))
    add("Record Opt-out", "n8n-nodes-base.googleSheets", 4.7,
        {"operation": "append",
         "documentId": {"__rl": True, "mode": "id", "value": "={{ $env.GOOGLE_SHEET_ID }}"},
         "sheetName": {"__rl": True, "mode": "name", "value": "Opt-outs"},
         "columns": {
             "mappingMode": "defineBelow",
             "value": {c: f"={{{{ $json.optRow['{c}'] }}}}" for c in ("Timestamp", "Phone", "Action")},
             "matchingColumns": [],
             "schema": [{"id": c, "displayName": c, "required": False, "defaultMatch": False,
                         "display": True, "type": "string", "canBeUsedToMatch": True} for c in ("Timestamp", "Phone", "Action")],
         },
         "options": {"cellFormat": "RAW", "useAppend": True}},
        (320, -40), credentials=SHEETS_CRED, onError="continueRegularOutput")
    link("Canned Reply", "Is Opt Change?")
    link("Is Opt Change?", "Record Opt-out")

    # ---- Classifier ----------------------------------------------------------
    add("Classify Intent", "@n8n/n8n-nodes-langchain.chainLlm", 1.9,
        {"promptType": "define",
         "text": "={{ 'PREVIOUS INTENT: ' + $json.lastIntent + '\\nPREVIOUS BOT MESSAGE: ' + ($json.lastBotMessage || '(none)') + '\\n\\nPATIENT MESSAGE:\\n\"\"\"\\n' + $json.text + '\\n\"\"\"' }}",
         "messages": {"messageValues": [{"type": "SystemMessagePromptTemplate",
                                         "message": "={{ $('Clinic Profile').first().json.prompts.classifier }}"}]}},
        (-160, 260), retryOnFail=True, maxTries=2)
    anthropic_model("Classifier Model", (-160, 460), 120, 0)
    link("Route by Lane", "Classify Intent", 3)
    link("Classifier Model", "Classify Intent", kind="ai_languageModel")

    code("Parse Intent", JS_PARSE_INTENT, (100, 260))
    link("Classify Intent", "Parse Intent")
    add("Route by Intent", "n8n-nodes-base.switch", 3.4,
        switch_rules("route", ["faq", "booking", "reschedule", "confirm", "handoff"]), (320, 260))
    link("Parse Intent", "Route by Intent")

    # ---- FAQ -----------------------------------------------------------------
    add("FAQ Agent", "@n8n/n8n-nodes-langchain.agent", 3.1,
        {"promptType": "define", "text": "={{ $json.text }}",
         "options": {"systemMessage": "={{ $json.faqPrompt }}", "maxIterations": 3, "enableStreaming": False}},
        (620, -80), onError="continueRegularOutput")
    anthropic_model("FAQ Model", (560, 120), 350, 0.3)
    memory("FAQ Memory", (720, 120))
    link("Route by Intent", "FAQ Agent", 0)
    link("FAQ Model", "FAQ Agent", kind="ai_languageModel")
    link("FAQ Memory", "FAQ Agent", kind="ai_memory")

    # ---- Booking / reschedule / cancel / confirm ----------------------------
    add("Get Upcoming Events", "n8n-nodes-base.googleCalendar", 1.3,
        {"operation": "getAll", "calendar": CALENDAR, "returnAll": True,
         "timeMin": "={{ $now.toISO() }}", "timeMax": "={{ $now.plus({ days: 45 }).toISO() }}",
         "options": {}},
        (620, 360), credentials=CAL_CRED, alwaysOutputData=True, retryOnFail=True, maxTries=2)
    link("Route by Intent", "Get Upcoming Events", 1)
    link("Route by Intent", "Get Upcoming Events", 2)
    link("Route by Intent", "Get Upcoming Events", 3)
    code("Prepare Booking Context", JS_BOOKING_CONTEXT, (840, 360))
    link("Get Upcoming Events", "Prepare Booking Context")
    add("Is Confirmation?", "n8n-nodes-base.if", 2.2,
        {"conditions": filter_value(cond("={{ $json.route }}", "string", "equals", "confirm")), "options": {}},
        (1060, 360))
    link("Prepare Booking Context", "Is Confirmation?")

    add("Mark Appointment Confirmed", "n8n-nodes-base.googleCalendar", 1.3,
        {"operation": "update", "calendar": CALENDAR, "eventId": "={{ $json.confirmTarget.id }}",
         "updateFields": {"summary": "={{ $json.confirmTarget.summary.startsWith('✅') ? $json.confirmTarget.summary : '✅ ' + $json.confirmTarget.summary }}"}},
        (1300, 200), credentials=CAL_CRED, onError="continueRegularOutput")
    code("Confirmation Reply", JS_CONFIRM, (1520, 200))
    link("Is Confirmation?", "Mark Appointment Confirmed", 0)
    link("Mark Appointment Confirmed", "Confirmation Reply")

    add("Booking Agent", "@n8n/n8n-nodes-langchain.agent", 3.1,
        {"promptType": "define", "text": "={{ $json.text }}",
         "options": {"systemMessage": "={{ $json.bookingPrompt }}", "maxIterations": 5,
                     "returnIntermediateSteps": True, "enableStreaming": False}},
        (1300, 520), onError="continueRegularOutput")
    anthropic_model("Booking Model", (1100, 760), 500, 0.2)
    memory("Booking Memory", (1240, 760))
    link("Is Confirmation?", "Booking Agent", 1)
    link("Booking Model", "Booking Agent", kind="ai_languageModel")
    link("Booking Memory", "Booking Agent", kind="ai_memory")

    tool_common = {"descriptionType": "manual", "calendar": CALENDAR}
    add("create_appointment", "n8n-nodes-base.googleCalendarTool", 1.3,
        {**tool_common,
         "toolDescription": "Book a NEW appointment. Only call after the patient clearly said yes to the exact name, reason and slot you read back to them.",
         "operation": "create",
         "start": f"={{{{ ({CTX}.slots[{SLOT_ARG}] || {{}}).start || 'INVALID_SLOT' }}}}",
         "end": f"={{{{ ({CTX}.slots[{SLOT_ARG}] || {{}}).end || 'INVALID_SLOT' }}}}",
         "useDefaultReminders": True,
         "additionalFields": {
             "summary": "={{ $fromAI('patient_name', 'Patient full name as confirmed', 'string') + ' – ' + $fromAI('reason', 'Short reason for the visit, e.g. Check-up and cleaning', 'string') }}",
             "description": f"=WhatsApp: {{{{ {CTX}.phone }}}}\nBooked by the WhatsApp AI receptionist on {{{{ $now.toFormat('yyyy-MM-dd HH:mm') }}}}.",
         }},
        (1380, 760), credentials=CAL_CRED)
    add("reschedule_appointment", "n8n-nodes-base.googleCalendarTool", 1.3,
        {**tool_common,
         "toolDescription": "Move one of THIS patient's existing appointments to a new free slot. Only call after the patient clearly confirmed both.",
         "operation": "update",
         "eventId": f"={{{{ ({CTX}.appointments[{APPT_ARG}] || {{}}).id || 'INVALID_APPOINTMENT' }}}}",
         "updateFields": {
             "start": f"={{{{ ({CTX}.slots[{NEW_SLOT_ARG}] || {{}}).start || 'INVALID_SLOT' }}}}",
             "end": f"={{{{ ({CTX}.slots[{NEW_SLOT_ARG}] || {{}}).end || 'INVALID_SLOT' }}}}",
         }},
        (1520, 760), credentials=CAL_CRED)
    add("cancel_appointment", "n8n-nodes-base.googleCalendarTool", 1.3,
        {**tool_common,
         "toolDescription": "Cancel one of THIS patient's existing appointments. Only call after the patient clearly confirmed which one.",
         "operation": "delete",
         "eventId": f"={{{{ ({CTX}.appointments[{APPT_ARG}] || {{}}).id || 'INVALID_APPOINTMENT' }}}}",
         "options": {}},
        (1660, 760), credentials=CAL_CRED)
    for t in ("create_appointment", "reschedule_appointment", "cancel_appointment"):
        link(t, "Booking Agent", kind="ai_tool")

    # ---- Finalize / handoff ----------------------------------------------------
    code("Finalize Reply", JS_FINALIZE, (1900, 200))
    link("FAQ Agent", "Finalize Reply")
    link("Booking Agent", "Finalize Reply")
    add("Needs Handoff?", "n8n-nodes-base.if", 2.2,
        {"conditions": filter_value(cond("={{ $json.needsHandoff }}", "boolean", "true")), "options": {}},
        (2120, 200))
    link("Finalize Reply", "Needs Handoff?")
    code("Start Handoff", JS_HANDOFF, (2340, 480))
    link("Needs Handoff?", "Start Handoff", 0)
    link("Route by Intent", "Start Handoff", 4)

    # ---- Reminders -------------------------------------------------------------
    add("Get Appointments in 24h", "n8n-nodes-base.googleCalendar", 1.3,
        {"operation": "getAll", "calendar": CALENDAR, "returnAll": True,
         "timeMin": "={{ $now.plus({ hours: $('Clinic Profile').first().json.profile.reminderHoursBefore - 1 }).toISO() }}",
         "timeMax": "={{ $now.plus({ hours: $('Clinic Profile').first().json.profile.reminderHoursBefore + 1 }).toISO() }}",
         "options": {}},
        (-640, 760), credentials=CAL_CRED, retryOnFail=True, maxTries=2)
    add("Get Opt-outs", "n8n-nodes-base.googleSheets", 4.7,
        {"operation": "read",
         "documentId": {"__rl": True, "mode": "id", "value": "={{ $env.GOOGLE_SHEET_ID }}"},
         "sheetName": {"__rl": True, "mode": "name", "value": "Opt-outs"},
         "options": {}},
        (-420, 760), credentials=SHEETS_CRED, executeOnce=True, alwaysOutputData=True, retryOnFail=True, maxTries=2)
    code("Build Reminders", JS_REMINDERS, (-200, 760))
    add("Mark Reminder Sent", "n8n-nodes-base.googleCalendar", 1.3,
        {"operation": "update", "calendar": CALENDAR, "eventId": "={{ $json.eventId }}",
         "updateFields": {"description": "={{ $json.markedDescription }}"}},
        (40, 960), credentials=CAL_CRED, onError="continueRegularOutput")
    link("Route by Trigger", "Get Appointments in 24h", 1)
    link("Get Appointments in 24h", "Get Opt-outs")
    link("Get Opt-outs", "Build Reminders")
    link("Build Reminders", "Mark Reminder Sent")

    # ---- Outbox: send + log ------------------------------------------------------
    code("Outbox", JS_OUTBOX, (2580, 200))
    for src in ("Handle Staff Command", "Forward to Staff", "Canned Reply", "Confirmation Reply", "Start Handoff", "Build Reminders"):
        link(src, "Outbox")
    link("Needs Handoff?", "Outbox", 1)

    add("Has Recipient?", "n8n-nodes-base.filter", 2.2,
        {"conditions": filter_value(cond("={{ !!$json.to }}", "boolean", "true")), "options": {}},
        (2800, 80))
    add("Send WhatsApp (Twilio API)", "n8n-nodes-base.httpRequest", 4.2,
        {"method": "POST",
         "url": "=https://api.twilio.com/2010-04-01/Accounts/{{ $env.TWILIO_ACCOUNT_SID }}/Messages.json",
         "authentication": "predefinedCredentialType", "nodeCredentialType": "twilioApi",
         "sendBody": True, "contentType": "form-urlencoded", "specifyBody": "string",
         "body": "={{ $json.form }}", "options": {}},
        (3020, 80), credentials=TWILIO_CRED, onError="continueRegularOutput", retryOnFail=True, maxTries=2, waitBetweenTries=1500)
    add("Has Lead Row?", "n8n-nodes-base.filter", 2.2,
        {"conditions": filter_value(cond("={{ !!$json.lead }}", "boolean", "true")), "options": {}},
        (2800, 320))

    columns = [
        ("Timestamp", "timestamp"), ("Phone", "phone"), ("Name", "name"), ("Intent", "intent"),
        ("Status", "status"), ("Appointment Time", "appointmentTime"), ("Event ID", "eventId"),
        ("Patient Message", "message"), ("Bot Reply", "reply"), ("Confidence", "confidence"),
    ]
    add("Log Lead to Sheet", "n8n-nodes-base.googleSheets", 4.7,
        {"operation": "append",
         "documentId": {"__rl": True, "mode": "id", "value": "={{ $env.GOOGLE_SHEET_ID }}"},
         "sheetName": {"__rl": True, "mode": "name", "value": "Leads"},
         "columns": {
             "mappingMode": "defineBelow",
             "value": {col: f"={{{{ $json.lead.{key} }}}}" for col, key in columns},
             "matchingColumns": [],
             "schema": [
                 {"id": col, "displayName": col, "required": False, "defaultMatch": False,
                  "display": True, "type": "string", "canBeUsedToMatch": True}
                 for col, _ in columns
             ],
         },
         "options": {"cellFormat": "RAW", "useAppend": True}},
        (3020, 320), credentials=SHEETS_CRED, onError="continueRegularOutput")
    link("Outbox", "Has Recipient?")
    link("Outbox", "Has Lead Row?")
    link("Has Recipient?", "Send WhatsApp (Twilio API)")
    link("Has Lead Row?", "Log Lead to Sheet")

    # ---- Sticky notes ------------------------------------------------------------
    def sticky(name, content, pos, w, h, color=None):
        p = {"content": content, "height": h, "width": w}
        if color:
            p["color"] = color
        add(name, "n8n-nodes-base.stickyNote", 1, p, pos)

    sticky("Note: Start here", (
        "## 🦷 WhatsApp AI Receptionist\n"
        "1. Edit **Clinic Profile** (name, hours, services, messages)\n"
        "2. Set env vars (see `.env.example`)\n"
        "3. Pick your credentials on the red nodes: Anthropic, Google Calendar, Google Sheets, Twilio\n"
        "4. Activate, then point Twilio's *When a message comes in* at the production webhook URL\n\n"
        "Full guide: `docs/setup_guide.md`"), (-1560, -260), 420, 300, 4)
    sticky("Note: Handoff", (
        "## 🙋 Human handoff\n"
        "Staff text the clinic number from `STAFF_WHATSAPP_NUMBER`:\n"
        "`#reply +1555… message` · `#resume +1555…` · `#pause +1555…` · `#status`\n\n"
        "Paused chats skip the AI and are forwarded to staff. They auto-resume after `handoffAutoResumeHours`."),
        (-220, -560), 460, 180, 3)
    sticky("Note: Cost", (
        "## 💸 Cost controls\n"
        "Claude Haiku 4.5 everywhere · classifier max 120 output tokens · replies 350–500 · memory = last 8 messages · "
        "per-number rate limit · no AI call for staff, paused, opt-out or media messages."),
        (540, -300), 420, 170, 6)
    sticky("Note: Reminders", (
        "## ⏰ 24h reminders\n"
        "Hourly: finds events 23–25h out with a `WhatsApp: +number` line, skips numbers in the `Opt-outs` sheet tab and stamps `Reminder sent` on the event so each is sent once. "
        "In production set `TWILIO_REMINDER_CONTENT_SID` to an approved template; free text only delivers inside WhatsApp's 24h window."),
        (-700, 940), 460, 170, 5)

    return {
        "id": "waDentalRecept01",
        "name": "WhatsApp AI Receptionist (Dental)",
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {"executionOrder": "v1", "saveDataSuccessExecution": "all", "saveManualExecutions": True},
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False},
        "tags": [],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--faq", type=Path, default=ROOT / "prompts" / "faq_seed.md")
    ap.add_argument("--prompts", type=Path, default=ROOT / "prompts" / "system_prompt.md")
    ap.add_argument("--out", type=Path, default=ROOT / "workflows" / "whatsapp_receptionist.json")
    args = ap.parse_args()
    wf = build(args.faq, args.prompts)
    names = {n["name"] for n in wf["nodes"]}
    for src, kinds in wf["connections"].items():
        assert src in names, src
        for outs in kinds.values():
            for out in outs:
                for c in out:
                    assert c["node"] in names, c["node"]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.out} ({len(wf['nodes'])} nodes)")


if __name__ == "__main__":
    main()
