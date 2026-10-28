#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
IGNORED = {".git", ".github", ".claude", "docs", "scripts", ".venv", "venv"}
RECOMMENDED = {"name", "depends", "license"}


def addon_dirs():
    for path in sorted(ROOT.iterdir()):
        if path.is_dir() and path.name not in IGNORED and (path / "__manifest__.py").exists():
            yield path


def load_manifest(path: pathlib.Path):
    try:
        value = ast.literal_eval(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"cannot parse as a literal Python dictionary: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("manifest is not a dictionary")
    return value


def main() -> int:
    failed = False
    seen = False
    for addon in addon_dirs():
        seen = True
        manifest_path = addon / "__manifest__.py"
        try:
            manifest = load_manifest(manifest_path)
        except ValueError as exc:
            print(f"ERROR {manifest_path.relative_to(ROOT)}: {exc}")
            failed = True
            continue
        missing = sorted(RECOMMENDED - manifest.keys())
        if missing:
            print(f"WARN  {addon.name}: recommended manifest keys missing: {', '.join(missing)}")
        depends = manifest.get("depends", [])
        if not isinstance(depends, (list, tuple)) or not all(isinstance(x, str) for x in depends):
            print(f"ERROR {addon.name}: 'depends' must be a list/tuple of strings")
            failed = True
        version = manifest.get("version")
        if version is not None and not isinstance(version, str):
            print(f"ERROR {addon.name}: manifest version must be a string when present")
            failed = True
    if not seen:
        print("No addons discovered; repository-level checks only.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
