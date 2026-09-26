import { STATUSES, addJob, deleteJob, getJobs, importJobs, onJobsChanged, updateJob } from "./storage.js";
import { activateLicense, deactivateLicense, getLicense, isPro, paymentsConfigured } from "./license.js";
import { csvToJobs, toCsv } from "./csv.js";
import { CONFIG } from "./config.js";

const $ = (id) => document.getElementById(id);
const DAY = 24 * 60 * 60 * 1000;

let jobs = [];
let pro = false;
let editingId = null;
let query = "";

// Tiny DOM builder. Page-scraped text only ever goes through textContent.
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c != null && c !== false) el.append(c);
  return el;
}

function ago(ts) {
  const d = Math.floor((Date.now() - ts) / DAY);
  if (d <= 0) return "today";
  if (d === 1) return "yesterday";
  if (d < 30) return `${d}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const isDue = (j) => j.followUpAt && j.followUpAt <= Date.now() && !["offer", "rejected"].includes(j.status);

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.add("hidden"), 2600);
}

function matches(j) {
  if (!query) return true;
  return [j.title, j.company, j.location, j.notes, j.salary].some((v) => (v || "").toLowerCase().includes(query));
}

function renderStats() {
  const applied = jobs.filter((j) => j.appliedAt);
  const reached = (j, s) => (j.history || []).some((e) => e.status === s) || j.status === s;
  const interviews = applied.filter((j) => reached(j, "interview") || reached(j, "offer")).length;
  const weekAgo = Date.now() - 7 * DAY;
  const stats = [
    ["Tracked", jobs.length],
    ["Applied this week", applied.filter((j) => j.appliedAt >= weekAgo).length],
    ["Interview rate", applied.length ? `${Math.round((interviews / applied.length) * 100)}%` : "–"],
    ["Offers", jobs.filter((j) => j.status === "offer").length],
    ["Follow-ups due", jobs.filter(isDue).length, "warn"],
  ];
  $("stats").replaceChildren(
    ...stats.map(([label, value, cls]) =>
      h("div", { class: `stat ${cls && value ? cls : ""}` }, h("div", { class: "value" }, String(value)), h("div", { class: "label" }, label)),
    ),
  );
}

function card(job) {
  return h(
    "button",
    {
      class: "card",
      draggable: "true",
      "data-id": job.id,
      style: `--dot: var(--s-${job.status})`,
      onclick: () => openEditor(job.id),
      ondragstart: (e) => {
        e.dataTransfer.setData("text/plain", job.id);
        e.dataTransfer.effectAllowed = "move";
        e.currentTarget.classList.add("dragging");
      },
      ondragend: (e) => e.currentTarget.classList.remove("dragging"),
    },
    h("div", { class: "t" }, job.title || "Untitled job"),
    job.company && h("div", { class: "c" }, job.company),
    h(
      "div",
      { class: "meta" },
      job.location && h("span", {}, job.location),
      job.salary && h("span", {}, job.salary),
      h("span", {}, ago(job.appliedAt || job.createdAt)),
      isDue(job) && h("span", { class: "due" }, "Follow up"),
    ),
  );
}

function renderBoard() {
  const visible = jobs.filter(matches);
  $("board").replaceChildren(
    ...STATUSES.map((s) => {
      const items = visible.filter((j) => j.status === s.id);
      const col = h(
        "section",
        { class: "column", "data-status": s.id, style: `--dot: var(--s-${s.id})`, "aria-label": s.label },
        h("h3", {}, s.label, h("span", { class: "count" }, String(items.length))),
        items.length ? items.map(card) : h("div", { class: "empty" }, query ? "No matches" : s.id === "saved" ? "Save a job from any posting" : "Drag jobs here"),
      );
      col.addEventListener("dragover", (e) => {
        e.preventDefault();
        col.classList.add("drop");
      });
      col.addEventListener("dragleave", (e) => {
        if (!col.contains(e.relatedTarget)) col.classList.remove("drop");
      });
      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.classList.remove("drop");
        const id = e.dataTransfer.getData("text/plain");
        const job = jobs.find((j) => j.id === id);
        if (job && job.status !== s.id) {
          await updateJob(id, { status: s.id });
          toast(`Moved to ${s.label}`);
        }
      });
      return col;
    }),
  );
}

function renderPlan() {
  $("plan").textContent = pro ? "Pro ✓" : "Upgrade";
  $("plan").classList.toggle("primary", !pro);
  $("export").title = pro ? "" : "Pro feature";
}

function render() {
  renderStats();
  renderBoard();
  renderPlan();
}

// ---------- Editor ----------

const toDateInput = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const fromDateInput = (v) => {
  if (!v) return null;
  const [y, m, d] = v.split("-").map(Number);
  return new Date(y, m - 1, d, 9, 0, 0).getTime();
};

function openEditor(id) {
  const job = id ? jobs.find((j) => j.id === id) : null;
  if (id && !job) return;
  if (!job && !pro && jobs.length >= CONFIG.freeLimit) {
    toast(`Free plan tracks up to ${CONFIG.freeLimit} jobs`);
    openUpgrade();
    return;
  }
  editingId = job?.id || null;
  const f = $("editor-form");
  $("editor-heading").textContent = job ? "Edit job" : "Add job";
  f.title.value = job?.title || "";
  f.company.value = job?.company || "";
  f.status.value = job?.status || "saved";
  f.location.value = job?.location || "";
  f.salary.value = job?.salary || "";
  f.url.value = job?.url || "";
  f.notes.value = job?.notes || "";
  f.followUp.value = toDateInput(job?.followUpAt);
  f.followUp.disabled = !pro;
  $("followup-lock").classList.toggle("hidden", pro);
  $("desc-wrap").classList.toggle("hidden", !job?.description);
  $("desc-wrap").open = false;
  $("f-description").textContent = job?.description || "";
  $("history-wrap").classList.toggle("hidden", !job);
  $("history").replaceChildren(
    ...(job?.history || []).map((e) =>
      h("li", {}, `${STATUSES.find((s) => s.id === e.status)?.label || e.status} · ${new Date(e.at).toLocaleString()}`),
    ),
  );
  $("delete").classList.toggle("hidden", !job);
  const url = safeUrl(job?.url);
  $("open-url").classList.toggle("hidden", !url);
  if (url) $("open-url").href = url;
  $("editor").showModal();
  f.title.focus();
}

function safeUrl(url) {
  try {
    const u = new URL(url);
    return /^https?:$/.test(u.protocol) ? u.href : "";
  } catch {
    return "";
  }
}

$("editor-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  const values = {
    title: f.title.value.trim(),
    company: f.company.value.trim(),
    status: f.status.value,
    location: f.location.value.trim(),
    salary: f.salary.value.trim(),
    url: f.url.value.trim(),
    notes: f.notes.value.trim(),
  };
  if (pro) values.followUpAt = fromDateInput(f.followUp.value);
  if (editingId) await updateJob(editingId, values);
  else await addJob({ ...values, source: "manual" });
  $("editor").close();
  toast(editingId ? "Saved" : "Job added");
});

$("delete").addEventListener("click", async () => {
  const job = jobs.find((j) => j.id === editingId);
  if (!job || !confirm(`Delete "${job.title || "this job"}"? This can't be undone.`)) return;
  await deleteJob(job.id);
  $("editor").close();
  toast("Job deleted");
});

