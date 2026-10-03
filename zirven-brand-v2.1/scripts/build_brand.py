#!/usr/bin/env python3
"""
Zirven V2.1 — brand asset generator.

One script, one source of truth. It writes:
  tokens/      design tokens (JSON, CSS, SCSS, Tailwind preset)
  logo/svg/    symbol, wordmarks, lockups (Latin + Arabic), endorsement lockups
  logo/exploration/  logo review candidates A / B / C + construction drawing
  favicon/     favicon + app-icon SVG masters (PNGs are rasterised by render.mjs)
  icons/svg/   technology icon set + sprite + JS injector
  pattern/     data-terrain contour pattern, ascent lines, module grid

All logo text is outlined from Readex Pro (OFL), so no logo file depends on an
installed font. Requirements: python3 -m pip install fonttools uharfbuzz brotli

Run from anywhere:  python3 zirven-brand-v2.1/scripts/build_brand.py
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"

# =============================================================================
# 1. TOKENS — the only place colour values are defined
# =============================================================================
BRAND = {
    "night":        {"hex": "#0E0B1F", "name": "Zirven Night",      "role": "Primary dark surface. The default stage for the brand."},
    "deep-violet":  {"hex": "#241654", "name": "Deep Violet",       "role": "Secondary dark surface, depth layers, app-icon gradient start."},
    "violet":       {"hex": "#5B34E0", "name": "Zirven Violet",     "role": "Primary brand colour. Symbol on light, primary actions, links on light."},
    "electric":     {"hex": "#9671FF", "name": "Electric Purple",   "role": "Brand accent on dark. Symbol on dark, focus, active states, highlights."},
    "lavender":     {"hex": "#D3C8FF", "name": "Lavender",          "role": "Soft accent. Secondary text on dark, tints, pattern lines."},
    "snow":         {"hex": "#F7F6FC", "name": "Snow",              "role": "Primary light surface and text on dark."},
    "cyan":         {"hex": "#3DD8E8", "name": "Intelligence Cyan", "role": "Restricted accent: live data and AI activity only. Max ~5% of any surface."},
}
CYAN_INK = "#0A7A88"  # Intelligence Cyan for text/strokes on light surfaces (5.1:1 on white)

NEUTRAL = {  # violet-tinted greys for UI
    "950": "#0E0B1F", "900": "#15112B", "850": "#1C1735", "800": "#241E40",
    "700": "#3A3456", "600": "#57516F", "500": "#77718F", "400": "#9C97B1",
    "300": "#C4C0D3", "200": "#E0DEEA", "100": "#EEEDF4", "50": "#F7F6FC", "0": "#FFFFFF",
}
FUNCTIONAL = {  # product-UI states only — never used as brand colours
    "success": "#2EB67D", "warning": "#F0A73A", "danger": "#E5484D", "info": CYAN_INK,
}

TYPE = {
    "family": {
        "sans": "'Readex Pro', 'Segoe UI', system-ui, -apple-system, 'Noto Sans Arabic', sans-serif",
        "mono": "'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace",
    },
    "weight": {"light": 300, "regular": 400, "medium": 500, "semibold": 600, "bold": 700},
    # size / line-height / tracking / weight
    "scale": {
        "display-xl": ["72px", "1.02", "-0.025em", 600],
        "display":    ["56px", "1.05", "-0.022em", 600],
        "h1":         ["44px", "1.1",  "-0.018em", 600],
        "h2":         ["34px", "1.15", "-0.012em", 600],
        "h3":         ["24px", "1.25", "-0.006em", 600],
        "h4":         ["19px", "1.35", "0",        600],
        "body-lg":    ["18px", "1.6",  "0",        400],
        "body":       ["16px", "1.6",  "0",        400],
        "body-sm":    ["14px", "1.55", "0",        400],
        "caption":    ["12px", "1.45", "0.01em",   500],
        "overline":   ["12px", "1.3",  "0.14em",   600],
        "code":       ["13.5px", "1.6", "0",       400],
    },
}

SPACE = {str(k): f"{v}px" for k, v in [(0, 0), (1, 4), (2, 8), (3, 12), (4, 16), (5, 20), (6, 24), (8, 32), (10, 40), (12, 48), (16, 64), (20, 80), (24, 96), (32, 128)]}
RADIUS = {"xs": "4px", "sm": "6px", "md": "10px", "lg": "14px", "xl": "20px", "2xl": "28px", "tile": "22.5%", "pill": "999px"}
MOTION = {
    "ease-summit": "cubic-bezier(0.2, 0.8, 0.2, 1)",
    "ease-standard": "cubic-bezier(0.4, 0, 0.2, 1)",
    "duration-fast": "120ms", "duration-base": "200ms", "duration-slow": "360ms", "duration-reveal": "640ms",
}
SHADOW = {
    "sm": "0 1px 2px rgba(14, 11, 31, 0.08)",
    "md": "0 6px 20px -6px rgba(14, 11, 31, 0.18)",
    "lg": "0 24px 60px -20px rgba(14, 11, 31, 0.35)",
    "glow": "0 0 0 1px rgba(150, 113, 255, 0.35), 0 12px 40px -12px rgba(150, 113, 255, 0.45)",
}
ANGLE = {"summit-ramp": "20deg", "summit-angle": "35deg", "summit-descent": "55deg"}


def write_tokens() -> None:
    out = ROOT / "tokens"
    out.mkdir(parents=True, exist_ok=True)
    data = {
        "$schema-note": "Zirven V2.1 design tokens. Generated by scripts/build_brand.py — edit there, not here.",
        "brand": "Zirven — technology & software company (SaaS · AI · digital products)",
        "color": {
            "brand": {k: {"value": v["hex"], "name": v["name"], "usage": v["role"]} for k, v in BRAND.items()},
            "cyan-ink": {"value": CYAN_INK, "usage": "Intelligence Cyan for text and strokes on light surfaces."},
            "neutral": {k: {"value": v} for k, v in NEUTRAL.items()},
            "functional": {k: {"value": v, "usage": "Product UI states only."} for k, v in FUNCTIONAL.items()},
        },
        "typography": TYPE,
        "space": SPACE,
        "radius": RADIUS,
        "motion": MOTION,
        "shadow": SHADOW,
        "angle": ANGLE,
    }
    (out / "tokens.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    css = ["/* Zirven V2.1 design tokens — generated by scripts/build_brand.py. Do not edit by hand. */",
           "/* Zirven builds intelligent digital products: Software · SaaS · AI. */", ":root {"]
    css.append("  /* Brand palette */")
    for k, v in BRAND.items():
        css.append(f"  --z-{k}: {v['hex']}; /* {v['name']} — {v['role']} */")
    css.append(f"  --z-cyan-ink: {CYAN_INK}; /* Intelligence Cyan on light surfaces */")
    css.append("  /* Neutrals (violet-tinted) */")
    for k, v in NEUTRAL.items():
        css.append(f"  --z-ink-{k}: {v};")
    css.append("  /* Functional — product UI states only */")
    for k, v in FUNCTIONAL.items():
        css.append(f"  --z-{k}: {v};")
    css.append("  /* Typography */")
    css.append(f"  --z-font-sans: {TYPE['family']['sans']};")
    css.append(f"  --z-font-mono: {TYPE['family']['mono']};")
    for k, (size, lh, tr, w) in TYPE["scale"].items():
        css.append(f"  --z-text-{k}: {w} {size}/{lh} var(--z-font-{'mono' if k == 'code' else 'sans'}); --z-tracking-{k}: {tr};")
    css.append("  /* Space (4px base) */")
    for k, v in SPACE.items():
        css.append(f"  --z-space-{k}: {v};")
    css.append("  /* Radius */")
    for k, v in RADIUS.items():
        css.append(f"  --z-radius-{k}: {v};")
    css.append("  /* Motion */")
    for k, v in MOTION.items():
        css.append(f"  --z-{k}: {v};")
    css.append("  /* Elevation */")
    for k, v in SHADOW.items():
        css.append(f"  --z-shadow-{k}: {v};")
    css.append("  /* Geometry — the summit angles */")
    for k, v in ANGLE.items():
        css.append(f"  --z-angle-{k}: {v};")
    css.append("}")
    css.append("")
    css.append("/* Semantic theme tokens: light is the default document theme, dark is the brand stage. */")
    light = {"bg": "var(--z-ink-50)", "surface": "var(--z-ink-0)", "surface-2": "var(--z-ink-100)", "line": "var(--z-ink-200)",
             "text": "var(--z-night)", "text-2": "var(--z-ink-600)", "text-3": "var(--z-ink-500)", "accent": "var(--z-violet)",
             "accent-contrast": "#FFFFFF", "accent-soft": "rgba(91, 52, 224, 0.08)", "signal": "var(--z-cyan-ink)", "focus": "var(--z-violet)"}
    dark = {"bg": "var(--z-night)", "surface": "var(--z-ink-900)", "surface-2": "var(--z-ink-850)", "line": "rgba(211, 200, 255, 0.12)",
            "text": "var(--z-snow)", "text-2": "var(--z-ink-300)", "text-3": "var(--z-ink-400)", "accent": "var(--z-electric)",
            "accent-contrast": "var(--z-night)", "accent-soft": "rgba(150, 113, 255, 0.14)", "signal": "var(--z-cyan)", "focus": "var(--z-electric)"}
    css.append(":root, [data-theme=\"light\"] {")
    css += [f"  --t-{k}: {v};" for k, v in light.items()]
    css.append("}")
    css.append("[data-theme=\"dark\"] {")
    css += [f"  --t-{k}: {v};" for k, v in dark.items()]
    css.append("}")
    (out / "tokens.css").write_text("\n".join(css) + "\n")

    scss = ["// Zirven V2.1 design tokens — generated by scripts/build_brand.py"]
    for k, v in BRAND.items():
        scss.append(f"$z-{k}: {v['hex']}; // {v['name']}")
    scss.append(f"$z-cyan-ink: {CYAN_INK};")
    for k, v in NEUTRAL.items():
        scss.append(f"$z-ink-{k}: {v};")
    for k, v in FUNCTIONAL.items():
        scss.append(f"$z-{k}: {v};")
    scss.append(f"$z-font-sans: {TYPE['family']['sans']};")
    scss.append(f"$z-font-mono: {TYPE['family']['mono']};")
    for k, v in ANGLE.items():
        scss.append(f"$z-angle-{k}: {v};")
    (out / "_tokens.scss").write_text("\n".join(scss) + "\n")

    tw = {
        "theme": {"extend": {
            "colors": {"zirven": {k: v["hex"] for k, v in BRAND.items()} | {"cyan-ink": CYAN_INK},
                       "ink": NEUTRAL, **{k: v for k, v in FUNCTIONAL.items()}},
            "fontFamily": {"sans": ["Readex Pro", "system-ui", "sans-serif"], "mono": ["JetBrains Mono", "ui-monospace", "monospace"]},
            "borderRadius": {k: v for k, v in RADIUS.items() if k not in ("tile",)},
            "transitionTimingFunction": {"summit": MOTION["ease-summit"]},
        }}
    }
    (out / "tailwind.preset.cjs").write_text(
        "// Zirven V2.1 Tailwind preset — generated by scripts/build_brand.py\nmodule.exports = "
        + json.dumps(tw, indent=2) + ";\n")


# =============================================================================
# 2. THE SUMMIT Z — geometry
# =============================================================================
# The symbol is drawn on a 64-unit artboard. One module (m) = 10 units = the
# height of the base bar. Three angles define it:
#   ramp     20°  the top stroke climbs left→right (progress)
#   summit   35°  the acute peak where the climb turns (the next level)
#   descent  55°  the diagonal — 20 + 35 = 55, so every angle is related
T20 = math.tan(math.radians(20))


def _inter(l1, l2):
    (p, d), (q, e) = l1, l2
    den = d[0] * e[1] - d[1] * e[0]
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return (p[0] + t * d[0], p[1] + t * d[1])


class Summit:
    """Parametric Summit Z. Default parameters are the V2.1 master."""

    def __init__(self, x0=11.0, x1=53.0, ys=7.0, yb=57.0, ramp=10.0, base=10.0, descent_deg=55.0, gap=4.5):
        self.x0, self.x1, self.ys, self.yb = x0, x1, ys, yb
        self.ramp, self.base, self.gap = ramp, base, gap
        W = x1 - x0
        self.TL = (x0, ys + W * T20)          # where the climb starts
        self.S = (x1, ys)                     # the summit
        self.k = 1 / math.tan(math.radians(descent_deg))
        self.up = (self.TL, (1, -T20))
        self.lo = ((x0, self.TL[1] + ramp), (1, -T20))
        self.bt = ((x0, yb - base), (1, 0))
        self.dr = (self.S, (-self.k, 1))
        self.dl = ((x0, yb - base), (-self.k, 1))

    # A — solid Summit Z (master)
    def solid(self):
        x0, x1, yb, base = self.x0, self.x1, self.yb, self.base
        return [[self.TL, self.S, _inter(self.dr, self.bt), (x1, yb - base), (x1, yb), (x0, yb), (x0, yb - base),
                 _inter(self.dl, self.lo), (x0, self.TL[1] + self.ramp)]]

    # B — modular: ramp / descent / base as three separate modules
    def modular(self):
        x0, x1, yb, base, g = self.x0, self.x1, self.yb, self.base, self.gap
        lo_g = ((x0, self.TL[1] + self.ramp + g), (1, -T20))
        bt_g = ((x0, yb - base - g), (1, 0))
        ramp = [self.TL, self.S, _inter(self.dr, self.lo), (x0, self.TL[1] + self.ramp)]
        desc = [_inter(self.dl, lo_g), _inter(self.dr, lo_g), _inter(self.dr, bt_g), _inter(self.dl, bt_g)]
        basebar = [(x0, yb - base), (x1, yb - base), (x1, yb), (x0, yb)]
        return [ramp, desc, basebar]

    # C — layered: the summit layer (ramp) resting on the platform layer (descent + base)
    def layered(self):
        x0, x1, yb, base, g = self.x0, self.x1, self.yb, self.base, self.gap
        lo_g = ((x0, self.TL[1] + self.ramp + g), (1, -T20))
        ramp = [self.TL, self.S, _inter(self.dr, self.lo), (x0, self.TL[1] + self.ramp)]
        platform = [_inter(self.dl, lo_g), _inter(self.dr, lo_g), _inter(self.dr, self.bt), (x1, yb - base), (x1, yb),
                    (x0, yb), (x0, yb - base)]
        return [ramp, platform]

    def bbox(self):
        return (self.x0, self.ys, self.x1, self.yb)


def path_d(polys, dx=0.0, dy=0.0, s=1.0, prec=3):
    f = lambda v: f"{v:.{prec}f}".rstrip("0").rstrip(".")
    return " ".join("M" + " L".join(f"{f((x + dx) * s)} {f((y + dy) * s)}" for x, y in p) + " Z" for p in polys)


MASTER = Summit()
# Micro master: re-drawn for 16–24 px. Thinner ramp and a 57° descent keep the left counter
# open; the 48-unit height maps to whole pixels (base bar = exactly 2 px in the 16 px favicon).
MICRO = Summit(x0=12.0, x1=52.0, ys=8.0, yb=56.0, ramp=8.4, base=9.6, descent_deg=57.0)
MICRO_GAP = 6.0  # modular/layered review candidates at micro size (1.25 px at 16 px)

# =============================================================================
# 3. TYPE — outlines from Readex Pro via HarfBuzz
# =============================================================================
_TTF_CACHE: dict[str, str] = {}


def _ttf(name: str) -> str:
    if name not in _TTF_CACHE:
        t = TTFont(str(FONT_DIR / f"{name}.woff2"))
        t.flavor = None
        tmp = Path(tempfile.gettempdir()) / f"zirven-{name}.ttf"
        t.save(str(tmp))
        _TTF_CACHE[name] = str(tmp)
    return _TTF_CACHE[name]


def _font_for(ch: str) -> str:
    cp = ord(ch)
    if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFEFF:
        return "readex-arabic"
    latin = TTFont(_ttf("readex-latin")).getBestCmap()
    return "readex-latin" if cp in latin else "readex-latin-ext"


def shape(text: str, wght: float = 600, tracking: float = 0.0, font: str | None = None):
    """Return (svg path d, advance) in font units (1000 upem), baseline at y=0."""
    fontname = font or _font_for(text[0])
    blob = hb.Blob.from_file_path(_ttf(fontname))
    hbfont = hb.Font(hb.Face(blob))
    hbfont.set_variations({"wght": wght})
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    x, cmds = 0.0, []
    infos, poss = buf.glyph_infos, buf.glyph_positions
    for i, (info, pos) in enumerate(zip(infos, poss)):
        rec = RecordingPen()
        hbfont.draw_glyph_with_pen(info.codepoint, rec)
        sp = SVGPathPen(None, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        rec.replay(TransformPen(sp, (1, 0, 0, -1, x + pos.x_offset, -pos.y_offset)))
        cmds.append(sp.getCommands())
        x += pos.x_advance + (tracking if i < len(infos) - 1 else 0)
    return " ".join(c for c in cmds if c), x


def shape_runs(text: str, wght: float, tracking: float = 0.0):
    """Shape mixed Latin/Latin-ext text run by run (for Turkish descriptors)."""
    runs, cur, curfont = [], "", None
    for ch in text:
        f = _font_for(ch) if ch != " " else (curfont or "readex-latin")
        if curfont is None or f == curfont:
            cur += ch
            curfont = f
        else:
            runs.append((cur, curfont))
            cur, curfont = ch, f
    runs.append((cur, curfont))
    parts, x = [], 0.0
    for i, (t, f) in enumerate(runs):
        d, adv = shape(t, wght, tracking, font=f)
        parts.append(f'<path transform="translate({x:.1f} 0)" d="{d}"/>')
        x += adv + (tracking if i < len(runs) - 1 else 0)
    return "".join(parts), x


# =============================================================================
# 4. LOGO COMPOSITION
# =============================================================================
XH = 525            # Readex Pro x-height
WORD = dict(text="zirven", wght=600, tracking=-6)


def svg_doc(w, h, body, title, desc="", extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'role="img" aria-labelledby="t d"{extra}><title id="t">{title}</title><desc id="d">{desc}</desc>{body}</svg>\n')


def symbol_group(summit: Summit, x, y, height, fill, polys=None):
    """Place the symbol so its bounding box top-left is (x, y) at the given height."""
    x0, ys, x1, yb = summit.bbox()
    s = height / (yb - ys)
    polys = polys if polys is not None else summit.solid()
    return f'<path fill="{fill}" d="{path_d(polys, -x0 + x / s, -ys + y / s, s, 2)}"/>', (x1 - x0) * s


SCHEMES = {
    "light":  {"sym": BRAND["violet"]["hex"],   "word": BRAND["night"]["hex"], "sub": NEUTRAL["600"], "bg": None},
    "dark":   {"sym": BRAND["electric"]["hex"], "word": BRAND["snow"]["hex"],  "sub": NEUTRAL["300"], "bg": None},
    "black":  {"sym": "#000000", "word": "#000000", "sub": "#000000", "bg": None},
    "white":  {"sym": "#FFFFFF", "word": "#FFFFFF", "sub": "#FFFFFF", "bg": None},
    "violet": {"sym": "#FFFFFF", "word": "#FFFFFF", "sub": BRAND["lavender"]["hex"], "bg": BRAND["violet"]["hex"]},
}
DESC_NOTE = "Zirven — technology and software company. Symbol: the Summit Z (20° ramp, 35° summit, 55° descent)."


def lockup_horizontal(scheme: str, descriptor: str | None = None, pad_units=0.0):
    """Symbol + 'zirven'. Symbol height = 1.62 × x-height; baseline-aligned."""
    c = SCHEMES[scheme]
    word_d, word_w = shape(WORD["text"], WORD["wght"], WORD["tracking"])
    sym_h = 1.62 * XH                      # 850.5 units
    gap = 0.30 * sym_h
    pad = pad_units
    top = pad
    base_y = top + sym_h                    # baseline = symbol bottom
    sym, sym_w = symbol_group(MASTER, pad, top, sym_h, c["sym"])
    word = f'<path fill="{c["word"]}" transform="translate({pad + sym_w + gap:.1f} {base_y:.1f})" d="{word_d}"/>'
    w = pad + sym_w + gap + word_w + pad
    h = sym_h + 2 * pad
    body = sym + word
    if descriptor:
        dd, dw = shape_runs(descriptor, 420, 34)
        scale = 0.25
        ty = base_y + 0.47 * sym_h
        body += f'<g fill="{c["sub"]}" transform="translate({pad + sym_w + gap + 8:.1f} {ty:.1f}) scale({scale})">{dd}</g>'
        h = ty + 0.08 * sym_h + pad
        w = max(w, pad + sym_w + gap + dw * scale + pad)
    if c["bg"]:
        body = f'<rect width="100%" height="100%" fill="{c["bg"]}"/>' + body
    return w, h, body


def lockup_stacked(scheme: str):
    c = SCHEMES[scheme]
    word_d, word_w = shape(WORD["text"], WORD["wght"], WORD["tracking"])
    sym_h = 2.1 * XH
    sym_w = (MASTER.x1 - MASTER.x0) * sym_h / (MASTER.yb - MASTER.ys)
    w = max(word_w, sym_w)
    sym, _ = symbol_group(MASTER, (w - sym_w) / 2, 0, sym_h, c["sym"])
    gap = 0.42 * sym_h
    base_y = sym_h + gap + XH
    word = f'<path fill="{c["word"]}" transform="translate({(w - word_w) / 2:.1f} {base_y:.1f})" d="{word_d}"/>'
    return w, base_y + 20, sym + word


def lockup_arabic(scheme: str, bilingual=False):
    """RTL lockup: symbol on the right (reading start), زيرفن to its left."""
    c = SCHEMES[scheme]
    ar_d, ar_w = shape("زيرفن", 560, 0, font="readex-arabic")
    sym_h = 1.62 * XH
    sym_w = (MASTER.x1 - MASTER.x0) * sym_h / (MASTER.yb - MASTER.ys)
    gap = 0.30 * sym_h
    base_y = sym_h * 0.86     # Arabic letters descend; baseline sits higher than in Latin lockup
    word = f'<path fill="{c["word"]}" transform="translate(0 {base_y:.1f})" d="{ar_d}"/>'
    sym, _ = symbol_group(MASTER, ar_w + gap, 0, sym_h, c["sym"])
    w, h = ar_w + gap + sym_w, sym_h + 0.22 * sym_h
    body = word + sym
    if bilingual:
        lat_d, lat_w = shape(WORD["text"], WORD["wght"], WORD["tracking"])
        s = 0.62
        body += f'<path fill="{c["word"]}" transform="translate({w + 0.55 * sym_h:.1f} {base_y:.1f}) scale({s})" d="{lat_d}"/>'
        body += f'<rect x="{w + 0.27 * sym_h:.1f}" y="{0.18 * sym_h:.1f}" width="6" height="{0.64 * sym_h:.1f}" fill="{c["sub"]}" opacity="0.5"/>'
        w = w + 0.55 * sym_h + lat_w * s
    return w, h, body


def wordmark(scheme: str):
    c = SCHEMES[scheme]
    d, w = shape(WORD["text"], WORD["wght"], WORD["tracking"])
    top = 760   # i-dot top
    return w, top + 20, f'<path fill="{c["word"]}" transform="translate(0 {top:.0f})" d="{d}"/>'


def symbol_only(scheme: str, summit: Summit = MASTER, polys=None, pad=0.0):
    c = SCHEMES[scheme]
    h = 500.0
    sym, w = symbol_group(summit, pad, pad, h, c["sym"], polys)
    return w + 2 * pad, h + 2 * pad, sym


# ---- product glyphs / app tiles ---------------------------------------------
def vevo_glyph(fill: str, x: float, y: float, size: float):
    """VEVO product glyph: a V whose right arm climbs higher — built on the 20° ramp."""
    s = size / 64
    # left arm descends from the top-left; right arm climbs past it to a 20° cut (the ramp)
    L = [(10, 15.6), (21.5, 15.6), (33.2, 40.5), (30.8, 51.5), (25.2, 51.5)]
    R = [(30.8, 51.5), (43.2, 13.2), (54.0, 9.27), (38.0, 51.5)]
    return f'<path fill="{fill}" d="{path_d([L, R], x / s, y / s, s, 2)}"/>'


def app_tile(size=1024, kind="zirven", radius=0.225, flat=False):
    """Rounded-square tile used for the Zirven app icon and every Zirven product icon."""
    r = size * radius
    gid = f"g-{kind}-{size}"
    if kind == "zirven":
        stops = (BRAND["deep-violet"]["hex"], BRAND["violet"]["hex"])
    else:
        stops = (BRAND["night"]["hex"], BRAND["deep-violet"]["hex"])
    fill = stops[1] if flat else f"url(#{gid})"
    defs = "" if flat else (
        f'<defs><linearGradient id="{gid}" x1="0" y1="1" x2="1" y2="0.364">'  # runs along the 20° ramp
        f'<stop offset="0" stop-color="{stops[0]}"/><stop offset="1" stop-color="{stops[1]}"/></linearGradient></defs>')
    body = defs + f'<rect width="{size}" height="{size}" rx="{r:.1f}" fill="{fill}"/>'
    if kind == "zirven":
        summit = MICRO if size <= 48 else MASTER
        h = round(size * 0.62) if size <= 48 else size * 0.56   # whole pixels at favicon sizes
        w = (summit.x1 - summit.x0) * h / (summit.yb - summit.ys)
        g, _ = symbol_group(summit, (size - w) / 2 + size * 0.004, (size - h) / 2, h, BRAND["snow"]["hex"])
        body += g
    elif kind == "vevo":
        body += vevo_glyph(BRAND["electric"]["hex"], size * 0.18, size * 0.18, size * 0.64)
    elif kind == "future":
        dash = max(size * 0.02, 1.5)
        body = (f'<rect x="{dash / 2:.1f}" y="{dash / 2:.1f}" width="{size - dash:.1f}" height="{size - dash:.1f}" rx="{r:.1f}" '
                f'fill="none" stroke="{BRAND["lavender"]["hex"]}" stroke-opacity="0.55" stroke-width="{dash:.1f}" stroke-dasharray="{dash * 3:.1f} {dash * 2.2:.1f}"/>')
        body += (f'<path d="M{size * 0.5:.1f} {size * 0.36:.1f} v{size * 0.28:.1f} M{size * 0.36:.1f} {size * 0.5:.1f} h{size * 0.28:.1f}" '
                 f'stroke="{BRAND["lavender"]["hex"]}" stroke-width="{dash * 1.6:.1f}" stroke-linecap="round"/>')
    return body


def endorsement(scheme: str, product="VEVO"):
    """Endorsed product lockup:  [product tile] PRODUCT  |  a product by / [Z] zirven"""
    c = SCHEMES[scheme]
    pd, pw = shape(product, 600, 60)
    tile = 820.0
    body = f'<g transform="scale({tile / 1024:.5f})">{app_tile(1024, "vevo")}</g>'
    gap = 220
    body += f'<path fill="{c["word"]}" transform="translate({tile + gap:.1f} {tile / 2 + 350:.1f})" d="{pd}"/>'
    x = tile + gap + pw + 170
    body += f'<rect x="{x:.1f}" y="{tile * 0.12:.1f}" width="8" height="{tile * 0.76:.1f}" fill="{c["sub"]}" opacity="0.45"/>'
    x += 170
    # line 1 — "a product by"
    s1 = 0.30
    l1, l1w = shape_runs("a product by", 430, 12)
    y1 = 275
    body += f'<g fill="{c["sub"]}" transform="translate({x:.1f} {y1}) scale({s1})">{l1}</g>'
    # line 2 — the Zirven horizontal logo, scaled
    s2 = 0.40
    zd, zw = shape(WORD["text"], WORD["wght"], WORD["tracking"])
    sym_h = 1.62 * XH * s2
    y2 = 425
    sym, sw = symbol_group(MASTER, x, y2, sym_h, c["sym"])
    body += sym
    body += f'<path fill="{c["word"]}" transform="translate({x + sw + 0.30 * sym_h:.1f} {y2 + sym_h:.1f}) scale({s2})" d="{zd}"/>'
    w = x + max(l1w * s1, sw + 0.30 * sym_h + zw * s2) + 10
    return w, tile, body


# =============================================================================
# 5. ICONS — 24 px grid, 1.75 stroke, round caps & joins, 2 px safe area
# =============================================================================
ICONS = {
    # --- technology set (brand guideline 13) ---
    "products": '<rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><path d="M13.5 9.6 20.5 3.5v5.4a1.6 1.6 0 0 1-1.6 1.6h-5.4Z" fill="currentColor"/>',
    "saas": '<path d="M12 3.5 20.5 8 12 12.5 3.5 8Z"/><path d="m3.5 12 8.5 4.5 8.5-4.5"/><path d="m3.5 16 8.5 4.5 8.5-4.5"/>',
    "ai": '<path d="M12 3 13.9 10.1 21 12 13.9 13.9 12 21 10.1 13.9 3 12 10.1 10.1Z"/><path d="M19 3.5v3M17.5 5h3"/>',
    "automation": '<path d="M20 12a8 8 0 1 1-2.35-5.66"/><path d="M20.2 3.8v4.2H16"/><path d="m10 9 5 3-5 3Z"/>',
    "api": '<path d="M8 3.5H7a2.5 2.5 0 0 0-2.5 2.5v3.2c0 1.2-.8 2.3-2 2.8 1.2.5 2 1.6 2 2.8V18A2.5 2.5 0 0 0 7 20.5h1"/><path d="M16 3.5h1A2.5 2.5 0 0 1 19.5 6v3.2c0 1.2.8 2.3 2 2.8-1.2.5-2 1.6-2 2.8V18a2.5 2.5 0 0 1-2.5 2.5h-1"/><path d="m10.5 14.5 3-5"/>',
    "integrations": '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/><path d="M11 7h3a3 3 0 0 1 3 3v3"/><path d="M13 17h-3a3 3 0 0 1-3-3v-3"/>',
    "cloud": '<path d="M7.5 19H17a4 4 0 0 0 .5-7.97A6 6 0 0 0 6 10.2 4.4 4.4 0 0 0 7.5 19Z"/>',
    "analytics": '<path d="M3.5 3.5v17h17"/><path d="M8 16.5v-4"/><path d="M12 16.5v-7"/><path d="M16 16.5v-5"/><path d="M20 16.5V7"/>',
    "data": '<rect x="3.5" y="4" width="17" height="16" rx="2.2"/><path d="M3.5 9.5h17"/><path d="M3.5 14.75h17"/><path d="M9.5 4v16"/>',
    "database": '<ellipse cx="12" cy="5.75" rx="7.5" ry="2.75"/><path d="M4.5 5.75v12.5c0 1.5 3.4 2.75 7.5 2.75s7.5-1.25 7.5-2.75V5.75"/><path d="M4.5 12c0 1.5 3.4 2.75 7.5 2.75s7.5-1.25 7.5-2.75"/>',
    "web": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3 8.5h18"/><path d="M6 6.25h.01M8.5 6.25h.01"/><path d="m7 16.5 4-3 3 1.5 3.5-3"/>',
    "mobile": '<rect x="6.5" y="2.5" width="11" height="19" rx="2.6"/><path d="M10.5 18.5h3"/>',
    "security": '<path d="M12 3 19.5 6v5.5c0 4.6-3.2 8.3-7.5 9.5-4.3-1.2-7.5-4.9-7.5-9.5V6Z"/><path d="m8.75 12 2.25 2.25 4.25-4.5"/>',
    "teams": '<circle cx="9" cy="8.5" r="3.25"/><path d="M3 19.5c.6-3.2 3-5 6-5s5.4 1.8 6 5"/><circle cx="16.75" cy="9.25" r="2.5"/><path d="M17.25 14.6c2.1.3 3.5 1.9 3.9 4.4"/>',
    "workflow": '<rect x="3" y="3.5" width="6.5" height="6.5" rx="1.6"/><rect x="14.5" y="14" width="6.5" height="6.5" rx="1.6"/><path d="M6.25 10v4.25a3 3 0 0 0 3 3h5.25"/><path d="m12 15 2.5 2.25-2.5 2.25"/><path d="M14.5 6.75h6.5"/>',
    "ai-assistant": '<path d="M20 14.5a2 2 0 0 1-2 2H9.5L5 20v-3.5H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2Z"/><path d="m12 7 1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1Z"/>',
    # --- UI utility set (product interfaces) ---
    "arrow-right": '<path d="M4.5 12h15"/><path d="m13.5 6 6 6-6 6"/>',
    "arrow-up-right": '<path d="M7 17 17 7"/><path d="M8.5 7H17v8.5"/>',
    "search": '<circle cx="10.75" cy="10.75" r="6.25"/><path d="m20 20-4.75-4.75"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2.75v2.5M12 18.75v2.5M21.25 12h-2.5M5.25 12h-2.5M18.54 5.46l-1.77 1.77M7.23 16.77l-1.77 1.77M18.54 18.54l-1.77-1.77M7.23 7.23 5.46 5.46"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15Z"/><path d="M10 21h4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "chevron-down": '<path d="m6.5 9.5 5.5 5.5 5.5-5.5"/>',
    "chevron-right": '<path d="m9.5 6.5 5.5 5.5-5.5 5.5"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="m7 9.5 3 2.5-3 2.5"/><path d="M12.5 15h4.5"/>',
    "git-branch": '<circle cx="6.5" cy="5.5" r="2.25"/><circle cx="6.5" cy="18.5" r="2.25"/><circle cx="17.5" cy="7.5" r="2.25"/><path d="M6.5 7.75v8.5"/><path d="M17.5 9.75c0 4-4.5 3.5-9.2 7.4"/>',
    "globe": '<circle cx="12" cy="12" r="8.75"/><path d="M3.25 12h17.5"/><path d="M12 3.25c2.4 2.4 3.6 5.3 3.6 8.75S14.4 18.35 12 20.75C9.6 18.35 8.4 15.45 8.4 12S9.6 5.65 12 3.25Z"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="10" rx="2.2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "home": '<path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 19Z"/><path d="M9.5 20.5v-6h5v6"/>',
    "inbox": '<path d="M3.5 13.5 6 5.5h12l2.5 8V19a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19Z"/><path d="M3.5 13.5H8l1.5 2.5h5l1.5-2.5h4.5"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "file": '<path d="M6.5 3h7.5l4.5 4.5v12A1.5 1.5 0 0 1 17 21H7a1.5 1.5 0 0 1-1.5-1.5V4.5A1.5 1.5 0 0 1 7 3Z"/><path d="M13.5 3v5h5"/><path d="M9 13h6M9 16.5h4"/>',
    "send": '<path d="M20.5 3.5 10.5 13.5"/><path d="m20.5 3.5-6.5 17-3.5-7-7-3.5Z"/>',
    "play": '<path d="M7.5 5v14l11-7Z"/>',
    "pause": '<path d="M8.5 5v14M15.5 5v14"/>',
    "filter": '<path d="M4 5.5h16M7 12h10M10 18.5h4"/>',
    "more": '<circle cx="5.5" cy="12" r="1.1" fill="currentColor"/><circle cx="12" cy="12" r="1.1" fill="currentColor"/><circle cx="18.5" cy="12" r="1.1" fill="currentColor"/>',
    "copy": '<rect x="8.5" y="8.5" width="12" height="12" rx="2"/><path d="M15.5 8.5V5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 5v9A1.5 1.5 0 0 0 5 15.5h3.5"/>',
    "key": '<circle cx="8" cy="15.5" r="4.25"/><path d="m11 12.5 8.5-8.5M16.5 7l2.5 2.5M14 9.5l2 2"/>',
    "webhook": '<circle cx="12" cy="6.5" r="3"/><circle cx="6" cy="17" r="3"/><circle cx="18" cy="17" r="3"/><path d="m10.5 9.1-3 5.3M13.5 9.1l3 5.3M9 17h6"/>',
    "activity": '<path d="M3 12h4l2.5-6.5 5 13L17 12h4"/>',
    "users": '<circle cx="12" cy="8" r="3.75"/><path d="M4.5 20c.8-3.8 3.8-6 7.5-6s6.7 2.2 7.5 6"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M21.5 12h-2M4.5 12h-2M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4M18.7 18.7l-1.4-1.4M6.7 6.7 5.3 5.3"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
    "phone": '<path d="M5 3.5h3.5l1.5 4.5-2.25 1.5a11 11 0 0 0 6.75 6.75L16 14l4.5 1.5V19a1.5 1.5 0 0 1-1.6 1.5C10.9 20 4 13.1 3.5 5.1A1.5 1.5 0 0 1 5 3.5Z"/>',
    "map-pin": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z"/><circle cx="12" cy="10" r="2.4"/>',
    "linkedin": '<rect x="3.5" y="3.5" width="17" height="17" rx="2.5"/><path d="M8 10.5V16M8 7.75v.01M11.5 16v-5.5M11.5 13c0-1.6 1-2.6 2.4-2.6s2.1 1 2.1 2.6v3"/>',
    "github": '<path d="M9 19c-4 1.3-4-2-5.5-2.5M14.5 21v-3.2a2.8 2.8 0 0 0-.8-2.2c2.7-.3 5.5-1.3 5.5-6a4.7 4.7 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6.1 0C5.9 2.9 4.9 3.2 4.9 3.2a4.3 4.3 0 0 0-.1 3.2 4.7 4.7 0 0 0-1.3 3.2c0 4.6 2.8 5.7 5.5 6a2.8 2.8 0 0 0-.8 2.2V21"/>',
    "layers": '<path d="M12 3.5 20.5 8 12 12.5 3.5 8Z"/><path d="m3.5 12.5 8.5 4.5 8.5-4.5"/>',
    "zap": '<path d="M13 2.5 4.5 13.5H12L11 21.5l8.5-11H12Z"/>',
    "summit": '<path d="M3 18.5 10 9.5l3.5 4.5L16.5 9l4.5 9.5Z"/>',
}
TECH_SET = ["products", "saas", "ai", "automation", "api", "integrations", "cloud", "analytics", "data", "database",
            "web", "mobile", "security", "teams", "workflow", "ai-assistant"]
ICON_LABELS = {"products": "Products", "saas": "SaaS", "ai": "Artificial Intelligence", "automation": "Automation", "api": "API",
               "integrations": "Integrations", "cloud": "Cloud", "analytics": "Analytics", "data": "Data", "database": "Database",
               "web": "Web", "mobile": "Mobile", "security": "Security", "teams": "Teams", "workflow": "Workflow", "ai-assistant": "AI Assistant"}
ICON_ATTRS = 'fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"'


def write_icons():
    out = ROOT / "icons" / "svg"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()
    for name, body in ICONS.items():
        label = ICON_LABELS.get(name, name.replace("-", " ").title())
        (out / f"{name}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {ICON_ATTRS} '
            f'role="img" aria-label="{label}">{body}</svg>\n')
    sprite = "".join(f'<symbol id="zi-{n}" viewBox="0 0 24 24">{b}</symbol>' for n, b in ICONS.items())
    (ROOT / "icons" / "zirven-icons.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none">{sprite}</svg>\n')
    js = ("/* Zirven icon sprite injector — generated by scripts/build_brand.py.\n"
          "   Usage: <svg class=\"zi\"><use href=\"#zi-analytics\"/></svg> */\n"
          "(function () {\n  var s = " + json.dumps(f'<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">{sprite}</svg>') + ";\n"
          "  function inject() { var d = document.createElement('div'); d.innerHTML = s; document.body.insertBefore(d.firstChild, document.body.firstChild); }\n"
          "  if (document.body) inject(); else document.addEventListener('DOMContentLoaded', inject);\n})();\n")
    (ROOT / "assets" / "js" / "zirven-icons.js").write_text(js)
    (ROOT / "icons" / "icons.json").write_text(json.dumps(
        {"grid": 24, "stroke": 1.75, "caps": "round", "joins": "round", "safe-area": 2,
         "technology": {n: ICON_LABELS[n] for n in TECH_SET},
         "ui": [n for n in ICONS if n not in TECH_SET]}, indent=2) + "\n")


# =============================================================================
# 6. PATTERNS — data terrain (contours), ascent lines, module grid
# =============================================================================
def _field(x, y, peaks):
    """Elevation = peaks + a ridge climbing at 20° toward the summit + fine undulation."""
    v = sum(a * math.exp(-(((x - px) / sx) ** 2 + ((y - py) / sy) ** 2) / 2) for px, py, a, sx, sy in peaks)
    d = abs((y - 900) + (x - 200) * T20) / math.hypot(1, T20)
    along = max(0.0, min(1.0, (x - 150) / 1100))
    v += 0.42 * along * math.exp(-(d / 120) ** 2 / 2)
    v += 0.035 * math.sin(x / 53 + y / 97) * math.cos(y / 61 - x / 140)
    return v


def _contours(w, h, step, levels, peaks):
    nx, ny = int(w / step) + 2, int(h / step) + 2
    grid = [[_field(i * step, j * step, peaks) for i in range(nx)] for j in range(ny)]
    paths = []
    for lv in levels:
        segs = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                v = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
                corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                pts = []
                for a in range(4):
                    b = (a + 1) % 4
                    if (v[a] - lv) * (v[b] - lv) < 0:
                        t = (lv - v[a]) / (v[b] - v[a])
                        (xa, ya), (xb, yb) = corners[a], corners[b]
                        pts.append(((xa + t * (xb - xa)) * step, (ya + t * (yb - ya)) * step))
                if len(pts) == 2:
                    segs.append(tuple(pts))
                elif len(pts) == 4:
                    segs.append((pts[0], pts[1]))
                    segs.append((pts[2], pts[3]))
        # stitch segments into polylines
        key = lambda p: (round(p[0], 3), round(p[1], 3))
        adj: dict = {}
        for s in segs:
            for p in s:
                adj.setdefault(key(p), []).append(s)
        used = set()
        for s in segs:
            if id(s) in used:
                continue
            used.add(id(s))
            line = [s[0], s[1]]
            for direction in (1, -1):
                while True:
                    end = line[-1] if direction == 1 else line[0]
                    nxt = None
                    for cand in adj.get(key(end), []):
                        if id(cand) not in used:
                            nxt = cand
                            break
                    if not nxt:
                        break
                    used.add(id(nxt))
                    other = nxt[1] if key(nxt[0]) == key(end) else nxt[0]
                    if direction == 1:
                        line.append(other)
                    else:
                        line.insert(0, other)
            if len(line) > 6:
                paths.append((lv, line))
    return paths


def _smooth(line, closed):
    # Catmull-Rom → cubic Bézier, after light decimation
    pts = line[::2] + ([line[-1]] if len(line) % 2 == 0 else [])
    if len(pts) < 3:
        pts = line
    f = lambda v: f"{v:.1f}"
    d = f"M{f(pts[0][0])} {f(pts[0][1])}"
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else (pts[-2] if closed else pts[i])
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else (pts[1] if closed else p2)
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}"
    return d


TERRAIN_PEAKS = [  # (x, y, amplitude, sx, sy) — one dominant summit, supporting ridges
    (1180, 300, 0.95, 170, 150), (980, 420, 0.45, 150, 120), (1400, 520, 0.50, 190, 170), (760, 610, 0.30, 170, 130),
    (420, 760, 0.28, 210, 170), (1480, 860, 0.22, 200, 150), (300, 250, 0.25, 180, 200), (620, 180, 0.18, 160, 120),
]
TERRAIN_NODES = [(1180, 300), (980, 420), (1400, 520)]


def terrain_svg(w=1600, h=1000, scheme="dark", nodes=True, highlight=True):
    levels = [0.06 + i * 0.06 for i in range(22)]
    paths = _contours(w, h, 10, levels, TERRAIN_PEAKS)
    bg = BRAND["night"]["hex"] if scheme == "dark" else BRAND["snow"]["hex"]
    line = BRAND["lavender"]["hex"] if scheme == "dark" else BRAND["violet"]["hex"]
    base_op = 0.20 if scheme == "dark" else 0.16
    out = [f'<rect width="{w}" height="{h}" fill="{bg}"/>'] if scheme != "transparent" else []
    hi_level = levels[8]
    for lv, ln in paths:
        closed = math.dist(ln[0], ln[-1]) < 12
        d = _smooth(ln, closed)
        if highlight and abs(lv - hi_level) < 1e-6:
            col = BRAND["electric"]["hex"]
            out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" stroke-opacity="0.9"/>')
        else:
            op = base_op + 0.25 * (lv / levels[-1]) * (1 if scheme == "dark" else 0.6)
            out.append(f'<path d="{d}" fill="none" stroke="{line}" stroke-width="1" stroke-opacity="{op:.2f}"/>')
    if nodes:
        sig = BRAND["cyan"]["hex"] if scheme == "dark" else CYAN_INK
        for (x, y) in TERRAIN_NODES:
            out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{sig}"/><circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{sig}" stroke-opacity="0.45"/>')
        (ax, ay), (bx, by), (cx, cy) = TERRAIN_NODES
        out.append(f'<path d="M{bx} {by} L{ax} {ay} L{cx} {cy}" fill="none" stroke="{sig}" stroke-opacity="0.5" stroke-width="1" stroke-dasharray="3 5"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice">' + "".join(out) + "</svg>\n"


def ascent_svg(w=1600, h=1000, scheme="dark"):
    bg = BRAND["night"]["hex"] if scheme == "dark" else BRAND["snow"]["hex"]
    col = BRAND["lavender"]["hex"] if scheme == "dark" else BRAND["violet"]["hex"]
    out = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    gap = 28
    for i in range(-40, 80):
        y0 = i * gap
        op = 0.07 + 0.30 * max(0.0, 1 - abs(i - 22) / 24)
        out.append(f'<path d="M0 {y0 + w * T20:.1f} L{w} {y0:.1f}" stroke="{col}" stroke-opacity="{op:.2f}" stroke-width="1"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice">' + "".join(out) + "</svg>\n"


def module_grid_svg(w=1600, h=1000, scheme="dark"):
    """Product-ecosystem grid. A quiet field of module points; along the 20° ramp the
    points become modules, and a few modules are 'live' products. Read: systems that
    build on each other and climb."""
    bg = BRAND["night"]["hex"] if scheme == "dark" else BRAND["snow"]["hex"]
    col = BRAND["lavender"]["hex"] if scheme == "dark" else BRAND["violet"]["hex"]
    acc = BRAND["electric"]["hex"] if scheme == "dark" else BRAND["violet"]["hex"]
    sig = BRAND["cyan"]["hex"] if scheme == "dark" else CYAN_INK
    out = [f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    cell = 40
    live = {(27, 9), (31, 7), (35, 5), (23, 11)}
    for j in range(h // cell + 1):
        for i in range(w // cell + 1):
            x, y = i * cell + cell / 2, j * cell + cell / 2
            # distance to the ramp line through (0, 980) rising at 20°
            d = abs((y - 980) + x * T20) / math.hypot(1, T20)
            band = max(0.0, 1 - d / 150)
            if (i, j) in live:
                out.append(f'<rect x="{x - 9}" y="{y - 9}" width="18" height="18" rx="4" fill="{acc}"/>')
            elif band > 0.55 and (i + j) % 2 == 0:
                out.append(f'<rect x="{x - 8}" y="{y - 8}" width="16" height="16" rx="3.5" fill="none" stroke="{col}" stroke-opacity="{0.18 + 0.4 * band:.2f}"/>')
            else:
                out.append(f'<circle cx="{x}" cy="{y}" r="1.3" fill="{col}" fill-opacity="{0.12 + 0.3 * band:.2f}"/>')
    (ax, ay) = (35 * cell + cell / 2, 5 * cell + cell / 2)
    out.append(f'<circle cx="{ax}" cy="{ay}" r="3.5" fill="{sig}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice">' + "".join(out) + "</svg>\n"


# =============================================================================
# 7. CONSTRUCTION DRAWING & LOGO REVIEW CANDIDATES
# =============================================================================
def candidate_tile(size, polys):
    """Flat Zirven Violet tile with a candidate symbol, for the logo review."""
    xs = [x for p in polys for x, _ in p]; ys = [y for p in polys for _, y in p]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    h = round(size * 0.62) if size <= 48 else size * 0.56
    s = h / (y1 - y0)
    w = (x1 - x0) * s
    body = f'<rect width="{size}" height="{size}" rx="{size * 0.225:.2f}" fill="{BRAND["violet"]["hex"]}"/>'
    body += f'<path fill="{BRAND["snow"]["hex"]}" d="{path_d(polys, -x0 + ((size - w) / 2) / s, -y0 + ((size - h) / 2) / s, s, 3)}"/>'
    return body


def construction_svg():
    s = MASTER
    k = 10  # px per unit
    W, H = 64 * k, 64 * k
    P = lambda p: (p[0] * k, p[1] * k)
    out = [f'<rect width="{W}" height="{H}" fill="{BRAND["snow"]["hex"]}"/>']
    for i in range(0, 65, 2):
        op = 0.22 if i % 10 == 0 else 0.08
        out.append(f'<path d="M{i * k} 0V{H}M0 {i * k}H{W}" stroke="{BRAND["violet"]["hex"]}" stroke-opacity="{op}" stroke-width="1"/>')
    out.append(f'<path d="{path_d(s.solid(), 0, 0, k, 1)}" fill="{BRAND["violet"]["hex"]}" fill-opacity="0.16" stroke="{BRAND["violet"]["hex"]}" stroke-width="2"/>')
    # extended construction lines
    tl, sm = P(s.TL), P(s.S)
    ln = lambda a, b, dash="6 6": f'<path d="M{a[0]:.1f} {a[1]:.1f} L{b[0]:.1f} {b[1]:.1f}" stroke="{BRAND["night"]["hex"]}" stroke-width="1.5" stroke-dasharray="{dash}"/>'
    out.append(ln((0, tl[1] + tl[0] * T20), (W, tl[1] - (W - tl[0]) * T20)))
    out.append(ln((sm[0] + 8 * k * s.k, sm[1] - 8 * k), (sm[0] - 52 * k * s.k, sm[1] + 52 * k)))
    out.append(ln((0, (s.yb - s.base) * k), (W, (s.yb - s.base) * k)))
    # angle labels
    lab = lambda x, y, t, c=BRAND["night"]["hex"]: f'<text x="{x}" y="{y}" font-family="Readex Pro, sans-serif" font-size="22" font-weight="600" fill="{c}">{t}</text>'
    out.append(f'<path d="M{tl[0] + 120:.1f} {tl[1]:.1f} A120 120 0 0 0 {tl[0] + 120 * math.cos(math.radians(20)):.1f} {tl[1] - 120 * math.sin(math.radians(20)):.1f}" fill="none" stroke="{BRAND["electric"]["hex"]}" stroke-width="3"/>')
    out.append(f'<path d="M{tl[0]:.1f} {tl[1]:.1f} H{tl[0] + 150:.1f}" stroke="{BRAND["electric"]["hex"]}" stroke-width="1.5"/>')
    out.append(lab(tl[0] + 130, tl[1] - 14, "20°", BRAND["violet"]["hex"]))
    out.append(lab(sm[0] - 112, sm[1] + 70, "35°", BRAND["violet"]["hex"]))
    bt = (_inter(s.dr, s.bt)[0] * k, (s.yb - s.base) * k)
    out.append(lab(bt[0] + 36, bt[1] - 14, "55°", BRAND["violet"]["hex"]))
    # module brackets
    out.append(f'<path d="M{(s.x1 + 2) * k} {(s.yb - s.base) * k} h12 M{(s.x1 + 2) * k} {s.yb * k} h12 M{(s.x1 + 2) * k + 6} {(s.yb - s.base) * k} V{s.yb * k}" stroke="{BRAND["night"]["hex"]}" stroke-width="2"/>')
    out.append(lab((s.x1 + 4) * k, (s.yb - s.base / 2) * k + 8, "1m"))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">' + "".join(out) + "</svg>\n"


# =============================================================================
# 8. WRITE EVERYTHING
# =============================================================================
def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main():
    write_tokens()
    write_icons()
    L = ROOT / "logo" / "svg"
    for old in L.glob("*.svg"):
        old.unlink()

    def emit(name, wh_body, title):
        w, h, body = wh_body
        write(L / f"{name}.svg", svg_doc(w, h, body, title, DESC_NOTE))

    for sc in ("light", "dark", "black", "white"):
        emit(f"zirven-symbol-{sc}", symbol_only(sc), "Zirven symbol")
        emit(f"zirven-symbol-micro-{sc}", symbol_only(sc, MICRO), "Zirven symbol — micro (16–24 px)")
        emit(f"zirven-wordmark-{sc}", wordmark(sc), "Zirven wordmark")
        emit(f"zirven-logo-horizontal-{sc}", lockup_horizontal(sc), "Zirven logo")
        emit(f"zirven-logo-stacked-{sc}", lockup_stacked(sc), "Zirven logo — stacked")
        emit(f"zirven-logo-arabic-{sc}", lockup_arabic(sc), "زيرفن — Zirven logo, Arabic")
    emit("zirven-logo-horizontal-violet", lockup_horizontal("violet", pad_units=180), "Zirven logo on Zirven Violet")
    for sc in ("light", "dark"):
        emit(f"zirven-logo-descriptor-en-{sc}", lockup_horizontal(sc, "Software · SaaS · AI"), "Zirven — Software · SaaS · AI")
        emit(f"zirven-logo-descriptor-tr-{sc}", lockup_horizontal(sc, "Yazılım · SaaS · Yapay Zekâ"), "Zirven — Yazılım · SaaS · Yapay Zekâ")
        emit(f"zirven-logo-bilingual-ar-{sc}", lockup_arabic(sc, bilingual=True), "Zirven — Arabic + Latin")
        emit(f"vevo-endorsed-{sc}", endorsement(sc), "VEVO — a product by Zirven")

    # app icon / favicon masters
    F = ROOT / "favicon"
    for old in F.glob("*.svg"):
        old.unlink()
    write(F / "app-icon.svg", svg_doc(1024, 1024, app_tile(1024), "Zirven app icon"))
    write(F / "app-icon-flat.svg", svg_doc(1024, 1024, app_tile(1024, flat=True), "Zirven app icon — flat"))
    write(F / "favicon.svg", svg_doc(48, 48, app_tile(48, flat=True), "Zirven"))
    write(F / "favicon-16.svg", svg_doc(16, 16, app_tile(16, flat=True), "Zirven"))
    maskable = f'<rect width="1024" height="1024" fill="{BRAND["violet"]["hex"]}"/>' + symbol_group(MASTER, (1024 - 0.42 * 1024 * 42 / 50) / 2, 1024 * 0.29, 1024 * 0.42, BRAND["snow"]["hex"])[0]
    write(F / "maskable-icon.svg", svg_doc(1024, 1024, maskable, "Zirven maskable icon"))
    write(F / "vevo-app-icon.svg", svg_doc(1024, 1024, app_tile(1024, "vevo"), "VEVO app icon — a Zirven product"))
    write(F / "future-product-tile.svg", svg_doc(1024, 1024, app_tile(1024, "future"), "Future Zirven product — placeholder tile"))
    write(F / "site.webmanifest", json.dumps({
        "name": "Zirven", "short_name": "Zirven", "description": "Zirven builds intelligent digital products — Software · SaaS · AI.",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
        "theme_color": BRAND["night"]["hex"], "background_color": BRAND["night"]["hex"], "display": "standalone"}, indent=2) + "\n")

    # logo review candidates
    E = ROOT / "logo" / "exploration"
    for old in E.glob("*.svg"):
        old.unlink()
    cands = {"A-summit-z-refined": MASTER.solid(), "B-summit-modular": MASTER.modular(), "C-summit-layered": MASTER.layered()}
    for name, polys in cands.items():
        for sc in ("light", "dark", "black"):
            w, h, body = symbol_only(sc, MASTER, polys)
            write(E / f"{name}-{sc}.svg", svg_doc(w, h, body, f"Logo review candidate {name}"))
        # micro variants for small-size comparison
        mg = Summit(x0=MICRO.x0, x1=MICRO.x1, ys=MICRO.ys, yb=MICRO.yb, ramp=MICRO.ramp, base=MICRO.base, descent_deg=57.0, gap=MICRO_GAP)
        mp = {"A-summit-z-refined": MICRO.solid(), "B-summit-modular": mg.modular(), "C-summit-layered": mg.layered()}[name]
        w, h, body = symbol_only("black", MICRO, mp)
        write(E / f"{name}-micro-black.svg", svg_doc(w, h, body, f"Logo review candidate {name} — micro"))
        # tile versions (app icon / favicon test) using the micro geometry
        for size in (16, 32, 48, 1024):
            write(E / f"{name}-tile-{size}.svg", svg_doc(size, size, candidate_tile(size, mp if size <= 48 else polys), f"{name} tile"))
    write(E / "construction.svg", construction_svg())

    P = ROOT / "pattern"
    for old in P.glob("*.svg"):
        old.unlink()
    write(P / "terrain-dark.svg", terrain_svg(scheme="dark"))
    write(P / "terrain-light.svg", terrain_svg(scheme="light"))
    write(P / "terrain-dark-plain.svg", terrain_svg(scheme="dark", nodes=False, highlight=False))
    write(P / "ascent-dark.svg", ascent_svg(scheme="dark"))
    write(P / "ascent-light.svg", ascent_svg(scheme="light"))
    write(P / "module-grid-dark.svg", module_grid_svg(scheme="dark"))
    write(P / "module-grid-light.svg", module_grid_svg(scheme="light"))

    # geometry report used by the guidelines
    write(ROOT / "logo" / "geometry.json", json.dumps({
        "artboard": 64, "module_m": MASTER.base,
        "angles_deg": {"ramp": 20, "summit": 35, "descent": 55},
        "symbol_bbox": {"x": MASTER.x0, "y": MASTER.ys, "w": MASTER.x1 - MASTER.x0, "h": MASTER.yb - MASTER.ys},
        "points_master": [[round(x, 3), round(y, 3)] for x, y in MASTER.solid()[0]],
        "points_micro": [[round(x, 3), round(y, 3)] for x, y in MICRO.solid()[0]],
        "lockup": {"symbol_height": "1.62 × x-height", "gap": "0.30 × symbol height", "wordmark": "Readex Pro 600, -6 units tracking, lowercase"},
    }, indent=2) + "\n")
    print("Zirven V2.1 assets generated in", ROOT)


if __name__ == "__main__":
    main()
