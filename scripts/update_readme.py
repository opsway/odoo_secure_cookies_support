#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START = "<!-- ADDON_LIST_START -->"
END = "<!-- ADDON_LIST_END -->"
IGNORED = {".git", ".github", ".claude", "docs", "scripts", ".venv", "venv"}


def addons():
    for path in sorted(ROOT.iterdir()):
        manifest_path = path / "__manifest__.py"
        if not path.is_dir() or path.name in IGNORED or not manifest_path.exists():
            continue
        try:
            manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        name = manifest.get("name") or path.name
        summary = str(manifest.get("summary") or "").strip()
        version = str(manifest.get("version") or "").strip()
        yield path.name, name, summary, version


def render() -> str:
    rows = list(addons())
    if not rows:
        return "_No addons discovered._"
    lines = []
    for directory, name, summary, version in rows:
        suffix = f" — {summary}" if summary else ""
        version_text = f" (`{version}`)" if version else ""
        lines.append(f"- **[{name}]({directory}/)**{version_text}{suffix}")
    return "\n".join(lines)


def updated_content() -> str:
    content = README.read_text(encoding="utf-8")
    if START not in content or END not in content:
        raise SystemExit("README addon-list markers are missing")
    before, rest = content.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n\n{render()}\n\n{END}{after}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    new = updated_content()
    old = README.read_text(encoding="utf-8")
    if new == old:
        return 0
    if args.check:
        print("README addon catalog is stale; run `make catalog`.")
        return 1
    README.write_text(new, encoding="utf-8")
    print("Updated README addon catalog.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
