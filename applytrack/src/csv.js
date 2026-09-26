export const CSV_COLUMNS = [
  ["title", "Title"],
  ["company", "Company"],
  ["location", "Location"],
  ["salary", "Salary"],
  ["status", "Status"],
  ["url", "URL"],
  ["source", "Source"],
  ["notes", "Notes"],
  ["followUpAt", "Follow up"],
  ["appliedAt", "Applied"],
  ["createdAt", "Saved"],
];
const DATE_FIELDS = new Set(["followUpAt", "appliedAt", "createdAt"]);

const isoDate = (ts) => (ts ? new Date(ts).toISOString().slice(0, 10) : "");

function cell(value) {
  let s = String(value ?? "");
  // Neutralise spreadsheet formula injection from scraped page text.
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(jobs) {
  const rows = [CSV_COLUMNS.map(([, h]) => h)];
  for (const j of jobs) rows.push(CSV_COLUMNS.map(([k]) => (DATE_FIELDS.has(k) ? isoDate(j[k]) : j[k])));
  return rows.map((r) => r.map(cell).join(",")).join("\r\n");
}

export function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  text = text.replace(/^﻿/, "");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); rows.push(row); row = []; field = "";
    } else field += ch;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim()));
}

// Maps CSV rows (with a header row) to job fields. Accepts our own export and common variants.
export function csvToJobs(text) {
  const [header, ...rows] = parseCsv(text);
  if (!header) return [];
  const aliases = {
    title: ["title", "job title", "position", "role"],
    company: ["company", "employer", "company name"],
    location: ["location"],
    salary: ["salary", "pay", "compensation"],
    status: ["status", "stage"],
    url: ["url", "link", "job url", "posting url"],
    source: ["source"],
    notes: ["notes", "note"],
    followUpAt: ["follow up", "follow-up", "followup"],
    appliedAt: ["applied", "date applied", "applied on"],
    createdAt: ["saved", "created", "date saved"],
  };
  const index = {};
  header.forEach((h, i) => {
    const key = Object.keys(aliases).find((k) => aliases[k].includes(h.trim().toLowerCase()));
    if (key && !(key in index)) index[key] = i;
  });
  return rows
    .map((r) => {
      const job = {};
      for (const [k, i] of Object.entries(index)) {
        let v = (r[i] || "").trim().replace(/^'(?=[=+\-@])/, "");
        if (DATE_FIELDS.has(k)) {
          const t = Date.parse(v);
          v = Number.isNaN(t) ? null : t;
        } else if (k === "status") v = v.toLowerCase();
        job[k] = v;
      }
      return job;
    })
    .filter((j) => j.title || j.company || j.url);
}
