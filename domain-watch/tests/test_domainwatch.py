import os
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domainwatch import checks, lookalike, report  # noqa: E402
from domainwatch.net import txt_join  # noqa: E402
from domainwatch.store import Store  # noqa: E402

NOW = datetime(2026, 9, 27, tzinfo=timezone.utc)


def fake_net(zone: dict, registered: set = frozenset(), fail: set = frozenset()):
    """A stand-in for domainwatch.net driven by a dict of records."""
    def dns(name, rtype):
        if ("dns", name, rtype) in fail:
            raise RuntimeError("resolver down")
        rec = zone.get(name)
        if rec is None:
            return {"status": 3, "answers": [], "ad": False}
        return {"status": 0, "answers": list(rec.get(rtype, [])), "ad": rec.get("AD", False)}

    def boom(key, value):
        def f(*_):
            if key in fail:
                raise RuntimeError(key + " unavailable")
            return value
        return f

    root = zone.get("shop.com", {})
    return types.SimpleNamespace(
        dns=dns,
        txt=lambda n: dns(n, "TXT"),
        resolves=lambda n: n in registered,
        cert_info=boom("cert", root.get("cert")),
        http_upgrades_to_https=boom("redirect", root.get("redirect")),
        rdap_expiry=boom("rdap", root.get("rdap")),
        ct_names=boom("ct", root.get("ct", [])),
    )


def zone_good(**over):
    z = {
        "shop.com": {"TXT": ["v=spf1 include:_spf.google.com -all"], "MX": ["1 aspmx.l.google.com."], "NS": ["ns1.host.com."], "AD": True,
                     "cert": {"expires": (NOW + timedelta(days=80)).isoformat(), "issuer": "Let's Encrypt"},
                     "redirect": True, "rdap": (NOW + timedelta(days=300)).isoformat(), "ct": ["shop.com", "www.shop.com"]},
        "_dmarc.shop.com": {"TXT": ["v=DMARC1; p=reject"]},
        "_mta-sts.shop.com": {"TXT": []},
    }
    for k, v in over.items():
        z["shop.com"][k] = v
    return z


def by_key(findings):
    return {f.key: f for f in findings}


class TestLookalike(unittest.TestCase):
    def test_variants(self):
        v = lookalike.variants("paypal.com")
        self.assertNotIn("paypal.com", v)
        for want in ("paypal.net", "paypa1.com", "pypal.com", "papyal.com", "paypal-support.com"):
            self.assertIn(want, v)
        self.assertEqual(len(v), len(set(v)))
        self.assertLessEqual(len(v), 80)

    def test_multi_glyph(self):
        self.assertIn("modern.com", lookalike.variants("rnodern.com"))


class TestHelpers(unittest.TestCase):
    def test_txt_join(self):
        self.assertEqual(txt_join('"v=spf1 " "include:x ~all"'), "v=spf1 include:x ~all")
        self.assertEqual(txt_join('"say \\"hi\\""'), 'say "hi"')


