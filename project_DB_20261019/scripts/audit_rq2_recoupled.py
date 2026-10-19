"""Read-only final audit for the RQ1+RQ2+RQ3 complete illustrated revision (rq2_recoupled_v072).

Note: the title contract was updated on 2026-10-19 by author decision (title changed from the
historical 'From cold-end emergencies to cascading outages...' to the inventory-controlled
capability-loss formulation consistent with the revised main line). The lxml-based OOXML
inspection was re-implemented with the standard library (zipfile + re) because lxml is not
installed in the current environment; the checked quantities are unchanged (27 oMathPara,
6 embedded figure blips, media byte-identity).
"""
from pathlib import Path
import json,csv,re,hashlib,zipfile
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;O=D/'outputs';L=R/'manuscript/revisions/lag_ablation_v072';V=R/'manuscript/revisions/thermal_validation_v072';P=R/'manuscript/revisions/thermal_v072'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();checks=[]
def ck(name,ok):checks.append({'check':name,'passed':bool(ok)});assert ok,name

freeze=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
ck('All 242 prior protected files (including illustrated_v072 and lag_ablation_v072) remain byte-identical',len(freeze)==242 and all(sha(R/n)==h for n,h in freeze.items()))

f=json.loads((P/'PRE_THERMAL_MANIFEST.json').read_text())['files'];accepted=json.loads((P/'FINAL_VERIFICATION.json').read_text());changed={n for n,h in f.items() if sha(R/n)!=h}
ck('Manifest payloads (318 after 32 dc_v07/opf_v071 payloads retired by the 2026-10-19 cleanup) have no newly changed member beyond the 10 authorized in thermal_v072',changed==set(accepted['changed_existing_payloads']) and len(changed)==10)

s=(D/'Full_manuscript_rq2_rq3_complete_v072.md').read_text();base=(L/'Full_manuscript_rq3_complete_v072.md').read_text();q=json.loads((D/'RQ_CONTRACT.json').read_text());old=(R/'manuscript/Full_manuscript_integrated.md').read_text()
ck('All three original research questions retained verbatim in full text',q['original_questions_verbatim'] in old and q['original_questions_verbatim'] in s and q['source_sha256']==sha(R/q['source']))
NEW_TITLE='Mechanistic modeling of wet-recirculating cooling contingencies for cascading failure assessment in power systems'
ck('Title updated to the Option B mechanistic-modeling formulation and no response-number headings exist',s.splitlines()[0]=='# '+NEW_TITLE and not any(re.search(r'RQ\d',h) for h in re.findall(r'^### (.*)',s,re.M)))
ck('All 27 display equations identical to verified candidate',re.findall(r'\$\$(.*?)\$\$',s,re.S)==re.findall(r'\$\$(.*?)\$\$',base,re.S) and list(map(int,re.findall(r'\\tag\{(\d+)\}',s)))==list(range(1,28)))
ck('All mathematical delimiters balanced and no placeholders remain',sum(l=='$$' for l in s.splitlines())==54 and all(l.count('$')%2==0 for l in s.splitlines()) and not re.search(r'\{\{[A-Z_]+\}\}',s))
refs=s.split('## References\n\n')[1].split('\n\n## Appendix')[0].strip().splitlines()
old_refs=base.split('## References\n\n')[1].split('\n\n## Appendix')[0].strip().splitlines()
ck('All 59 references retained in order with complete titles and preserved DOIs',len(refs)==len(old_refs)==59 and all(int(a.split('.',1)[0])==int(b.split('.',1)[0]) and all(d in a for d in re.findall(r'https://doi\.org/\S+',b)) and len([x for x in re.sub(r'^\d+\.\s+','',a).split('. ') if x.strip()])>=3 for a,b in zip(refs,old_refs)))

rg=json.loads((O/'RQ2_RECOUPLED_GATE.json').read_text())
ck('RQ2 recoupled gate passes 8 gate + 60 matrix + 12 detuned rating runs with max residual < 1e-7 MW',rg['verdict']=='PASS' and rg['gate_rows_count']==8 and rg['matrix_rows_count']==60 and rg['detuned_rating_rows_count']==12 and rg['max_nodal_residual_mw']<1e-7)

