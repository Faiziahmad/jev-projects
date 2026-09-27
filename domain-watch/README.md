# domain-watch

Weekly, plain-English domain health reports for small businesses. It's the paid follow-on to the free [Domain Health Check](../site-check/) page.

**Public information only.** It reads DNS records, the public certificate log (crt.sh) and public domain registration data (RDAP), and it makes one normal visit to the homepage. It never scans, probes or tests a website.

## What each client gets every week

| Check | What the report says |
|---|---|
| Fake-email protection | Whether others can send email pretending to be them (SPF + DMARC) |
| Padlock certificate | Days until it expires. Warns at 30 days and alerts at 14 |
| Secure redirect | Whether `http://` visitors are sent to `https://` |
| Domain registration | Days until the domain name lapses (when the registry publishes it) |
| New web addresses | Addresses that appeared since last week, such as forgotten test sites |
| Look-alike domains | Newly registered look-alikes (`sh0p.com`, `shop-support.com`…) often used to trick customers |
| Settings changes | Changes to where their email goes or who controls their domain |

Problems come first, anything new since last week is marked **NEW**, and every problem has a one-line "What to do".

## Usage

```bash
pip install -e .

domain-watch check yourbusiness.com          # one-off report in the terminal
domain-watch check yourbusiness.com --json   # machine-readable

domain-watch init                            # creates clients.yaml
domain-watch run                             # saves reports/<domain>.txt and .html
domain-watch run --send                      # also emails each client
```

`clients.yaml`:

```yaml
sender: Faizi Ahmad
clients:
  - name: Sarah
    business: Bright Smile Dental
    domain: brightsmile.example
    email: sarah@brightsmile.example
    consent: yes        # clients without consent: yes are skipped
```

Last week's results are kept in `state/` so each report can say what changed. The first run for a client is the starting point.

### Sending email

Set these environment variables (any SMTP provider works: Google Workspace, Zoho, Postmark, Brevo…):

```
DW_SMTP_HOST  DW_SMTP_PORT (587)  DW_SMTP_USER  DW_SMTP_PASS  DW_FROM
```

### Running it every week

- **Your own machine or server:** add a cron job, e.g. `0 7 * * 1 cd ~/domain-watch && domain-watch run --send`.
- **GitHub Actions:** see [`examples/weekly.yml`](examples/weekly.yml). Keep that repo **private**, because it holds client details.

## Pricing idea

| Plan | Price | For |
|---|---|---|
| Starter | $29/month | 1 domain, weekly email report |
| Business | $59/month | Up to 3 domains, plus a monthly 15-minute call |
| Agency | $149/month | Up to 15 client domains, reports under the agency's brand |

Offer it to every check-up client: "Want me to keep an eye on this every week?"

## Tests

```bash
python3 -m unittest discover -s tests
```