class TestChecks(unittest.TestCase):
    def run_week(self, zone, prev=None, registered=frozenset(), fail=frozenset()):
        snap = checks.collect("shop.com", net=fake_net(zone, registered, fail), workers=2)
        return snap, checks.evaluate(snap, prev, now=NOW)

    def test_all_good(self):
        snap, f = self.run_week(zone_good())
        k = by_key(f)
        self.assertEqual(k["email"].status, checks.GOOD)
        self.assertEqual(k["cert"].status, checks.GOOD)
        self.assertEqual(k["https"].status, checks.GOOD)
        self.assertEqual(k["domain"].status, checks.GOOD)
        self.assertEqual(k["addresses"].status, checks.INFO)  # first week = baseline
        self.assertTrue(snap["dnssec"])
        self.assertGreaterEqual(checks.score(f), 90)
        self.assertIn("All good", report.headline(f))

    def test_missing_email_protection(self):
        z = zone_good(TXT=["google-site-verification=x"])
        z["_dmarc.shop.com"]["TXT"] = []
        _, f = self.run_week(z)
        e = by_key(f)["email"]
        self.assertEqual(e.status, checks.BAD)
        self.assertIn("SPF", e.summary)
        self.assertIn("DMARC", e.summary)

    def test_weak_dmarc_is_warning(self):
        z = zone_good()
        z["_dmarc.shop.com"]["TXT"] = ["v=DMARC1; p=none"]
        _, f = self.run_week(z)
        self.assertEqual(by_key(f)["email"].status, checks.WARN)

    def test_expiring_cert_and_domain(self):
        z = zone_good(cert={"expires": (NOW + timedelta(days=10)).isoformat(), "issuer": "x"}, rdap=(NOW + timedelta(days=45)).isoformat())
        _, f = self.run_week(z)
        k = by_key(f)
        self.assertEqual(k["cert"].status, checks.BAD)
        self.assertIn("10 days", k["cert"].summary)
        self.assertEqual(k["domain"].status, checks.WARN)

    def test_week_over_week_changes(self):
        week1, _ = self.run_week(zone_good(), registered={"shop.net"})
        z2 = zone_good(ct=["shop.com", "www.shop.com", "old-test.shop.com"], MX=["10 mail.other.com."])
        _, f = self.run_week(z2, prev=week1, registered={"shop.net", "sh0p.com"})
        k = by_key(f)
        self.assertEqual(k["addresses"].status, checks.WARN)
        self.assertEqual(k["addresses"].details, ["old-test.shop.com"])
        self.assertTrue(k["addresses"].new)
        self.assertEqual(k["lookalikes"].status, checks.BAD)
        self.assertEqual(k["lookalikes"].details, ["sh0p.com"])
        self.assertEqual(k["changes"].status, checks.WARN)
        self.assertTrue(any("MX" in d for d in k["changes"].details))
        self.assertIn("new this week", report.headline(f))

    def test_failures_are_soft(self):
        snap, f = self.run_week(zone_good(), fail={"cert", "ct", "rdap"})
        k = by_key(f)
        self.assertIn("cert", snap["errors"])
        self.assertEqual(k["addresses"].status, checks.INFO)
        self.assertEqual(k["domain"].status, checks.INFO)
        self.assertEqual(k["cert"].status, checks.WARN)

    def test_lookalikes_skipped(self):
        snap = checks.collect("shop.com", net=fake_net(zone_good()), check_lookalikes=False, workers=2)
        self.assertNotIn("lookalikes", by_key(checks.evaluate(snap, None, now=NOW)))

    def test_rdap_error_message(self):
        _, f = self.run_week(zone_good(), fail={"rdap"})
        self.assertIn("couldn't reach", by_key(f)["domain"].summary)

    def test_store_keeps_last_good_values(self):
        with tempfile.TemporaryDirectory() as d:
            st = Store(d)
            week1, _ = self.run_week(zone_good())
            st.save(week1)
            week2, _ = self.run_week(zone_good(), fail={"ct"})
            st.save(week2, st.last("shop.com"))
            self.assertEqual(st.last("shop.com")["web_addresses"], ["shop.com", "www.shop.com"])


class TestReport(unittest.TestCase):
    def test_text_and_html(self):
        z = zone_good(TXT=[])
        z["_dmarc.shop.com"]["TXT"] = []
        snap = checks.collect("shop.com", net=fake_net(z), workers=2)
        f = checks.evaluate(snap, None, now=NOW)
        t = report.text("shop.com", f, client="Sam", when=NOW)
        h = report.html_report("shop.com", f, client="Sam <b>", when=NOW)
        self.assertIn("Hi Sam,", t)
        self.assertIn("What to do:", t)
        self.assertIn("public information", t)
        self.assertIn("Sam &lt;b&gt;", h)
        self.assertIn("needs attention", report.subject("shop.com", f))
        self.assertLess(t.index("fake emails"), t.index("Website padlock"))  # problems listed first


if __name__ == "__main__":
    unittest.main()
