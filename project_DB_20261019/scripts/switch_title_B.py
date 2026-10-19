# -*- coding: utf-8 -*-
"""One-click title switch to Option B in rq2_recoupled_v072 (run on the Windows host)."""
import zipfile, re, hashlib, json, subprocess, shutil
from pathlib import Path

D = Path(__file__).resolve().parent
MD = D / "Full_manuscript_rq2_rq3_complete_v072.md"
DOCX = D / "Full_manuscript_rq2_rq3_complete_v072.docx"
OLD = "Inventory-controlled capability loss in wet-recirculating cooling: a finite-storage model and response-conditioned DC grid consequences"
NEW = "Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems"
sha = lambda b: hashlib.sha256(b).hexdigest()

# 1) MD first line: A -> B
s = MD.read_text(encoding="utf-8")
lines = s.splitlines()
assert lines[0] == "# " + OLD, f"MD line 1 = {lines[0]!r}, expected Option A"
lines[0] = "# " + NEW
MD.write_text("\n".join(lines) + ("\n" if s.endswith("\n") else ""), encoding="utf-8")
print("MD title -> Option B")

# 2) docx in-place title swap (paragraph + core.xml), all other bytes preserved
with zipfile.ZipFile(DOCX) as z:
    names = z.namelist(); entries = {n: z.read(n) for n in names}
dx = entries["word/document.xml"].decode("utf-8"); cx = entries["docProps/core.xml"].decode("utf-8")
assert dx.count(OLD) == 1 and cx.count(OLD) == 1, "Option A title not found in docx"
entries["word/document.xml"] = dx.replace(OLD, NEW).encode("utf-8")
entries["docProps/core.xml"] = cx.replace(OLD, NEW).encode("utf-8")
tmp = D / ".docx.tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for n in names:
        with zipfile.ZipFile(DOCX) as z: zi = z.getinfo(n)
        zo.writestr(zi, entries[n])
shutil.move(str(tmp), str(DOCX))
with zipfile.ZipFile(DOCX) as z:
    x2 = z.read("word/document.xml").decode("utf-8")
    assert OLD not in x2 and NEW in x2
    assert len(re.findall(r"<m:oMathPara(?:\s|>)", x2)) == 27
    assert len(re.findall(r"<a:blip(?:\s|/>)", x2)) == 6
print("DOCX title -> Option B (27 OMML / 6 figures intact)")

# 3) WORD_AUDIT.json hashes + title
wa = json.loads((D / "WORD_AUDIT.json").read_text(encoding="utf-8"))
wa["title"] = NEW; wa["source_sha256"] = sha(MD.read_bytes()); wa["output_sha256"] = sha(DOCX.read_bytes())
(D / "WORD_AUDIT.json").write_text(json.dumps(wa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# 4) audit contract: NEW_TITLE constant A -> B
ap = (D / "audit_rq2_recoupled.py").read_text(encoding="utf-8")
assert "NEW_TITLE='" + OLD + "'" in ap, "audit constant not found"
ap = ap.replace("NEW_TITLE='" + OLD + "'", "NEW_TITLE='" + NEW + "'")
(D / "audit_rq2_recoupled.py").write_text(ap, encoding="utf-8")

# 5) re-run full audit (rewrites FINAL_AUDIT.json)
r = subprocess.run(["python", "audit_rq2_recoupled.py"], cwd=str(D), capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr

# 6) restore audit date/note
fa = json.loads((D / "FINAL_AUDIT.json").read_text(encoding="utf-8"))
fa["date"] = "2026-10-19"
fa["revision_note"] = ("Re-audit after the 2026-10-19 author decision to adopt Option B title "
                       "(Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems). "
                       "MD first line and docx title paragraph/core.xml updated in place; 27 OMML equations and 6 embedded figures verified intact.")
(D / "FINAL_AUDIT.json").write_text(json.dumps(fa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# 7) rebuild delivery zip
r = subprocess.run(["python", "build_package.py"], cwd=str(D), capture_output=True, text=True)
print(r.stdout.strip()); assert r.returncode == 0, r.stderr
print("DONE: Option B applied to MD + docx; audit 16-check re-pass; zip rebuilt")
