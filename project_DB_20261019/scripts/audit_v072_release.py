# -*- coding: utf-8 -*-
"""Self-contained release audit for the v0.7.2 current-version release set.

Checks only what exists inside release_v072/ (no dependency on the full project
workspace tree): title contract, equation/table/figure/reference counts in the
Markdown, Word OOXML structure, media hashes against the released figures, and
consistency of the archived audits. Pure standard library.
"""
import json, re, hashlib, zipfile
from pathlib import Path

D = Path(__file__).resolve().parents[1]
TITLE = "Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def ck(name, ok):
    checks.append({"check": name, "passed": bool(ok)})
    assert ok, name

md = (D / "manuscript" / "Full_manuscript_rq2_rq3_complete_v072.md").read_text(encoding="utf-8")

# 1. Title contract
ck("Markdown first line equals the Option B title", md.splitlines()[0] == "# " + TITLE)
ck("No response-numbered subsection headings remain", not any(re.search(r"RQ\d", h) for h in re.findall(r"^### (.*)", md, re.M)))

# 2. Equations: 27 display blocks, tags 1..27, balanced delimiters
eqs = re.findall(r"\$\$(.*?)\$\$", md, re.S)
ck("All 27 display equations present with tags 1..27",
   len(eqs) == 27 and list(map(int, re.findall(r"\\tag\{(\d+)\}", md))) == list(range(1, 28)))
ck("Mathematical delimiters balanced (54 $$ lines, even $ counts)",
   sum(l == "$$" for l in md.splitlines()) == 54 and all(l.count("$") % 2 == 0 for l in md.splitlines()))

# 3. Tables and subsections
tables = md.count("\n|")  # table rows begin with |
sep_rows = [l for l in md.splitlines() if re.match(r"^\s*\|[\s:|-]+\|\s*$", l)]
ck("11 markdown tables present (11 separator rows)", len(sep_rows) == 11)
subs = re.findall(r"^### (.*)", md, re.M)
ck("19 subsections present", len(subs) == 19)

# 4. References: 59 full entries
refs = md.split("## References\n\n")[1].split("\n\n## Appendix")[0].strip().splitlines()
ck("59 references retained in order", len(refs) == 59 and all(re.match(r"^\d+\.\s+\S", r) for r in refs))

# 5. Word OOXML: 27 oMathPara, 6 blips, media hashes match released figures
wa = json.loads((D / "docs" / "WORD_AUDIT.json").read_text(encoding="utf-8"))
ck("Archived WORD_AUDIT verdict PASS", wa["verdict"] == "PASS")
ck("WORD_AUDIT source hash matches released Markdown", wa["source_sha256"] == sha(D / "manuscript" / "Full_manuscript_rq2_rq3_complete_v072.md"))
ck("WORD_AUDIT output hash matches released docx", wa["output_sha256"] == sha(D / "manuscript" / "Full_manuscript_rq2_rq3_complete_v072.docx"))
with zipfile.ZipFile(D / "manuscript" / "Full_manuscript_rq2_rq3_complete_v072.docx") as z:
    doc_xml = z.read("word/document.xml").decode("utf-8")
    omath = len(re.findall(r"<m:oMathPara(?:\s|>)", doc_xml))
    blips = len(re.findall(r"<a:blip(?:\s|/>)", doc_xml))
ck("Word XML contains 27 oMathPara and 6 embedded figures", omath == 27 and blips == 6)
with zipfile.ZipFile(D / "manuscript" / "Full_manuscript_rq2_rq3_complete_v072.docx") as z:
    ck("All 6 embedded media hashes match the released PNGs",
       all(hashlib.sha256(z.read(row["docx_media"])).hexdigest() == row["sha256"] == sha(D / "figures" / Path(row["source"]).name)
           for row in wa["images"]))

# 6. Figures and atlas present
pngs = sorted(p.name for p in (D / "figures").glob("fig*.png"))
ck("6 released figure PNGs present", len(pngs) == 6 and pngs == [f"fig0{i}.png" for i in range(1, 7)])
for ext in ("tiff", "svg", "pdf"):
    n = len(list((D / "figures").glob(f"fig0[1-6].{ext}")))
    ck(f"6 released figure {ext.upper()} files present", n == 6)
