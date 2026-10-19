"""Gated cold-end v0.7.2 candidate evaluation. No AC or ensemble campaign.
Write evidence only to manuscript/revisions/thermal_v072/outputs.
"""
from pathlib import Path
import argparse,csv,hashlib,json,sys,zipfile,types,math,contextlib,io
from dataclasses import replace
from importlib.metadata import version
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'code/src'))
from cooling.dynamics import simulate_cold_end,NoQuasiStaticEquilibrium
from cooling.benchmarks import from_timeseries,BenchmarkTrajectory,instant_trip_trajectory
from cooling.prototype_500mw import WetRecircPrototype500
from grid.coupling import event_aware_time_samples,integrate_time_series
from scenarios import load_unit_config,load_unit_params
from scenarios.fault_makeup_basin import build_unit_model
D=R/'manuscript/revisions/thermal_v072';O=D/'outputs';O.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CORE=[R/'code/src/cooling'/n for n in ['dynamics.py','transient.py','benchmarks.py','prototype_500mw.py']]
def hashes():return {str(p.relative_to(R)):sha(p) for p in CORE}
def csvout(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (O/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def model():return build_unit_model(load_unit_config()['G33'],params=load_unit_params('baseline'))

def plant():
    cases={'S1a':dict(fault_type='makeup_interrupt'),
           'S1b':dict(fault_type='makeup_interrupt',blowdown_policy='maintain'),
           'C1':dict(fault_type='makeup_interrupt',strategy='hold_load'),
           'S2':dict(fault_type='pump_failure'),
           'S3a':dict(fault_type='pump_failure',pump_loss_frac=.5),
           'S3b':dict(fault_type='pump_failure',pump_loss_frac=.3),
           'S4':dict(fault_type='wet_bulb_increase',twb_rise_c=6)}
    z=zipfile.ZipFile(D/'PRE_THERMAL_BASELINE.zip')
    mod=types.ModuleType('cooling._frozen_dynamics_v071');sys.modules[mod.__name__]=mod
    exec(compile(z.read('code/src/cooling/dynamics.py'),'frozen/dynamics.py','exec'),mod.__dict__)
    rows=[];checks=[]
    for name,kw in cases.items():
        horizon=1 if name=='S2' else 8
        old=mod.simulate_cold_end(model(),t_max_h=horizon,**kw)
        steps=[.1,.025] if name=="S2" else [1.,.25]
        for dt in steps:
            t=simulate_cold_end(model(),dt_s=dt,sample_every_s=60 if name!='S2' else 1,t_max_h=horizon,**kw)
            traj=from_timeseries(t,name=name,label=name)
            assert t.t_s[0]==0 and t.qcw_frac[0]==1 and t.t_s[-1]<=horizon*3600+1e-7
            assert all(math.isfinite(v) for v in t.backpressure_kpa)
            assert all(-1e-6<=v<=t.initial_p_mw+1e-5 for v in t.p_avail_mw)
            assert t.max_condenser_energy_residual_mj<1e-6
            rows.append(dict(case=name,dt_s=dt,trip_h=t.t_trip_h,mechanism=t.trip_mechanism,
                             delivered_energy_mwh=traj.delivered_energy_mwh(),p_end_mw=t.p_avail_mw[-1],
                             initial_p_mw=t.initial_p_mw,initial_pb_kpa=t.initial_pb_kpa,
                             max_energy_residual_mj=t.max_condenser_energy_residual_mj,
                             old_v071_trip_h=old.t_trip_h,old_v071_mechanism=old.trip_mechanism))
            if dt==steps[0]:
                with (O/(name+'_v072.json')).open('w') as f:
                    json.dump(dict(model_version=t.model_version,t_trip_h=t.t_trip_h,p_trip_left_mw=t.p_before_trip_mw,rows=t.rows()),f,indent=2)
        a,b=rows[-2:]
        trip_error_s=abs(a['trip_h']-b['trip_h'])*3600 if a['trip_h'] is not None and b['trip_h'] is not None else 0.
        energy_error_pct=abs(a['delivered_energy_mwh']-b['delivered_energy_mwh'])/max(b['delivered_energy_mwh'],1)*100
        ok=a['mechanism']==b['mechanism'] and (a['trip_h'] is None)==(b['trip_h'] is None) and trip_error_s<=5 and energy_error_pct<.1
        checks.append(dict(case=name,trip_difference_s=trip_error_s,energy_difference_pct=energy_error_pct,passed=ok))
        print(name,a['trip_h'],a['mechanism'],'dt error',trip_error_s,'s /',energy_error_pct,'%',flush=True)
    # A zero-storage/zero-flow control must not manufacture a finite trip time.
    try:simulate_cold_end(model(),fault_type='pump_failure',quasi_static=True,t_max_h=.1)
    except NoQuasiStaticEquilibrium:qs='NO_FINITE_EQUILIBRIUM'
    else:raise AssertionError('singular quasi-static state was hidden')
    # Time-constant intervention and two existing tail replays, not fresh sampling.
    interventions=[]
    for tau in [30.,1800.]:
        t=simulate_cold_end(replace(model(),tower_tau_s=tau),fault_type='wet_bulb_increase',twb_rise_c=6,t_max_h=.5,sample_every_s=60)
        interventions.append(t)
    pb_delta=max(abs(a-b) for a,b in zip(interventions[0].backpressure_kpa,interventions[1].backpressure_kpa));assert pb_delta>.01
    from cooling.uncertainty import default_uncertainty_parameters
    oldrows=list(csv.DictReader((R/'code/examples/probabilistic_uncertainty_samples.csv').open()))
    tails=[]
    base=WetRecircPrototype500();specs=default_uncertainty_parameters(base)
    for r in oldrows:
        if r['trip_mechanism']!='backpressure_protection':continue
        changes={s.name:float(r[s.name]) for s in specs if s.destination=='model'}
        kw={s.name:float(r[s.name]) for s in specs if s.destination=='dynamics'}
        t=simulate_cold_end(replace(base,**changes),dt_s=1,sample_every_s=60,t_max_h=8,**kw)
        assert t.initial_pb_kpa<float(r['pb_trip_kpa'])
        tails.append(dict(sample_id=r['sample_id'],old_trip_h=float(r['t_trip_h']),new_trip_h=t.t_trip_h,
                          old_mechanism=r['trip_mechanism'],new_mechanism=t.trip_mechanism,
                          initialized_p_mw=t.initial_p_mw,initialized_pb_kpa=t.initial_pb_kpa,setpoint_kpa=float(r['pb_trip_kpa'])))
    csvout('plant_comparison_v072.csv',rows)
    report=dict(version='0.7.2-candidate',verdict='PASS' if all(c['passed'] for c in checks) else 'FAIL',source_sha256=hashes(),checks=checks,
                cases=rows,quasi_static_full_loss=qs,tower_tau_intervention_max_pb_difference_kpa=pb_delta,
                two_old_mc_tail_replays=tails,recommended_dt_s={'S2_full_pump_loss':.1,'other_representative_cases':1.},
                prior_coarse_failure='PLANT_GATE_FIRST_FAILED.json: S2 dt1/.25s energy error0.504%, exceeds0.1% gate',
                scope='Numerical/structural verification, not plant calibration or empirical validation')
    (O/'PLANT_GATE.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['verdict']=='PASS'
    print('PLANT GATE PASS',flush=True)


def primary():
    gate=json.loads((O/'PLANT_GATE.json').read_text());assert gate['verdict']=='PASS' and gate['source_sha256']==hashes()
    from grid.opf import evaluate_grid_impact
    opf=R/'code/src/grid/opf.py';signature=sha(opf)+'/'+version('pandapower')
    static=json.loads((R/'manuscript/revisions/opf_v071/STATIC_OPF_VERIFICATION.json').read_text())
    assert static['verdict']=='PASS' and static['opf_source_sha256']==sha(opf)
    cachepath=O/'opf_snapshot_cache_v072.json';source=cachepath if cachepath.exists() else R/'code/examples/opf_snapshot_cache_v071.json'
    stored=json.loads(source.read_text());assert stored['signature']==signature
    cache=stored['snapshots'];initial_n=len(cache);solves=0;warnings=io.StringIO()
    def snap(caps):
        nonlocal solves
        key=json.dumps([1.15,sorted(caps.items())])
        if key not in cache:
            with contextlib.redirect_stderr(warnings):r=evaluate_grid_impact(caps,load_scale=1.15)
            assert r.converged and r.n_branches_checked==46 and r.max_nodal_residual_mw<1e-5 and r.n_overloaded_branches==0
            cache[key]=vars(r);solves+=1
            if solves%25==0:
                cachepath.write_text(json.dumps(dict(signature=signature,snapshots=cache),indent=2)+'\n')
                print('New validated DC snapshots',solves,flush=True)
        return cache[key]
    baseline=snap({})['shed_load_mw'];m=model()
    ts=simulate_cold_end(m,t_max_h=8)
    mech=from_timeseries(ts,name='mechanistic_ride_down',label='serial finite storage')
    aligned=BenchmarkTrajectory('aligned','Full capability until same later trip','G33',m.p_rated_mw,
                                t_h=[0,mech.trip_h],p_avail_mw=[m.p_rated_mw]*2,trip_h=mech.trip_h,p_trip_left_mw=m.p_rated_mw)
    enc={'instant':instant_trip_trajectory(m),'aligned':aligned,'mechanistic':mech}
    rows=[];traces={}
    for name,tr in enc.items():
        for step in ([.25,1/60] if name=='mechanistic' else [.25]):
            samples=event_aware_time_samples(tr,t_end_h=8,macro_step_h=step);trace=[]
            for t,side in samples:
                cap=tr.p_avail_at(t,side=side);shed=snap({'G33':cap})['shed_load_mw']
                trace.append(dict(t_h=t,side=side,cap_mw=cap,shed_mw=shed,incremental_mw=max(0.,shed-baseline)))
            inc=integrate_time_series([v['t_h'] for v in trace],[v['incremental_mw'] for v in trace])
            rows.append(dict(encoding=name,step_h=step,incremental_uae_mwh=inc,trip_h=tr.trip_h,delivered_energy_mwh=tr.delivered_energy_mwh()))
            traces[f'{name}/{step}']=trace
    a={v['encoding']:v['incremental_uae_mwh'] for v in rows if v['step_h']==.25}
    ref=rows[-1]['incremental_uae_mwh'];error=(a['mechanistic']-ref)/ref*100
    summary=dict(instant_mwh=a['instant'],aligned_mwh=a['aligned'],mechanistic_mwh=a['mechanistic'],
                 reduction_vs_instant_pct=100*(a['instant']-a['mechanistic'])/a['instant'],
                 gap_mwh=a['instant']-a['mechanistic'],timing_mwh=a['instant']-a['aligned'],shape_mwh=a['aligned']-a['mechanistic'],
                 difference_15min_vs_1min_pct=error)
    assert abs(error)<.1
    assert a['aligned']<=a['mechanistic']<=a['instant']
    assert abs(summary['gap_mwh']-summary['timing_mwh']-summary['shape_mwh'])<1e-8
    csvout('primary_uae_v072.csv',rows)
    cachepath.write_text(json.dumps(dict(signature=signature,snapshots=cache),indent=2)+'\n')
    (O/'PRIMARY_UAE_GATE.json').write_text(json.dumps(dict(verdict='PASS',version='0.7.2-candidate',summary=summary,rows=rows,
                traces=traces,source_sha256={**hashes(),'code/src/grid/opf.py':sha(opf)},cache_reused=initial_n,new_snapshots=solves,
                scope='Candidate open-loop cold-end trajectories; DC-only, not empirical validation'),indent=2)+'\n')
    (O/'PRIMARY_OPF_WARNINGS.txt').write_text(warnings.getvalue())
    print('PRIMARY UAE PASS',summary,'new solves',solves,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['plant','primary'],default='plant');args=ap.parse_args()
    (plant if args.stage=='plant' else primary)()
