# -*- coding: utf-8 -*-
"""Update the manuscript title inside the existing rq2_recoupled_v072 docx
(zero third-party dependencies; zip + XML text replacement only).

Preserves every other entry byte-for-byte; only word/document.xml first
paragraph text and docProps/core.xml dc:title are changed.
Run from the rq2_recoupled_v072 directory.
"""
import zipfile, re, hashlib, shutil, sys
from pathlib import Path

D = Path(__file__).resolve().parent
DOCX = D / "Full_manuscript_rq2_rq3_complete_v072.docx"
MD = D / "Full_manuscript_rq2_rq3_complete_v072.md"

OLD_TITLE = "From cold-end emergencies to cascading outages: a multi-timescale mechanistic model of wet-recirculating cooling under fault contingencies"
NEW_TITLE = "Inventory-controlled capability loss in wet-recirculating cooling: a finite-storage model and response-conditioned DC grid consequences"

sha = lambda b: hashlib.sha256(b).hexdigest()

# --- 1. Read source and derive the new Word title from the MD heading ---
md_title = MD.read_text(encoding="utf-8").splitlines()[0]
assert md_title.startswith("# "), "MD first line is not a heading"
md_title = md_title[2:]
assert md_title == NEW_TITLE, f"MD title mismatch: {md_title!r} vs {NEW_TITLE!r}"

with zipfile.ZipFile(DOCX) as z:
    names = z.namelist()
    entries = {}
    for n in names:
        entries[n] = z.read(n)

doc_xml = entries["word/document.xml"].decode("utf-8")
core_xml = entries["docProps/core.xml"].decode("utf-8")

n_doc = doc_xml.count(OLD_TITLE)
n_core = core_xml.count(OLD_TITLE)
if n_doc == 0 and n_core == 0 and NEW_TITLE in doc_xml and NEW_TITLE in core_xml:
    print("INFO: title already updated; running verification only")
else:
    assert n_doc == 1, f"document.xml contains {n_doc} occurrences of OLD_TITLE (expected 1)"
    assert n_core == 1, f"core.xml contains {n_core} occurrences of OLD_TITLE (expected 1)"
    doc_xml = doc_xml.replace(OLD_TITLE, NEW_TITLE)
    core_xml = core_xml.replace(OLD_TITLE, NEW_TITLE)
    entries["word/document.xml"] = doc_xml.encode("utf-8")
    entries["docProps/core.xml"] = core_xml.encode("utf-8")

    # --- 2. Rebuild the docx, preserving order and compression of all entries ---
    tmp = D / "Full_manuscript_rq2_rq3_complete_v072.docx.tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zi = None
            with zipfile.ZipFile(DOCX) as z:  # preserve original per-entry metadata
                zi = z.getinfo(n)
            if zi is not None:
                zout.writestr(zi, entries[n])
            else:
                zout.writestr(n, entries[n])
    shutil.move(str(tmp), str(DOCX))

# --- 3. Verify the rebuilt docx ---
with zipfile.ZipFile(DOCX) as z:
    assert z.testzip() is None
    xml2 = z.read("word/document.xml").decode("utf-8")
    core2 = z.read("docProps/core.xml").decode("utf-8")
    first_par = re.search(r"<w:p\b.*?</w:p>", xml2, re.S).group(0)
    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", first_par, re.S)
    assert "".join(texts) == NEW_TITLE, texts
    assert "".join(texts).strip() == NEW_TITLE
    assert NEW_TITLE in core2 and OLD_TITLE not in core2
    assert OLD_TITLE not in xml2
    m_count = len(re.findall(r"<m:oMathPara(?:\s|>)", xml2))
    b_count = len(re.findall(r"<a:blip(?:\s|/>)", xml2))
    assert m_count == 27, f"oMathPara count {m_count}"
    assert b_count == 6, f"blip count {b_count}"

new_md_sha = sha(MD.read_bytes())
new_docx_sha = sha(DOCX.read_bytes())
print(f"WORD TITLE UPDATE OK: {len(entries)} entries preserved; 27 OMML / 6 images intact")
print(f"md_sha256={new_md_sha}")
print(f"docx_sha256={new_docx_sha}")
print(f"title={NEW_TITLE}")