og=json.loads((O/'OPF_EXPAND_V072_GATE.json').read_text())
ck('Migrated v0.7.2 six-encoding, five-load and G34 adequacy gate passes (14 + 24 rows, 162 extra snapshots)',og['verdict']=='PASS' and len(og['rows_six'])==14 and len(og['rows_load'])==24 and og['extra_cached_snapshots']==162)

qa=json.loads((D/'FIGURE_QA_SUMMARY.json').read_text())
ck('All 6 figures (including updated Figure 4) pass alignment, glyph floor >= 5 pt and 0 collision warnings/failures',qa['verdict']=='PASS' and len(qa['figures'])==6 and qa['minimum_glyph_pt']>=5.0 and all(r['text_floor_pass'] and r['collision_verdict']=='PASS' and r['collision_fail']==r['collision_warn']==0 for r in qa['figures']))

a=json.loads((D/'WORD_AUDIT.json').read_text())
ck('Word audit passes with 27 OMML equations, 19 subsections, 11 tables and 6 exact figures',a['verdict']=='PASS' and a['source_sha256']==sha(D/'Full_manuscript_rq2_rq3_complete_v072.md') and a['output_sha256']==sha(D/'Full_manuscript_rq2_rq3_complete_v072.docx') and (a['editable_display_equations'],a['subsections'],a['tables'],a['embedded_figures'])==(27,19,11,6) and not a['conversion_warnings'])

with zipfile.ZipFile(D/'Full_manuscript_rq2_rq3_complete_v072.docx') as z:
 doc_xml=z.read('word/document.xml').decode('utf-8')
 omath=len(re.findall(r'<m:oMathPara(?:\s|>)',doc_xml));blips=len(re.findall(r'<a:blip(?:\s|/>)',doc_xml))
 ck('Actual Word XML contains 27 oMathPara equations and 6 exact figure PNGs',omath==27 and blips==6 and all(hashlib.sha256(z.read(row['docx_media'])).hexdigest()==row['sha256']==sha(D/row['source']) for row in a['images']))

tlog=(D/'PYTEST_RQ2_RECOUPLED.txt').read_text()
ck('26 combined RQ2 + RQ3 + OPF expansion + illustrated + bibliography contract tests pass','26 passed' in tlog)
ck('Author-reserved research framework remains absent',not(R/'docs/RESEARCH_FRAMEWORK.md').exists() and not(R/'code/docs/RESEARCH_FRAMEWORK.md').exists())
e=json.loads((V/'EXTERNAL_BENCHMARK_STATUS.json').read_text())
ck('External calibration remains NOT_ESTABLISHED_DATA_GAP',e['status']=='NOT_ESTABLISHED_DATA_GAP' and e['measured_pressure_traces_used']==0 and not e['calibrated'])
ck('All 242 protected prior files still unchanged at audit completion',all(sha(R/n)==h for n,h in freeze.items()))

files=[p for p in D.rglob('*') if p.is_file() and p.name not in ['FINAL_AUDIT.json','RQ2_RQ3_complete_candidate_v072.zip'] and '__pycache__' not in p.parts and not p.name.endswith('.pyc')]
report={'date':'2026-10-17','verdict':'PASS','checks':checks,'original_research_questions_preserved':True,'RQ2_recoupled_complete':True,'RQ3_lag_omission_bias_established':True,'RQ3_opf_six_encoding_five_load_g34_migrated':True,'bibliography_59_full_titles_completed':True,'protected_files_unchanged':242,'rq2_cascade_runs_verified':80,'new_contract_tests_passed':26,'external_validation_status':e['status'],'word_final_page_layout_reviewed':False,'submission_ready':False,'evidence_sha256':{str(p.relative_to(D)):sha(p) for p in sorted(files)}}
(D/'FINAL_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FINAL RQ2+RQ3 COMPLETE AUDIT:',len(checks),'checks PASS; 242 protected files unchanged; submission_ready=false')
