import { test } from "node:test";
import assert from "node:assert/strict";
import { csvToJobs, parseCsv, toCsv } from "../src/csv.js";

test("round-trips jobs through CSV, including quotes, commas and newlines", () => {
  const jobs = [
    { title: 'Engineer, "Platform"', company: "Acme", notes: "line1\nline2", status: "applied", url: "https://a.example/1", appliedAt: Date.UTC(2026, 0, 5) },
  ];
  const [back] = csvToJobs(toCsv(jobs));
  assert.equal(back.title, 'Engineer, "Platform"');
  assert.equal(back.notes, "line1\nline2");
  assert.equal(back.status, "applied");
  assert.equal(new Date(back.appliedAt).toISOString().slice(0, 10), "2026-01-05");
});

test("neutralises spreadsheet formulas on export and restores them on import", () => {
  const csv = toCsv([{ title: "=HYPERLINK(\"http://evil\")", company: "@corp" }]);
  const [, row] = parseCsv(csv);
  assert.equal(row[0], "'=HYPERLINK(\"http://evil\")");
  assert.equal(row[1], "'@corp");
  const [back] = csvToJobs(csv);
  assert.equal(back.title, '=HYPERLINK("http://evil")');
});

test("imports common header variants and skips blank rows", () => {
  const jobs = csvToJobs("Job Title,Employer,Link,Stage\r\nQA Lead,Beta Inc,https://b.example,Interview\r\n,,,\r\n");
  assert.deepEqual(jobs, [{ title: "QA Lead", company: "Beta Inc", url: "https://b.example", status: "interview" }]);
});
