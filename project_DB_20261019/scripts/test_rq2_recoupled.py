"""Read-only regression and contract tests for the RQ2 recoupled + RQ3 complete illustrated revision."""
from pathlib import Path
import json,csv,hashlib,re
import pytest
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;O=D/'outputs';L=R/'manuscript/revisions/lag_ablation_v072'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def test_all242_protected_prior_files_unchanged():
 f=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
 assert len(f)==242 and all(sha(R/n)==h for n,h in f.items())

def test_original_research_questions_and_title_retained_verbatim():
 rq=json.loads((D/'RQ_CONTRACT.json').read_text())['original_questions_verbatim']
 s=(D/'Full_manuscript_rq2_rq3_complete_v072.md').read_text()
 old=(R/'manuscript/Full_manuscript_integrated.md').read_text()
 assert rq in old and rq in s
 assert s.splitlines()[0]==old.splitlines()[0]
 assert not any(re.search(r'RQ\d',h) for h in re.findall(r'^### (.*)',s,re.M))

def test_recoupled_rq2_gate_and_non_monotonic_h_severity():
 g=json.loads((O/'RQ2_RECOUPLED_GATE.json').read_text())
 assert g['verdict']=='PASS' and g['gate_rows_count']==8 and g['matrix_rows_count']==60 and g['detuned_rating_rows_count']==12
 assert g['max_nodal_residual_mw']<1e-7
 gate={(r['schedule'],r['policy']):r for r in g['gate_rows']}
 assert gate[('S3a_dual_derate','S')]['shed_load_mw']==pytest.approx(44.55601280707651)
 assert gate[('S3a_dual_derate','H')]['shed_load_mw']==pytest.approx(0.0)
 assert gate[('G1_single_33_trip','H')]['shed_load_mw']==pytest.approx(1753.2)
 assert gate[('G2_dual_collapse','H')]['shed_load_mw']==pytest.approx(1087.23)
 det={(r['policy'],r['rule'],float(r['rate_factor'])):r for r in g['detuned_rating_rows']}
 assert det[('S','simultaneous',1.0)]['shed_load_mw']==pytest.approx(788.3369610271966)
 assert det[('H','simultaneous',1.0)]['shed_load_mw']==pytest.approx(1909.5369610271964)
 assert det[('H','simultaneous',0.9)]['shed_load_mw']==pytest.approx(3154.94691718145)
 assert det[('H','simultaneous',0.9)]['n_lines_removed']==14 and det[('H','simultaneous',0.9)]['n_stages']==5
 assert det[('H','sequential',1.0)]['shed_load_mw']==pytest.approx(1312.0669610271962)

def test_thermal_step_invariance_of_recoupled_inputs():
 g=json.loads((O/'RQ2_RECOUPLED_GATE.json').read_text())
 ref=g['reference_thermal_inputs_v072'];fine=g['fine_thermal_inputs_v072'];ex=g['exact1s_thermal_inputs_v072']
 assert ref['first_trip_h']==pytest.approx(4.273888888888889)
 assert ref['second_trip_h']==pytest.approx(5.0472222222222225)
 assert abs(ref['surviving_capability_mw']-fine['surviving_capability_mw'])<0.01
 assert abs(ref['surviving_capability_mw']-ex['surviving_capability_mw'])<0.01

def test_figure4_updated_and_all6_figures_pass_qa():
 qa=json.loads((D/'FIGURE_QA_SUMMARY.json').read_text())
 assert qa['verdict']=='PASS' and len(qa['figures'])==6 and qa['minimum_glyph_pt']>=5.0
 for r in qa['figures']:
  assert r['text_floor_pass'] and r['collision_verdict']=='PASS' and r['collision_fail']==r['collision_warn']==0
  assert r['alignment']==('PASS' if r['figure']<6 else 'NOT APPLICABLE')
 rows=list(csv.DictReader((D/'source_data/fig04_all68_recoupled_electrical_probes.csv').open()))
 assert len(rows)==68

def test_word_and_markdown_structure_and_27_equations():
 s=(D/'Full_manuscript_rq2_rq3_complete_v072.md').read_text()
 base=(L/'Full_manuscript_rq3_complete_v072.md').read_text()
 assert re.findall(r'\$\$(.*?)\$\$',s,re.S)==re.findall(r'\$\$(.*?)\$\$',base,re.S)
 w=json.loads((D/'WORD_AUDIT.json').read_text())
 assert w['verdict']=='PASS' and (w['editable_display_equations'],w['subsections'],w['tables'],w['embedded_figures'])==(27,19,11,6)
 # Verify all 5 Highlights are <= 85 characters including spaces and numbering
 hl=s.split('## Highlights\n\n')[1].split('\n\n## Abstract')[0].strip().splitlines()
 assert len(hl)==5 and all(len(x)<=85 for x in hl)
 # Verify Abstract is <= 300 words
 abs_txt=s.split('## Abstract\n\n')[1].split('\n\n**Keywords:**')[0].strip()
 assert len(abs_txt.split())<=300

def test_migrated_v072_opf_six_encodings_five_loads_and_g34():
 g=json.loads((O/'OPF_EXPAND_V072_GATE.json').read_text())
 assert g['verdict']=='PASS' and g['extra_cached_snapshots']==162 and g['total_pool_snapshots']==1124
 assert len(g['rows_six'])==14 and len(g['rows_load'])==24
 by_six={(r['unit'],r['benchmark']):r for r in g['rows_six']}
 assert by_six[('G33','mechanistic_ride_down')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(2170.2546148738283)
 assert by_six[('G34','mechanistic_ride_down')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(1665.5484417159268)
 assert by_six[('G34','instant_trip')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(3560.317316434513)
 assert by_six[('G34','delayed_instant_trip')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(1314.1032693818456)
 by_load={(r['unit'],float(r['load_scale']),r['encoding']):r for r in g['rows_load']}
 assert by_load[('G33',1.0,'mechanistic_ride_down')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(361.0415262786182)
 assert by_load[('G33',1.2,'mechanistic_ride_down')]['incremental_unserved_energy_0_8h_mwh']==pytest.approx(2296.9822595163975)

def test_all59_references_have_complete_titles_and_preserved_dois():
 s=(D/'Full_manuscript_rq2_rq3_complete_v072.md').read_text()
 base=(L/'Full_manuscript_rq3_complete_v072.md').read_text()
 refs=s.split('## References\n\n')[1].split('\n\n## Appendix')[0].strip().splitlines()
 old_refs=base.split('## References\n\n')[1].split('\n\n## Appendix')[0].strip().splitlines()
 assert len(refs)==len(old_refs)==59
 for line,old_line in zip(refs,old_refs):
  idx=int(line.split('.',1)[0])
  old_idx=int(old_line.split('.',1)[0])
  assert idx==old_idx
  # Every DOI in old_line must remain verbatim in line
  for doi in re.findall(r'https://doi\.org/\S+',old_line):
   assert doi in line
  # Every reference line must have at least 3 period-separated bibliographic segments (Author. Title. Venue/Publisher)
  segments=[x.strip() for x in re.sub(r'^\d+\.\s+','',line).split('. ') if x.strip()]
  assert len(segments)>=3,f"Ref {idx} missing title segment: {line}"
