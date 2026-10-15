"""
Demo: basin makeup interrupt + single coal-unit fault Pavail table.

Level-A (steady-state) view.  For the mechanism-resolved trajectory see
``run_timeseries_demo.py``; for grid impact see ``run_grid_impact_demo.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling import WetRecircPrototype500  # noqa: E402
from scenarios import (  # noqa: E402
    COAL_WR_IDS,
    evaluate_scenario,
    load_scenarios,
    load_unit_config,
)


def demo_basin() -> None:
    wr = WetRecircPrototype500()
    print("=== 500 MW wet-recirc + collecting basin ===")
    print(
        f"V0={wr.basin_design_volume_m3():.0f} m3  "
        f"Vmin={wr.basin_vmin_m3():.0f} m3  "
        f"level_min={wr.basin_level_min_m():.2f} m  "
        f"t_trip={wr.time_to_trip_after_makeup_stop_h():.2f} h"
    )

    r0 = wr.evaluate()
    print(
        f"reference point: pb_ref={r0.pb_design_kpa:.3f} kPa (fixed reference chain), "
        f"Pavail={r0.p_avail_mw:.6f} MW (rated {wr.p_rated_mw:.0f} MW)"
    )
    print(
        f"water balance: E={r0.evaporation_m3s:.4f} m3/s, "
        f"B={r0.blowdown_m3s:.4f}, D={r0.drift_m3s:.5f}, M={r0.makeup_m3s:.4f}; "
        f"derived holdup={wr.basin_holdup_h:.2f} h"
    )
    print("calibration status: reference template -- NOT a site-measured plant calibration")

    r_mid = wr.evaluate_makeup_basin_interrupt(t_eval_h=2.0)
    print(f"t=2 h after makeup stop: Pavail={r_mid.p_avail_mw:.1f} MW  ({r_mid.notes})")

    r_end = wr.evaluate_makeup_basin_interrupt(t_eval_h=None)
    print(f"terminal (basin trip): Pavail={r_end.p_avail_mw:.1f} MW  ({r_end.notes})")


def demo_scenarios() -> None:
    units = load_unit_config()
    scenarios = load_scenarios()
    print(f"\n=== Coal WR units: {COAL_WR_IDS} ===")
    print("=== Makeup-basin interrupt: single-unit faults only ===")
    rows = []
    for sc in scenarios:
        out = evaluate_scenario(sc)
        faulted = sc.faulted_units[0]
        rows.append(
            {
                "scenario_id": out["scenario_id"],
                "n_faulted": 1,
                "faulted": out["faulted_units"],
                "band": out.band,
                "package": out.package,
                "capacity_lost_mw": round(out["capacity_lost_mw"], 1),
                "fault_pavail_mw": {faulted: round(out["pavail_mw"][faulted], 1)},
                "time_to_trip_h": {
                    faulted: round(out["unit_details"][faulted]["time_to_trip_h"], 2)
                },
            }
        )
        print(
            f"{out['scenario_id']:14s}  "
            f"lost={out['capacity_lost_mw']:7.1f} MW  "
            f"pavail[{faulted}]={out['pavail_mw'][faulted]:.1f}  "
            f"t_trip_h={out['unit_details'][faulted]['time_to_trip_h']:.2f}"
        )

    out_path = ROOT / "examples" / "scenario_pavail_summary.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    demo_basin()
    demo_scenarios()
