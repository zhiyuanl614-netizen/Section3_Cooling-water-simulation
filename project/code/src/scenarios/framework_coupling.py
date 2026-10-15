"""
Framework v0.3 scenario registry and cold-end → IEEE39 cascade coupling.

Maps literature-anchored contingencies (S/G/C) onto scaled 500 MW prototypes
and evaluates the cascading outlet when unit outputs collapse.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from cooling.dynamics import TimeseriesResult, simulate_cold_end
from cooling.prototype_500mw import WetRecircPrototype500
from cooling.scale import scale_prototype_to_unit
from grid.cascade import CascadeResult, IEEE39CascadeGrid

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "data" / "framework_scenarios_v03.csv"

Strategy = Literal["ride_down", "hold_load"]
Blowdown = Literal["isolate_on_detection", "maintain"]


@dataclass
class FrameworkScenario:
    scenario_id: str
    family: str
    fault_type: str
    primary_bus: int
    primary_mw: float
    secondary_bus: int | None
    secondary_mw: float | None
    pump_loss_frac: float
    twb_rise_c: float
    blowdown_policy: Blowdown
    strategy: Strategy
    quasi_static: bool
    t_max_h: float
    description: str


@dataclass
class CoupledUnitResult:
    bus: int
    p_rated_mw: float
    fault_type: str
    timeseries: TimeseriesResult
    p_final_mw: float
    t_trip_h: float | None
    trip_mechanism: str


@dataclass
class FrameworkRunResult:
    scenario: FrameworkScenario
    units: list[CoupledUnitResult]
    cascade: CascadeResult | None
    base_pg: dict[int, float] = field(default_factory=dict)
    final_pg: dict[int, float] = field(default_factory=dict)

    def summary_row(self) -> dict[str, Any]:
        u0 = self.units[0]
        u1 = self.units[1] if len(self.units) > 1 else None
        casc = self.cascade
        return {
            "scenario_id": self.scenario.scenario_id,
            "family": self.scenario.family,
            "fault_type": self.scenario.fault_type,
            "primary_bus": u0.bus,
            "primary_mw": u0.p_rated_mw,
            "t_trip_h": None if u0.t_trip_h is None else round(u0.t_trip_h, 4),
            "t_trip_min": None if u0.t_trip_h is None else round(u0.t_trip_h * 60.0, 3),
            "trip_mechanism": u0.trip_mechanism,
            "p_final_mw": round(u0.p_final_mw, 2),
            "secondary_bus": None if u1 is None else u1.bus,
            "secondary_t_trip_h": None
            if u1 is None or u1.t_trip_h is None
            else round(u1.t_trip_h, 4),
            "secondary_mechanism": None if u1 is None else u1.trip_mechanism,
            "cascade_triggered": None if casc is None else casc.cascade_triggered,
            "n_lines_removed": None if casc is None else casc.n_removed,
            "n_cascade_stages": None if casc is None else len(casc.stages),
            "quasi_static": self.scenario.quasi_static,
            "blowdown_policy": self.scenario.blowdown_policy,
            "strategy": self.scenario.strategy,
            "description": self.scenario.description,
        }


def load_framework_scenarios(
    path: Path | str = DEFAULT_REGISTRY,
) -> list[FrameworkScenario]:
    rows: list[FrameworkScenario] = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            sec_bus = (raw.get("secondary_bus") or "").strip()
            sec_mw = (raw.get("secondary_mw") or "").strip()
            rows.append(
                FrameworkScenario(
                    scenario_id=raw["scenario_id"].strip(),
                    family=raw["family"].strip(),
                    fault_type=raw["fault_type"].strip(),
                    primary_bus=int(raw["primary_bus"]),
                    primary_mw=float(raw["primary_mw"]),
                    secondary_bus=int(sec_bus) if sec_bus else None,
                    secondary_mw=float(sec_mw) if sec_mw else None,
                    pump_loss_frac=float(raw["pump_loss_frac"] or 0.0),
                    twb_rise_c=float(raw["twb_rise_c"] or 0.0),
                    blowdown_policy=raw["blowdown_policy"].strip(),  # type: ignore[arg-type]
                    strategy=raw["strategy"].strip(),  # type: ignore[arg-type]
                    quasi_static=str(raw["quasi_static"]).strip() in {"1", "true", "True"},
                    t_max_h=float(raw["t_max_h"]),
                    description=raw["description"].strip(),
                )
            )
    return rows


def get_scenario(
    scenario_id: str, path: Path | str = DEFAULT_REGISTRY
) -> FrameworkScenario:
    for spec in load_framework_scenarios(path):
        if spec.scenario_id == scenario_id:
            return spec
    raise KeyError(f"unknown framework scenario {scenario_id!r}")


def _unit_fault_type(spec: FrameworkScenario, *, primary: bool) -> str:
    if spec.fault_type != "mixed_pump_makeup":
        return spec.fault_type
    return "pump_failure" if primary else "makeup_interrupt"


def _simulate_unit(
    *,
    bus: int,
    p_mw: float,
    fault_type: str,
    spec: FrameworkScenario,
) -> CoupledUnitResult:
    model = scale_prototype_to_unit(WetRecircPrototype500(), p_mw, gen_id=f"Bus{bus}")
    sample = 1.0 if fault_type == "pump_failure" else 60.0
    # Makeup / wet-bulb need longer horizons; pump outages resolve in minutes.
    ts = simulate_cold_end(
        model,
        fault_type=fault_type,  # type: ignore[arg-type]
        strategy=spec.strategy,
        blowdown_policy=spec.blowdown_policy,
        pump_loss_frac=spec.pump_loss_frac if fault_type == "pump_failure" else 0.0,
        twb_rise_c=spec.twb_rise_c if fault_type == "wet_bulb_increase" else 0.0,
        quasi_static=spec.quasi_static,
        t_max_h=spec.t_max_h,
        sample_every_s=sample,
    )
    p_final = 0.0 if ts.trip is not None else float(ts.p_avail_mw[-1])
    return CoupledUnitResult(
        bus=bus,
        p_rated_mw=p_mw,
        fault_type=fault_type,
        timeseries=ts,
        p_final_mw=p_final,
        t_trip_h=ts.t_trip_h,
        trip_mechanism=ts.trip_mechanism,
    )


def run_framework_scenario(
    spec: FrameworkScenario | str,
    *,
    evaluate_cascade: bool | None = None,
) -> FrameworkRunResult:
    """Run cold-end contingencies and optional IEEE39 cascade check."""
    if isinstance(spec, str):
        spec = get_scenario(spec)

    units = [
        _simulate_unit(
            bus=spec.primary_bus,
            p_mw=spec.primary_mw,
            fault_type=_unit_fault_type(spec, primary=True),
            spec=spec,
        )
    ]
    if spec.secondary_bus is not None and spec.secondary_mw is not None:
        units.append(
            _simulate_unit(
                bus=spec.secondary_bus,
                p_mw=spec.secondary_mw,
                fault_type=_unit_fault_type(spec, primary=False),
                spec=spec,
            )
        )

    grid = IEEE39CascadeGrid()
    base_pg = {int(g["bus"]): float(g["Pg"]) for g in grid.generators}
    final_pg = dict(base_pg)
    for u in units:
        final_pg[u.bus] = u.p_final_mw

    if evaluate_cascade is None:
        # Cascade outlet for G*/baseline/control and any dual-unit case.
        # Single-unit cold-end rows defer to G1 unless explicitly requested.
        do_cascade = (
            spec.family in {"cascade", "baseline", "control"}
            or spec.secondary_bus is not None
            or spec.scenario_id.startswith("G")
        )
    else:
        do_cascade = bool(evaluate_cascade)

    cascade = None
    if do_cascade:
        cascade = grid.solve_cascade(final_pg)

    return FrameworkRunResult(
        scenario=spec,
        units=units,
        cascade=cascade,
        base_pg=base_pg,
        final_pg=final_pg,
    )


def run_framework_matrix(
    scenario_ids: list[str] | None = None,
    *,
    path: Path | str = DEFAULT_REGISTRY,
) -> list[FrameworkRunResult]:
    specs = load_framework_scenarios(path)
    if scenario_ids is not None:
        wanted = set(scenario_ids)
        specs = [s for s in specs if s.scenario_id in wanted]
    return [run_framework_scenario(s) for s in specs]


def write_summary_csv(results: list[FrameworkRunResult], path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.summary_row() for r in results]
    if not rows:
        out.write_text("", encoding="utf-8")
        return out
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out
