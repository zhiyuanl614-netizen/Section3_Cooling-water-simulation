#!/usr/bin/env python3
"""Run the 15 K2 unordered pairs; both makeup interruptions begin at t=0."""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT/"src") not in sys.path:
    sys.path.insert(0,str(ROOT/"src"))
from coupling.coupled import simulate_single_unit_dynamic, write_scenario_outputs, _write_csv

MATRIX=ROOT/"scenarios"/"K2"/"pairwise_matrix.csv"
DEFAULT_OUT=ROOT/"results"/"K2"

def read_matrix():
    with MATRIX.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_matrix(rows):
    with MATRIX.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main(argv=None):
    ap=argparse.ArgumentParser(description="K2 IEEE30 双机补水同时中断—异步冷端跳机组合")
    ap.add_argument("--scenario",action="append",help="可重复指定 K2-G1-G2 等；默认运行完整 15 案")
    ap.add_argument("--output-root",default=str(DEFAULT_OUT))
    args=ap.parse_args(argv)
    matrix=read_matrix()
    by_id={r["scenario_id"]:r for r in matrix}
    selected=args.scenario or list(by_id)
    unknown=sorted(set(selected)-set(by_id))
    if unknown: ap.error(f"情景矩阵中不存在：{unknown}")
    if len(selected)!=len(set(selected)): ap.error("情景 ID 不可重复")
    out=Path(args.output_root)
    summaries=[]
    for i,sid in enumerate(selected,1):
        row=by_id[sid]
        pair=(row["unit_a"],row["unit_b"])
        print(f"[{i}/{len(selected)}] {sid}: t=0 同时断水 {pair[0]} + {pair[1]}",flush=True)
        summary,demand,cooling,dispatch,_=simulate_single_unit_dynamic(
            pair[0],makeup_interrupted_units=pair)
        s=summary[0]
        s["scenario_id"]=sid
        s["scenario_class"]="K2_pairwise_simultaneous_makeup_loss"
        s["makeup_interruption_timing_protocol"]="both_start_at_t0; trip_times_are_coldend_determined"
        s["scenario_status"]="completed"
        write_scenario_outputs(out/"scenarios"/sid,summary,demand,cooling,dispatch)
        summaries.extend(summary)
        print(f"  first trip={s['initial_trip_units']} at {s['initial_trip_h']:.4f} h; "
              f"f_nadir={s['f_nadir_hz']:.3f} Hz; UFLS={s['ufls_shed_mw']:.3f} MW; "
              f"hard buses={s['n_bus_hard_failure']}; class={s['impact_class']}; "
              f"stop={s['simulation_stop_reason']}",flush=True)
    _write_csv(out/"tables"/"pairwise_summary.csv",summaries)
    if len(selected)==len(by_id):
        for row in matrix:
            row["timing_protocol"]="simultaneous_makeup_interruption_at_t0; coldend_determined_trip_times"
            row["status"]="completed"
        write_matrix(matrix)
    print(f"K2 complete: {len(summaries)} scenario(s); outputs: {out}",flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
