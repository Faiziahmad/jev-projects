# Domain Health Check — outreach playbook

The free checker (`index.html`) is the bait. Every result links to a paid check-up.
Share a link that runs the check for a business automatically:

```
https://<where-you-host-it>/?d=theirbusiness.com
```

## Ground rules (keeps you trusted and out of spam folders)

- Only mention what the free checker shows. It uses **public information only**, the same records every email service reads. Never test anything else without written permission.
- Be helpful, not scary. No "you've been hacked", no "urgent", no threats.
- Send from your own named address, e.g. `faizi@yourdomain.com`, not a no-reply address.
- Set up SPF and DMARC on **your own** sending domain first. Run it through your own checker and get 100.
- Keep it personal: 20–30 hand-sent emails a day, not bulk blasts. No attachments, and only one link.
- Always include who you are and an easy way to say "no thanks". Honour it immediately.
- Follow local rules for business email (for example CAN-SPAM in the US, PECR/GDPR in the UK/EU).

## Who to contact

1. Pick one niche: clinics, dentists, law firms, accountants, real estate agents or online shops.
2. Find 50–100 of them on Google Maps or local directories.
3. Run each website through the checker. Only email businesses that are **missing DMARC or SPF**. That's the easiest problem to explain.

---

## Template 1: first email (businesses)

**Subject:** Quick heads-up about emails from {{business}}

> Hi {{first name}},
>
> I was looking at {{business}} and noticed something small but important: right now, anyone could send an email that looks like it's from **@{{domain}}**, for example a fake invoice to one of your customers.
>
> It's usually a 10-minute fix in your domain settings. I put the free results here, with the exact steps:
> {{link to checker with ?d=domain}}
>
> If you'd like, I can fix it for you, or do a full check-up of your website and systems ({{price}}, plain-English report, free re-check).
>
> Either way, hope this helps.
>
> Faizi Ahmad
> Security consultant · {{your website}}
> *Not relevant? Just reply "no thanks" and I won't email again.*

## Template 2: follow-up (5–7 days later, once only)

**Subject:** Re: Quick heads-up about emails from {{business}}

> Hi {{first name}}, just making sure this didn't get lost. Your free results are still here: {{link}}
>
> Happy to walk you through the fix on a 10-minute call, no charge. After that I'll leave you be.
>
> Faizi

## Template 3: web designers and agencies (partnership)

**Subject:** A simple add-on for your clients' websites

> Hi {{first name}},
>
> I'm a security consultant, and I help small businesses fix the settings that let others send fake emails in their name, plus check their websites properly.
>
> Your clients probably ask you "is our site secure?" now and then. I'd be happy to handle that for you, either under your brand or with a {{20–30}}% referral fee for each client you send.
>
> Here's a free tool you can try on any of your clients' domains: {{link}}
>
> Open to a quick chat this week?
>
> Faizi Ahmad · {{your website}}

---

## Numbers to expect

- About 100 personal emails a week → about 5 replies → 1–2 paid check-ups.
- Agencies reply less often but bring several clients each.
- Every check-up client is a candidate for the monthly monitor (idea 4).
