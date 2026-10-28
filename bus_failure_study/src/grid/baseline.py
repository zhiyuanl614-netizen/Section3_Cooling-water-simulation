#!/usr/bin/env python3
"""无故障 K0 基准交流潮流测试；结果写入 results/K0_baseline。"""
from __future__ import annotations
import csv
from pathlib import Path
from grid import cases
from grid.cascade import solve_island

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"results"/"K0_baseline"

def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main():
    case=cases.loader()
    result, shed_by_bus, shed_total, ok=solve_island(case, cases.cfg())
    if not ok or result is None:
        raise SystemExit("K0 基准 IEEE30 潮流不收敛")
    bus_rows=[]
    for row in result["bus"]:
        b=int(row[0]); vm=float(row[7]); vmin=float(row[12]); vmax=float(row[11])
        bus_rows.append({"bus":b,"vm_pu":f"{vm:.8f}","vmin_pu":f"{vmin:.4f}","vmax_pu":f"{vmax:.4f}","f1_violation":int(vm<vmin or vm>vmax)})
    gen_rows=[]
    for row in result["gen"]:
        gen_rows.append({"bus":int(row[0]),"pg_mw":f"{float(row[1]):.8f}","qg_mvar":f"{float(row[2]):.8f}","status":int(row[7]),"pmax_mw":f"{float(row[8]):.6f}"})
    total_load=float(result["bus"][:,2].sum())
    total_pg=float(result["gen"][:,1].sum())
    summary=[{"case":"IEEE30","status":"converged","n_bus":len(result["bus"]),"n_gen":len(result["gen"]),"n_branch":len(result["branch"]),"load_mw":f"{total_load:.6f}","generation_mw":f"{total_pg:.6f}","loss_mw":f"{total_pg-total_load:.6f}","f1_bus_count":sum(x["f1_violation"] for x in bus_rows),"load_shed_mw":f"{float(shed_total):.6f}"}]
    write_csv(OUT/"system_summary.csv",summary)
    write_csv(OUT/"bus_voltage.csv",bus_rows)
    write_csv(OUT/"generator_dispatch.csv",gen_rows)
    print(f"K0 IEEE30 AC PF: converged; load={total_load:.3f} MW; generation={total_pg:.4f} MW; F1={summary[0]['f1_bus_count']}; outputs={OUT}")

if __name__=="__main__": main()
