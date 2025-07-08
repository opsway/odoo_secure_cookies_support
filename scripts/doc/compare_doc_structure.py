import os
import sys
import zipfile
import io
import requests


def get_local_structure(root):
    structure = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, f), root)
            structure.add(rel_path)
    return structure


def get_reference_structure():
    # Download zip archive of the structure folder
    url = "https://github.com/opsway/odoo_sop/archive/refs/heads/main.zip"
    headers = {}
    token = os.environ.get("GH_PAT")
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to download reference repo: {resp.status_code}")
        sys.exit(1)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        prefix = "odoo_sop-main/doc/"
        structure = set()
        for name in z.namelist():
            if name.startswith(prefix) and not name.endswith("/"):
                rel_path = os.path.relpath(name, prefix)
                structure.add(rel_path)
        return structure


def main():
    local = get_local_structure("doc")
    ref = get_reference_structure()
    missing = ref - local
    extra = local - ref
    if missing or extra:
        print("Doc structure mismatch!")
        if missing:
            print(f"Missing files: {sorted(missing)}")
        if extra:
            print(f"Extra files: {sorted(extra)}")
        sys.exit(1)
    print("Doc structure matches reference.")


if __name__ == "__main__":
    main()
