"""Recouple RQ2 partial-capability and detuned thermal-to-cascade snapshots under v0.7.2 without modifying frozen files."""
from pathlib import Path
from dataclasses import replace
import sys,json,csv,hashlib
R=Path(__file__).resolve().parents[3];D=Path(__file__).parent;O=D/'outputs';O.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'code/src'))
from cooling.dynamics import simulate_cold_end
from cooling.benchmarks import from_timeseries
from cooling.prototype_500mw import WetRecircPrototype500
from cooling.scale import scale_prototype_to_unit
from grid.cascade import IEEE39CascadeGrid
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def guard():
 f=json.loads((D/'PRE_EDIT_STATE.json').read_text())['files']
 assert len(f)==242 and all(sha(R/n)==h for n,h in f.items()),'a protected file was modified'

def make_grid(rf=1.0):
 g=IEEE39CascadeGrid()
 for e in g.lines:e['rate']*=rf
 return g

def verify(grid,result,caps):
 assert result.converged,f'{result.status}: {result.notes}'
 ceilings={g['bus']:g['Pmax'] for g in grid.generators};ceilings.update(caps)
 prev_load={b['id']:b['Pd'] for b in grid.buses};prev_pg=None
 for s in result.trace:
  assert s['max_nodal_residual_mw']<=1e-7
  assert not any(v>prev_load[n]+1e-7 or v<-1e-7 for n,v in s['served_load_mw'].items())
  assert not any(v<-1e-7 or v>ceilings[n]+1e-7 for n,v in s['generation_mw'].items())
  if result.policy=='S' and prev_pg is not None:
   assert all(v<=prev_pg[n]+1e-7 for n,v in s['generation_mw'].items())
  for isl in s['islands']:
   assert abs(sum(s['generation_mw'].get(n,0) for n in isl['buses'])-sum(s['served_load_mw'][n] for n in isl['buses']))<=1e-7
  prev_load=s['served_load_mw'];prev_pg=s['generation_mw']
 assert grid.overloaded(result.line_flows_mw)==[]
 refs=[i['buses'][-1] for i in result.islands]
 f,_=grid.dc_power_flow(result.generation_mw,served_load_mw=result.served_load_mw,reference_buses=refs)
 assert max((abs(a-b) for a,b in zip(f,result.line_flows_mw)),default=0)<=1e-7

def solve_thermal_inputs(dt_s=1.0,sample_s=1.0):
 m33=scale_prototype_to_unit(WetRecircPrototype500(),652.0)
 m34=scale_prototype_to_unit(WetRecircPrototype500(),508.0)
 m34_det=replace(m34,basin_area_m2=m34.basin_area_m2*0.85)
 s3a_33=simulate_cold_end(m33,fault_type='pump_failure',pump_loss_frac=0.5,strategy='ride_down',dt_s=dt_s,sample_every_s=sample_s,t_max_h=8.0)
 s3a_34=simulate_cold_end(m34,fault_type='pump_failure',pump_loss_frac=0.5,strategy='ride_down',dt_s=dt_s,sample_every_s=sample_s,t_max_h=8.0)
 assert s3a_33.trip is None and s3a_34.trip is None
 s1a_33=simulate_cold_end(m33,fault_type='makeup_interrupt',strategy='ride_down',blowdown_policy='isolate_on_detection',dt_s=dt_s,sample_every_s=sample_s,t_max_h=8.0)
 s1a_34_sync=simulate_cold_end(m34,fault_type='makeup_interrupt',strategy='ride_down',blowdown_policy='isolate_on_detection',dt_s=dt_s,sample_every_s=sample_s,t_max_h=8.0)
 s1a_34_det=simulate_cold_end(m34_det,fault_type='makeup_interrupt',strategy='ride_down',blowdown_policy='isolate_on_detection',dt_s=dt_s,sample_every_s=sample_s,t_max_h=8.0)
 assert s1a_33.t_trip_h==s1a_34_sync.t_trip_h
 t_first=min(s1a_33.t_trip_h,s1a_34_det.t_trip_h);t_second=max(s1a_33.t_trip_h,s1a_34_det.t_trip_h)
 first_bus,survivor=(34,33) if s1a_34_det.t_trip_h<s1a_33.t_trip_h else (33,34)
 surv_cap=float(s1a_33.p_avail_at(t_first))
 return dict(dt_s=dt_s,sample_s=sample_s,
             partial_caps_mw={33:float(s3a_33.p_avail_mw[-1]),34:float(s3a_34.p_avail_mw[-1])},
             s3a_33_energy_mwh=from_timeseries(s3a_33,name='s3a_33',label='s3a').delivered_energy_mwh(8.0),
             s3a_34_energy_mwh=from_timeseries(s3a_34,name='s3a_34',label='s3a').delivered_energy_mwh(8.0),
             sync_trip_h=float(s1a_33.t_trip_h),first_trip_h=float(t_first),second_trip_h=float(t_second),
             first_bus=first_bus,surviving_bus=survivor,surviving_capability_mw=surv_cap,
             s1a_33_energy_mwh=from_timeseries(s1a_33,name='s1a_33',label='s1a').delivered_energy_mwh(8.0),
             s1a_34_det_energy_mwh=from_timeseries(s1a_34_det,name='s1a_34_det',label='s1a').delivered_energy_mwh(8.0))

