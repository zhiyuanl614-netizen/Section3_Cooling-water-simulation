"""Export the RQ1+RQ2+RQ3 complete illustrated manuscript with 27 OMML equations, 19 subsections, 10 tables and 6 verified figures."""
from pathlib import Path
import re,json,hashlib,subprocess,zipfile
import pypandoc
from lxml import etree
from docx import Document
from docx.shared import Mm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent
src=D/'Full_manuscript_rq2_rq3_complete_v072.md';out=D/'Full_manuscript_rq2_rq3_complete_v072.docx'
raw=src.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();scratch=D/'_export';scratch.mkdir(exist_ok=True)
ref=Document();sec=ref.sections[0];sec.page_width=Mm(210);sec.page_height=Mm(297);sec.left_margin=sec.right_margin=Mm(20);sec.top_margin=sec.bottom_margin=Mm(20)
normal=ref.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(11);normal.paragraph_format.line_spacing=1.08;normal.paragraph_format.space_after=Pt(5)
for name,size in [('Heading 1',16),('Heading 2',13),('Heading 3',11.5)]:
 s=ref.styles[name];s.font.name='Times New Roman';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0);s.paragraph_format.keep_with_next=True
p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run('v0.7.2 RQ1-RQ3 complete illustrated review candidate | ').font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
reference=scratch/'reference.docx';ref.save(reference)
cmd=[pypandoc.get_pandoc_path(),str(src),'--from=markdown-smart+tex_math_dollars','--to=docx','--standalone','--resource-path='+str(D),'--reference-doc='+str(reference),'--output='+str(out)]
r=subprocess.run(cmd,capture_output=True,text=True);(D/'WORD_CONVERSION_LOG.txt').write_text(r.stdout+r.stderr);assert r.returncode==0 and not r.stderr.strip(),r.stderr
doc=Document(out)
for p in doc.paragraphs:
 if p._p.findall('.//'+qn('m:oMathPara')):
  for run in p._p.findall('.//'+qn('m:r')):
   pr=run.find(qn('w:rPr'))
   if pr is None:pr=OxmlElement('w:rPr');run.append(pr)
   size=OxmlElement('w:sz');size.set(qn('w:val'),'18');pr.append(size)
 if p._p.findall('.//'+qn('w:drawing')):
  p.paragraph_format.keep_with_next=True;p.alignment=WD_ALIGN_PARAGRAPH.CENTER
 if re.match(r'^Figure [1-6]\. ',p.text):
  p.paragraph_format.keep_together=True;p.paragraph_format.space_after=Pt(8)
  for run in p.runs:run.font.size=Pt(9)
for table in doc.tables:
 table.style='Table Grid'
 for i,row in enumerate(table.rows):
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  if i==0:pr.append(OxmlElement('w:tblHeader'))
  for cell in row.cells:
   for p in cell.paragraphs:
    p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1
    for run in p.runs:run.font.size=Pt(8.5)
for shape in doc.inline_shapes:
 ratio=Mm(170)/shape.width;shape.height=round(shape.height*ratio);shape.width=Mm(170)
setting=OxmlElement('w:doNotAutoCompressPictures');doc.settings.element.append(setting)
doc.core_properties.title=src.read_text().splitlines()[0][2:];doc.core_properties.subject='Original research questions preserved; RQ2 recoupled + RQ3 lag-ablation completed; six verified figures; internal review candidate';doc.core_properties.author='';doc.save(out)
ns={'m':'http://schemas.openxmlformats.org/officeDocument/2006/math','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
expected=json.loads((D/'FIGURE_CAPTIONS.json').read_text());media=[]
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 root=etree.fromstring(z.read('word/document.xml'));eq=root.findall('.//m:oMathPara',ns);assert len(eq)==27
 relations={e.get('Id'):e for e in etree.fromstring(z.read('word/_rels/document.xml.rels'))}
 blips=root.findall('.//a:blip',ns);assert len(blips)==6
 for blip,item in zip(blips,expected):
  rel=relations[blip.get(qn('r:embed'))];assert rel.get('TargetMode')!='External';name='word/'+rel.get('Target');data=z.read(name);image=D/item['image'];assert sha(data)==sha(image.read_bytes())
  media.append(dict(figure=item['figure'],source=item['image'],docx_media=name,sha256=sha(data)))
assert len(doc.inline_shapes)==6
assert all(abs(shape.width-Mm(170))<Mm(.02) for shape in doc.inline_shapes)
heads=[p.text for p in doc.paragraphs if p.style.name=='Heading 3'];assert heads==re.findall(r'^### (.*)',src.read_text(),re.M) and len(heads)==19
assert len(doc.tables)==11
cap=[p for p in doc.paragraphs if re.match(r'^Figure [1-6]\. ',p.text)];assert len(cap)==6
assert src.read_bytes()==raw
(D/'WORD_AUDIT.json').write_text(json.dumps(dict(verdict='PASS',scope='source/OOXML/media-identity verification, not rendered page-layout proof',source_sha256=sha(raw),output_sha256=sha(out.read_bytes()),editable_display_equations=27,subsections=19,tables=11,embedded_figures=6,figure_width_mm=170,external_image_links=0,conversion_warnings=[],images=media,final_page_layout_reviewed=False),indent=2)+'\n')
reference.unlink();scratch.rmdir();print('WORD PASS:27 native equations /19 subsections /11 tables /6 exact images + captions; source unchanged')
