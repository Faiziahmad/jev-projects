// Injected into the job page with chrome.scripting.executeScript({ func: extractJob }).
// Must stay self-contained: no imports, no references to outer scope.
export function extractJob() {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const text = (sel) => {
    for (const s of [].concat(sel)) {
      const el = document.querySelector(s);
      if (el && clean(el.textContent)) return clean(el.textContent);
    }
    return "";
  };
  const meta = (name) =>
    clean(document.querySelector(`meta[property="${name}"], meta[name="${name}"]`)?.content);
  const stripHtml = (html) => {
    const div = document.createElement("div");
    div.innerHTML = html || "";
    return (div.innerText || div.textContent || "").replace(/\n{3,}/g, "\n\n").trim();
  };

  // 1. schema.org JobPosting (LinkedIn guest pages, Indeed, Glassdoor, Workday, Greenhouse, most ATSs)
  const findPosting = (node) => {
    if (!node || typeof node !== "object") return null;
    if (Array.isArray(node)) {
      for (const n of node) {
        const hit = findPosting(n);
        if (hit) return hit;
      }
      return null;
    }
    const type = [].concat(node["@type"] || []);
    if (type.includes("JobPosting")) return node;
    return findPosting(node["@graph"]);
  };
  let posting = null;
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      posting = findPosting(JSON.parse(s.textContent));
    } catch {}
    if (posting) break;
  }

  const ld = {};
  if (posting) {
    ld.title = clean(posting.title);
    const org = [].concat(posting.hiringOrganization || [])[0];
    ld.company = clean(typeof org === "string" ? org : org?.name);
    const locs = [].concat(posting.jobLocation || []).map((l) => {
      const a = l?.address || {};
      if (typeof a === "string") return clean(a);
      const country = typeof a.addressCountry === "string" ? a.addressCountry : a.addressCountry?.name;
      return [a.addressLocality, a.addressRegion, country].filter(Boolean).join(", ");
    });
    ld.location = clean(locs.filter(Boolean).join(" · "));
    if (/TELECOMMUTE/i.test(posting.jobLocationType || "")) ld.location = ld.location ? `${ld.location} (Remote)` : "Remote";
    const pay = posting.baseSalary || posting.estimatedSalary;
    const v = pay && ([].concat(pay)[0].value ?? [].concat(pay)[0]);
    if (v && typeof v === "object") {
      const n = (x) => (x == null || x === "" ? "" : Number(x).toLocaleString("en-US"));
      const range = v.minValue != null && v.maxValue != null ? `${n(v.minValue)}–${n(v.maxValue)}` : n(v.value ?? v.minValue ?? v.maxValue);
      const cur = [].concat(pay)[0].currency || "";
      const unit = (v.unitText || "").toLowerCase();
      if (range) ld.salary = clean(`${cur} ${range}${unit ? ` / ${unit}` : ""}`);
    }
    ld.description = stripHtml(posting.description);
  }

  // 2. Site-specific selectors for pages without structured data (e.g. LinkedIn logged-in view)
  const host = location.hostname;
  const site = {};
  let url = location.href;
  let source = host.replace(/^www\./, "");
  if (host.endsWith("linkedin.com")) {
    source = "LinkedIn";
    site.title = text([".job-details-jobs-unified-top-card__job-title h1", ".job-details-jobs-unified-top-card__job-title", "h1.top-card-layout__title", ".jobs-unified-top-card__job-title", "h1"]);
    site.company = text([".job-details-jobs-unified-top-card__company-name a", ".job-details-jobs-unified-top-card__company-name", ".topcard__org-name-link", ".jobs-unified-top-card__company-name"]);
    site.location = text([".job-details-jobs-unified-top-card__primary-description-container .tvm__text", ".topcard__flavor--bullet", ".jobs-unified-top-card__bullet"]);
    site.description = text(["#job-details", ".jobs-description__content", ".show-more-less-html__markup"]);
    const id = new URLSearchParams(location.search).get("currentJobId") || location.pathname.match(/\/jobs\/view\/(?:[^/]*-)?(\d+)/)?.[1];
    if (id) url = `https://www.linkedin.com/jobs/view/${id}/`;
  } else if (/(^|\.)indeed\./.test(host)) {
    source = "Indeed";
    site.title = text(['[data-testid="jobsearch-JobInfoHeader-title"]', "h1.jobsearch-JobInfoHeader-title", "h1"]).replace(/\s*-\s*job post$/i, "");
    site.company = text(['[data-testid="inlineHeader-companyName"]', '[data-company-name="true"]', ".jobsearch-CompanyInfoContainer a"]);
    site.location = text(['[data-testid="inlineHeader-companyLocation"]', '[data-testid="job-location"]', ".jobsearch-JobInfoHeader-subtitle > div:last-child"]);
    site.salary = text(["#salaryInfoAndJobType span", '[data-testid="attribute_snippet_testid"]']);
    site.description = text(["#jobDescriptionText"]);
    const jk = new URLSearchParams(location.search).get("vjk") || new URLSearchParams(location.search).get("jk");
    if (jk) url = `${location.origin}/viewjob?jk=${jk}`;
  } else if (host.endsWith("greenhouse.io")) {
    source = "Greenhouse";
    site.title = text(["h1.app-title", ".job__title h1", "h1"]);
    site.company = text([".company-name"]).replace(/^at\s+/i, "");
    site.location = text([".location", ".job__location"]);
  } else if (host.endsWith("lever.co")) {
    source = "Lever";
    site.title = text([".posting-headline h2", "h2"]);
    site.company = (location.pathname.split("/")[1] || "").replace(/-/g, " ");
    site.location = text([".posting-categories .location", ".location"]);
  } else if (host.endsWith("glassdoor.com")) {
    source = "Glassdoor";
  } else if (host.includes("myworkdayjobs.com")) {
    source = "Workday";
    site.title = text(['[data-automation-id="jobPostingHeader"]']);
    site.location = text(['[data-automation-id="locations"] dd']);
  }

  // 3. Generic fallback
  const knownBoard = source !== host.replace(/^www\./, "");
  if (site.salary && !/\d/.test(site.salary)) site.salary = "";
  const generic = {
    title: text("h1") || meta("og:title") || clean(document.title),
    // On job boards og:site_name is the board ("LinkedIn"), not the employer.
    company: knownBoard ? "" : meta("og:site_name"),
  };

  const pick = (field) => ld[field] || site[field] || generic[field] || "";
  let title = pick("title");
  let company = pick("company");
  // "Senior Engineer at Acme" / "Senior Engineer - Acme" style titles
  const m = !company && title.match(/^(.+?)\s+(?:at|@|[-–|])\s+(.+)$/);
  if (m) [title, company] = [m[1], m[2]];

  return {
    title: title.slice(0, 200),
    company: company.slice(0, 120),
    location: pick("location").slice(0, 160),
    salary: pick("salary").slice(0, 80),
    description: pick("description").slice(0, 20000),
    url,
    source,
    structured: Boolean(posting),
  };
}
