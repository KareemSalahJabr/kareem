#!/usr/bin/env node
/**
 * Zirven V2.1 — PDF export.
 *
 *   node scripts/export-pdf.mjs
 *
 * Prints the HTML pages with headless Chromium as vector PDFs (selectable text, embedded
 * Readex Pro), one page per guideline section / application at its natural height, then
 * merges them with scripts/pdf_merge.py (pypdf). Output: pdf/
 *
 *   Zirven-V2.1-Brand-Book.pdf     brand board + guidelines + logo review + 20 applications
 *   Zirven-V2.1-Guidelines.pdf     guidelines, cover + sections 01–24
 *   Zirven-V2.1-Brand-Board.pdf    the brand board (one page)
 *
 * Requires: python3 -m pip install pypdf
 */
import { createRequire } from 'node:module';
import { mkdirSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = join(ROOT, 'pdf');
const TMP = join(tmpdir(), `zirven-pdf-${Date.now()}`);
mkdirSync(OUT, { recursive: true });
mkdirSync(TMP, { recursive: true });

// [source, width, viewport height, split selector | null, extra CSS]
const GUIDE_CSS = '.toc{display:none!important}.layout{display:block!important}';
// Screen-only paper grain (feTurbulence + blend) makes Chromium flatten whole pages; drop it in print.
const PRINT_CSS = '.card::after,.paper::after{display:none!important}';
const BOARD = ['brand-board/index.html', 1600, 1000, null, ''];
const GUIDELINES = ['guidelines/index.html', 1180, 900, 'header.cover, section.sec', GUIDE_CSS];
const LOGO_REVIEW = ['logo/exploration/logo-review.html', 1440, 900, null, ''];
const APPS = [
  ['applications/web/index.html', 1440, 900], ['applications/web/products.html', 1440, 900], ['applications/web/vevo.html', 1440, 900],
  ['applications/product/dashboard.html', 1440, 900], ['applications/product/ai-assistant.html', 1440, 900],
  ['applications/product/analytics.html', 1440, 900], ['applications/product/automation.html', 1440, 900],
  ['applications/product/mobile.html', 1440, 1000], ['applications/product/api-integrations.html', 1440, 900],
  ['applications/print/business-card.html', 1440, 900], ['applications/print/letterhead.html', 1440, 900],
  ['applications/comms/email-signature.html', 1440, 900], ['applications/social/linkedin-post.html', 1440, 900],
  ['applications/social/announcement.html', 1440, 900], ['applications/environment/signage.html', 1440, 900],
  ['applications/presentation/deck-cover.html', 1440, 900], ['applications/developer/github.html', 1440, 900],
  ['applications/app-icon/index.html', 1440, 900],
].map(([s, w, h]) => [s, w, h, null, '']);

let n = 0;
async function printPart(browser, [src, width, vh, split, css]) {
  const page = await browser.newPage({ viewport: { width, height: vh } });
  await page.emulateMedia({ media: 'screen', reducedMotion: 'reduce' });
  await page.goto('file://' + join(ROOT, src), { waitUntil: 'networkidle' });
  await page.addStyleTag({ content: PRINT_CSS + (css || '') });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(200);
  const files = [];
  const count = split ? await page.locator(split).count() : 1;
  for (let i = 0; i < count; i++) {
    const h = await page.evaluate(({ split, i }) => {
      if (!split) return Math.ceil(Math.max(document.documentElement.scrollHeight, document.body.scrollHeight));
      const parts = [...document.querySelectorAll(split)];
      parts.forEach((p, j) => { p.style.display = j === i ? '' : 'none'; });
      window.scrollTo(0, 0);
      return Math.ceil(document.documentElement.scrollHeight);
    }, { split, i });
    const file = join(TMP, `${String(++n).padStart(3, '0')}.pdf`);
    await page.pdf({ path: file, width: `${width}px`, height: `${h + 1}px`, printBackground: true, pageRanges: '1',
                     margin: { top: 0, right: 0, bottom: 0, left: 0 } });
    files.push(file);
  }
  await page.close();
  return files;
}

function merge(out, files, title) {
  execFileSync('python3', [join(ROOT, 'scripts', 'pdf_merge.py'), join(OUT, out), title, ...files], { stdio: 'inherit' });
}

const browser = await chromium.launch();
try {
  const board = await printPart(browser, BOARD);
  const guide = await printPart(browser, GUIDELINES);
  const review = await printPart(browser, LOGO_REVIEW);
  const apps = [];
  for (const a of APPS) apps.push(...await printPart(browser, a));
  merge('Zirven-V2.1-Brand-Board.pdf', board, 'Zirven V2.1 — Brand board');
  merge('Zirven-V2.1-Guidelines.pdf', guide, 'Zirven V2.1 — Brand guidelines');
  merge('Zirven-V2.1-Brand-Book.pdf', [...board, ...guide, ...review, ...apps], 'Zirven V2.1 — Brand book');
} finally {
  await browser.close();
  rmSync(TMP, { recursive: true, force: true });
}
