# -*- coding: utf-8 -*-
"""Rebuild the self-contained current-version release ZIP from release_v072/.

Pure standard library; excludes this script, caches and the ZIP itself.
"""
import zipfile
from pathlib import Path

D = Path(__file__).resolve().parents[1]
OUT = D.parent / "Current_release_v072.zip"
exclude = {"__pycache__", ".pyc", "Current_release_v072.zip"}
files = sorted(p for p in D.rglob("*") if p.is_file()
               and "__pycache__" not in p.parts and not p.name.endswith(".pyc")
               and p.name != "Current_release_v072.zip")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, f.relative_to(D.parent).as_posix())
print(f"RELEASE PACKAGE: {len(files)} members; {OUT.stat().st_size} bytes; SHA256 {__import__('hashlib').sha256(OUT.read_bytes()).hexdigest()}")
