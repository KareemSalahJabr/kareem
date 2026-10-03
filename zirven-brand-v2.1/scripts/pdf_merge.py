#!/usr/bin/env python3
"""Merge single-page PDFs into one document with Zirven metadata.

Usage: pdf_merge.py <out.pdf> <title> <in1.pdf> [<in2.pdf> ...]   (called by export-pdf.mjs)
"""
import sys
from pypdf import PdfReader, PdfWriter


def main():
    out, title, inputs = sys.argv[1], sys.argv[2], sys.argv[3:]
    writer = PdfWriter()
    for path in inputs:
        for page in PdfReader(path).pages:
            writer.add_page(page)
    writer.add_metadata({
        "/Title": title,
        "/Author": "Zirven Technology",
        "/Subject": "Zirven builds intelligent digital products. Software · SaaS · AI.",
        "/Keywords": "Zirven, brand identity, V2.1, software, SaaS, AI, VEVO",
    })
    for page in writer.pages:
        page.compress_content_streams(level=9)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with open(out, "wb") as fh:
        writer.write(fh)
    print(f"{out}: {len(writer.pages)} pages")


if __name__ == "__main__":
    main()
