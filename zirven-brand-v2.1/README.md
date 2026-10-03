# Zirven — Brand identity V2.1

**Zirven builds intelligent digital products.** Software · SaaS · AI

V2.1 corrects the business positioning of the Zirven identity. Zirven is a **technology and software company** and the **parent brand** of a product portfolio: VEVO today, more SaaS and AI products later, and custom software through Zirven Solutions. V2.1 keeps the visual craft of V2 and rebuilds the strategy, the guidelines and every application around that position.

> **About the V2 backup.** The brief asked for the V2 folder to be preserved as a backup next to this one. It was not in this repository when V2.1 was created: the repository and its remote had no files or branches. V2.1 is therefore a self-contained package. It rebuilds the V2 elements the brief asked to keep (Summit Z, 20° summit, purple palette, Readex Pro, contour pattern, token and SVG generation) from their description. If the V2 files exist elsewhere, add them as `zirven-brand-v2/` beside this folder. Nothing in V2.1 reads, overwrites or depends on them. If V2's exact colour values differ, change them in `scripts/build_brand.py` and rebuild.

## Start here

| Open | What it is |
|---|---|
| `pdf/Zirven-V2.1-Brand-Book.pdf` | **Everything in one PDF** (45 pages): brand board, guidelines 01–24, logo review, all applications |
| `pdf/Zirven-V2.1-Guidelines.pdf` | Brand guidelines only (cover + 24 sections) |
| `pdf/Zirven-V2.1-Brand-Board.pdf` | Brand board, one page |
| `index.html` | Package hub |
| `brand-board/index.html` | The whole identity on one board (PNG: `previews/00-brand-board.png`) |
| `guidelines/index.html` | Brand guidelines, sections 01–24 |
| `applications/index.html` | The 20 applications |
| `logo/exploration/logo-review.html` | Logo review: A / B / C at 16–64 px, app icon, header, monochrome |
| `audit/semantic-audit.md` | Terminology scan and semantic review |
| `CHANGELOG.md` | What changed from V2 |

Every page works offline from disk: fonts, icons, patterns and logos are all local.

## Positioning in one paragraph

For businesses ready to move forward, Zirven builds intelligent digital products: SaaS platforms, AI-powered business software, web and mobile applications, automation, APIs and integrations, and data and cloud platforms. Zirven builds and owns these products and keeps improving them. The name comes from *zirve*, Turkish for summit. For Zirven, the summit means progress, solving difficult problems, reaching the next level and products that keep evolving.

- **Primary line:** Building intelligent digital products.
- **Descriptor:** Software · SaaS · AI
- **TR:** Akıllı dijital ürünler geliştiriyoruz. · Yazılım · SaaS · Yapay Zekâ
- **AR:** نبني منتجات رقمية ذكية · برمجيات · منصات سحابية · ذكاء اصطناعي
- **Corporate name:** Zirven Technology (TR: Zirven Teknoloji)

## Brand architecture

```
ZIRVEN  ·  technology & software company  (master brand)
│
├── Zirven platform  ·  identity, permissions, billing, data, AI services, API, design system
│
├── VEVO             ·  SaaS / AI-powered business platform        "a product by Zirven"
├── Product 02       ·  SaaS platform        (in development)
├── Product 03       ·  AI product           (research)
└── Zirven Solutions ·  custom digital solutions (descriptive sub-brand)
```

## Folder map

```
zirven-brand-v2.1/
├── index.html                  package hub
├── brand-board/                final brand board
├── guidelines/                 brand guidelines (24 sections)
├── applications/               20 applications
│   ├── web/                    01–05  website, hero, products, ecosystem, VEVO
│   ├── product/                06–11  dashboard, AI assistant, analytics, automation, mobile, API
│   ├── print/                  12–13  business card, letterhead (+ envelope)
│   ├── comms/                  14     email signature
│   ├── social/                 15–16  LinkedIn post, announcement set (EN / TR / AR)
│   ├── environment/            17     office & building signage
│   ├── presentation/           18     pitch deck cover
│   ├── developer/              19     GitHub org, README banner, CLI
│   └── app-icon/               20     app icon & favicon
├── logo/svg · logo/png         every logo file (light, dark, black, white, violet; EN, TR, AR)
├── logo/exploration/           logo review candidates, rasters, construction drawing
├── favicon/                    favicon.svg/.ico/PNGs, app icons, VEVO tile, manifest
├── icons/                      16 technology icons + 36 UI icons, sprite, icons.json
├── pattern/                    data terrain, ascent lines, module grid
├── tokens/                     tokens.json · tokens.css · _tokens.scss · tailwind.preset.cjs
├── assets/                     zirven.css, icon injector, fonts (Readex Pro, JetBrains Mono, OFL)
├── pdf/                        Brand Book, Guidelines and Brand Board as vector PDFs
├── previews/                   PNG renders of every page
├── audit/                      semantic audit report
└── scripts/                    build_brand.py · render.mjs · audit.py
```

## Rebuild

```bash
python3 -m pip install fonttools uharfbuzz brotli    # once
python3 scripts/build_brand.py   # tokens, logos (outlined from Readex Pro), icons, patterns, favicon masters
node scripts/render.mjs          # favicon PNG/ICO, logo PNGs, page previews (Playwright Chromium)
node scripts/export-pdf.mjs      # vector PDFs in pdf/ (needs: python3 -m pip install pypdf)
python3 scripts/audit.py         # semantic audit; exits non-zero on any violation
```

`build_brand.py` holds the single source of truth: palette, type scale, Summit Z geometry (20° ramp, 35° summit, 55° descent, micro master), lockup proportions, icon paths and pattern generators. Generated files say so in their headers. Edit the script, not the outputs.

## Placeholders

The people, customer companies, metrics, phone numbers, addresses, the `zirven.com` domains and the VEVO feature details in the mock-ups are illustrative. Replace them with real data before anything is published. The product names "Product 02" and "Product 03" are reserved slots, not names. Before the Summit Z is registered, it needs a trademark search in classes 9, 35 and 42.

## Fonts

Readex Pro (© The Readex Pro Project Authors) and JetBrains Mono (© JetBrains) are licensed under the SIL Open Font License 1.1 (https://openfontlicense.org). Local `.woff2` subsets are in `assets/fonts/`.
