"""Copy verified figures 1-3, 5-6 and re-render Figure 4 with the recoupled 68-row v0.7.2 RQ2 cascade matrix."""
from pathlib import Path
import sys,json,csv,hashlib,subprocess,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;O=D/'outputs';I=R/'manuscript/revisions/illustrated_v072'
F=D/'figures';S=D/'source_data';F.mkdir(exist_ok=True);S.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'figures/qa'))
from audit_panel_alignment import require_matplotlib_panel_alignment
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BLUE='#176B9B';GREY='#555D66';ORANGE='#C45631';TEAL='#16867D';PALE='#F1F5F7';BLACK='#202830'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':7.6,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':7.6,'ytick.labelsize':7.6,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'lines.linewidth':1.25,'legend.fontsize':7.6,'legend.frameon':False,'svg.fonttype':'none','pdf.fonttype':42,'mathtext.fontset':'dejavusans','savefig.facecolor':'white'})

def tag(ax,letter,title):
 ax.text(-.19,1.065,letter,transform=ax.transAxes,fontsize=9,fontweight='bold',va='bottom')
 ax.set_title(title,loc='left',pad=12,fontweight='normal')

def main():
 frozen=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
 assert len(frozen)==242 and all(sha(R/n)==h for n,h in frozen.items())

 for n in [1,2,3,5,6]:
  for ext in ['.pdf','.svg','.png','.tiff','.alignment.json','.text-audit.json','.collision-audit.json']:
   shutil.copy2(I/'figures'/f'fig{n:02d}{ext}',F/f'fig{n:02d}{ext}')
 for p in (I/'source_data').glob('*.csv'):
  if not p.name.startswith('fig04'):shutil.copy2(p,S/p.name)

 gate=list(csv.DictReader((O/'dc_minimal_validation_v072.csv').open()))
 m2=[r for r in csv.DictReader((O/'m2_cascade_robustness_v072.csv').open()) if r['probe']=='M2_rule_robustness']
 det=list(csv.DictReader((O/'detuned_rating_sensitivity_v072.csv').open()))
 all_rows=gate+m2+det
 fig4_csv=S/'fig04_all68_recoupled_electrical_probes.csv'
 with fig4_csv.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)

 fig=plt.figure(figsize=(170/25.4,104/25.4))
 a=fig.add_axes([.115,.22,.315,.58]);b=fig.add_axes([.63,.22,.345,.58])
 states_a=['S3a_dual_derate','G1_single_33_trip','M6_detuned_at_first_trip','G2_dual_collapse']
 xlabels_a=['S3a\nderate','G33\nzero','Detuned\n1st trip','Both\nzero']
 for pol,col,marker,ls in [('S',BLUE,'o','-'),('H',ORANGE,'s','--')]:
  vals=[]
  for st in states_a:
   if st=='M6_detuned_at_first_trip':
    r=next(x for x in det if x['policy']==pol and x['rule']=='simultaneous' and float(x['rate_factor'])==1.0)
   else:
    r=next(x for x in gate if x['schedule']==st and x['policy']==pol)
   vals.append(float(r['shed_load_mw']))
  a.plot(range(4),vals,color=col,marker=marker,ms=4,ls=ls,label=pol)
 a.set_xlim(-.22,3.22);a.set_ylim(-60,2100);a.set_xticks(range(4),xlabels_a);a.set_yticks([0,500,1000,1500,2000])
 a.set_ylabel('Terminal shed load (MW)');tag(a,'a','Nominal simultaneous removal')
 fig.legend(*a.get_legend_handles_labels(),loc='upper left',bbox_to_anchor=(.11,.985),ncol=2,title='Balancing policy',handlelength=2.3)

 b.set_xlim(-.5,5.5);b.set_ylim(7.5,-.5)
 b.set_xticks(range(6),['Sim.\n1.0','Sim.\n0.9','Sim.\n1.1','Seq.\n1.0','Seq.\n0.9','Seq.\n1.1'])
 b.set_yticks(range(8),['S3a / S','S3a / H','G33 / S','G33 / H','Det.1 / S','Det.1 / H','Both / S','Both / H'])
 b.tick_params(length=0,pad=5);tag(b,'b','Removed branches [rounds]')
 for sp in b.spines.values():sp.set_visible(False)
 row_specs=[('S3a_dual_derate','S'),('S3a_dual_derate','H'),('G1_single_33_trip','S'),('G1_single_33_trip','H'),
            ('M6_detuned_at_first_trip','S'),('M6_detuned_at_first_trip','H'),('G2_dual_collapse','S'),('G2_dual_collapse','H')]
 for y,(sched,pol) in enumerate(row_specs):
  for x,(rule,factor) in enumerate([(r,f) for r in ['simultaneous','sequential'] for f in [1.0,0.9,1.1]]):
   pool=det if sched=='M6_detuned_at_first_trip' else m2
   row=next(r for r in pool if r['schedule']==sched and r['policy']==pol and r['rule']==rule and float(r['rate_factor'])==factor)
   b.text(x,y,f"{row['n_lines_removed']} [{row['n_stages']}]",ha='center',va='center',fontsize=7.6,color=BLACK)
 for y0 in [0,4]:
  b.axhspan(y0-.5,y0+1.5,color=PALE,zorder=-1)
 b.set_xlabel('Removal rule / rating multiplier',labelpad=7)
 fig.text(.535,.022,'v0.7.2 recoupled state snapshots; independent static evaluations, not a continuous cascade.',ha='center',fontsize=7.6)

 base=F/'fig04'
 fig.canvas.draw()
 require_matplotlib_panel_alignment(fig,axes=[a,b],panel_ids=['a','b'],row_groups=[['a','b']],json_out=str(base)+'.alignment.json',tolerance_pt=1.5,strict=True)
 for ext in ['pdf','svg','png','tiff']:
  kw={'dpi':600} if ext in ['png','tiff'] else {}
  if ext=='tiff':kw['pil_kwargs']={'compression':'tiff_lzw'}
  fig.savefig(str(base)+'.'+ext,**kw)
 plt.close(fig)

 for script,args,out in [('audit_pdf_text.py',['--min-pt','5','--json'],str(base)+'.text-audit.json'),('audit_figure_collisions.py',['--json'],str(base)+'.collision-audit.json')]:
  res=subprocess.run([sys.executable,str(R/'figures/qa'/script),str(base)+'.pdf',*args],text=True,capture_output=True)
  assert res.returncode==0,res.stdout+res.stderr
  Path(out).write_text(res.stdout)

 old_man=json.loads((I/'FIGURE_SOURCE_MANIFEST.json').read_text())
 new_figs=[]
 for item in old_man['figures']:
  if item['figure']==4:
   new_figs.append({
    'figure':4,
    'source_sha256':{str((O/n).relative_to(R)):sha(O/n) for n in ['RQ2_RECOUPLED_GATE.json','dc_minimal_validation_v072.csv','m2_cascade_robustness_v072.csv','detuned_rating_sensitivity_v072.csv']},
    'selection':'a: 8 nominal simultaneous states across S3a dual derate, G33 zero, detuned first trip (t=4.273889 h) and both zero (2 healthy controls in source CSV). b: all 48 non-healthy rule/rating combinations across those 4 states; 68-row source CSV retains healthy controls.',
    'source_data':'source_data/fig04_all68_recoupled_electrical_probes.csv'
   })
  else:new_figs.append(item)
 (D/'FIGURE_SOURCE_MANIFEST.json').write_text(json.dumps({'backend':'python-matplotlib','dpi':600,'width_mm':170,'figures':new_figs},ensure_ascii=False,indent=2)+'\n')

 import pymupdf
 out=pymupdf.open()
 for n in range(1,7):
  with pymupdf.open(F/f'fig{n:02d}.pdf') as src:out.insert_pdf(src)
 out.save(D/'Figure_atlas_rq2_rq3_v072.pdf');out.close()

 rows=[]
 for n in range(1,7):
  bpath=F/f'fig{n:02d}'
  j={s:json.loads(Path(str(bpath)+s).read_text()) for s in ['.alignment.json','.text-audit.json','.collision-audit.json']}
  rows.append({'figure':n,'alignment':j['.alignment.json']['verdict'],'minimum_glyph_pt':j['.text-audit.json']['minimum_found_pt'],'text_floor_pass':j['.text-audit.json']['below_minimum_count']==0,'collision_verdict':j['.collision-audit.json']['verdict'],'collision_fail':j['.collision-audit.json']['summary']['fail'],'collision_warn':j['.collision-audit.json']['summary']['warn']})
 (D/'FIGURE_QA_SUMMARY.json').write_text(json.dumps({'verdict':'PASS','backend':'python-matplotlib','figures':rows,'minimum_glyph_pt':min(r['minimum_glyph_pt'] for r in rows)},indent=2)+'\n')

 assert all(sha(R/n)==h for n,h in frozen.items())
 print('Updated Figure 4 rendered and audited: alignment PASS, text PASS, collision PASS')
if __name__=='__main__':main()
