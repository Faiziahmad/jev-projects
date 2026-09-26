// Renders icons/icon.svg to the PNG sizes Chrome needs. Usage: node scripts/make-icons.mjs
import { chromium } from "playwright";
import { readFileSync } from "node:fs";

const root = new URL("..", import.meta.url).pathname;
const svg = readFileSync(`${root}icons/icon.svg`, "utf8");
const browser = await chromium.launch();
const page = await browser.newPage();
for (const size of [16, 32, 48, 128]) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(
    `<style>html,body{margin:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${svg}`,
  );
  await page.locator("svg").screenshot({ path: `${root}icons/icon${size}.png`, omitBackground: true });
}
await browser.close();
