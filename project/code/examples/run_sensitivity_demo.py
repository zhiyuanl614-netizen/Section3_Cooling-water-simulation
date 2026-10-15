"""
Demo: uncertainty-band envelope and plant-calibration template packages.

Produces ``examples/pavail_envelope_band.csv`` and a one-at-a-time
``examples/parameter_sensitivity.csv`` for the 500 MW reference prototype.
All shipped unit values are reference templates, not site-measured plant
calibrations.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import replace as dc_replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.dynamics import simulate_makeup_interrupt  # noqa: E402
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from scenarios import evaluate_scenario, load_scenarios, load_unit_params  # noqa: E402


def main() -> int:
    scenarios = {sc.faulted_units[0]: sc for sc in load_scenarios()}
    rows: list[dict] = []

    print("=== uncertainty band envelope (package = baseline) ===")
    print(f"{'unit':6s} {'band':6s} {'t_trip(h)':>10s} {'mechanism':>24s} {'P@4.5h':>8s}")
    for uid, sc in scenarios.items():
        for band in ("low", "base", "high"):
            out = evaluate_scenario(dc_replace(sc, band=band), timeseries=True)
            ts = out.timeseries[uid]
            p45 = ts.p_avail_at(4.5)
            print(f"{uid:6s} {band:6s} {ts.t_trip_h:10.3f} {ts.trip_mechanism:>24s} {p45:8.1f}")
            rows.append(
                {
                    "scenario_id": sc.scenario_id,
                    "gen_id": uid,
                    "package": "baseline",
                    "band": band,
                    "t_trip_h": ts.t_trip_h,
                    "trip_mechanism": ts.trip_mechanism,
                    "p_avail_at_4p5h_mw": round(p45, 3),
                    "pb_ref_kpa": round(float(out.unit_details[uid]["pb_ref_kpa"]), 3),
                }
            )

    print("\n=== plant-calibration template package (band = base) ===")
    print(
        f"{'unit':6s} {'TwbRef':>7s} {'Area':>8s} {'CoC':>5s} "
        f"{'t_trip(h)':>10s} {'mechanism':>24s}"
    )
    params = load_unit_params("regional")
    for uid, sc in scenarios.items():
        out = evaluate_scenario(sc, package="regional", timeseries=True)
        ts = out.timeseries[uid]
        p = params[uid]
        print(
            f"{uid:6s} {p.twb_ref_c:7.1f} {p.basin_area_m2:8.0f} {p.cycles_of_concentration:5.1f} "
            f"{ts.t_trip_h:10.3f} {ts.trip_mechanism:>24s}"
        )
        rows.append(
            {
                "scenario_id": sc.scenario_id,
                "gen_id": uid,
                "package": "regional",
                "band": "base",
                "t_trip_h": ts.t_trip_h,
                "trip_mechanism": ts.trip_mechanism,
                "p_avail_at_4p5h_mw": round(ts.p_avail_at(4.5), 3),
                "pb_ref_kpa": round(float(out.unit_details[uid]["pb_ref_kpa"]), 3),
            }
        )

    print("\n=== one-at-a-time parameter sensitivity (500 MW prototype) ===")
    base = WetRecircPrototype500()
    oat_cases: list[tuple[str, WetRecircPrototype500, dict]] = [("base", base, {})]
    for name, updates in [
        ("tower_mult_0.85", {"tower_characteristic_mult": 0.85}),
        ("tower_mult_1.15", {"tower_characteristic_mult": 1.15}),
        ("cond_clean_0.90", {"condenser_cleanliness": 0.90}),
        ("cond_clean_1.05", {"condenser_cleanliness": 1.05}),
        ("basin_area_x0.85", {"basin_area_m2": base.basin_area_m2 * 0.85}),
        ("basin_area_x1.15", {"basin_area_m2": base.basin_area_m2 * 1.15}),
        ("evap_frac_0.74", {"evap_heat_fraction": 0.74}),
        ("evap_frac_0.90", {"evap_heat_fraction": 0.90}),
        ("coc_3", {"cycles_of_concentration": 3.0}),
        ("coc_5", {"cycles_of_concentration": 5.0}),
        ("npshr_6.4", {"pump_npshr_design_m": 6.4}),
        ("npshr_9.6", {"pump_npshr_design_m": 9.6}),
        ("sop_start_1.5", {"operator_shed_start_level_m": 1.5}),
        ("sop_start_2.5", {"operator_shed_start_level_m": 2.5}),
        ("pmin_0.35", {"p_min_tech_frac": 0.35}),
        ("pmin_0.45", {"p_min_tech_frac": 0.45}),
        ("pb_trip_12", {"pb_trip_kpa": 12.0}),
        ("pb_trip_18", {"pb_trip_kpa": 18.0}),
    ]:
        oat_cases.append((name, dc_replace(base, **updates), {}))
    oat_cases.extend([
        ("twb_op_18", base, {"twb_op_c": 18.0}),
        ("twb_op_28", base, {"twb_op_c": 28.0}),
        ("airflow_0.9", base, {"airflow_ratio": 0.9}),
        ("airflow_1.1", base, {"airflow_ratio": 1.1}),
    ])
    oat_rows: list[dict] = []
    for name, model, dyn_kw in oat_cases:
        snap = model.evaluate(
            twb_c=dyn_kw.get("twb_op_c", model.twb_ref_c),
            airflow_ratio=dyn_kw.get("airflow_ratio", 1.0),
        )
        row = {
            "case": name,
            "pb_ref_kpa": round(model.reference_backpressure_kpa(), 4),
            "rated_eval_pb_kpa": round(snap.backpressure_kpa, 4),
            "rated_eval_p_mw": round(snap.p_avail_mw, 2),
            "design_makeup_m3s": round(model.makeup_m3s(model.qcw_design_m3s), 5),
            "derived_holdup_h": round(model.basin_holdup_h, 4),
        }
        for strategy in ("ride_down", "hold_load"):
            ts = simulate_makeup_interrupt(model, strategy=strategy, **dyn_kw)
            row[f"{strategy}_derate_h"] = ts.t_derate_start_h
            row[f"{strategy}_trip_h"] = ts.t_trip_h
            row[f"{strategy}_mech"] = ts.trip_mechanism
        oat_rows.append(row)
        print(
            f"{name:20s} ride={row['ride_down_trip_h']:.3f} h ({row['ride_down_mech']}), "
            f"hold={row['hold_load_trip_h']:.3f} h ({row['hold_load_mech']})"
        )
    oat_csv = ROOT / "examples" / "parameter_sensitivity.csv"
    with open(oat_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(oat_rows[0]))
        w.writeheader()
        w.writerows(oat_rows)
    print(f"wrote {oat_csv} ({len(oat_rows)} rows)")

    out_csv = ROOT / "examples" / "pavail_envelope_band.csv"
    fields = [
        "package",
        "band",
        "scenario_id",
        "gen_id",
        "t_trip_h",
        "trip_mechanism",
        "p_avail_at_4p5h_mw",
        "pb_ref_kpa",
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out_csv} ({len(rows)} rows)")
    print("Note: packages are calibration templates; regional values are climate-zone representatives, not plant fits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
