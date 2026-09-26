import { STATUSES, addJob, findJobByUrl, getJobs, updateJob } from "./storage.js";
import { isPro } from "./license.js";
import { extractJob } from "./extract.js";
import { CONFIG } from "./config.js";

const $ = (id) => document.getElementById(id);
const FIELDS = ["title", "company", "location", "salary", "notes"];

let extracted = {};
let existing = null;

$("status").innerHTML = STATUSES.map((s) => `<option value="${s.id}">${s.label}</option>`).join("");

async function readActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url || !/^https?:/.test(tab.url)) return { url: "" };
  try {
    const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractJob });
    return res?.result || { url: tab.url, title: tab.title };
  } catch {
    return { url: tab.url, title: tab.title || "" };
  }
}

function notice(msg) {
  $("notice").textContent = msg;
  $("notice").classList.toggle("hidden", !msg);
}

async function init() {
  const [pro, jobs, page] = await Promise.all([isPro(), getJobs(), readActiveTab()]);
  extracted = page;
  $("plan").textContent = pro ? "Pro" : "Free";
  $("plan").classList.toggle("pro-badge", pro);
  $("usage").textContent = pro ? `${jobs.length} jobs tracked` : `${jobs.length} / ${CONFIG.freeLimit} free jobs used`;

  existing = page.url ? await findJobByUrl(page.url) : null;
  if (existing) {
    for (const f of FIELDS) $(f).value = existing[f] || "";
    $("status").value = existing.status;
    $("save").textContent = "Update job";
    notice("This job is already on your board.");
  } else {
    if (!pro && jobs.length >= CONFIG.freeLimit) {
      $("limit-text").textContent = `Free plan tracks up to ${CONFIG.freeLimit} jobs. Pro is unlimited and adds follow-up reminders and CSV export.`;
      $("limit").classList.remove("hidden");
      return;
    }
    for (const f of FIELDS) $(f).value = page[f] || "";
    if (!page.url) notice("Can't read this page. Fill in the details manually.");
    else if (!page.title) notice("Couldn't detect the job details. Fill them in below.");
  }
  $("form").classList.remove("hidden");
  $("title").focus();
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const values = Object.fromEntries(FIELDS.map((f) => [f, $(f).value.trim()]));
  values.status = $("status").value;
  $("save").disabled = true;
  try {
    if (existing) {
      await updateJob(existing.id, values);
      $("saved-text").textContent = "Job updated.";
    } else {
      await addJob({
        ...values,
        url: extracted.url || "",
        source: extracted.source || "",
        description: extracted.description || "",
      });
      $("saved-text").textContent = "Saved to your board.";
    }
    $("form").classList.add("hidden");
    notice("");
    $("saved").classList.remove("hidden");
  } catch (err) {
    $("error").textContent = err.message;
    $("error").classList.remove("hidden");
    $("save").disabled = false;
  }
});

init();
