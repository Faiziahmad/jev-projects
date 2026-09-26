import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chromium } from "playwright";

const root = new URL("..", import.meta.url).pathname;
const src = readFileSync(`${root}src/extract.js`, "utf8").replace("export function", "function");
const fixture = (name) => readFileSync(`${root}tests/fixtures/${name}`, "utf8");

let browser;
before(async () => (browser = await chromium.launch()));
after(() => browser?.close());

// Serves a fixture at a real-looking URL so hostname-based rules apply.
async function extractFrom(url, name) {
  const page = await browser.newPage();
  await page.route("**/*", (route) => route.fulfill({ contentType: "text/html", body: fixture(name) }));
  await page.goto(url);
  const result = await page.evaluate(`(() => { ${src}; return extractJob(); })()`);
  await page.close();
  return result;
}

test("reads schema.org JobPosting inside @graph", async () => {
  const job = await extractFrom("https://careers.northwind.example/jobs/42?utm_source=x", "jsonld.html");
  assert.equal(job.title, "Senior Frontend Engineer");
  assert.equal(job.company, "Northwind Labs");
  assert.equal(job.location, "Berlin, DE (Remote)");
  assert.equal(job.salary, "EUR 75,000–95,000 / year");
  assert.match(job.description, /Build the best dashboard/);
  assert.doesNotMatch(job.description, /<b>/);
  assert.equal(job.structured, true);
});

test("LinkedIn logged-in view uses DOM selectors and canonical job URL", async () => {
  const job = await extractFrom("https://www.linkedin.com/jobs/search/?currentJobId=3901234567&keywords=backend", "linkedin.html");
  assert.equal(job.title, "Backend Engineer");
  assert.equal(job.company, "Acme Robotics");
  assert.equal(job.location, "Austin, TX");
  assert.equal(job.source, "LinkedIn");
  assert.equal(job.url, "https://www.linkedin.com/jobs/view/3901234567/");
});

test("generic page splits 'Title at Company'", async () => {
  const job = await extractFrom("https://jobs.pinecone.example/analyst", "generic.html");
  assert.equal(job.title, "Data Analyst");
  assert.equal(job.company, "Pinecone Foods");
});

test("markup in page text is returned as plain text", async () => {
  const job = await extractFrom("https://evil.example/", "xss.html");
  assert.equal(job.title, '<img src=x onerror="window.__pwned=1"> Engineer');
});
