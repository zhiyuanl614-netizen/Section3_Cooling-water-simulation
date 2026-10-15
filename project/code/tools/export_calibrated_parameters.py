"""
Regenerate ``data/calibrated_unit_parameters.csv`` from the model itself.

The table is a derived artifact of the plant-calibratable model.  It now
exports the reference/design anchors, tower/condenser calibration quantities,
explicit basin geometry, water-balance components and reference dynamic
outcomes.  ``calibration_status`` is carried through from the unit package:
shipped values are reference templates, not site measurements.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.dynamics import simulate_makeup_interrupt  # noqa: E402
from scenarios import COAL_WR_IDS, load_unit_config, load_unit_params  # noqa: E402
from scenarios.fault_makeup_basin import build_unit_model  # noqa: E402

FIELDS = (
    "gen_id",
    "package",
    "calibration_status",
    "pmax_mw",
    "scale_s",
    "qcw_design_m3s",
    "Qc_mw_th",
    "eta_net_design",
    "approach_design_c",
    "twb_ref_c",
    "ttd_design_c",
    "delta_t_design_c",
    "pb_ref_kpa",
    "pb_ref_source",
    "tower_ntu_design",
    "condenser_UA_mw_per_k",
    "evaporation_m3s",
    "blowdown_m3s",
    "drift_m3s",
    "makeup_m3s",
    "evap_frac_design",
    "CoC",
    "tower_characteristic_mult",
    "condenser_cleanliness",
    "backpressure_sens_per_kpa",
    "backpressure_sens_high_per_kpa",
    "basin_area_m2",
    "basin_level_normal_m",
    "basin_level_trip_m",
    "basin_V0_m3",
    "basin_Vmin_m3",
    "basin_holdup_h_derived",
    "analytic_t_trip_h",
    "pump_npshr_design_m",
    "p_min_tech_frac",
    "pb_trip_kpa",
    "ride_down_t_derate_h",
    "ride_down_t_trip_h",
    "ride_down_mechanism",
    "hold_load_t_trip_h",
    "hold_load_mechanism",
    "source_note",
)


def _fmt(x: float | None, digits: int = 4) -> str:
    if x is None:
        return ""
    return f"{x:.{digits}f}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", default="baseline")
    ap.add_argument("--out", default=str(ROOT / "data" / "calibrated_unit_parameters.csv"))
    args = ap.parse_args()

    units = load_unit_config()
    params = load_unit_params(args.package)

    rows = []
    for uid in COAL_WR_IDS:
        unit = units[uid]
        model = build_unit_model(unit, band="base", params=params)
        p = params.get(uid)
        q = model.heat_reject_mw_th()
        evap, blowdown, drift, makeup = model.water_balance_m3s(
            q, model.qcw_design_m3s, model.design_inlet_c()
        )
        ride = simulate_makeup_interrupt(model, gen_id=uid, strategy="ride_down")
        hold = simulate_makeup_interrupt(model, gen_id=uid, strategy="hold_load")
        rows.append(
            {
                "gen_id": uid,
                "package": args.package,
                "calibration_status": p.calibration_status if p else "prototype_reference",
                "pmax_mw": _fmt(model.p_rated_mw, 1),
                "scale_s": _fmt(model.p_rated_mw / 500.0, 4),
                "qcw_design_m3s": _fmt(model.qcw_design_m3s, 4),
                "Qc_mw_th": _fmt(q, 1),
                "eta_net_design": _fmt(model.eta_net_design, 4),
                "approach_design_c": _fmt(model.approach_design_c, 2),
                "twb_ref_c": _fmt(model.twb_ref_c, 2),
                "ttd_design_c": _fmt(model.ttd_design_c, 2),
                "delta_t_design_c": _fmt(model.design_delta_t_c(), 3),
                "pb_ref_kpa": _fmt(model.reference_backpressure_kpa(), 3),
                "pb_ref_source": (
                    "explicit plant/reference override"
                    if model.pb_ref_kpa is not None
                    else "derived at fixed reference point: tower + condenser chain"
                ),
                "tower_ntu_design": _fmt(model.tower_design_ntu(), 4),
                "condenser_UA_mw_per_k": _fmt(model.condenser_ua_design_mw_per_k(), 3),
                "evaporation_m3s": _fmt(evap, 5),
                "blowdown_m3s": _fmt(blowdown, 5),
                "drift_m3s": _fmt(drift, 5),
                "makeup_m3s": _fmt(makeup, 5),
                "evap_frac_design": _fmt(model.evap_frac, 5),
                "CoC": _fmt(model.cycles_of_concentration, 2),
                "tower_characteristic_mult": _fmt(model.tower_characteristic_mult, 3),
                "condenser_cleanliness": _fmt(model.condenser_cleanliness, 3),
                "backpressure_sens_per_kpa": _fmt(model.backpressure_sens_per_kpa, 4),
                "backpressure_sens_high_per_kpa": _fmt(model.backpressure_sens_high_per_kpa, 4),
                "basin_area_m2": _fmt(model.basin_area_effective_m2(), 1),
                "basin_level_normal_m": _fmt(model.basin_level_normal_m, 3),
                "basin_level_trip_m": _fmt(model.basin_level_trip_m, 3),
                "basin_V0_m3": _fmt(model.basin_design_volume_m3(), 1),
                "basin_Vmin_m3": _fmt(model.basin_vmin_m3(), 1),
                "basin_holdup_h_derived": _fmt(model.basin_holdup_h, 3),
                "analytic_t_trip_h": _fmt(model.time_to_trip_after_makeup_stop_h(), 3),
                "pump_npshr_design_m": _fmt(model.pump_npshr_design_m, 2),
                "p_min_tech_frac": _fmt(model.p_min_tech_frac, 3),
                "pb_trip_kpa": _fmt(model.pb_trip_kpa, 2),
                "ride_down_t_derate_h": _fmt(ride.t_derate_start_h, 3),
                "ride_down_t_trip_h": _fmt(ride.t_trip_h, 3),
                "ride_down_mechanism": ride.trip_mechanism,
                "hold_load_t_trip_h": _fmt(hold.t_trip_h, 3),
                "hold_load_mechanism": hold.trip_mechanism,
                "source_note": p.source_note if p else "",
            }
        )

    out = Path(args.out)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(FIELDS), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows, package={args.package})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
