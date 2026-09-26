// Edit these before publishing. See README.md → "Set up payments".
export const CONFIG = {
  // Gumroad product ID (Product → Content → "License key" section). Empty = payments disabled.
  gumroadProductId: "",
  // Public Gumroad checkout link shown on the Upgrade button.
  checkoutUrl: "https://gumroad.com/",
  // Jobs a free user can track before upgrading.
  freeLimit: 20,
  // How often a stored license is re-verified, and how long it stays valid offline.
  licenseRecheckDays: 7,
  licenseOfflineGraceDays: 30,
};