ck("Vector figure atlas present", (D / "figures" / "Figure_atlas_rq2_rq3_v072.pdf").exists())

# 7. Data sets present
ck("8 output gate/data files present", len(list((D / "data" / "outputs").glob("*"))) == 8)
ck("6 figure source-data CSVs present", len(list((D / "data" / "source_data").glob("*.csv"))) == 6)

# 8. Archived full-workspace audit reference
fa = json.loads((D / "docs" / "FINAL_AUDIT.json").read_text(encoding="utf-8"))
ck("Archived FINAL_AUDIT verdict PASS with all checks passing", fa["verdict"] == "PASS" and all(c["passed"] for c in fa["checks"]))

# 9. Numerical gate assertions from the released data (reproducibility of the data-to-conclusion chain)
rg = json.loads((D / "data" / "outputs" / "RQ2_RECOUPLED_GATE.json").read_text(encoding="utf-8"))
ck("RQ2 recoupled gate: verdict PASS with 8 gate + 60 matrix + 12 detuned rows and max residual < 1e-7 MW",
   rg["verdict"] == "PASS" and rg["gate_rows_count"] == 8 and rg["matrix_rows_count"] == 60
   and rg["detuned_rating_rows_count"] == 12 and rg["max_nodal_residual_mw"] < 1e-7)
og = json.loads((D / "data" / "outputs" / "OPF_EXPAND_V072_GATE.json").read_text(encoding="utf-8"))
ck("Migrated OPF gate: verdict PASS with 14 six-encoding rows, 24 load rows and 162 extra snapshots",
   og["verdict"] == "PASS" and len(og["rows_six"]) == 14 and len(og["rows_load"]) == 24
   and og["extra_cached_snapshots"] == 162)
import csv as _csv
with (D / "data" / "outputs" / "m2_cascade_robustness_v072.csv").open(newline="", encoding="utf-8") as fh:
    rows = list(_csv.reader(fh))
ck("Cascade robustness CSV carries header + 60 matrix rows", len(rows) == 61)
with (D / "data" / "outputs" / "detuned_rating_sensitivity_v072.csv").open(newline="", encoding="utf-8") as fh:
    drows = list(_csv.reader(fh))
ck("Detuned-rating sensitivity CSV carries header + 12 rows", len(drows) == 13)

# 10. Full script chain archived (model run -> simulation -> visualization -> QA)
chain = ["run_recoupled_rq2.py", "run_opf_expand_v072.py", "render_fig04_update.py",
         "finalize_bibliography.py", "update_manuscript.py", "test_rq2_recoupled.py",
         "audit_rq2_recoupled.py", "build_package.py", "export_word.py"]
ck("Full analysis/simulation/visualization script chain archived under scripts/",
   all((D / "scripts" / n).exists() for n in chain))
ck("Thermal model-run entry archived under code/examples (run_thermal_revision_v072.py)",
   (D / "code" / "examples" / "run_thermal_revision_v072.py").exists())
ck("Model package archived under code/src (cooling/grid/scenarios) with pyproject metadata",
   (D / "code" / "src" / "cooling" / "dynamics.py").exists()
   and (D / "code" / "src" / "grid" / "cascade.py").exists()
   and (D / "code" / "src" / "scenarios" / "fault_makeup_basin.py").exists()
   and (D / "code" / "pyproject.toml").exists())
ck("Figure QA system archived under figures/qa (panel-alignment/collision/text audits)",
   (D / "figures" / "qa" / "audit_panel_alignment.py").exists()
   and (D / "figures" / "qa" / "audit_figure_collisions.py").exists())
ck("OPF simulation caches archived under data/cache (pre-migration snapshot pools)",
   (D / "data" / "cache" / "opf_snapshot_cache_v072.json").exists()
   and (D / "data" / "cache" / "additional_dc_snapshots.json").exists())

print(f"RELEASE AUDIT: {len(checks)} checks PASS; Option B title confirmed; set is self-contained")
