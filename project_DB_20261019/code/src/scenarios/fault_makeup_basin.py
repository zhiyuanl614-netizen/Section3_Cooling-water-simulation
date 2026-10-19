"""
IEEE39 scenarios: 2 mapped coal wet-recirc units, single-unit makeup-basin
interrupt.

Fault definition:
  external water source stops supplying the collecting basin (集水池补水中断).

Scope (hard-enforced):
  - only single-unit faults (G33 at bus 33 or G34 at bus 34 per scenario)
  - only wet_recirc cold ends
  - only the makeup_basin_interrupt fault mode

Two evaluation depths are available:
  * level A (default): steady-state snapshot / terminal state, as before.
  * mechanism-resolved: pass ``timeseries=True`` to run the basin-drain
    integration of ``cooling.dynamics`` and hand the grid a Pavail(t) curve
    instead of a binary MW step.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from cooling.dynamics import (
    RIDE_DOWN,
    LoadStrategy,
    TimeseriesResult,
    simulate_makeup_interrupt,
)
from cooling.pavail import available_power_mw
from cooling.prototype_500mw import UncertaintyBand, WetRecircPrototype500, band_factors
from cooling.scale import scale_prototype_to_unit
from scenarios.unit_params import (
    UnitIntensiveParams,
    apply_plant_unit_params,
    apply_thermal_unit_params,
    load_unit_params,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNITS = ROOT / "data" / "ieee39_unit_config.csv"
DEFAULT_SCENARIOS = ROOT / "data" / "fault_scenarios_makeup_basin.csv"

COAL_WR_IDS = ("G33", "G34")
DEFAULT_PACKAGE = "baseline"


@dataclass
class UnitConfig:
    gen_id: str
    bus: int
    pmax_mw: float
    pmin_mw: float
    is_slack: bool
    fuel: str
    cooling_type: str
    source_cluster: str
    include_cold_end: bool


@dataclass
class ScenarioSpec:
    scenario_id: str
    n_faulted: int
    fault_pattern: str
    faulted_units: list[str]
    unit_faults: list[dict[str, Any]]
    description: str
    band: UncertaintyBand = "base"


@dataclass
class ScenarioResult:
    """Everything a downstream (grid) model needs from one scenario."""

    scenario_id: str
    fault_pattern: str
    n_faulted: int
    faulted_units: list[str]
    capacity_lost_mw: float
    pavail_mw: dict[str, float]
    unit_details: dict[str, Any]
    description: str
    band: str = "base"
    package: str = DEFAULT_PACKAGE
    timeseries: dict[str, TimeseriesResult] = field(default_factory=dict)

    def as_dict(self, include_timeseries_rows: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "fault_pattern": self.fault_pattern,
            "n_faulted": self.n_faulted,
            "faulted_units": self.faulted_units,
            "capacity_lost_mw": self.capacity_lost_mw,
            "pavail_mw": self.pavail_mw,
            "unit_details": self.unit_details,
            "description": self.description,
            "band": self.band,
            "package": self.package,
        }
        if include_timeseries_rows:
            out["timeseries_rows"] = {
                gid: ts.rows() for gid, ts in self.timeseries.items()
            }
        return out

    def __getitem__(self, key: str) -> Any:
        """Dict-like access so existing scripts keep working."""
        if key in ("timeseries",):
            return self.timeseries
        return self.as_dict()[key]

    def keys(self):  # pragma: no cover - convenience
        return self.as_dict().keys()


def load_unit_config(path: Path | str = DEFAULT_UNITS) -> dict[str, UnitConfig]:
    units: dict[str, UnitConfig] = {}
    coal_wr: list[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid = row["gen_id"]
            cooling = row["cooling_type"].strip()
            include = row["include_cold_end"].strip() == "1"
            if include:
                if cooling != "wet_recirc":
                    raise ValueError(f"{uid}: cold-end must be wet_recirc")
                if row["fuel"].strip() != "coal":
                    raise ValueError(f"{uid}: cold-end unit must be coal")
                coal_wr.append(uid)
            units[uid] = UnitConfig(
                gen_id=uid,
                bus=int(row["bus"]),
                pmax_mw=float(row["pmax_mw"]),
                pmin_mw=float(row["pmin_mw"]),
                is_slack=row["is_slack"].strip() == "1",
                fuel=row["fuel"].strip(),
                cooling_type=cooling,
                source_cluster=row["source_cluster"],
                include_cold_end=include,
            )
    if sorted(coal_wr) != sorted(COAL_WR_IDS):
        raise ValueError(
            f"expected exactly coal WR units {COAL_WR_IDS}, got {tuple(coal_wr)}"
        )
    return units


def _parse_optional_float(s: str | None) -> float | None:
    if s is None or str(s).strip() == "":
        return None
    return float(s)


def load_scenarios(path: Path | str = DEFAULT_SCENARIOS) -> list[ScenarioSpec]:
    scenarios: list[ScenarioSpec] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            units = [u for u in row["faulted_units"].split("|") if u]
            n = int(row["n_faulted"])
            if n != 1:
                raise ValueError(
                    f"{row['scenario_id']}: only single-unit faults allowed (n_faulted=1)"
                )
            if len(units) != 1:
                raise ValueError(
                    f"{row['scenario_id']}: faulted_units must contain exactly one unit"
                )
            if units[0] not in COAL_WR_IDS:
                raise ValueError(f"{row['scenario_id']}: {units[0]} is not a coal WR unit")

            mode = row["unit1_fault_mode"].strip()
            if mode != "makeup_basin_interrupt":
                raise ValueError(
                    f"{row['scenario_id']}: only makeup_basin_interrupt allowed"
                )

            band = (row.get("band") or "base").strip() or "base"
            band_factors(band)  # validates

            scenarios.append(
                ScenarioSpec(
                    scenario_id=row["scenario_id"],
                    n_faulted=1,
                    fault_pattern=row["fault_pattern"],
                    faulted_units=units,
                    unit_faults=[
                        {
                            "gen_id": units[0],
                            "mode": mode,
                            "param": row["unit1_param"].strip(),
                            "value": _parse_optional_float(row["unit1_value"]),
                        }
                    ],
                    description=row["description"],
                    band=band,  # type: ignore[arg-type]
                )
            )
    return scenarios


def build_unit_model(
    unit: UnitConfig,
    *,
    band: UncertaintyBand = "base",
    params: dict[str, UnitIntensiveParams] | None = None,
) -> WetRecircPrototype500:
    """Thermal anchors -> capacity scaling -> plant anchors, in that order."""
    model = WetRecircPrototype500(band=band, gen_id=unit.gen_id)
    p = params.get(unit.gen_id) if params else None
    if p is not None:
        model = apply_thermal_unit_params(model, p)
    model = scale_prototype_to_unit(model, unit.pmax_mw, gen_id=unit.gen_id)
    if p is not None:
        model = apply_plant_unit_params(model, p)
    return model


def _apply_makeup_interrupt(
    model: WetRecircPrototype500, param: str, value: float | None
):
    if param != "t_eval_h":
        raise ValueError("makeup_basin_interrupt expects param t_eval_h")
    return model.evaluate_makeup_basin_interrupt(t_eval_h=value)


def evaluate_scenario(
    scenario: ScenarioSpec,
    units: dict[str, UnitConfig] | None = None,
    *,
    package: str = DEFAULT_PACKAGE,
    params: dict[str, UnitIntensiveParams] | None = None,
    timeseries: bool = False,
    strategy: LoadStrategy = RIDE_DOWN,
    dyn_kwargs: dict[str, Any] | None = None,
) -> ScenarioResult:
    """
    Pavail vector under a single-unit makeup-basin interrupt.

    Non-coal / no-cold-end gens keep Pmax.  Healthy coal WR units stay at their
    design-point Pavail (which is now exactly Pmax, see the design-point
    closure in ``cooling.prototype_500mw``).

    With ``timeseries=True`` the faulted unit is simulated with the basin-drain
    dynamics and the returned object also carries ``timeseries[gen_id]`` -- a
    Pavail(t) trajectory for the grid model.
    """
    if scenario.n_faulted != 1 or len(scenario.faulted_units) != 1:
        raise ValueError("only single-unit fault scenarios are supported")

    units = units or load_unit_config()
    site_params = params if params is not None else load_unit_params(package)
    fault_map = {f["gen_id"]: f for f in scenario.unit_faults}

    pavail: dict[str, float] = {}
    details: dict[str, Any] = {}
    ts_out: dict[str, TimeseriesResult] = {}

    for uid, unit in units.items():
        if not unit.include_cold_end:
            pavail[uid] = unit.pmax_mw
            details[uid] = {
                "status": "no_cold_end",
                "p_avail_mw": unit.pmax_mw,
            }
            continue

        model = build_unit_model(unit, band=scenario.band, params=site_params)

        if uid in fault_map:
            f = fault_map[uid]
            if f["param"] != "t_eval_h":
                raise ValueError("makeup_basin_interrupt expects param t_eval_h")
            t_eval = f["value"]
            if timeseries:
                ts = simulate_makeup_interrupt(
                    model, gen_id=uid, strategy=strategy, **(dyn_kwargs or {})
                )
                ts_out[uid] = ts
                p = 0.0 if t_eval is None else ts.p_avail_at(t_eval)
                status = "faulted_makeup_basin"
                details[uid] = {
                    "status": status,
                    "cooling_type": unit.cooling_type,
                    "source_cluster": unit.source_cluster,
                    "p_avail_mw": float(max(0.0, min(unit.pmax_mw, p))),
                    "t_derate_start_h": ts.t_derate_start_h,
                    "time_to_trip_h": ts.t_trip_h,
                    "trip_mechanism": ts.trip_mechanism,
                    "trip_detail": None if ts.trip is None else ts.trip.detail,
                    "strategy": ts.strategy,
                    "loss_basis": ts.loss_basis,
                    "pb_design_kpa": model.reference_backpressure_kpa(),
                    "pb_ref_kpa": model.reference_backpressure_kpa(),
                    "calibration_status": (site_params.get(uid).calibration_status if site_params.get(uid) else "prototype_reference"),
                    "basin_area_m2": model.basin_area_effective_m2(),
                    "basin_level_normal_m": model.basin_level_normal_m,
                    "basin_level_min_m": model.basin_level_min_m(),
                    "basin_holdup_h_derived": model.basin_holdup_h,
                    "basin_volume_m3": model.basin_design_volume_m3(),
                    "basin_vmin_m3": model.basin_vmin_m3(),
                    "notes": "dynamics: plant-calibratable basin drain with cold end, pump and SOP/protection logic",
                }
                p = details[uid]["p_avail_mw"]
            else:
                result = _apply_makeup_interrupt(model, f["param"], t_eval)
                p = available_power_mw(result, unit.pmax_mw)
                details[uid] = {
                    "status": "faulted_makeup_basin",
                    "cooling_type": unit.cooling_type,
                    "source_cluster": unit.source_cluster,
                    "p_avail_mw": p,
                    "basin_volume_m3": result.basin_volume_m3,
                    "basin_vmin_m3": result.basin_vmin_m3,
                    "basin_level_m": result.basin_level_m,
                    "time_to_trip_h": result.time_to_trip_h,
                    "backpressure_kpa": result.backpressure_kpa,
                    "pb_design_kpa": model.reference_backpressure_kpa(),
                    "pb_ref_kpa": model.reference_backpressure_kpa(),
                    "calibration_status": (site_params.get(uid).calibration_status if site_params.get(uid) else "prototype_reference"),
                    "basin_area_m2": model.basin_area_effective_m2(),
                    "basin_level_normal_m": model.basin_level_normal_m,
                    "basin_level_min_m": model.basin_level_min_m(),
                    "basin_holdup_h_derived": model.basin_holdup_h,
                    "notes": result.notes,
                }
        else:
            result = model.evaluate()
            p = available_power_mw(result, unit.pmax_mw)
            details[uid] = {
                "status": "healthy_coal_wr",
                "cooling_type": unit.cooling_type,
                "source_cluster": unit.source_cluster,
                "p_avail_mw": p,
                "basin_volume_m3": result.basin_volume_m3,
                "basin_vmin_m3": result.basin_vmin_m3,
                "basin_level_m": result.basin_level_m,
                "time_to_trip_h": result.time_to_trip_h,
                "backpressure_kpa": result.backpressure_kpa,
                "pb_design_kpa": model.reference_backpressure_kpa(),
                "pb_ref_kpa": model.reference_backpressure_kpa(),
                "calibration_status": (site_params.get(uid).calibration_status if site_params.get(uid) else "prototype_reference"),
                "basin_area_m2": model.basin_area_effective_m2(),
                "basin_level_normal_m": model.basin_level_normal_m,
                "basin_level_min_m": model.basin_level_min_m(),
                "basin_holdup_h_derived": model.basin_holdup_h,
                "notes": result.notes,
            }

        pavail[uid] = p

    faulted = scenario.faulted_units[0]
    lost_mw = units[faulted].pmax_mw - pavail[faulted]
    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        fault_pattern=scenario.fault_pattern,
        n_faulted=1,
        faulted_units=scenario.faulted_units,
        capacity_lost_mw=lost_mw,
        pavail_mw=pavail,
        unit_details=details,
        description=scenario.description,
        band=scenario.band,
        package=package,
        timeseries=ts_out,
    )