def main():
 guard()
 ref_in=solve_thermal_inputs(1.0,60.0)
 fine_in=solve_thermal_inputs(0.25,15.0)
 exact1s_in=solve_thermal_inputs(1.0,1.0)
 assert abs(ref_in['surviving_capability_mw']-exact1s_in['surviving_capability_mw'])<0.01
 assert abs(ref_in['first_trip_h']-fine_in['first_trip_h'])*3600<=5.0
 assert abs(ref_in['second_trip_h']-fine_in['second_trip_h'])*3600<=5.0
 assert abs(ref_in['surviving_capability_mw']-fine_in['surviving_capability_mw'])<0.01

 states={'healthy':{},'G1_single_33_trip':{33:0.0},'G2_dual_collapse':{33:0.0,34:0.0},'S3a_dual_derate':ref_in['partial_caps_mw']}
 snapshots={'M6_synchronous_G3':({33:0.0,34:0.0},ref_in['sync_trip_h']),
            'M6_detuned_at_first_trip':({ref_in['first_bus']:0.0,ref_in['surviving_bus']:ref_in['surviving_capability_mw']},ref_in['first_trip_h']),
            'M6_detuned_at_second_trip':({33:0.0,34:0.0},ref_in['second_trip_h'])}
 traces={}
 def evaluate(probe,name,caps,policy,rule,rf,event_time=''):
  g=make_grid(rf);r=g.solve_cascade(caps,policy=policy,rule=rule);verify(g,r,caps)
  key=f'{probe}/{name}/{policy}/{rule}/{rf}'
  traces[key]={'capabilities_mw':caps,'status':r.status,'rounds':r.trace,'removed_lines':r.removed_lines,'deenergized_intact_lines':r.deenergized_intact_lines}
  return {'probe':probe,'schedule':name,'policy':policy,'rule':rule,'rate_factor':rf,'status':r.status,
          'n_lines_removed':r.n_removed,'n_stages':len(r.stages),'n_lines_first_stage':len(r.stages[0]) if r.stages else 0,
          'shed_load_mw':r.shed_load_mw,'served_load_mw':sum(r.served_load_mw.values()),'n_islands':len(r.islands),
          'n_deenergized_intact_lines':len(r.deenergized_intact_lines),
          'max_nodal_residual_mw':max(s['max_nodal_residual_mw'] for s in r.trace),
          't_snapshot_h':event_time,'surviving_bus_at_first_trip':ref_in['surviving_bus'] if 'first' in name else '',
          'surviving_capability_mw':ref_in['surviving_capability_mw'] if 'first' in name else ''}

 gate=[evaluate('minimal_gate',name,caps,p,'simultaneous',1.0) for name,caps in states.items() for p in ('S','H')]
 rows=[evaluate('M2_rule_robustness',name,caps,p,rule,rf) for name,caps in states.items() for p in ('S','H') for rule in ('simultaneous','sequential') for rf in (0.9,1.0,1.1)]
 rows+=[evaluate('M6_unit_decorrelation',name,caps,p,rule,1.0,time) for name,(caps,time) in snapshots.items() for p in ('S','H') for rule in ('simultaneous','sequential')]
 # Also run the detuned first-trip snapshot across 0.9 and 1.1 rating multipliers for full rule/rating completeness.
 det_extra=[evaluate('M6_detuned_rating_check','M6_detuned_at_first_trip',{ref_in['first_bus']:0.0,ref_in['surviving_bus']:ref_in['surviving_capability_mw']},p,rule,rf,ref_in['first_trip_h']) for p in ('S','H') for rule in ('simultaneous','sequential') for rf in (0.9,1.0,1.1)]

 # Compare against fine thermal inputs to verify topological & load invariance
 fine_det=[evaluate('fine_check','M6_detuned_at_first_trip',{fine_in['first_bus']:0.0,fine_in['surviving_bus']:fine_in['surviving_capability_mw']},p,rule,1.0,fine_in['first_trip_h']) for p in ('S','H') for rule in ('simultaneous','sequential')]
 for a,b in zip([r for r in rows if r['schedule']=='M6_detuned_at_first_trip'],fine_det):
  assert a['n_lines_removed']==b['n_lines_removed'] and a['n_stages']==b['n_stages'] and a['n_islands']==b['n_islands']
  assert abs(a['shed_load_mw']-b['shed_load_mw'])<0.01

 for fname,data in [('dc_minimal_validation_v072.csv',gate),('m2_cascade_robustness_v072.csv',rows),('detuned_rating_sensitivity_v072.csv',det_extra)]:
  with (O/fname).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

 old_ev=json.loads((R/'code/examples/dc_cascade_evidence_v07.json').read_text())
 report={'verdict':'PASS','date':'2026-10-17','scope':'v0.7.2 recoupled DC-only S/H cascade snapshots; independent state snapshots, NOT a continuous time-domain cascade','reference_thermal_inputs_v072':ref_in,'exact1s_thermal_inputs_v072':exact1s_in,'fine_thermal_inputs_v072':fine_in,'historical_v070_inputs':old_ev['unrounded_inputs'],'gate_rows_count':len(gate),'matrix_rows_count':len(rows),'detuned_rating_rows_count':len(det_extra),'max_nodal_residual_mw':max(r['max_nodal_residual_mw'] for r in gate+rows+det_extra),'gate_rows':gate,'rows':rows,'detuned_rating_rows':det_extra,'runs':traces}
 (O/'RQ2_RECOUPLED_GATE.json').write_text(json.dumps(report,indent=2)+'\n')
 guard()
 print('RQ2 RECOUPLED PASS:',len(gate),'gate +',len(rows),'matrix +',len(det_extra),'detuned rating rows; max residual',report['max_nodal_residual_mw'])
if __name__=='__main__':main()
