"""
Calibration utilities for the plant-calibratable cold-end model.

The calibration target is steady or quasi-steady historian data.  Required
row keys are ``p_net_mw``, ``qcw_m3s`` and ``twb_c``; observed outputs may
include ``tin_c``, ``tout_c``, ``pb_kpa`` and ``makeup_m3s``.  Rows should be screened by the
user for steady operation (stable load, pump combination, tower fans and
valve lineup) before fitting.  This module deliberately does not manufacture
plant data: it only evaluates and fits the model against data supplied by
the plant/researcher.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from .prototype_500mw import WetRecircPrototype500

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "data" / "parameter_registry.csv"


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    unit: str
    lower: float
    upper: float
    source_class: str
    calibration_data: str
    identifiability: str


# Bounds are fitting guardrails, not claims that every plant lies inside a
# narrower physical range.  Widen them only with plant-specific evidence.
PARAMETER_SPECS: dict[str, ParameterSpec] = {
    "eta_net_design": ParameterSpec("eta_net_design", "-", 0.30, 0.48, "heat-balance test / manufacturer", "fuel flow, gross/net MW, steam flow", "medium"),
    "partload_heatrate_penalty": ParameterSpec("partload_heatrate_penalty", "-", 0.0, 0.80, "part-load heat-rate test", "P, fuel/steam flow at 40-100% load", "medium"),
    "condenser_waste_heat_frac": ParameterSpec("condenser_waste_heat_frac", "-", 0.80, 0.98, "plant heat balance", "fuel, steam, feedwater and loss split", "low-medium"),
    "qcw_design_m3s": ParameterSpec("qcw_design_m3s", "m3/s", 5.0, 40.0, "pump curve / flow element", "CW flow at reference pump lineup", "high"),
    "approach_design_c": ParameterSpec("approach_design_c", "degC", 2.5, 8.0, "tower design sheet / performance test", "Twb, tower outlet at design range", "high"),
    "ttd_design_c": ParameterSpec("ttd_design_c", "degC", 1.5, 6.0, "condenser design sheet / HEI test", "Tsat, CW outlet at design", "high"),
    "tower_characteristic_mult": ParameterSpec("tower_characteristic_mult", "-", 0.60, 1.50, "tower performance test", "Twb, Tin, Tout, Qcw, fan state", "high"),
    "tower_ntu_exp": ParameterSpec("tower_ntu_exp", "-", 0.0, 1.0, "tower off-design test", "varied CW/air flow points", "medium"),
    "condenser_cleanliness": ParameterSpec("condenser_cleanliness", "-", 0.70, 1.10, "condenser performance test", "Qc, Qcw, Tin, Tout, pb", "high"),
    "condenser_u_flow_exp": ParameterSpec("condenser_u_flow_exp", "-", 0.40, 1.10, "condenser off-design test", "varied CW flow points", "medium"),
    "condenser_air_partial_pressure_kpa": ParameterSpec("condenser_air_partial_pressure_kpa", "kPa", 0.0, 1.0, "vacuum/air-removal assessment", "pb, Tsat, air-removal state", "low"),
    "evap_heat_fraction": ParameterSpec("evap_heat_fraction", "-", 0.65, 0.95, "tower heat/water balance", "makeup, blowdown, Qc, weather", "medium"),
    "drift_frac": ParameterSpec("drift_frac", "-", 0.0, 0.0005, "tower manufacturer / water balance", "circulating flow and total loss", "low"),
    "cycles_of_concentration": ParameterSpec("cycles_of_concentration", "-", 2.0, 8.0, "water chemistry", "makeup/circulating conductivity or silica", "high"),
    "backpressure_sens_per_kpa": ParameterSpec("backpressure_sens_per_kpa", "1/kPa", 0.003, 0.015, "turbine manufacturer correction curve", "P versus pb near reference", "high"),
    "backpressure_sens_high_per_kpa": ParameterSpec("backpressure_sens_high_per_kpa", "1/kPa", 0.005, 0.030, "turbine manufacturer correction curve", "P versus pb at high backpressure", "medium"),
    "basin_area_m2": ParameterSpec("basin_area_m2", "m2", 50.0, 20000.0, "civil drawing / level-volume table", "level and inventory survey", "high (geometry)"),
    "pump_npshr_design_m": ParameterSpec("pump_npshr_design_m", "m", 3.0, 20.0, "pump manufacturer curve", "NPSHr versus flow", "high"),
    "pump_design_head_m": ParameterSpec("pump_design_head_m", "m", 8.0, 45.0, "pump manufacturer curve", "head versus flow", "high"),
    "pump_static_lift_design_m": ParameterSpec("pump_static_lift_design_m", "m", 3.0, 35.0, "system elevation survey", "basin/discharge elevations", "high (geometry)"),
    "tower_tau_s": ParameterSpec("tower_tau_s", "s", 30.0, 1800.0, "dynamic historian fit", "step/load-change transients", "medium"),
    "condenser_tau_s": ParameterSpec("condenser_tau_s", "s", 10.0, 600.0, "dynamic historian fit", "load/CW-flow transients", "medium"),
}


@dataclass
class CalibrationResult:
    model: WetRecircPrototype500
    parameters: list[str]
    initial_metrics: dict[str, float]
    final_metrics: dict[str, float]
    history: list[dict[str, Any]]


def load_parameter_registry(path: Path | str = DEFAULT_REGISTRY) -> list[dict[str, str]]:
    """Load the human-readable parameter registry shipped with the model."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_historian_csv(path: Path | str) -> list[dict[str, float]]:
    """Load historian rows and validate the minimum calibration schema."""
    required = {"p_net_mw", "qcw_m3s", "twb_c"}
    rows: list[dict[str, float]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"historian data missing required columns {sorted(missing)}")
        for i, raw in enumerate(reader, start=2):
            row: dict[str, float] = {}
            for key, value in raw.items():
                if value is None or str(value).strip() == "":
                    continue
                try:
                    row[key] = float(value)
                except ValueError:
                    # Non-numeric metadata columns are ignored by the fitter.
                    continue
            if not required <= set(row):
                raise ValueError(f"historian row {i} lacks required numeric values")
            rows.append(row)
    if not rows:
        raise ValueError("historian data contains no rows")
    return rows


