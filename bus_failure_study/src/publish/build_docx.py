"""Build a submission-ready DOCX from docs/manuscript_EN.md.

Equations are rendered by matplotlib mathtext to high-resolution PNGs and
embedded as images (no LaTeX / pandoc available in this environment).
Figures are rasterised from their SVG source into a build directory so that
results/paper/figures keeps SVG as its only format.
"""
import base64, io, os, re, shutil, sys
from pathlib import Path

try:
    import cairosvg  # noqa: F401  (only used when the PNG cache misses; cairo may be absent on Windows)
except Exception:
    cairosvg = None
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "manuscript_EN.md"
FIGDIR = ROOT / "results" / "paper" / "figures"
BUILD = ROOT / "build" / "img"
OUT = ROOT / "results" / "paper" / "manuscript.docx"

BUILD.mkdir(parents=True, exist_ok=True)
ACCENT = RGBColor(0x0B, 0x4F, 0x8A)

md = SRC.read_text(encoding="utf-8")

# ----------------------------------------------------------------- equation --
_FIG = plt.figure(figsize=(8, 1.2))


def prep(tex: str) -> str:
    t = re.sub(r"\\tag\{[^}]*\}", "", tex)
    t = re.sub(r"\\text\{([^{}]*)\}", r"\\mathrm{\1}", t)
    t = re.sub(r"\\operatorname\{([^{}]*)\}", r"\\mathrm{\1}", t)
    t = re.sub(r"\\mathbb\{1\}", r"\\mathrm{1}", t)
    t = re.sub(r"\\mathbb\{R\}", r"\\mathrm{R}", t)
    t = t.replace("\\vee", "\\cup").replace("\\longrightarrow", "\\rightarrow")
    t = t.replace("\\begin{cases}", "").replace("\\end{cases}", "")
    t = t.replace("\\begin{aligned}", "").replace("\\end{aligned}", "")
    return t.strip()


def tex_png(tex: str, display: bool, dpi: int = 320):
    """Render LaTeX to a tightly-cropped transparent PNG. Returns bytes."""
    t = prep(tex)
    _FIG.clear()
    try:
        _FIG.text(0.02, 0.5, f"${t}$", fontsize=17 if display else 13)
        _FIG.canvas.draw()
        buf = io.BytesIO()
        _FIG.savefig(buf, dpi=dpi, transparent=True, format="png",
                     bbox_inches="tight", pad_inches=0.02)
        return buf.getvalue(), None
    except Exception as e:                                   # pragma: no cover
        return None, str(e)


def fig_png(name: str):
    src = FIGDIR / name
    dst = BUILD / (src.stem + ".png")
    if not dst.exists():
        if cairosvg is None:
            raise RuntimeError(
                f"PNG cache miss for {src.stem} and cairosvg unavailable; "
                f"run the Edge headless SVG->PNG batch conversion into {BUILD} first.")
        cairosvg.svg2png(url=str(src), write_to=str(dst), output_width=3600)
    return dst


