#!/usr/bin/env python3
"""Run the sole K6 all-six-unit scenario; all six makeup interruptions start at t=0."""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/"src") not in sys.path:
    sys.path.insert(0,str(ROOT/"src"))
from coupling.coupled import simulate_single_unit_dynamic, write_scenario_outputs, _write_csv

MATRIX=ROOT/"scenarios"/"K6"/"six_unit_matrix.csv"
DEFAULT_OUT=ROOT/"results"/"K6"
UNITS=("unit_a","unit_b","unit_c","unit_d","unit_e","unit_f")

def read_matrix():
    with MATRIX.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_matrix(rows):
    with MATRIX.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main(argv=None):
    ap=argparse.ArgumentParser(description="K6 IEEE30 全六机补水同时中断—冷端错时跳机情景")
    ap.add_argument("--continue-after-hard-loss",action="store_true",
                    help="K6专用：首次H>0后继续，直至六台目标机组跳闸、无在线机组、24h或F2b潮流失败")
    ap.add_argument("--output-root",default=None)
    args=ap.parse_args(argv)
    out=Path(args.output_root) if args.output_root else (
        DEFAULT_OUT/"continuation" if args.continue_after_hard_loss else DEFAULT_OUT)
    matrix=read_matrix()
    if len(matrix)!=1:
        ap.error(f"K6 应且仅应有 1 个全六机情景，矩阵实际为 {len(matrix)} 行")
    row=matrix[0]
    sid=row["scenario_id"]
    faulted_units=tuple(row[k] for k in UNITS)
    if len(set(faulted_units))!=6:
        ap.error("K6 必须恰好包含六台不同机组")
    print(f"[1/1] {sid}: t=0 同时断水 {' + '.join(faulted_units)}",flush=True)
    summary,demand,cooling,dispatch,_=simulate_single_unit_dynamic(
        faulted_units[0],makeup_interrupted_units=faulted_units,
        stop_at_hard_service_loss=not args.continue_after_hard_loss,
        stop_on_solver_failure=args.continue_after_hard_loss)
    s=summary[0]
    s["scenario_id"]=sid
    s["scenario_class"]=("K6_all_six_continuation" if args.continue_after_hard_loss
                         else "K6_all_six_first_hard_loss")
    s["makeup_interruption_timing_protocol"]="all_six_start_at_t0; trip_times_are_coldend_determined"
    s["simulation_stop_protocol"]=("continue_after_first_H_until_all_six_trip_no_online_units_24h_or_F2b_solver_failure"
                                   if args.continue_after_hard_loss else "stop_at_first_H_positive")
    if int(s.get("n_f3_deenergized",0))==30 and int(s.get("n_bus_dead",0))==30:
        s["grid_endpoint_class"]="all_30_buses_F3_deenergized_no_source"
    elif int(s.get("n_bus_hard_failure",0))>0:
        s["grid_endpoint_class"]="partial_hard_service_loss"
    else:
        s["grid_endpoint_class"]="no_hard_service_loss_observed"
    s["scenario_status"]="completed"
    selected_tripped=set(s["initial_trip_units"].split(';'))
    selected_tripped.update(e.split('@',1)[0] for e in s["other_coldend_trip_events"].split(';') if e)
    selected_tripped.intersection_update(faulted_units)
    s["faulted_units_tripped_count_before_stop"]=len(selected_tripped)
    s["faulted_units_not_tripped_before_stop"]=";".join(sorted(set(faulted_units)-selected_tripped))
    write_scenario_outputs(out/"scenarios"/sid,summary,demand,cooling,dispatch)
    _write_csv(out/"tables"/"six_unit_summary.csv",summary)
    row["status"]="completed"
    write_matrix(matrix)
    print(f"  initial trips={s['initial_trip_units']} at {s['initial_trip_events']}; "
          f"later cold trips={s['other_coldend_trip_events'] or '(none before stop)'}; "
          f"selected trips before stop={s['faulted_units_tripped_count_before_stop']}/6; "
          f"f_nadir={s['f_nadir_hz']:.3f} Hz; UFLS={s['ufls_shed_mw']:.3f} MW; "
          f"hard buses={s['n_bus_hard_failure']}; stop={s['simulation_stop_reason']}",flush=True)
    print(f"K6 complete: output: {out}",flush=True)
    return 0

if __name__=="__main__": raise SystemExit(main())
