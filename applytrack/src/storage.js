export const STATUSES = [
  { id: "saved", label: "Saved" },
  { id: "applied", label: "Applied" },
  { id: "interview", label: "Interview" },
  { id: "offer", label: "Offer" },
  { id: "rejected", label: "Rejected" },
];

const JOBS_KEY = "jobs";

export function normalizeUrl(url) {
  if (!url) return "";
  try {
    const u = new URL(url);
    u.hash = "";
    for (const p of [...u.searchParams.keys()]) {
      if (/^(utm_|ref|refId|trackingId|trk|src|from)/i.test(p)) u.searchParams.delete(p);
    }
    return u.toString().replace(/\/$/, "");
  } catch {
    return url.trim();
  }
}

export async function getJobs() {
  const data = await chrome.storage.local.get(JOBS_KEY);
  return data[JOBS_KEY] || [];
}

async function setJobs(jobs) {
  await chrome.storage.local.set({ [JOBS_KEY]: jobs });
}

export async function findJobByUrl(url) {
  const key = normalizeUrl(url);
  if (!key) return null;
  return (await getJobs()).find((j) => normalizeUrl(j.url) === key) || null;
}

export async function addJob(fields) {
  const jobs = await getJobs();
  const now = Date.now();
  const status = fields.status || "saved";
  const job = {
    id: crypto.randomUUID(),
    title: "",
    company: "",
    location: "",
    salary: "",
    url: "",
    source: "",
    description: "",
    notes: "",
    followUpAt: null,
    followUpNotified: false,
    ...fields,
    status,
    appliedAt: fields.appliedAt ?? (status === "saved" ? null : now),
    createdAt: now,
    updatedAt: now,
    history: [{ status, at: now }],
  };
  jobs.unshift(job);
  await setJobs(jobs);
  return job;
}

export async function updateJob(id, patch) {
  const jobs = await getJobs();
  const job = jobs.find((j) => j.id === id);
  if (!job) return null;
  const now = Date.now();
  if (patch.status && patch.status !== job.status) {
    job.history = [...(job.history || []), { status: patch.status, at: now }];
    if (patch.status !== "saved" && !job.appliedAt) job.appliedAt = now;
  }
  if ("followUpAt" in patch && patch.followUpAt !== job.followUpAt) job.followUpNotified = false;
  Object.assign(job, patch, { updatedAt: now });
  await setJobs(jobs);
  return job;
}

export async function deleteJob(id) {
  await setJobs((await getJobs()).filter((j) => j.id !== id));
}

export async function importJobs(list) {
  const jobs = await getJobs();
  const seen = new Set(jobs.map((j) => normalizeUrl(j.url)).filter(Boolean));
  const now = Date.now();
  let added = 0;
  for (const fields of list) {
    const key = normalizeUrl(fields.url);
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    const status = STATUSES.some((s) => s.id === fields.status) ? fields.status : "saved";
    const createdAt = fields.createdAt || now;
    jobs.push({
      title: "", company: "", location: "", salary: "", url: "", source: "import",
      description: "", notes: "", followUpAt: null, appliedAt: null,
      ...fields,
      id: crypto.randomUUID(),
      status,
      followUpNotified: false,
      createdAt,
      updatedAt: now,
      history: [{ status, at: createdAt }],
    });
    added++;
  }
  await setJobs(jobs);
  return added;
}

export function onJobsChanged(cb) {
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes[JOBS_KEY]) cb(changes[JOBS_KEY].newValue || []);
  });
}
