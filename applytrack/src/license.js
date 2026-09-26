import { CONFIG } from "./config.js";

const LICENSE_KEY = "license";
const DAY = 24 * 60 * 60 * 1000;

export function paymentsConfigured() {
  return Boolean(CONFIG.gumroadProductId);
}

export async function getLicense() {
  const data = await chrome.storage.local.get(LICENSE_KEY);
  return data[LICENSE_KEY] || null;
}

export async function isPro() {
  const lic = await getLicense();
  if (!lic?.valid) return false;
  return Date.now() - lic.verifiedAt < CONFIG.licenseOfflineGraceDays * DAY;
}

async function callGumroad(key, incrementUses) {
  const body = new URLSearchParams({
    product_id: CONFIG.gumroadProductId,
    license_key: key,
    increment_uses_count: String(incrementUses),
  });
  const res = await fetch("https://api.gumroad.com/v2/licenses/verify", { method: "POST", body });
  const data = await res.json().catch(() => ({}));
  if (!data.success) return { ok: false, reason: data.message || "That license key was not found." };
  const p = data.purchase || {};
  if (p.refunded || p.chargebacked || p.disputed) return { ok: false, reason: "This purchase was refunded or disputed." };
  if (p.subscription_ended_at || p.subscription_cancelled_at || p.subscription_failed_at) {
    return { ok: false, reason: "This subscription is no longer active." };
  }
  return { ok: true, email: p.email || "" };
}

// Throws with a user-facing message when the key is rejected.
export async function activateLicense(rawKey) {
  const key = rawKey.trim();
  if (!paymentsConfigured()) throw new Error("Payments are not configured in this build.");
  if (!key) throw new Error("Enter your license key.");
  const result = await callGumroad(key, true);
  if (!result.ok) throw new Error(result.reason);
  const lic = { key, valid: true, email: result.email, verifiedAt: Date.now() };
  await chrome.storage.local.set({ [LICENSE_KEY]: lic });
  return lic;
}

export async function deactivateLicense() {
  await chrome.storage.local.remove(LICENSE_KEY);
}

// Re-checks a stored key. Network errors keep the license (offline grace period applies).
export async function recheckLicense() {
  const lic = await getLicense();
  if (!lic?.key || !paymentsConfigured()) return;
  if (Date.now() - lic.verifiedAt < CONFIG.licenseRecheckDays * DAY) return;
  let result;
  try {
    result = await callGumroad(lic.key, false);
  } catch {
    return;
  }
  await chrome.storage.local.set({
    [LICENSE_KEY]: result.ok ? { ...lic, verifiedAt: Date.now() } : { ...lic, valid: false, reason: result.reason },
  });
}
