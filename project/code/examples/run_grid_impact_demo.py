"""
Demo (assessment tier B): cold-end failure -> DC-OPF -> unserved load.

Two sweeps are produced:

1. demand-level sweep -- IEEE 39 has ~15% capacity margin at the case peak, so
   a single cold-end loss only shows up as unserved load once demand is high.
   This is the adequacy picture.
2. time sweep -- the OPF is re-solved along the cold-end Pavail(t) trajectory
   of the faulted unit, giving unserved load as a *function of time*.

Writes ``examples/grid_impact_loadlevel.csv`` and
``examples/grid_impact_timeseries.csv``.  Requires pandapower (tier B);
everything else in the project runs on the standard library alone.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grid import baseline_no_fault, evaluate_grid_impact, evaluate_timeseries  # noqa: E402
from scenarios import evaluate_scenario, load_scenarios  # noqa: E402


def main() -> int:
    scenarios = load_scenarios()
    units = [sc.faulted_units[0] for sc in scenarios]

    # ---------------------------------------------------------- load-level
    print("=== tier B: demand-level adequacy sweep (DC-OPF + load shedding) ===")
    print(f"{'load x':>7s} {'load(MW)':>9s} {'case shed':>10s} " + " ".join(f"{u:>10s}" for u in units))
    ll_rows = []
    for scale in (1.00, 1.05, 1.10, 1.15, 1.20):
        base = baseline_no_fault(load_scale=scale)
        per_unit = {u: evaluate_grid_impact({u: 0.0}, load_scale=scale) for u in units}
        print(
            f"{scale:7.2f} {base.total_load_mw:9.1f} {base.shed_load_mw:10.1f} "
            + " ".join(f"{per_unit[u].shed_load_mw:10.1f}" for u in units)
        )
        ll_rows.append(
            {
                "load_scale": scale,
                "total_load_mw": round(base.total_load_mw, 2),
                "case_shed_mw": round(base.shed_load_mw, 3),
                "case_max_line_loading_percent": round(base.max_line_loading_percent, 2),
                **{
                    f"{u}_out_shed_mw": round(per_unit[u].shed_load_mw, 3)
                    for u in units
                },
                **{
                    f"{u}_incremental_shed_mw": round(
                        per_unit[u].shed_load_mw - base.shed_load_mw, 3
                    )
                    for u in units
                },
            }
        )

    ll_csv = ROOT / "examples" / "grid_impact_loadlevel.csv"
    with open(ll_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ll_rows[0]))
        w.writeheader()
        w.writerows(ll_rows)
    print(f"\nwrote {ll_csv}")

    # -------------------------------------------------------- time sweep
    print("\n=== tier B: unserved load along the cold-end trajectory (load x1.15) ===")
    ts_rows: list[dict] = []
    for sc in scenarios:
        out = evaluate_scenario(sc, timeseries=True, strategy="ride_down")
        fa = sc.faulted_units[0]
        healthy = {u: p for u, p in out.pavail_mw.items() if u != fa}
        rows = evaluate_timeseries(
            out.timeseries,
            faulted_unit=fa,
            healthy_pmax_mw=healthy,
            load_scale=1.15,
            macro_step_h=5.0 / 60.0,
            event_aware=True,
        )
        print(f"\n  {sc.scenario_id}  (trip at {out.timeseries[fa].t_trip_h:.3f} h, "
              f"{out.timeseries[fa].trip_mechanism})")
        print(f"    {'t(h)':>6s} {'Pavail(MW)':>11s} {'shed(MW)':>10s} {'maxLine(%)':>11s}")
        show = {0.0, 3.0, 4.5, 4.75, 5.0}
        for r in rows:
            if r["t_h"] in show or r is rows[-1]:
                print(
                    f"    {r['t_h']:6.2f} {r['pavail_faulted_mw']:11.1f} "
                    f"{r['shed_load_mw']:10.1f} {r['max_line_loading_percent']:11.2f}"
                )
        for r in rows:
            r["scenario_id"] = sc.scenario_id
        ts_rows.extend(rows)

    ts_csv = ROOT / "examples" / "grid_impact_timeseries.csv"
    with open(ts_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ts_rows[0]))
        w.writeheader()
        w.writerows(ts_rows)
    print(f"\nwrote {ts_csv} ({len(ts_rows)} rows)")
    print("\nNote: in a converged DC-OPF line limits are constraints, so overloads")
    print("      appear as shed load.  Overload counting belongs to tier C (cascade).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
