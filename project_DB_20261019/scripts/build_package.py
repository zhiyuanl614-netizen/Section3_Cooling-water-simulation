"""Package the RQ1+RQ2+RQ3 complete illustrated revision after its read-only audit passes."""
from pathlib import Path
import json,zipfile,hashlib
D=Path(__file__).parent;out=D/'RQ2_RQ3_complete_candidate_v072.zip'
a=json.loads((D/'FINAL_AUDIT.json').read_text())
assert a['verdict']=='PASS' and a['original_research_questions_preserved'] and a['RQ2_recoupled_complete'] and a['RQ3_lag_omission_bias_established']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(D/n)==h for n,h in a['evidence_sha256'].items())
files=[p for p in D.rglob('*') if p.is_file() and p!=out and '__pycache__' not in p.parts and not p.name.endswith('.pyc') and '_export' not in p.parts]
arc=lambda p:'rq2_recoupled_v072/'+p.relative_to(D).as_posix()
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,arc(p))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for p in files:assert hashlib.sha256(z.read(arc(p))).hexdigest()==sha(p)
print('PACKAGE PASS:',len(files),'members;',out.stat().st_size,'bytes; SHA256',sha(out))
