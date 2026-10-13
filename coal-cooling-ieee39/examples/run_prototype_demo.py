"""Demo: basin makeup interrupt + single coal-unit fault Pavail table."""

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
        f"t_trip={wr.time_to_trip_after_makeup_stop_h():.2f} h"
    )

    r0 = wr.evaluate()
    print(f"healthy Pavail={r0.p_avail_mw:.1f} MW")

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
        out = evaluate_scenario(sc, units)
        faulted = sc.faulted_units[0]
        rows.append(
            {
                "scenario_id": out["scenario_id"],
                "n_faulted": 1,
                "faulted": out["faulted_units"],
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
