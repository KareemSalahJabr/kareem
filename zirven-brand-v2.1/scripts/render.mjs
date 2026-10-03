#!/usr/bin/env node
/**
 * Zirven V2.1 — rasteriser.
 *
 *   node scripts/render.mjs                 favicons, app icons, logo PNGs and every page preview
 *   node scripts/render.mjs icons           favicons, app icons and logo PNGs only
 *   node scripts/render.mjs previews        page previews only
 *   node scripts/render.mjs page <in.html> <out.png> [width=1440] [height=900] [fullPage=1] [scale=1]
 *
 * Uses Playwright's bundled Chromium (PLAYWRIGHT_BROWSERS_PATH) — no other dependencies.
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch {
  ({ chromium } = require('/opt/node22/lib/node_modules/playwright'));
}

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const P = (...p) => join(ROOT, ...p);

// Page previews: [source html, preview png, viewport width, viewport height, fullPage]
// Application pages first: the composite pages (brand board, guidelines, index) embed their previews.
export const PAGES = [
  ['applications/web/index.html', 'previews/app-01-website-home.png', 1440, 900, true],
  ['applications/web/index.html', 'previews/app-02-homepage-hero.png', 1440, 900, false],
  ['applications/web/products.html', 'previews/app-03-products-page.png', 1440, 900, true],
  ['applications/web/vevo.html', 'previews/app-05-vevo-product-page.png', 1440, 900, true],
  ['applications/product/dashboard.html', 'previews/app-06-saas-dashboard.png', 1440, 900, false],
  ['applications/product/ai-assistant.html', 'previews/app-07-ai-assistant.png', 1440, 900, false],
  ['applications/product/analytics.html', 'previews/app-08-analytics.png', 1440, 900, false],
  ['applications/product/automation.html', 'previews/app-09-automation-workflow.png', 1440, 900, false],
  ['applications/product/mobile.html', 'previews/app-10-mobile-app.png', 1440, 1000, false],
  ['applications/product/api-integrations.html', 'previews/app-11-api-integrations.png', 1440, 900, false],
  ['applications/print/business-card.html', 'previews/app-12-business-card.png', 1440, 900, true],
  ['applications/print/letterhead.html', 'previews/app-13-letterhead.png', 1440, 900, true],
  ['applications/comms/email-signature.html', 'previews/app-14-email-signature.png', 1440, 900, true],
  ['applications/social/linkedin-post.html', 'previews/app-15-linkedin-post.png', 1440, 900, true],
  ['applications/social/announcement.html', 'previews/app-16-social-announcement.png', 1440, 900, true],
  ['applications/environment/signage.html', 'previews/app-17-office-signage.png', 1440, 900, true],
  ['applications/presentation/deck-cover.html', 'previews/app-18-pitch-deck-cover.png', 1440, 900, true],
  ['applications/developer/github.html', 'previews/app-19-github-developer.png', 1440, 900, true],
  ['applications/app-icon/index.html', 'previews/app-20-app-icon-favicon.png', 1440, 900, true],
  ['brand-board/index.html', 'previews/00-brand-board.png', 1600, 1000, true],
  ['logo/exploration/logo-review.html', 'previews/01-logo-review.png', 1440, 900, true],
  ['guidelines/index.html', 'previews/02-guidelines.png', 1440, 900, true],
  ['applications/index.html', 'previews/03-applications-index.png', 1440, 900, true],
];

// SVG → PNG at exact pixel sizes: [svg, png, width, height]
const RASTERS = [
  ['favicon/favicon-16.svg', 'favicon/favicon-16.png', 16, 16],
  ['favicon/favicon.svg', 'favicon/favicon-32.png', 32, 32],
  ['favicon/favicon.svg', 'favicon/favicon-48.png', 48, 48],
  ['favicon/maskable-icon.svg', 'favicon/apple-touch-icon.png', 180, 180],
  ['favicon/app-icon.svg', 'favicon/icon-192.png', 192, 192],
  ['favicon/app-icon.svg', 'favicon/icon-512.png', 512, 512],
  ['favicon/maskable-icon.svg', 'favicon/maskable-512.png', 512, 512],
  ['favicon/app-icon.svg', 'favicon/app-icon-1024.png', 1024, 1024],
  ['favicon/vevo-app-icon.svg', 'favicon/vevo-app-icon-512.png', 512, 512],
  ['logo/svg/zirven-symbol-light.svg', 'logo/png/zirven-symbol-light-512.png', 430, 512],
  ['logo/svg/zirven-symbol-dark.svg', 'logo/png/zirven-symbol-dark-512.png', 430, 512],
  ['logo/svg/zirven-logo-horizontal-light.svg', 'logo/png/zirven-logo-horizontal-light-1200.png', 1200, 0],
  ['logo/svg/zirven-logo-horizontal-dark.svg', 'logo/png/zirven-logo-horizontal-dark-1200.png', 1200, 0],
  ['logo/svg/zirven-logo-descriptor-en-light.svg', 'logo/png/zirven-logo-descriptor-en-light-1200.png', 1200, 0],
  ['logo/svg/zirven-logo-descriptor-en-dark.svg', 'logo/png/zirven-logo-descriptor-en-dark-1200.png', 1200, 0],
  ['logo/svg/zirven-logo-arabic-light.svg', 'logo/png/zirven-logo-arabic-light-1200.png', 1200, 0],
  ['logo/svg/vevo-endorsed-light.svg', 'logo/png/vevo-endorsed-light-1200.png', 1200, 0],
  ['logo/svg/vevo-endorsed-dark.svg', 'logo/png/vevo-endorsed-dark-1200.png', 1200, 0],
];
for (const c of ['A-summit-z-refined', 'B-summit-modular', 'C-summit-layered']) {
  for (const px of [16, 24, 32, 64]) RASTERS.push([`logo/exploration/${c}-micro-black.svg`, `logo/exploration/png/${c}-${px}.png`, Math.round(px * 40 / 48), px]);
  RASTERS.push([`logo/exploration/${c}-tile-16.svg`, `logo/exploration/png/${c}-tile-16.png`, 16, 16]);
  RASTERS.push([`logo/exploration/${c}-tile-32.svg`, `logo/exploration/png/${c}-tile-32.png`, 32, 32]);
}

async function shot(browser, input, out, w = 1440, h = 900, full = true, scale = 1) {
  const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: +scale });
  await page.goto('file://' + resolve(input), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(250);
  mkdirSync(dirname(resolve(out)), { recursive: true });
  await page.screenshot({ path: resolve(out), fullPage: !!full, animations: 'disabled' });
  await page.close();
}

async function raster(browser, svg, out, w, h) {
  const src = readFileSync(P(svg), 'utf8');
  const vb = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(src);
  if (!h && vb) h = Math.round((w * +vb[2]) / +vb[1]);
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const html = `<html><body style="margin:0;background:transparent"><img src="file://${P(svg)}" style="display:block;width:${w}px;height:${h}px"></body></html>`;
  const tmp = P('previews', `.tmp-${Date.now()}.html`);
  mkdirSync(P('previews'), { recursive: true });
  writeFileSync(tmp, html);
  await page.goto('file://' + tmp);
  await page.waitForTimeout(80);
  mkdirSync(dirname(P(out)), { recursive: true });
  await page.screenshot({ path: P(out), omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
  await page.close();
  (await import('node:fs')).unlinkSync(tmp);
}

function writeIco(pngs, out) {
  // ICO container with embedded PNG images (supported by every current browser and OS).
  const bufs = pngs.map((f) => readFileSync(P(f)));
  const header = Buffer.alloc(6 + 16 * bufs.length);
  header.writeUInt16LE(0, 0); header.writeUInt16LE(1, 2); header.writeUInt16LE(bufs.length, 4);
  let offset = header.length;
  bufs.forEach((b, i) => {
    const size = b.readUInt32BE(16); // PNG IHDR width
    const e = 6 + 16 * i;
    header.writeUInt8(size >= 256 ? 0 : size, e); header.writeUInt8(size >= 256 ? 0 : size, e + 1);
    header.writeUInt8(0, e + 2); header.writeUInt8(0, e + 3);
    header.writeUInt16LE(1, e + 4); header.writeUInt16LE(32, e + 6);
    header.writeUInt32LE(b.length, e + 8); header.writeUInt32LE(offset, e + 12);
    offset += b.length;
  });
  writeFileSync(P(out), Buffer.concat([header, ...bufs]));
}

const [, , mode = 'all', ...rest] = process.argv;
const browser = await chromium.launch();
try {
  if (mode === 'page') {
    const [input, out, w, h, full = '1', scale = '1'] = rest;
    await shot(browser, input, out, w, h, full === '1', scale);
  } else {
    if (mode === 'all' || mode === 'icons') {
      for (const [svg, out, w, h] of RASTERS) await raster(browser, svg, out, w, h);
      writeIco(['favicon/favicon-16.png', 'favicon/favicon-32.png', 'favicon/favicon-48.png'], 'favicon/favicon.ico');
      console.log(`rasterised ${RASTERS.length} icons/logos + favicon.ico`);
    }
    if (mode === 'all' || mode === 'previews') {
      let n = 0;
      for (const [src, out, w, h, full] of PAGES) {
        if (!existsSync(P(src))) { console.warn('skip (missing):', src); continue; }
        await shot(browser, P(src), P(out), w, h, full);
        n++;
      }
      console.log(`rendered ${n} page previews`);
    }
  }
} finally {
  await browser.close();
}
