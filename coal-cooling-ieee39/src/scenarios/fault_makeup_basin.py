"""
IEEE39 scenarios: 3 coal wet-recirc units, single-unit makeup-basin interrupt.

Fault definition:
  external water source stops supplying the collecting basin (集水池补水中断).

Scope:
  - only single-unit faults (one of G30 / G34 / G38 per scenario)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cooling.pavail import available_power_mw
from cooling.prototype_500mw import WetRecircPrototype500
from cooling.scale import scale_prototype_to_unit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNITS = ROOT / "data" / "ieee39_unit_config.csv"
DEFAULT_SCENARIOS = ROOT / "data" / "fault_scenarios_makeup_basin.csv"

COAL_WR_IDS = ("G30", "G34", "G38")


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
                )
            )
    return scenarios


def _build_model(unit: UnitConfig) -> WetRecircPrototype500:
    return scale_prototype_to_unit(WetRecircPrototype500(), unit.pmax_mw)


def _apply_makeup_interrupt(
    model: WetRecircPrototype500, param: str, value: float | None
):
    if param != "t_eval_h":
        raise ValueError("makeup_basin_interrupt expects param t_eval_h")
    return model.evaluate_makeup_basin_interrupt(t_eval_h=value)


def evaluate_scenario(
    scenario: ScenarioSpec,
    units: dict[str, UnitConfig] | None = None,
) -> dict[str, Any]:
    """
    Pavail vector under a single-unit makeup-basin interrupt.

    Non-coal / no-cold-end gens keep Pmax.
    Healthy coal WR units stay at design-point Pavail.
    """
    if scenario.n_faulted != 1 or len(scenario.faulted_units) != 1:
        raise ValueError("only single-unit fault scenarios are supported")

    units = units or load_unit_config()
    fault_map = {f["gen_id"]: f for f in scenario.unit_faults}

    pavail: dict[str, float] = {}
    details: dict[str, Any] = {}

    for uid, unit in units.items():
        if not unit.include_cold_end:
            pavail[uid] = unit.pmax_mw
            details[uid] = {
                "status": "no_cold_end",
                "p_avail_mw": unit.pmax_mw,
            }
            continue

        model = _build_model(unit)
        if uid in fault_map:
            f = fault_map[uid]
            result = _apply_makeup_interrupt(model, f["param"], f["value"])
            status = "faulted_makeup_basin"
        else:
            result = model.evaluate()
            status = "healthy_coal_wr"

        p = available_power_mw(result, unit.pmax_mw)
        pavail[uid] = p
        details[uid] = {
            "status": status,
            "cooling_type": unit.cooling_type,
            "source_cluster": unit.source_cluster,
            "p_avail_mw": p,
            "basin_volume_m3": result.basin_volume_m3,
            "basin_vmin_m3": result.basin_vmin_m3,
            "time_to_trip_h": result.time_to_trip_h,
            "backpressure_kpa": result.backpressure_kpa,
            "notes": result.notes,
        }

    faulted = scenario.faulted_units[0]
    lost_mw = units[faulted].pmax_mw - pavail[faulted]
    return {
        "scenario_id": scenario.scenario_id,
        "fault_pattern": scenario.fault_pattern,
        "n_faulted": 1,
        "faulted_units": scenario.faulted_units,
        "capacity_lost_mw": lost_mw,
        "pavail_mw": pavail,
        "unit_details": details,
        "description": scenario.description,
    }
