# -*- coding: utf-8 -*-
"""Check sync status of Option B title switch in rq2_recoupled_v072."""
import zipfile, re, json
from pathlib import Path
D = Path(__file__).resolve().parent
OLD = "Inventory-controlled capability loss in wet-recirculating cooling: a finite-storage model and response-conditioned DC grid consequences"
NEW = "Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems"

with zipfile.ZipFile(D / "Full_manuscript_rq2_rq3_complete_v072.docx") as z:
    dx = z.read("word/document.xml").decode("utf-8")
    cx = z.read("docProps/core.xml").decode("utf-8")
    first = re.search(r"<w:p\b.*?</w:p>", dx, re.S).group(0)
    t = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", first, re.S))
    print("DOCX_TITLE_OK:", t == NEW)
    print("DOCX_HAS_OLD:", OLD in dx, "| oMath:", len(re.findall(r"<m:oMathPara(?:\s|>)", dx)), "| blips:", len(re.findall(r"<a:blip(?:\s|/>)", dx)))

wa = json.loads((D / "WORD_AUDIT.json").read_text(encoding="utf-8"))
print("WORD_AUDIT.title:", wa.get("title", "(none)"))
print("WORD_AUDIT.source_sha:", wa["source_sha256"][:16])
print("WORD_AUDIT.output_sha:", wa["output_sha256"][:16])

ap = (D / "audit_rq2_recoupled.py").read_text(encoding="utf-8")
print("AUDIT_CONSTANT_IS_B:", ("NEW_TITLE='" + NEW + "'") in ap)

fa = json.loads((D / "FINAL_AUDIT.json").read_text(encoding="utf-8"))
print("FINAL_AUDIT.date:", fa.get("date"), "| verdict:", fa.get("verdict"))
print("FINAL_AUDIT.md_sha:", fa["evidence_sha256"]["Full_manuscript_rq2_rq3_complete_v072.md"][:16])
print("FINAL_AUDIT.docx_sha:", fa["evidence_sha256"]["Full_manuscript_rq2_rq3_complete_v072.docx"][:16])