for (const d of document.querySelectorAll("dialog")) {
  d.addEventListener("click", (e) => {
    if (e.target === d || e.target.matches("[data-close]")) d.close();
  });
  d.addEventListener("close", () => {
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  });
}

// ---------- Upgrade / license ----------

async function openUpgrade() {
  const lic = await getLicense();
  $("pro-pitch").classList.toggle("hidden", pro);
  $("pro-active").classList.toggle("hidden", !pro);
  $("pro-email").textContent = lic?.email ? ` for ${lic.email}` : "";
  $("buy").href = CONFIG.checkoutUrl;
  $("license-error").classList.toggle("hidden", !(lic && !lic.valid && lic.reason));
  $("license-error").textContent = lic?.reason || "";
  if (!paymentsConfigured()) {
    $("license-error").textContent = "Payments aren't set up in this build yet.";
    $("license-error").classList.remove("hidden");
  }
  $("upgrade").showModal();
}

$("activate").addEventListener("click", async () => {
  const btn = $("activate");
  btn.disabled = true;
  $("license-error").classList.add("hidden");
  try {
    await activateLicense($("license-key").value);
    pro = true;
    render();
    $("upgrade").close();
    toast("Pro unlocked. Thank you!");
  } catch (err) {
    $("license-error").textContent = err.message || "Couldn't reach the license server. Try again.";
    $("license-error").classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
});

$("deactivate").addEventListener("click", async () => {
  await deactivateLicense();
  pro = false;
  render();
  $("upgrade").close();
  toast("License removed");
});

// ---------- CSV ----------

$("export").addEventListener("click", () => {
  if (!pro) return openUpgrade();
  const blob = new Blob(["﻿" + toCsv(jobs)], { type: "text/csv;charset=utf-8" });
  const a = h("a", { href: URL.createObjectURL(blob), download: `applytrack-${toDateInput(Date.now())}.csv` });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
});

$("import").addEventListener("click", () => $("import-file").click());
$("import-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  let rows = csvToJobs(await file.text());
  if (!rows.length) return toast("No jobs found in that file");
  let note = "";
  if (!pro) {
    const room = Math.max(0, CONFIG.freeLimit - jobs.length);
    if (rows.length > room) note = ` (free plan limit: ${rows.length - room} skipped)`;
    rows = rows.slice(0, room);
  }
  const added = await importJobs(rows);
  toast(`Imported ${added} job${added === 1 ? "" : "s"}${note}`);
});

// ---------- Wiring ----------

$("f-status").innerHTML = STATUSES.map((s) => `<option value="${s.id}">${s.label}</option>`).join("");
for (const el of document.querySelectorAll("[data-free-limit]")) el.textContent = `${CONFIG.freeLimit} jobs`;
$("add").addEventListener("click", () => openEditor(null));
$("plan").addEventListener("click", openUpgrade);
$("search").addEventListener("input", (e) => {
  query = e.target.value.trim().toLowerCase();
  renderBoard();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
    e.preventDefault();
    $("search").focus();
  }
});

if (new URLSearchParams(location.search).get("welcome")) $("welcome").classList.remove("hidden");
$("dismiss-welcome").addEventListener("click", () => {
  $("welcome").classList.add("hidden");
  history.replaceState(null, "", location.pathname);
});

onJobsChanged((next) => {
  jobs = next;
  render();
});
chrome.storage.onChanged.addListener(async (changes, area) => {
  if (area === "local" && changes.license) {
    pro = await isPro();
    render();
  }
});

function handleHash() {
  const hash = location.hash.slice(1);
  if (hash === "upgrade") openUpgrade();
  else if (hash.startsWith("job=")) openEditor(hash.slice(4));
}

(async () => {
  [jobs, pro] = await Promise.all([getJobs(), isPro()]);
  render();
  handleHash();
  window.addEventListener("hashchange", handleHash);
})();
