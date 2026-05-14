#!/usr/bin/env python3
"""Create gitwell-<version>-<slug>.zip with a single top-level binary (equivalent to zip -j).

Uses the stdlib so Windows runners do not need a ``zip`` executable.
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path


def main() -> int:
    version = os.environ.get("GITWELL_VERSION", "").strip()
    slug = os.environ.get("SLUG", "").strip()
    if not version or not slug:
        print("error: GITWELL_VERSION and SLUG must be set", file=sys.stderr)
        return 1

    root = Path.cwd()
    dist = root / "dist"
    win_bin = dist / "gitwell.exe"
    posix_bin = dist / "gitwell"
    if win_bin.is_file():
        binary = win_bin
    elif posix_bin.is_file():
        binary = posix_bin
    else:
        print(f"error: expected {win_bin} or {posix_bin}", file=sys.stderr)
        return 1

    out = root / f"gitwell-{version}-{slug}.zip"
    if out.exists():
        out.unlink()

    arcname = binary.name
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(binary, arcname=arcname)

    print(f"Wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
