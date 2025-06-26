#!/usr/bin/env python3
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRUCTURE_DIR = os.path.abspath(os.path.join(ROOT, "../doc"))
README = os.path.abspath(os.path.join(ROOT, "../README.md"))
START_MARK = "<!-- CONTENT_LIST_START -->"
END_MARK = "<!-- CONTENT_LIST_END -->"


def extract_title_and_description(md_path):
    with open(md_path, encoding="utf-8") as f:
        lines = f.readlines()
    title = None
    description = None
    in_purpose = False
    purpose_lines = []
    for line in lines:
        # Title extraction
        if title is None and line.startswith("# "):
            title = line.strip("# ").strip()
            continue
        # Start Purpose section
        if line.strip().lower().startswith("## purpose"):
            in_purpose = True
            continue
        # End Purpose section at next header
        if in_purpose and (line.startswith("## ") and not line.lower().startswith("## purpose")
                           or not line.strip() and purpose_lines):
            break
        # Collect Purpose lines
        if in_purpose:
            purpose_lines.append(line.rstrip("\n"))
    if purpose_lines:
        description = "\n".join(purpose_lines).strip()
    return title, description


def build_content_list():
    entries = []
    for fname in sorted(os.listdir(STRUCTURE_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join("doc", fname)
        title, desc = extract_title_and_description(
            os.path.join(STRUCTURE_DIR, fname))
        if not title:
            continue
        desc = desc or ""
        entries.append(f"- [{title}]({path})\n  - {desc}")
    return "\n".join(entries)


def update_readme():
    with open(README, encoding="utf-8") as f:
        content = f.read()
    content_list = build_content_list()
    new_section = f"{START_MARK}\n\n{content_list}\n\n{END_MARK}"
    if START_MARK in content and END_MARK in content:
        # Replace
        new_content = re.sub(f"{START_MARK}.*?{END_MARK}",
                             new_section, content, flags=re.DOTALL)
    else:
        # Insert after first heading
        parts = content.split("\n", 2)
        if len(parts) > 2:
            new_content = (
                f"{parts[0]}\n{parts[1]}\n\n{new_section}\n{parts[2]}"
            )
        else:
            new_content = f"{content}\n\n{new_section}"
    if new_content != content:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md was updated. Please add it to your changelog and re-stage the file before committing.",
              file=sys.stderr)
        sys.exit(1)
    # No change
    sys.exit(0)


if __name__ == "__main__":
    update_readme()
