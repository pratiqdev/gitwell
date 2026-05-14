#!/usr/bin/env python3
"""Emit optional release-notes prefix from CHANGELOG.md or release-notes/gitwell-{version}.md."""
from __future__ import annotations

import pathlib
import re
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: extract_changelog_fragment VERSION", file=sys.stderr)
        return 2
    ver = argv[1]
    parts: list[str] = []

    chlog = pathlib.Path("CHANGELOG.md")
    if chlog.is_file():
        text = chlog.read_text(encoding="utf-8")
        patterns = (
            rf"## \[{re.escape(ver)}\].*?(?=\n## |\Z)",
            rf"## \s*{re.escape(ver)}\s*.*?(?=\n## |\Z)",
        )
        for pat in patterns:
            m = re.search(pat, text, flags=re.DOTALL)
            if m:
                parts.append(m.group(0).strip())
                break

    frag = pathlib.Path(f"release-notes/gitwell-{ver}.md")
    if frag.is_file():
        parts.append(frag.read_text(encoding="utf-8").strip())

    prefix = "\n\n".join(parts).strip()
    if prefix:
        pathlib.Path("_release_notes_prefix.md").write_text(prefix + "\n\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
