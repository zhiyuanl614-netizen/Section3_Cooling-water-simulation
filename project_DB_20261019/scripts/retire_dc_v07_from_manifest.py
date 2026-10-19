# -*- coding: utf-8 -*-
"""2026-10-19 workspace cleanup: retire dc_v07 payloads from the pre-thermal manifest.

The dc_v07 directory was removed during the author-requested workspace cleanup
(retain only the final revision chain). Its 11 files were protected inside
thermal_v072/PRE_THERMAL_MANIFEST.json (350 payloads). This script removes those
entries and records the retirement with original SHA-256 for traceability.
"""
import json
from pathlib import Path

P = Path(r"C:\Users\995599\Desktop\project\manuscript\revisions\thermal_v072\PRE_THERMAL_MANIFEST.json")
m = json.loads(P.read_text(encoding="utf-8"))
files = m["files"]
retired = {n: h for n, h in files.items() if n.startswith("manuscript/revisions/dc_v07/")}
assert len(retired) == 11, f"expected 11 dc_v07 entries, found {len(retired)}"
for n in retired:
    del files[n]
m["retired_files"] = {
    "date": "2026-10-19",
    "reason": "Author-requested workspace cleanup: retain only the final revision chain; "
              "manuscript/revisions/dc_v07 was the retired DC-only v0.7 revision record.",
    "count": 11,
    "sha256": retired,
}
P.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"manifest payloads: 350 -> {len(files)}; retired 11 dc_v07 entries; trace recorded")
