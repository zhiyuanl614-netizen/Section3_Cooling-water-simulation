# -*- coding: utf-8 -*-
"""2026-10-19 workspace cleanup: retire payloads whose files no longer exist
(dc_v07 done in a prior step; this pass removes opf_v071) from the pre-thermal manifest.
Records original SHA-256 for traceability.
"""
import json
from pathlib import Path

R = Path(r"C:\Users\995599\Desktop\project")
P = R / "manuscript" / "revisions" / "thermal_v072" / "PRE_THERMAL_MANIFEST.json"
m = json.loads(P.read_text(encoding="utf-8"))
files = m["files"]
missing = {n: h for n, h in files.items() if not (R / n).exists()}
assert missing and all(n.startswith("manuscript/revisions/opf_v071/") for n in missing), \
    f"unexpected missing set: {list(missing)[:3]}"
for n in missing:
    del files[n]
m.setdefault("retired_files", {})["additional"] = {
    "date": "2026-10-19",
    "reason": "Author-requested workspace cleanup: retire the opf_v071 revision record "
              "superseded by rq2_recoupled_v072.",
    "count": len(missing),
    "sha256": missing,
}
P.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"manifest payloads: 339 -> {len(files)}; retired {len(missing)} opf_v071 entries; trace recorded")
