#!/usr/bin/env python3
"""Regenerate FLOUCI_FIN_KATMCHI_FULL_BOOK.md from book/*.md (RTL-wrapped for correct Arabic rendering)."""
import glob
import io
import re

HEADER = (
    "# فلوسي فين كتمشي؟\n"
    "## الدليل العملي للشاب المغربي لتنظيم الراتب، التحكم في المصاريف، الادخار وبناء أول خطة مالية\n"
    "### الطبعة التفاعلية الكاملة \u2014 مراجعة لغوية منق\u0651حة (2026)\n"
)

WRAP_RE = re.compile(r"^<div dir=\"rtl\">\s*$|^</div>\s*$", re.M)


def strip_wrappers(text: str) -> str:
    return WRAP_RE.sub("", text).strip()


def main() -> None:
    parts = []
    for f in sorted(glob.glob("book/*.md")):
        with io.open(f, encoding="utf-8") as fh:
            parts.append(strip_wrappers(fh.read()))
    body = "\n\n---\n\n".join(parts)
    full = '<div dir="rtl">\n\n' + HEADER + "\n---\n\n" + body + "\n\n</div>\n"
    with io.open("FLOUCI_FIN_KATMCHI_FULL_BOOK.md", "w", encoding="utf-8") as fh:
        fh.write(full)
    print(f"FLOUCI_FIN_KATMCHI_FULL_BOOK.md rebuilt ({len(full)} chars, RTL-wrapped)")


if __name__ == "__main__":
    main()
