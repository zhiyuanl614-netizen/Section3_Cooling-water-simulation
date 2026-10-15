"""
U1 one-at-a-time sensitivity for framework v0.3 (A4).

Perturbs maintenance-state and inventory parameters around the 600 MW Bus33
archetype.  Reports trip time / final power / cascade flag changes.
Not a plant posterior — scenario ranges only.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cooling.dynamics import simulate_cold_end  # noqa: E402
from cooling.prototype_500mw import WetRecircPrototype500  # noqa: E402
from cooling.scale import scale_prototype_to_unit  # noqa: E402
from grid.cascade import IEEE39CascadeGrid  # noqa: E402

OUT = ROOT / "examples" / "u1_sensitivity_summary.csv"

# A4 core + inventory/protection modulators that matter for S1/S2 narratives.
PERTURBATIONS = [
    ("tower_characteristic_mult", 0.85, 1.15),
    ("condenser_cleanliness", 0.88, 1.06),
    ("evap_heat_fraction", 0.74, 0.90),
    ("basin_area_m2_scale", 0.85, 1.15),  # applied as multiplier on scaled area
    ("pb_trip_kpa", 12.0, 20.0),
]

CASES = [
    ("S1a", dict(fault_type="makeup_interrupt", strategy="ride_down",
                 blowdown_policy="isolate_on_detection", t_max_h=12.0, sample_every_s=60.0)),
    ("S2", dict(fault_type="pump_failure", strategy="hold_load", pump_loss_frac=1.0,
                t_max_h=1.0, sample_every_s=1.0)),
    ("S3a", dict(fault_type="pump_failure", strategy="ride_down", pump_loss_frac=0.5,
                 t_max_h=1.0, sample_every_s=10.0)),
]


def _base_model() -> WetRecircPrototype500:
    return scale_prototype_to_unit(WetRecircPrototype500(), 600.0, gen_id="Bus33")


def _apply(name: str, value: float, model: WetRecircPrototype500) -> WetRecircPrototype500:
    if name == "basin_area_m2_scale":
        return replace(model, basin_area_m2=model.basin_area_m2 * value)
    return replace(model, **{name: value})


def _eval_unit(model: WetRecircPrototype500, kwargs: dict) -> dict:
    ts = simulate_cold_end(model, **kwargs)
    p_final = 0.0 if ts.trip is not None else float(ts.p_avail_mw[-1])
    return {
        "t_trip_h": ts.t_trip_h,
        "t_trip_min": None if ts.t_trip_h is None else ts.t_trip_h * 60.0,
        "trip_mechanism": ts.trip_mechanism,
        "p_final_mw": p_final,
    }


def _cascade_dual(p33: float, p34: float) -> dict:
    grid = IEEE39CascadeGrid()
    pg = {int(g["bus"]): float(g["Pg"]) for g in grid.generators}
    pg[33] = p33
    pg[34] = p34
    casc = grid.solve_cascade(pg)
    return {
        "cascade_triggered": casc.cascade_triggered,
        "n_lines_removed": casc.n_removed,
    }


def main() -> None:
    rows: list[dict] = []
    base = _base_model()

    for case_id, kwargs in CASES:
        base_out = _eval_unit(base, kwargs)
        rows.append({
            "case_id": case_id,
            "param": "baseline",
            "level": "base",
            "value": "",
            **{k: _fmt(base_out[k]) for k in base_out},
            "cascade_triggered": "",
            "n_lines_removed": "",
            "delta_t_trip_min": "",
            "delta_p_final_mw": "",
        })
        for name, lo, hi in PERTURBATIONS:
            for level, val in (("low", lo), ("high", hi)):
                m = _apply(name, val, base)
                out = _eval_unit(m, kwargs)
                dt = ""
                if base_out["t_trip_min"] is not None and out["t_trip_min"] is not None:
                    dt = round(out["t_trip_min"] - base_out["t_trip_min"], 3)
                dp = round(out["p_final_mw"] - base_out["p_final_mw"], 2)
                rows.append({
                    "case_id": case_id,
                    "param": name,
                    "level": level,
                    "value": val,
                    **{k: _fmt(out[k]) for k in out},
                    "cascade_triggered": "",
                    "n_lines_removed": "",
                    "delta_t_trip_min": dt,
                    "delta_p_final_mw": dp,
                })

    # G2 cascade robustness: both units at 0 vs both at S3a final power.
    s3 = _eval_unit(base, CASES[2][1])
    for label, p33, p34 in (
        ("G2_both_trip", 0.0, 0.0),
        ("G2_both_S3a_derate", s3["p_final_mw"], s3["p_final_mw"] * 508.0 / 600.0),
        ("G1_only_33_trip", 0.0, 508.0),
    ):
        casc = _cascade_dual(p33, p34)
        rows.append({
            "case_id": label,
            "param": "cascade_probe",
            "level": "n/a",
            "value": "",
            "t_trip_h": "",
            "t_trip_min": "",
            "trip_mechanism": "",
            "p_final_mw": "",
            "cascade_triggered": casc["cascade_triggered"],
            "n_lines_removed": casc["n_lines_removed"],
            "delta_t_trip_min": "",
            "delta_p_final_mw": "",
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} rows)")


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return round(v, 4)
    return v


if __name__ == "__main__":
    main()
