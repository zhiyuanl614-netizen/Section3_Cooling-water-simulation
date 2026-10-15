"""
Plant-calibratable cold-end dynamics for wet-recirculating coal units.

Integrates:

1. basin level (explicit area; holdup is diagnostic only);
2. circulating-pump hydraulics/NPSH, with optional first-order flow lag;
3. tower/condenser thermal states with first-order lag; and
4. operator/protection logic (ride-down SOP, ramp, low-vacuum, tech-min,
   pump low-level / cavitation trips).

Phase B (framework v0.3) extends the original makeup-interrupt integrator to a
multi-contingency entry point (:func:`simulate_cold_end`) covering:

* ``makeup_interrupt`` — basin drain (default blowdown isolation);
* ``pump_failure`` — circulating-flow loss with hydraulic lag;
* ``wet_bulb_increase`` — slow ambient wet-bulb rise;
* ``none`` — healthy baseline hold.

``quasi_static=True`` freezes thermal/flow lags (methodological control C2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

from .prototype_500mw import WetRecircPrototype500, _sat_pressure_kpa

LoadStrategy = Literal["ride_down", "hold_load"]
LossBasis = Literal["heat_scaled", "design_frozen"]
BlowdownPolicy = Literal["isolate_on_detection", "maintain"]
PumpModel = Literal["npsh_hydraulic", "level_band"]
FaultType = Literal[
    "makeup_interrupt",
    "pump_failure",
    "wet_bulb_increase",
    "none",
]

RIDE_DOWN: LoadStrategy = "ride_down"
HOLD_LOAD: LoadStrategy = "hold_load"


@dataclass
class TripEvent:
    """Why and when the unit stopped delivering power."""

    t_h: float
    mechanism: str
    detail: str = ""


@dataclass
class TimeseriesResult:
    """Result of one cold-end contingency simulation."""

    gen_id: str
    strategy: str
    loss_basis: str
    sample_dt_s: float
    p_rated_mw: float
    fault_type: str = "makeup_interrupt"
    quasi_static: bool = False
    t_s: list[float] = field(default_factory=list)
    t_h: list[float] = field(default_factory=list)
    level_m: list[float] = field(default_factory=list)
    volume_m3: list[float] = field(default_factory=list)
    qcw_frac: list[float] = field(default_factory=list)
    p_avail_mw: list[float] = field(default_factory=list)
    p_capability_mw: list[float] = field(default_factory=list)
    heat_reject_mw_th: list[float] = field(default_factory=list)
    backpressure_kpa: list[float] = field(default_factory=list)
    t_sat_c: list[float] = field(default_factory=list)
    tin_c: list[float] = field(default_factory=list)
    tout_c: list[float] = field(default_factory=list)
    twb_c: list[float] = field(default_factory=list)
    evaporation_m3s: list[float] = field(default_factory=list)
    blowdown_m3s: list[float] = field(default_factory=list)
    drift_m3s: list[float] = field(default_factory=list)
    water_loss_m3s: list[float] = field(default_factory=list)
    t_derate_start_h: float | None = None
    trip: TripEvent | None = None

    @property
    def t_trip_h(self) -> float | None:
        return None if self.trip is None else self.trip.t_h

    @property
    def trip_mechanism(self) -> str:
        return "no_trip_within_horizon" if self.trip is None else self.trip.mechanism

    def p_avail_at(self, t_h: float) -> float:
        """Linear interpolation of delivered/available power at a time (h)."""
        if not self.t_h:
            return float("nan")
        if t_h <= self.t_h[0]:
            return self.p_avail_mw[0]
        if t_h >= self.t_h[-1]:
            return self.p_avail_mw[-1]
        for i in range(1, len(self.t_h)):
            if self.t_h[i] >= t_h:
                t0, t1 = self.t_h[i - 1], self.t_h[i]
                p0, p1 = self.p_avail_mw[i - 1], self.p_avail_mw[i]
                if t1 <= t0:
                    return p1
                w = (t_h - t0) / (t1 - t0)
                return p0 + w * (p1 - p0)
        return self.p_avail_mw[-1]

    def rows(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i, t in enumerate(self.t_h):
            out.append(
                {
                    "gen_id": self.gen_id,
                    "fault_type": self.fault_type,
                    "strategy": self.strategy,
                    "quasi_static": self.quasi_static,
                    "t_h": round(t, 4),
                    "basin_level_m": round(self.level_m[i], 4),
                    "basin_volume_m3": round(self.volume_m3[i], 2),
                    "qcw_frac": round(self.qcw_frac[i], 5),
                    "p_avail_mw": round(self.p_avail_mw[i], 3),
                    "p_capability_mw": round(self.p_capability_mw[i], 3),
                    "heat_reject_mw_th": round(self.heat_reject_mw_th[i], 2),
                    "backpressure_kpa": round(self.backpressure_kpa[i], 4),
                    "t_sat_c": round(self.t_sat_c[i], 3),
                    "tin_c": round(self.tin_c[i], 3),
                    "tout_c": round(self.tout_c[i], 3),
                    "twb_c": round(self.twb_c[i], 3),
                    "evaporation_m3s": round(self.evaporation_m3s[i], 5),
                    "blowdown_m3s": round(self.blowdown_m3s[i], 5),
                    "drift_m3s": round(self.drift_m3s[i], 5),
                    "water_loss_m3s": round(self.water_loss_m3s[i], 5),
                }
            )
        return out


def _lag_alpha(dt_s: float, tau_s: float) -> float:
    if tau_s <= 0:
        return 1.0
    return 1.0 - math.exp(-dt_s / tau_s)


def simulate_makeup_interrupt(
    model: WetRecircPrototype500,
    **kwargs: Any,
) -> TimeseriesResult:
    """Backward-compatible wrapper: makeup interruption contingency."""
    kwargs.pop("fault_type", None)
    return simulate_cold_end(model, fault_type="makeup_interrupt", **kwargs)


def simulate_cold_end(
    model: WetRecircPrototype500,
    *,
    fault_type: FaultType = "makeup_interrupt",
    gen_id: str | None = None,
    strategy: LoadStrategy = RIDE_DOWN,
    initial_load_frac: float = 1.0,
    p_min_tech_frac: float | None = None,
    pb_trip_kpa: float | None = None,
    pb_trip_delay_s: float | None = None,
    derate_lo_m: float = 1.2,
    derate_hi_m: float = 1.7,
    pump_model: PumpModel = "npsh_hydraulic",
    twb_op_c: float | None = None,
    airflow_ratio: float = 1.0,
    blowdown_policy: BlowdownPolicy = "isolate_on_detection",
    blowdown_detection_delay_h: float = 0.25,
    use_operator_sop: bool = True,
    operator_shed_start_level_m: float | None = None,
    max_ramp_frac_per_min: float | None = None,
    dt_s: float = 1.0,
    t_max_h: float = 24.0,
    sample_every_s: float = 60.0,
    loss_basis: LossBasis = "heat_scaled",
    qcw_frac_floor: float = 0.02,
    pump_loss_frac: float = 1.0,
    pump_tau_s: float | None = None,
    twb_rise_c: float = 0.0,
    wet_bulb_tau_s: float | None = None,
    quasi_static: bool = False,
) -> TimeseriesResult:
    """
    Integrate a cold-end contingency on the plant-calibratable model.

    Parameters
    ----------
    fault_type
        ``makeup_interrupt``, ``pump_failure``, ``wet_bulb_increase``, or ``none``.
    pump_loss_frac
        For ``pump_failure``: fraction of design circulating capacity lost
        (1.0 = full outage, 0.5 = half the pumps).
    quasi_static
        If True, thermal and pump lags are removed (control experiment C2).
    """
    if strategy not in (RIDE_DOWN, HOLD_LOAD):
        raise ValueError(f"unknown strategy {strategy!r}")
    if loss_basis not in ("heat_scaled", "design_frozen"):
        raise ValueError(f"unknown loss_basis {loss_basis!r}")
    if blowdown_policy not in ("isolate_on_detection", "maintain"):
        raise ValueError(f"unknown blowdown_policy {blowdown_policy!r}")
    if pump_model not in ("npsh_hydraulic", "level_band"):
        raise ValueError(f"unknown pump_model {pump_model!r}")
    if fault_type not in (
        "makeup_interrupt",
        "pump_failure",
        "wet_bulb_increase",
        "none",
    ):
        raise ValueError(f"unknown fault_type {fault_type!r}")
    if dt_s <= 0 or sample_every_s <= 0:
        raise ValueError("time steps must be positive")
    if not (0.0 <= pump_loss_frac <= 1.0):
        raise ValueError("pump_loss_frac must be in [0, 1]")
    if twb_rise_c < 0:
        raise ValueError("twb_rise_c must be non-negative")

    gid = gen_id or model.gen_id
    p_min_frac = model.p_min_tech_frac if p_min_tech_frac is None else float(p_min_tech_frac)
    pb_trip = model.pb_trip_kpa if pb_trip_kpa is None else float(pb_trip_kpa)
    pb_delay = model.pb_trip_delay_s if pb_trip_delay_s is None else float(pb_trip_delay_s)
    ramp_frac = (
        model.max_ramp_frac_per_min
        if max_ramp_frac_per_min is None
        else float(max_ramp_frac_per_min)
    )
    if ramp_frac <= 0:
        raise ValueError("max_ramp_frac_per_min must be positive")
    shed_start = (
        model.operator_shed_start_level()
        if operator_shed_start_level_m is None
        else float(operator_shed_start_level_m)
    )
    twb_base = model.twb_ref_c if twb_op_c is None else float(twb_op_c)
    twb_state = twb_base
    twb_target = twb_base + (float(twb_rise_c) if fault_type == "wet_bulb_increase" else 0.0)

    tau_tower = 0.0 if quasi_static else float(model.tower_tau_s)
    tau_cond = 0.0 if quasi_static else float(model.condenser_tau_s)
    tau_pump = 0.0 if quasi_static else float(
        model.pump_tau_s if pump_tau_s is None else pump_tau_s
    )
    tau_wb = 0.0 if quasi_static else float(
        model.wet_bulb_tau_s if wet_bulb_tau_s is None else wet_bulb_tau_s
    )

    p0 = min(max(float(initial_load_frac), 0.0), 1.0) * model.p_rated_mw
    p_state = p0
    qc_hold_mw_th = model.heat_reject_mw_th(p0)

    area = model.basin_area_effective_m2()
    level = model.basin_level_normal_m
    level_trip = model.basin_level_trip_m

    initial = model.predict_cold_end(
        p_state, qcw_m3s=model.qcw_design_m3s, twb_c=twb_state, airflow_ratio=airflow_ratio
    )
    tin_state = initial.tin_c
    tsat_state = initial.t_sat_c
    pb_state = initial.backpressure_kpa
    x_state = 1.0

    res = TimeseriesResult(
        gen_id=gid,
        strategy=strategy,
        loss_basis=loss_basis,
        sample_dt_s=sample_every_s,
        p_rated_mw=model.p_rated_mw,
        fault_type=fault_type,
        quasi_static=quasi_static,
    )

    t_s = 0.0
    derate_start: float | None = None
    pb_high_since: float | None = None
    next_sample = 0.0
    t_max_s = t_max_h * 3600.0
    design_loss = model.makeup_m3s(model.qcw_design_m3s)
    drain_basin = fault_type == "makeup_interrupt"

    while t_s <= t_max_s + 1e-9:
        # ---- wet-bulb state (environmental contingency) -----------------
        if fault_type == "wet_bulb_increase":
            twb_state += (twb_target - twb_state) * _lag_alpha(dt_s, tau_wb)

        # ---- pump low-low level trip (inventory contingencies) ----------
        if drain_basin and level <= level_trip + 1e-12:
            res.trip = TripEvent(
                t_h=t_s / 3600.0,
                mechanism="pump_level",
                detail=(
                    f"basin level {level:.3f} m <= pump trip level {level_trip:.3f} m; "
                    "circulating pumps trip"
                ),
            )
            _record(
                res, t_s, level, 0.0, 0.0, 0.0, 0.0,
                pb_state, tsat_state, tin_state, float("nan"), twb_state,
                0.0, 0.0, 0.0, 0.0, model,
            )
            break

        # ---- circulating-water flow target + lag ------------------------
        if pump_model == "level_band":
            x_hyd = model.qcw_frac_from_level(level, derate_lo_m, derate_hi_m)
        else:
            x_hyd = model.pump_flow_fraction(level, tin_state)

        if fault_type == "pump_failure":
            x_tgt = max(0.0, (1.0 - pump_loss_frac) * x_hyd)
        else:
            x_tgt = x_hyd

        if quasi_static or tau_pump <= 0:
            x_state = x_tgt
        else:
            x_state += (x_tgt - x_state) * _lag_alpha(dt_s, tau_pump)
        x_state = max(0.0, min(1.0, x_state))
        qcw = model.qcw_design_m3s * x_state

        if (
            pump_model == "npsh_hydraulic"
            and fault_type == "makeup_interrupt"
            and x_state <= qcw_frac_floor
        ):
            res.trip = TripEvent(
                t_h=t_s / 3600.0,
                mechanism="pump_cavitation",
                detail=(
                    f"pump flow fraction {x_state:.3f} at basin level {level:.3f} m; "
                    "NPSH/hydraulic capability exhausted"
                ),
            )
            _record(
                res, t_s, level, 0.0, x_state, 0.0, 0.0,
                pb_state, tsat_state, tin_state, float("nan"), twb_state,
                0.0, 0.0, 0.0, 0.0, model,
            )
            break

        # ---- thermal state (lagged quasi-steady targets) ----------------
        qc = qc_hold_mw_th if strategy == HOLD_LOAD else model.heat_reject_mw_th(p_state)
        if x_state <= qcw_frac_floor:
            # Lost circulating water: heat rejection collapses. Drive the
            # saturation state toward a high-backpressure protection target
            # (needed for pump-outage contingencies; inventory trips still
            # dominate makeup-interrupt endings via level/NPSH checks).
            tin_target = tin_state
            tout_state = float("nan")
            tsat_target = _sat_temperature_for_pb(max(pb_trip, pb_state) + 5.0)
        else:
            tin_target = model.tower_outlet_c(twb_state, qc, qcw, airflow_ratio)
            tout_state, tsat_target, _, _ = model.condenser_state(qc, qcw, tin_target)

        tin_state += (tin_target - tin_state) * _lag_alpha(dt_s, tau_tower)
        tsat_state += (tsat_target - tsat_state) * _lag_alpha(dt_s, tau_cond)
        pb_state = _sat_pressure_kpa(tsat_state) + model.condenser_air_partial_pressure_kpa
        if x_state > qcw_frac_floor:
            _, tout_state_calc, _, _ = model.condenser_state(qc, qcw, tin_state)
            tout_state = tout_state_calc

        # ---- capability and control -------------------------------------
        p_thermal = model._power_derate_from_backpressure(pb_state)  # noqa: SLF001
        if strategy == RIDE_DOWN and use_operator_sop and drain_basin:
            if level >= shed_start:
                sop_cap = model.p_rated_mw
            elif level > level_trip:
                frac = p_min_frac + (1.0 - p_min_frac) * (level - level_trip) / max(
                    shed_start - level_trip, 1e-9
                )
                sop_cap = model.p_rated_mw * frac
            else:
                sop_cap = 0.0
            p_capability = min(p0, p_thermal, sop_cap)
        else:
            p_capability = min(p0, p_thermal)

        if strategy == RIDE_DOWN:
            max_delta = ramp_frac * model.p_rated_mw / 60.0 * dt_s
            if p_state > p_capability:
                p_state = max(p_capability, p_state - max_delta)
            elif p_state < p_capability:
                p_state = min(p_capability, p_state + max_delta)
        else:
            p_state = p_capability

        if derate_start is None and p_state < 0.995 * p0:
            derate_start = t_s / 3600.0

        # ---- low-vacuum protection --------------------------------------
        if pb_state == pb_state and pb_state >= pb_trip:
            if pb_high_since is None:
                pb_high_since = t_s
            elif t_s - pb_high_since >= pb_delay:
                res.trip = TripEvent(
                    t_h=t_s / 3600.0,
                    mechanism="backpressure_protection",
                    detail=(
                        f"condenser pressure {pb_state:.2f} kPa >= {pb_trip:.1f} kPa "
                        f"for {pb_delay:.0f} s; low-vacuum protection"
                    ),
                )
                _record(
                    res, t_s, level, 0.0, x_state, p_capability, qc,
                    pb_state, tsat_state, tin_state, tout_state, twb_state,
                    0.0, 0.0, 0.0, 0.0, model,
                )
                break
        else:
            pb_high_since = None

        # ---- technical minimum (ride-down inventory path) ---------------
        if (
            strategy == RIDE_DOWN
            and drain_basin
            and p_capability < p_min_frac * model.p_rated_mw - 1e-9
            and p_state <= p_min_frac * model.p_rated_mw + 0.5
        ):
            res.trip = TripEvent(
                t_h=t_s / 3600.0,
                mechanism="technical_minimum",
                detail=(
                    f"capability {p_capability:.1f} MW below technical minimum "
                    f"{p_min_frac * model.p_rated_mw:.1f} MW ({p_min_frac:.0%} of rated); "
                    "controlled shutdown"
                ),
            )
            _record(
                res, t_s, level, 0.0, x_state, p_capability, qc,
                pb_state, tsat_state, tin_state, tout_state, twb_state,
                0.0, 0.0, 0.0, 0.0, model,
            )
            break

        # ---- water losses / basin drain ---------------------------------
        evap, blowdown, drift, makeup = model.water_balance_m3s(qc, qcw, tin_state)
        if loss_basis == "design_frozen":
            evap = blowdown = drift = 0.0
            total_loss = design_loss
            makeup = design_loss
        else:
            if (
                drain_basin
                and blowdown_policy == "isolate_on_detection"
                and t_s >= blowdown_detection_delay_h * 3600.0
            ):
                blowdown = 0.0
            total_loss = evap + blowdown + drift
            makeup = total_loss

        if t_s >= next_sample - 1e-9:
            _record(
                res, t_s, level, p_state, x_state, p_capability, qc,
                pb_state, tsat_state, tin_state, tout_state, twb_state,
                evap, blowdown, drift, total_loss if drain_basin else 0.0, model,
            )
            next_sample += sample_every_s

        if drain_basin:
            level = max(0.0, level - total_loss / max(area, 1e-9) * dt_s)
        t_s += dt_s

    res.t_derate_start_h = derate_start
    return res


def _sat_temperature_for_pb(pb_kpa: float) -> float:
    """Inverse Magnus saturation temperature used when CW flow collapses."""
    from .prototype_500mw import _sat_temperature_c

    return _sat_temperature_c(max(pb_kpa, 0.1))


def _record(
    res: TimeseriesResult,
    t_s: float,
    level_m: float,
    p_mw: float,
    qcw_frac: float,
    p_capability_mw: float,
    qc_mw_th: float,
    pb_kpa: float,
    t_sat_c: float,
    tin_c: float,
    tout_c: float,
    twb_c: float,
    evap_m3s: float,
    blowdown_m3s: float,
    drift_m3s: float,
    total_loss_m3s: float,
    model: WetRecircPrototype500,
) -> None:
    res.t_s.append(t_s)
    res.t_h.append(t_s / 3600.0)
    res.level_m.append(level_m)
    res.volume_m3.append(model.basin_volume_from_level(level_m))
    res.qcw_frac.append(qcw_frac)
    res.p_avail_mw.append(p_mw)
    res.p_capability_mw.append(p_capability_mw)
    res.heat_reject_mw_th.append(qc_mw_th)
    res.backpressure_kpa.append(pb_kpa)
    res.t_sat_c.append(t_sat_c)
    res.tin_c.append(tin_c)
    res.tout_c.append(tout_c)
    res.twb_c.append(twb_c)
    res.evaporation_m3s.append(evap_m3s)
    res.blowdown_m3s.append(blowdown_m3s)
    res.drift_m3s.append(drift_m3s)
    res.water_loss_m3s.append(total_loss_m3s)