def strip_inline(s: str) -> str:
    """Remove markdown emphasis markers; keep numbers/symbols as text."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s, flags=re.S)
    s = re.sub(r"\*(.+?)\*", r"\1", s, flags=re.S)
    s = re.sub(r"`(.+?)`", r"\1", s)
    return s


# ---------------------------------------------------------------- document ---
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(10.5)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15

for sec in doc.sections:
    sec.top_margin = sec.bottom_margin = Inches(0.9)
    sec.left_margin = sec.right_margin = Inches(0.9)


def add_run(par, text):
    """Add text, converting ^n^ citations to superscripts."""
    parts = re.split(r"(\^\d[\d,\u2013-]*\^)", text)
    for p in parts:
        if not p:
            continue
        m = re.fullmatch(r"\^(\d[\d,\u2013-]*)\^", p)
        if m:
            r = par.add_run(m.group(1))
            r.font.superscript = True
            r.font.size = Pt(8.5)
        else:
            par.add_run(p)


def add_rich(par, text):
    """Handle **bold**, *italic*, `code` and $math$ within a text fragment."""
    tokens = re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+`|\$[^$\n]+?\$)", text, flags=re.S)
    for tk in tokens:
        if not tk:
            continue
        if tk.startswith("**") and tk.endswith("**") and len(tk) > 4:
            par.add_run(strip_inline(tk)).bold = True
        elif tk.startswith("*") and tk.endswith("*") and len(tk) > 2:
            par.add_run(strip_inline(tk)).italic = True
        elif tk.startswith("`") and tk.endswith("`") and len(tk) > 2:
            r = par.add_run(tk[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9.5)
        elif tk.startswith("$") and tk.endswith("$") and len(tk) > 2:
            data, err = tex_png(tk[1:-1], display=False)
            if data:
                par.add_run().add_picture(io.BytesIO(data), height=Pt(13))
            else:
                par.add_run(tk)
        else:
            add_run(par, tk)


def parse_row(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


lines = md.split("\n")
i = 0
eq_counter = 0

while i < len(lines):
    line = lines[i]

    # display equation -------------------------------------------------------
    if line.strip().startswith("$$"):
        single = line.strip()
        if len(single) > 4 and single.endswith("$$"):
            tex = single[2:-2].strip()
        else:
            buf = [line]
            while True:
                i += 1
                if i >= len(lines):
                    break
                buf.append(lines[i])
                if lines[i].strip().endswith("$$"):
                    break
            tex = re.sub(r"^\s*\$\$|\$\$\s*$", "", "\n".join(buf)).strip()
        m = re.search(r"\\tag\{([^}]*)\}", tex)
        num = f"({m.group(1)})" if m else ""
        data, err = tex_png(tex, display=True)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        if data:
            if num:
                p.add_run("\t\t")
            p.add_run().add_picture(io.BytesIO(data), width=Inches(5.6))
            if num:
                r = p.add_run("\t" + num)
                r.font.size = Pt(10)
        else:
            p.add_run(tex + "  " + num)
        i += 1
        continue

    # heading ----------------------------------------------------------------
    m = re.match(r"^(#{1,4})\s+(.*)$", line)
    if m:
        lvl, title = len(m.group(1)), m.group(2).strip()
        h = doc.add_heading(level=min(lvl, 4))
        add_rich(h, title)
        for r in h.runs:
            r.font.color.rgb = ACCENT if lvl >= 3 else RGBColor(0, 0, 0)
            r.font.name = "Times New Roman"
        i += 1
        continue

    # figure -----------------------------------------------------------------
    m = re.match(r"!\[Figure ([^\]]*)\]\(([^)]+)\)", line.strip())
    if m:
        name = os.path.basename(m.group(2))
        try:
            png = fig_png(name)
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(png), width=Inches(6.4))
        except Exception as e:
            doc.add_paragraph(f"[figure {name}: {e}]")
        i += 1
        continue

    # table ------------------------------------------------------------------
    if line.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(parse_row(lines[i]))
            i += 1
        header, body = rows[0], rows[2:]
        t = doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for k, c in enumerate(header):
            cell = t.rows[0].cells[k]
            cell.text = ""
            par = cell.paragraphs[0]
            add_rich(par, strip_inline(c))
            for r in par.runs:
                r.bold = True
                r.font.size = Pt(8.5)
        for row in body:
            cells = t.add_row().cells
            for k, c in enumerate(row[:len(header)]):
                cells[k].text = ""
                par = cells[k].paragraphs[0]
                add_rich(par, strip_inline(c))
                for r in par.runs:
                    r.font.size = Pt(8.5)
        doc.add_paragraph()
        continue

    # blockquote -------------------------------------------------------------
    if line.strip().startswith(">"):
        buf = []
        while i < len(lines) and lines[i].strip().startswith(">"):
            buf.append(lines[i].strip().lstrip(">").strip())
            i += 1
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.space_before = Pt(4)
        for r in p.runs:
            r.font.size = Pt(9)
        add_rich(p, " ".join(buf))
        continue

    # horizontal rule --------------------------------------------------------
    if line.strip() in ("---", "***", "___"):
        i += 1
        continue

    # blank ------------------------------------------------------------------
    if not line.strip():
        i += 1
        continue

    # paragraph --------------------------------------------------------------
    buf = [line]
    i += 1
    while i < len(lines) and lines[i].strip() and not re.match(
        r"^(#{1,4}\s|\$\$|!\[|\||>|$)", lines[i]
    ):
        buf.append(lines[i])
        i += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_rich(p, " ".join(buf))

doc.save(OUT)
print(f"wrote {OUT}")
print(f"paragraphs={len(doc.paragraphs)} tables={len(doc.tables)}")
