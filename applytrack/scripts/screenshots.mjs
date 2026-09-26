// Loads the unpacked extension with demo data and captures store screenshots into store/screenshots/.
// Usage: node scripts/screenshots.mjs
import { chromium } from "playwright";
import { createServer } from "node:http";
import { mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const out = join(root, "store/screenshots");
mkdirSync(out, { recursive: true });

const server = createServer((req, res) => {
  try {
    res.setHeader("content-type", "text/html");
    res.end(readFileSync(join(root, "tests/fixtures", req.url.slice(1) || "jsonld.html")));
  } catch {
    res.statusCode = 404;
    res.end();
  }
}).listen(0);
const port = server.address().port;

const context = await chromium.launchPersistentContext(mkdtempSync(join(tmpdir(), "applytrack-")), {
  channel: "chromium",
  args: [`--disable-extensions-except=${root}`, `--load-extension=${root}`],
  viewport: { width: 1280, height: 800 },
  colorScheme: process.env.DARK ? "dark" : "light",
});
const sw = context.serviceWorkers()[0] || (await context.waitForEvent("serviceworker"));
const id = new URL(sw.url()).host;
const ext = (p) => `chrome-extension://${id}/src/${p}`;
for (const p of context.pages()) if (p.url().includes("welcome")) await p.close();

const d = (days, h = 10) => Date.now() - days * 864e5 + h * 36e5 * 0;
const job = (title, company, location, salary, status, days, extra = {}) => ({
  id: crypto.randomUUID(), title, company, location, salary, status, url: `https://example.com/jobs/${encodeURIComponent(title)}`,
  source: "LinkedIn", description: "", notes: "", followUpAt: null, followUpNotified: false,
  createdAt: d(days + 2), updatedAt: d(days), appliedAt: status === "saved" ? null : d(days),
  history: [{ status: "saved", at: d(days + 2) }, ...(status === "saved" ? [] : [{ status: "applied", at: d(days) }]), ...(["interview", "offer"].includes(status) ? [{ status: "interview", at: d(days - 1) }] : []), ...(status === "offer" ? [{ status: "offer", at: d(0) }] : [])],
  ...extra,
});
const demo = [
  job("Senior Frontend Engineer", "Northwind Labs", "Berlin (Remote)", "EUR 75,000–95,000 / year", "saved", 0),
  job("Product Designer", "Lumen Health", "London", "£60k–£70k", "saved", 1),
  job("Full-Stack Developer", "Brightpath", "Remote", "", "saved", 3),
  job("React Engineer", "Kite & Co", "Amsterdam", "EUR 70k", "applied", 2),
  job("Software Engineer II", "Harbor Analytics", "New York, NY", "$140k–$165k", "applied", 6, { followUpAt: d(0) - 3600e3 }),
  job("Frontend Developer", "Orbit Payments", "Remote (EU)", "", "applied", 9),
  job("UI Engineer", "Maple Street", "Toronto", "CA$110k", "applied", 12),
  job("Staff Engineer, Web", "Cobalt AI", "San Francisco", "$210k–$240k", "interview", 10, { notes: "Tech screen Thu 3pm with Priya" }),
  job("Senior Web Developer", "Fjord Travel", "Oslo (Hybrid)", "NOK 900k", "interview", 14),
  job("Frontend Lead", "Parcel Nine", "Remote", "$175k", "offer", 20),
  job("JavaScript Engineer", "Quartz Media", "Paris", "", "rejected", 18),
];

const board = await context.newPage();
await board.goto(ext("board.html"));
await board.evaluate((jobs) => chrome.storage.local.set({ jobs }), demo);
await board.reload();
await board.waitForSelector(".card");
await board.screenshot({ path: join(out, "1-board.png") });

await board.locator(".card", { hasText: "Staff Engineer" }).click();
await board.waitForTimeout(200);
await board.screenshot({ path: join(out, "2-editor.png") });
await board.keyboard.press("Escape");

await board.click("#plan");
await board.waitForTimeout(200);
await board.screenshot({ path: join(out, "3-upgrade.png") });
await board.keyboard.press("Escape");

// Popup: activeTab is only granted on a real toolbar click, so run the extractor on the job
// page directly and hand its result to the popup through stubbed tab/scripting APIs.
const jobPage = await context.newPage();
await jobPage.goto(`http://localhost:${port}/jsonld.html`);
const extractSrc = readFileSync(join(root, "src/extract.js"), "utf8").replace("export function", "function");
const extracted = await jobPage.evaluate(`(() => { ${extractSrc}; return extractJob(); })()`);
const popup = await context.newPage();
await popup.addInitScript((result) => {
  chrome.tabs.query = async () => [{ id: 1, url: result.url }];
  chrome.scripting.executeScript = async () => [{ result }];
}, extracted);
await popup.setViewportSize({ width: 360, height: 560 });
popup.on("pageerror", (e) => console.error("popup error:", e.message));
popup.on("console", (m) => console.log("popup:", m.text()));
await popup.goto(ext("popup.html"));
await popup.waitForSelector("#form:not(.hidden)");
await popup.waitForFunction(() => document.getElementById("title").value);
await popup.screenshot({ path: join(out, "4-popup.png") });

await context.close();
server.close();
console.log(`Saved screenshots to ${out}`);