def _metrics_for_rows(model: WetRecircPrototype500, rows: Iterable[dict[str, float]]) -> dict[str, float]:
    rows = list(rows)
    residuals: dict[str, list[float]] = {
        "tin_c": [], "tout_c": [], "pb_kpa": [], "makeup_m3s": []
    }
    for row in rows:
        pred = model.predict_cold_end(
            row["p_net_mw"],
            qcw_m3s=row["qcw_m3s"],
            twb_c=row["twb_c"],
            airflow_ratio=row.get("airflow_ratio", 1.0),
        )
        if "tin_c" in row:
            residuals["tin_c"].append(pred.tin_c - row["tin_c"])
        if "tout_c" in row:
            residuals["tout_c"].append(pred.tout_c - row["tout_c"])
        if "pb_kpa" in row:
            residuals["pb_kpa"].append(pred.backpressure_kpa - row["pb_kpa"])
        if "makeup_m3s" in row:
            residuals["makeup_m3s"].append(pred.makeup_m3s - row["makeup_m3s"])

    out: dict[str, float] = {"n_rows": float(len(rows))}
    weighted_sq: list[float] = []
    for key, values in residuals.items():
        prefix = key.replace("_c", "").replace("_kpa", "")
        if values:
            rmse = math.sqrt(sum(v * v for v in values) / len(values))
            mae = sum(abs(v) for v in values) / len(values)
            bias = sum(values) / len(values)
            # Normalisation scales: 0.5 degC / 0.5 kPa / 0.02 m3/s.
            scale = 0.02 if key == "makeup_m3s" else 0.5
            weighted_sq.extend((v / scale) ** 2 for v in values)
        else:
            rmse = mae = bias = float("nan")
        out[f"{prefix}_rmse"] = rmse
        out[f"{prefix}_mae"] = mae
        out[f"{prefix}_bias"] = bias
        out[f"{prefix}_n"] = float(len(values))
    out["objective"] = math.sqrt(sum(weighted_sq) / len(weighted_sq)) if weighted_sq else float("inf")
    return out


def calibration_metrics(model: WetRecircPrototype500, rows: Iterable[dict[str, float]]) -> dict[str, float]:
    """RMSE/MAE/bias for Tin, Tout, condenser pressure and makeup demand."""
    return _metrics_for_rows(model, rows)


def _set_param(model: WetRecircPrototype500, name: str, value: float) -> WetRecircPrototype500:
    return replace(model, **{name: float(value)})


def calibrate_model(
    model: WetRecircPrototype500,
    rows: list[dict[str, float]],
    parameters: list[str],
    *,
    max_sweeps: int = 12,
) -> CalibrationResult:
    """
    Fit selected parameters by bounded coordinate descent.

    The method is intentionally dependency-free and transparent.  It is a
    screening/calibration engine, not a replacement for plant engineering
    review or a Bayesian uncertainty analysis.  Fit on one historian period
    and validate on a separate period before accepting parameters.
    """
    if not parameters:
        raise ValueError("at least one calibration parameter is required")
    unknown = [p for p in parameters if p not in PARAMETER_SPECS]
    if unknown:
        raise ValueError(f"parameters not registered for calibration: {unknown}")
    for p in parameters:
        if not hasattr(model, p):
            raise ValueError(f"model has no parameter {p!r}")

    current = model
    initial = calibration_metrics(current, rows)
    best_obj = initial["objective"]
    history: list[dict[str, Any]] = [{"sweep": 0, "objective": best_obj}]
    steps = {
        p: (PARAMETER_SPECS[p].upper - PARAMETER_SPECS[p].lower) * 0.08 for p in parameters
    }

    for sweep in range(1, max_sweeps + 1):
        improved = False
        for p in parameters:
            spec = PARAMETER_SPECS[p]
            current_value = float(getattr(current, p))
            candidates = [current_value]
            for direction in (-1.0, 1.0):
                candidates.append(min(spec.upper, max(spec.lower, current_value + direction * steps[p])))
            best_candidate = current_value
            best_candidate_obj = best_obj
            for value in candidates:
                if value == current_value:
                    continue
                trial = _set_param(current, p, value)
                obj = calibration_metrics(trial, rows)["objective"]
                if obj < best_candidate_obj - 1e-12:
                    best_candidate_obj = obj
                    best_candidate = value
            if best_candidate != current_value:
                current = _set_param(current, p, best_candidate)
                best_obj = best_candidate_obj
                improved = True
        history.append({"sweep": sweep, "objective": best_obj})
        if not improved:
            for p in parameters:
                steps[p] *= 0.5
            if max(steps.values()) < 1e-9:
                break

    return CalibrationResult(
        model=current,
        parameters=list(parameters),
        initial_metrics=initial,
        final_metrics=calibration_metrics(current, rows),
        history=history,
    )
