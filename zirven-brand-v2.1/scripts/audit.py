#!/usr/bin/env python3
"""
Zirven V2.1 — semantic audit.

Scans every text file in the V2.1 package (HTML, CSS, JS, JSON, SVG incl. <title>/<desc>/alt
text, Markdown, scripts) for vocabulary from the retired consumer positioning, in English,
Turkish and Arabic, plus generic hype language the voice rules forbid.

  python3 scripts/audit.py          writes audit/semantic-audit.md + audit/semantic-audit.json
                                    exits 1 if any positioning violation is found

This file necessarily contains the search terms, so it excludes itself and its own reports.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXT = {".html", ".css", ".js", ".mjs", ".cjs", ".json", ".svg", ".md", ".py", ".scss", ".webmanifest", ".txt"}
EXCLUDE = {Path("scripts/audit.py"), Path("audit/semantic-audit.md"), Path("audit/semantic-audit.json")}

# Retired positioning — must not describe Zirven anywhere.
POSITIONING = {
    "deal/deals": r"\bdeal(s|ing)?\b",
    "coupon": r"\bcoupons?\b",
    "voucher": r"\bvouchers?\b",
    "discount": r"\bdiscount\w*",
    "merchant": r"\bmerchants?\b",
    "offer/offering": r"\boffer(s|ed|ing|ings)?\b",
    "QR / redemption": r"\bQR\b|\bredeem\w*|\bredemption\w*",
    "restaurant": r"\brestaurants?\b",
    "cafe / coffee": r"\bcaf[eé]s?\b|\bcoffee\b",
    "hammam": r"\bhammams?\b",
    "barber": r"\bbarber\w*",
    "beauty / shopping": r"\bbeauty\b|\bshopping\b",
    "money saving": r"\bsave money\b|\bsave up to\b|\bsavings?\b|money[- ]saving|\bcashback\b|\d+\s?%\s?off\b|\bpromo(s|tion|tions)?\b",
    "old taglines": r"every deal|her f[ıi]rsat|at its peak",
    "Summit Coral rationale": r"where money is saved",
    "Getir / Gulf / tourists": r"\bgetir\b|\bgulf\b|\btourists?\b|\btourism\b",
    "audience: Arabs in Türkiye": r"arabs?\s+(living\s+)?in\s+t[uü]rk",
    "TR: fırsat / indirim / kupon": r"f[ıi]rsat|indirim|\bkupon|\brestoran|\bkafe\b|\bberber|\bhamam",
    "AR: offer / discount / coupon / venues": r"عرض|عروض|خصم|كوبون|قسيمة|مطعم|مقهى|حمّام|حلاق|توفير|في قمته",
}
# Generic hype — allowed only as documented negative examples in the guidelines.
HYPE = {
    "hype": r"revolutioni[sz]\w*|innovating tomorrow|next[- ]gen\w*|cutting[- ]edge|ai-powered everything|\bseamless\w*|\bunleash\w*|game[- ]chang\w*|world[- ]class|\bsynerg\w*|supercharg\w*",
}
HYPE_ALLOWED_FILES = {Path("guidelines/index.html")}  # voice section: "Never use" / "Don't write" examples
INFO = {"words containing 'deal'": r"\b\w+deal\w*\b"}  # e.g. 'ideal' — reported for review, not a violation

# Signal inventory: does the package read as a technology company?
TECH_SIGNALS = r"\b(saas|software|platform|api|ai|workflow|automation|analytics|integration\w*|data|cloud|developer\w*|sdk|webhook\w*|dashboard|product\w*)\b"


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and p.suffix.lower() in TEXT_EXT and rel not in EXCLUDE and "node_modules" not in p.parts:
            yield p, rel


def scan():
    hits, info, tech_count, scanned = [], [], 0, 0
    for p, rel in files():
        scanned += 1
        text = p.read_text(encoding="utf-8", errors="ignore")
        tech_count += len(re.findall(TECH_SIGNALS, text, flags=re.I))
        for n, line in enumerate(text.splitlines(), 1):
            for label, rx in POSITIONING.items():
                for m in re.finditer(rx, line, flags=re.I):
                    hits.append({"file": str(rel), "line": n, "category": "positioning", "term": label, "match": m.group(0),
                                 "context": line.strip()[max(0, m.start() - 60): m.end() + 60][:200], "status": "VIOLATION"})
            for label, rx in HYPE.items():
                for m in re.finditer(rx, line, flags=re.I):
                    ok = rel in HYPE_ALLOWED_FILES
                    hits.append({"file": str(rel), "line": n, "category": "voice", "term": label, "match": m.group(0),
                                 "context": line.strip()[max(0, m.start() - 60): m.end() + 60][:200],
                                 "status": "allowed (documented 'never use' example)" if ok else "VIOLATION"})
            for label, rx in INFO.items():
                for m in re.finditer(rx, line, flags=re.I):
                    info.append({"file": str(rel), "line": n, "match": m.group(0)})
    return hits, info, tech_count, scanned


def main():
    hits, info, tech_count, scanned = scan()
    violations = [h for h in hits if h["status"] == "VIOLATION"]
    allowed = [h for h in hits if h["status"] != "VIOLATION"]
    out = ROOT / "audit"
    out.mkdir(exist_ok=True)
    (out / "semantic-audit.json").write_text(json.dumps({
        "date": str(date.today()), "files_scanned": scanned, "violations": violations, "allowed_references": allowed,
        "info": info, "technology_signal_terms": tech_count}, indent=2, ensure_ascii=False) + "\n")

    md = [f"# Zirven V2.1 — semantic audit", "",
          f"Generated by `scripts/audit.py` on {date.today()}. Files scanned: **{scanned}** (all text files in the package; "
          "binary fonts and PNG renders excluded; this script and its reports exclude themselves because they contain the search terms).", "",
          "## 1. Terminology scan", "",
          "| Category | Result |", "|---|---|",
          f"| Retired positioning vocabulary (EN / TR / AR) | **{len([h for h in violations if h['category']=='positioning'])} occurrences** |",
          f"| Hype language outside the guidelines' negative examples | **{len([h for h in violations if h['category']=='voice'])} occurrences** |",
          f"| Hype language inside documented 'never use' examples | {len(allowed)} (intentional) |",
          f"| Words containing 'deal' (e.g. 'ideal') for manual review | {len(info)} |",
          f"| Technology signal terms (SaaS, software, platform, API, AI, workflow, data…) | {tech_count} |", ""]
    if violations:
        md += ["### Violations", "", "| File | Line | Term | Context |", "|---|---|---|---|"]
        esc = lambda t: t.replace("|", "\\|")
        md += [f"| `{h['file']}` | {h['line']} | {h['term']} (`{h['match']}`) | {esc(h['context'])} |" for h in violations]
        md.append("")
    if allowed:
        md += ["### Allowed references", "", "| File | Line | Match | Why it is allowed |", "|---|---|---|---|"]
        md += [f"| `{h['file']}` | {h['line']} | `{h['match']}` | {h['status']} |" for h in allowed]
        md.append("")
    if info:
        md += ["### For review", "", "| File | Line | Match |", "|---|---|---|"]
        md += [f"| `{i['file']}` | {i['line']} | `{i['match']}` |" for i in info]
        md.append("")
    md += ["### Terms searched", ""]
    md += [f"- **{k}**: `{v}`" for k, v in {**POSITIONING, **HYPE}.items()]
    md.append("")
    md.append((ROOT / "audit" / "semantic-review.md").read_text() if (ROOT / "audit" / "semantic-review.md").exists() else "")
    (out / "semantic-audit.md").write_text("\n".join(md))
    print(f"scanned {scanned} files · positioning violations: {len([h for h in violations if h['category']=='positioning'])} · "
          f"voice violations: {len([h for h in violations if h['category']=='voice'])} · allowed: {len(allowed)} · review: {len(info)}")
    for h in violations:
        print(f"  {h['file']}:{h['line']}  [{h['term']}]  {h['match']}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
