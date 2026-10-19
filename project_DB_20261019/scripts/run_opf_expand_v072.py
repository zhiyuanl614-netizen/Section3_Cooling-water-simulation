"""Migrate six-encoding, five-load (1.00-1.20) and G34 adequacy comparisons to v0.7.2 without modifying frozen files."""
from pathlib import Path
import sys,json,csv,hashlib,io,contextlib
from importlib.metadata import version
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;O=D/'outputs'
sys.path.insert(0,str(R/'code/src'))
from grid.opf import evaluate_grid_impact
from grid.coupling import event_aware_time_samples,integrate_time_series
from cooling.benchmarks import build_benchmark_trajectories,BenchmarkTrajectory
from scenarios import load_unit_config,load_unit_params
from scenarios.fault_makeup_basin import build_unit_model
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 frozen=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
 assert len(frozen)==242 and all(sha(R/n)==h for n,h in frozen.items())
 sig=sha(R/'code/src/grid/opf.py')+'/'+version('pandapower')
 c1=json.loads((R/'manuscript/revisions/thermal_v072/outputs/opf_snapshot_cache_v072.json').read_text())
 c2=json.loads((R/'manuscript/revisions/thermal_validation_v072/outputs/additional_dc_snapshots.json').read_text())
 assert c1['signature']==c2['signature']==sig
 pool={**c1['snapshots'],**c2['snapshots']}
 extra_file=O/'rq3_expansion_dc_snapshots_v072.json'
 extra=json.loads(extra_file.read_text())['snapshots'] if extra_file.exists() else {}
 pool.update(extra)
 new_solves=0;warnings=io.StringIO()

 def snapshot(caps,load):
  nonlocal new_solves
  key=json.dumps([load,sorted(caps.items())])
  if key not in pool:
   with contextlib.redirect_stderr(warnings):res=evaluate_grid_impact(caps,load_scale=load)
   assert res.converged and res.n_branches_checked==46 and res.n_overloaded_branches==0 and res.max_nodal_residual_mw<1e-5
   d=vars(res);pool[key]=d;extra[key]=d;new_solves+=1
  return pool[key]

 models={uid:build_unit_model(load_unit_config()[uid],params=load_unit_params('baseline')) for uid in ('G33','G34')}
 by_unit={uid:{t.name:t for t in build_benchmark_trajectories(m)} for uid,m in models.items()}
 rows_load=[];rows_six=[];traces={}

 def eval_path(uid,name,traj,load,step=0.25):
  samples=event_aware_time_samples(traj,t_end_h=8.0,macro_step_h=step)
  base=snapshot({},load)['shed_load_mw'];states=[]
  for t,side in samples:
   cap=traj.p_avail_at(t,side=side)
   res=snapshot({uid:cap},load)
   states.append({'t_h':t,'side':side,'capability_mw':cap,'shed_load_mw':res['shed_load_mw'],'incremental_shed_mw':max(0.,res['shed_load_mw']-base)})
  times=[s['t_h'] for s in states];vals=[s['incremental_shed_mw'] for s in states]
  inc=integrate_time_series(times,vals)
  tot=integrate_time_series(times,[s['shed_load_mw'] for s in states])
  assert abs(tot-(base*8.0+inc))<1e-5
  if name in ('delayed_instant_trip@t_mech','fixed_holdup_trip','instant_trip','instant_trip@0'):
   t_tr=0.0 if 'instant_trip@0' in name or name=='instant_trip' else traj.trip_h
   post=max(0.,snapshot({uid:0.},load)['shed_load_mw']-base)
   assert abs(inc-post*(8.0-t_tr))<1e-6
  traces[f'{uid}/{load}/{name}/{step}']=states
  return {'unit':uid,'load_scale':load,'encoding':name,'macro_step_h':step,'baseline_shed_mw':base,
          'incremental_unserved_energy_0_8h_mwh':inc,'unserved_energy_0_8h_mwh':tot,
          'n_snapshot_samples':len(states),'trip_h':traj.trip_h,'trip_mechanism':traj.trip_mechanism,
          'pretrip_capability_mw':traj.p_trip_left_mw,'delivered_energy_0_8h_mwh':traj.delivered_energy_mwh(8.0)}

 for uid,trajs in by_unit.items():
  mech=trajs['mechanistic_ride_down'];trip=mech.trip_h
  delayed=BenchmarkTrajectory('delayed_instant_trip','Flat capacity until same trip',uid,models[uid].p_rated_mw,t_h=[0.,trip],p_avail_mw=[models[uid].p_rated_mw]*2,trip_h=trip,p_trip_left_mw=models[uid].p_rated_mw,trip_mechanism='aligned_control')
  enc4={'instant_trip@0':trajs['instant_trip'],'delayed_instant_trip@t_mech':delayed,'mechanistic_ride_down':mech,'fixed_holdup_trip':trajs['fixed_holdup_trip']}
  levels=(1.0,1.05,1.10,1.15,1.20) if uid=='G33' else (1.15,)
  for load in levels:
   for name,traj in enc4.items():
    rows_load.append(eval_path(uid,name,traj,load,0.25))
  for name,traj in trajs.items():
   r=eval_path(uid,name,traj,1.15,0.25)
   rows_six.append({'scope':f'IEEE39_{uid}_grid','benchmark':name,**traj.metrics(),**r})
  # Also add the aligned control to rows_six for completeness (7 rows per unit)
  r_al=eval_path(uid,'delayed_instant_trip@t_mech',delayed,1.15,0.25)
  rows_six.append({'scope':f'IEEE39_{uid}_grid','benchmark':'delayed_instant_trip@t_mech',**delayed.metrics(),**r_al})

 extra_file.write_text(json.dumps({'signature':sig,'snapshots':extra},indent=2)+'\n')
 for fname,data in [('opf_encoding_expand_v072.csv',rows_load),('opf_six_encodings_v072.csv',rows_six)]:
  with (O/fname).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

 gate={'verdict':'PASS','date':'2026-10-17','version':'0.7.2','scope':'v0.7.2 six-encoding, five-load (1.00-1.20) and G34 adequacy expansion at 15-min event-aware exchange','signature':sig,'new_dc_snapshots_solved':new_solves,'extra_cached_snapshots':len(extra),'total_pool_snapshots':len(pool),'rows_load':rows_load,'rows_six':rows_six}
 (O/'OPF_EXPAND_V072_GATE.json').write_text(json.dumps(gate,indent=2)+'\n')
 assert all(sha(R/n)==h for n,h in frozen.items())
 print('OPF EXPAND v0.7.2 PASS: new solves=',new_solves,'total extra=',len(extra))
if __name__=='__main__':main()
