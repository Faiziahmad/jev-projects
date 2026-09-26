#!/usr/bin/env python3
"""Send a fake, correctly signed Twilio WhatsApp webhook to your n8n instance.

Lets you test the whole workflow (routing, AI replies, calendar, sheet logging)
without a phone. Replies are still sent through the real Twilio API, so use the
sandbox number and your own phone as --from if you want to see them arrive.

    export TWILIO_AUTH_TOKEN=...            # same value n8n uses
    export TWILIO_WEBHOOK_URL=https://n8n.example.com/webhook/whatsapp-inbound
    python3 scripts/send_test_message.py "Hi, how much is a cleaning?"
    python3 scripts/send_test_message.py --from +15551234567 --name "Maria" "Can I book Tuesday?"
    python3 scripts/send_test_message.py --bad-signature "should be dropped"

Standard library only.
"""
import argparse
import base64
import hashlib
import hmac
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


def sign(url: str, params: dict, token: str) -> str:
    # https://www.twilio.com/docs/usage/webhooks/webhooks-security
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode("utf-8"), hashlib.sha1).digest()).decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("body", nargs="?", default="", help="message text")
    ap.add_argument("--from", dest="sender", default="+15551230001", help="patient number, E.164")
    ap.add_argument("--to", default=os.environ.get("TWILIO_WHATSAPP_NUMBER", "+14155238886"))
    ap.add_argument("--name", default="Test Patient", help="WhatsApp profile name")
    ap.add_argument("--media", type=int, default=0, help="NumMedia value (simulate a photo)")
    ap.add_argument("--url", default=os.environ.get("TWILIO_WEBHOOK_URL"))
    ap.add_argument("--token", default=os.environ.get("TWILIO_AUTH_TOKEN"))
    ap.add_argument("--bad-signature", action="store_true", help="send an invalid signature")
    a = ap.parse_args()
    if not a.url or not a.token:
        sys.exit("Set TWILIO_WEBHOOK_URL and TWILIO_AUTH_TOKEN (or pass --url/--token).")

    params = {
        "SmsMessageSid": "SM" + uuid.uuid4().hex,
        "NumMedia": str(a.media),
        "ProfileName": a.name,
        "MessageType": "image" if a.media else "text",
        "SmsSid": "SM" + uuid.uuid4().hex,
        "WaId": a.sender.lstrip("+"),
        "SmsStatus": "received",
        "Body": a.body,
        "To": "whatsapp:" + a.to,
        "NumSegments": "1",
        "ReferralNumMedia": "0",
        "MessageSid": "SM" + uuid.uuid4().hex,
        "AccountSid": "AC" + "0" * 32,
        "From": "whatsapp:" + a.sender,
        "ApiVersion": "2010-04-01",
    }
    sig = "invalid" + sign(a.url, params, a.token)[7:] if a.bad_signature else sign(a.url, params, a.token)
    req = urllib.request.Request(
        a.url,
        data=urllib.parse.urlencode(params).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": sig},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(r.status, r.headers.get("Content-Type"), r.read().decode()[:200])
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode()[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()
