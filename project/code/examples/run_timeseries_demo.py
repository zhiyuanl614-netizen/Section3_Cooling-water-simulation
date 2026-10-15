"""
Demo: mechanism-resolved basin-drain trajectory for the three coal units.

Replaces the binary "capacity step" picture with a Pavail(t) curve:
basin level -> circulating-flow fraction -> condenser pressure -> available MW,
plus the trip mechanism and time.

Writes ``examples/scenario_pavail_timeseries.csv``.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scenarios import load_scenarios, load_unit_config, evaluate_scenario  # noqa: E402


def main() -> int:
    units = load_unit_config()
    scenarios = load_scenarios()
    out_csv = ROOT / "examples" / "scenario_pavail_timeseries.csv"
    all_rows: list[dict] = []
    summary: list[dict] = []

    print("=== mechanism-resolved basin drain (both operating strategies) ===")
    for strategy in ("ride_down", "hold_load"):
        print(f"\n--- strategy: {strategy} ---")
        print(
            f"{'scenario':10s} {'Pmax':>6s} {'derate':>7s} {'trip':>7s} "
            f"{'mechanism':>24s}  P@trip-0.2h"
        )
        for sc in scenarios:
            out = evaluate_scenario(sc, timeseries=True, strategy=strategy)
            fa = sc.faulted_units[0]
            ts = out.timeseries[fa]
            pmax = units[fa].pmax_mw
            p_before = ts.p_avail_at(max(0.0, (ts.t_trip_h or 0.0) - 0.2))
            derate_txt = "--" if ts.t_derate_start_h is None else f"{ts.t_derate_start_h:.2f}"
            print(
                f"{sc.scenario_id:10s} {pmax:6.0f} {derate_txt:>7s} "
                f"{ts.t_trip_h:7.3f} {ts.trip_mechanism:>24s}  {p_before:6.1f} MW"
            )
            for r in ts.rows():
                r["strategy"] = strategy
                r["scenario_id"] = sc.scenario_id
                r["pmax_mw"] = pmax
                all_rows.append(r)
            summary.append(
                {
                    "strategy": strategy,
                    "scenario_id": sc.scenario_id,
                    "gen_id": fa,
                    "pmax_mw": pmax,
                    "t_derate_start_h": ts.t_derate_start_h,
                    "t_trip_h": ts.t_trip_h,
                    "trip_mechanism": ts.trip_mechanism,
                    "p_avail_at_trip_minus_0p2h_mw": round(p_before, 3),
                }
            )

    fields = [
        "strategy",
        "scenario_id",
        "gen_id",
        "t_h",
        "basin_level_m",
        "basin_volume_m3",
        "qcw_frac",
        "p_avail_mw",
        "p_capability_mw",
        "heat_reject_mw_th",
        "backpressure_kpa",
        "t_sat_c",
        "tin_c",
        "tout_c",
        "evaporation_m3s",
        "blowdown_m3s",
        "drift_m3s",
        "water_loss_m3s",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["pmax_mw"], extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {out_csv} ({len(all_rows)} rows)")

    print("\n=== cross-check: operating strategy changes trajectory and trip time ===")
    for sc in scenarios:
        a = evaluate_scenario(sc, timeseries=True, strategy="ride_down").timeseries[sc.faulted_units[0]]
        b = evaluate_scenario(sc, timeseries=True, strategy="hold_load").timeseries[sc.faulted_units[0]]
        dt_min = abs((a.t_trip_h or 0) - (b.t_trip_h or 0)) * 60
        print(
            f"  {sc.scenario_id}: ride_down {a.t_trip_h:.3f} h ({a.trip_mechanism}) vs "
            f"hold_load {b.t_trip_h:.3f} h ({b.trip_mechanism}) -> delta {dt_min:.1f} min"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
