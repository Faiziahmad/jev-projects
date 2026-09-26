import { getJobs, updateJob, onJobsChanged } from "./storage.js";
import { isPro, recheckLicense } from "./license.js";

const CHECK_ALARM = "followup-check";

chrome.runtime.onInstalled.addListener(({ reason }) => {
  chrome.alarms.create(CHECK_ALARM, { periodInMinutes: 30, delayInMinutes: 1 });
  if (reason === "install") chrome.tabs.create({ url: chrome.runtime.getURL("src/board.html?welcome=1") });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(CHECK_ALARM, { periodInMinutes: 30, delayInMinutes: 1 });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== CHECK_ALARM) return;
  await recheckLicense();
  await checkFollowUps();
});

onJobsChanged(updateBadge);
updateBadge();

function dueJobs(jobs) {
  const now = Date.now();
  return jobs.filter((j) => j.followUpAt && j.followUpAt <= now && !["offer", "rejected"].includes(j.status));
}

async function updateBadge(jobs) {
  const due = dueJobs(jobs || (await getJobs())).length;
  await chrome.action.setBadgeBackgroundColor({ color: "#d9480f" });
  await chrome.action.setBadgeText({ text: due ? String(due) : "" });
}

async function checkFollowUps() {
  const jobs = await getJobs();
  await updateBadge(jobs);
  if (!(await isPro())) return;
  for (const job of dueJobs(jobs).filter((j) => !j.followUpNotified)) {
    chrome.notifications.create(`followup:${job.id}`, {
      type: "basic",
      iconUrl: chrome.runtime.getURL("icons/icon128.png"),
      title: "Time to follow up",
      message: `${job.title || "Job"}${job.company ? ` at ${job.company}` : ""}`,
      priority: 1,
    });
    await updateJob(job.id, { followUpNotified: true });
  }
}

chrome.notifications.onClicked.addListener((notificationId) => {
  const [kind, id] = notificationId.split(":");
  if (kind !== "followup") return;
  chrome.tabs.create({ url: chrome.runtime.getURL(`src/board.html#job=${id}`) });
  chrome.notifications.clear(notificationId);
});
