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
from .transient import condenser_exchange, condenser_capacity_mj_per_k, advance_condenser, NoQuasiStaticEquilibrium


class IneligibleInitialState(ValueError):
    """The requested prefault equilibrium already violates protection."""

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
    p_before_trip_mw: float | None = None
    model_version: str = "0.7.2-candidate"
    thermal_closure: str = "serial_finite_storage"
    initial_p_mw: float = 0.0
    initial_pb_kpa: float = 0.0
    condenser_capacity_mj_per_k: float = 0.0
    water_heat_removed_mw_th: list[float] = field(default_factory=list)
    condenser_storage_rate_mw: list[float] = field(default_factory=list)
    max_condenser_energy_residual_mj: float = 0.0

    @property
    def t_trip_h(self) -> float | None:
        return None if self.trip is None else self.trip.t_h

    @property
    def trip_mechanism(self) -> str:
        return "no_trip_within_horizon" if self.trip is None else self.trip.mechanism

    def p_avail_at(self, t_h: float, *, side: str = "right") -> float:
        """Linear interpolation of delivered/available power at a time (h)."""
        if not self.t_h:
            return float("nan")
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")
        if self.t_trip_h is not None and t_h >= self.t_trip_h:
            if t_h == self.t_trip_h and side == "left" and self.p_before_trip_mw is not None:
                return self.p_before_trip_mw
            return 0.0
        if t_h <= self.t_h[0]:
            return self.p_avail_mw[0]
        if t_h >= self.t_h[-1]:
            return self.p_avail_mw[-1]
        for i in range(1, len(self.t_h)):
            if self.t_h[i] >= t_h:
                t0, t1 = self.t_h[i - 1], self.t_h[i]
                p0, p1 = self.p_avail_mw[i - 1], self.p_avail_mw[i]
                if self.t_h[i] == self.t_trip_h and self.p_before_trip_mw is not None:
                    p1 = self.p_before_trip_mw
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
                    "model_version": self.model_version,
                    "thermal_closure": self.thermal_closure,
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
                    "water_heat_removed_mw_th": self.water_heat_removed_mw_th[i],
                    "condenser_storage_rate_mw": self.condenser_storage_rate_mw[i],
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

    numeric = [dt_s, sample_every_s, t_max_h, initial_load_frac, pb_trip, pb_delay,
               ramp_frac, twb_base, airflow_ratio, blowdown_detection_delay_h,
               tau_tower, tau_cond, tau_pump, tau_wb]
    if not all(math.isfinite(float(v)) for v in numeric):
        raise ValueError("non-finite integration input")
    if t_max_h < 0 or pb_delay < 0 or min(tau_tower,tau_cond,tau_pump,tau_wb) < 0:
        raise ValueError("negative horizon/delay/time constant")
    if airflow_ratio <= 0 or not 0 <= initial_load_frac <= 1:
        raise ValueError("positive airflow and initial load fraction in [0,1] required")
    if not 0 < qcw_frac_floor < 1:
        raise ValueError("flow protection floor must be in (0,1)")

    # Establish a self-consistent healthy operating point BEFORE the fault.
    initial = model.evaluate(p_setpoint_mw=initial_load_frac*model.p_rated_mw,
                             twb_c=twb_base, airflow_ratio=airflow_ratio)
    p0 = float(initial.p_avail_mw)
    p_state = p0
    qc_hold_mw_th = model.heat_reject_mw_th(p0)
    tin_state, tsat_state = initial.tin_c, initial.t_sat_c
    pb_state = initial.backpressure_kpa
    if not math.isfinite(pb_state) or pb_state >= pb_trip:
        raise IneligibleInitialState("prefault equilibrium violates the vacuum setpoint; do not treat it as a fault-induced trip")
    area = model.basin_area_effective_m2()
    level, level_trip = model.basin_level_normal_m, model.basin_level_trip_m
    x_state = 1.0
    capacity = condenser_capacity_mj_per_k(model, tau_cond)
    res = TimeseriesResult(gen_id=gid, strategy=strategy, loss_basis=loss_basis,
                          sample_dt_s=sample_every_s, p_rated_mw=model.p_rated_mw,
                          fault_type=fault_type, quasi_static=quasi_static,
                          initial_p_mw=p0, initial_pb_kpa=pb_state,
                          condenser_capacity_mj_per_k=capacity)
    drain_basin = fault_type == "makeup_interrupt"
    t_s, t_max_s = 0.0, float(t_max_h)*3600
    next_sample = float(sample_every_s)
    pb_high_since = None
    derate_start = None
    design_loss = model.makeup_m3s(model.qcw_design_m3s)
    detect_s = max(0., blowdown_detection_delay_h*3600)

    def process_values():
        qcw = model.qcw_design_m3s*x_state
        ex = condenser_exchange(model,qcw)
        steam = qc_hold_mw_th if strategy == HOLD_LOAD else model.heat_reject_mw_th(p_state)
        water = ex.water_heat_mw(tsat_state,tin_state)
        outlet = ex.outlet_c(tsat_state,tin_state)
        evap, blow, drift, _ = model.water_balance_m3s(max(0.,water),qcw,tin_state)
        if loss_basis == "design_frozen":
            evap=blow=drift=0.;loss=design_loss
        else:
            if drain_basin and blowdown_policy == "isolate_on_detection" and t_s >= detect_s-1e-10:
                blow=0.
            loss=evap+blow+drift
        return steam,water,outlet,evap,blow,drift,loss

    def record(capability, *, tripped=False):
        steam,water,outlet,evap,blow,drift,loss = process_values()
        if tripped:
            steam=0.;evap=blow=drift=loss=0.
        _record(res,t_s,level,0. if tripped else p_state,x_state,capability,steam,
                pb_state,tsat_state,tin_state,outlet,twb_state,
                evap,blow,drift,loss if drain_basin else 0.,model)
        res.water_heat_removed_mw_th.append(water)
        res.condenser_storage_rate_mw.append(steam-water)

    record(p0)
    while t_s < t_max_s-1e-10:
        h=min(float(dt_s),t_max_s-t_s,next_sample-t_s)
        if drain_basin and blowdown_policy == "isolate_on_detection" and t_s < detect_s-1e-10:
            h=min(h,detect_s-t_s)
        if h <= 1e-10:
            next_sample += float(sample_every_s)
            continue
        steam0,water0,_,_,_,_,loss0=process_values()
        old_level=level
        # Midpoint input holds give serial tower->condenser causality while
        # retaining exact scalar interval updates for the frozen inputs.
        wb_mid=twb_target+(twb_state-twb_target)*math.exp(-h/(2*tau_wb)) if fault_type == "wet_bulb_increase" and tau_wb>0 else (twb_target if fault_type == "wet_bulb_increase" else twb_state)
        if pump_model == "level_band":
            x_hyd=model.qcw_frac_from_level(level,derate_lo_m,derate_hi_m)
        else:
            x_hyd=model.pump_flow_fraction(level,tin_state)
        x_target=(1-pump_loss_frac)*x_hyd if fault_type == "pump_failure" else x_hyd
        x_mid=x_target+(x_state-x_target)*math.exp(-h/(2*tau_pump)) if tau_pump>0 else x_target
        x_new=x_target+(x_state-x_target)*math.exp(-h/tau_pump) if tau_pump>0 else x_target
        x_mid=max(0.,min(1.,x_mid));x_new=max(0.,min(1.,x_new))
        qmid=model.qcw_design_m3s*x_mid
        exchange=condenser_exchange(model,qmid)
        water_target=max(0.,exchange.water_heat_mw(tsat_state,tin_state))
        tin_target=model.tower_outlet_c(wb_mid,water_target,qmid,airflow_ratio) if qmid>0 else tin_state
        tin_mid=tin_state+(tin_target-tin_state)*_lag_alpha(h/2,tau_tower)
        tin_new=tin_state+(tin_target-tin_state)*_lag_alpha(h,tau_tower)
        step=advance_condenser(tsat_state,tin_mid,steam0,exchange.conductance_mw_per_k,capacity,h)
        res.max_condenser_energy_residual_mj=max(res.max_condenser_energy_residual_mj,abs(step.energy_residual_mj))
        tsat_state,tin_state,x_state=step.tsat_c,tin_new,x_new
        if fault_type == "wet_bulb_increase":
            twb_state=twb_target+(twb_state-twb_target)*math.exp(-h/tau_wb) if tau_wb>0 else twb_target
        t_s += h
        # Water inventory uses a trapezoid of actual water-side heat duties.
        _,_,_,_,_,_,loss1=process_values()
        if drain_basin:
            # A detection jump is right-continuous and has zero time width.
            if blowdown_policy == "isolate_on_detection" and abs(t_s-detect_s)<1e-8:
                _,b_end,_,_=model.water_balance_m3s(max(0.,condenser_exchange(model,model.qcw_design_m3s*x_state).water_heat_mw(tsat_state,tin_state)),model.qcw_design_m3s*x_state,tin_state)
                loss1 += b_end
            level=max(0.,old_level-(loss0+loss1)*.5*h/area)
        pb_state=_sat_pressure_kpa(tsat_state)+model.condenser_air_partial_pressure_kpa
        p_thermal=model._power_derate_from_backpressure(pb_state)
        if strategy == RIDE_DOWN and use_operator_sop and drain_basin:
            # Left limit of the operator cap at the independently tripped level.
            frac=p_min_frac+(1-p_min_frac)*max(0.,min(1.,(level-level_trip)/max(shed_start-level_trip,1e-9)))
            sop=model.p_rated_mw*frac
            p_capability=min(p0,p_thermal,sop)
        else:
            p_capability=min(p0,p_thermal)
        max_delta=ramp_frac*model.p_rated_mw*h/60
        p_state += max(-max_delta,min(max_delta,p_capability-p_state))
        if derate_start is None and p_state < .995*p0:
            derate_start=t_s/3600
        mechanism=None;detail=""
        if drain_basin and level<=level_trip+1e-12:
            mechanism="pump_level";detail="basin at pump trip level"
        elif pump_model == "npsh_hydraulic" and drain_basin and x_state<=qcw_frac_floor:
            mechanism="pump_cavitation";detail="hydraulic availability below protection floor"
        else:
            if pb_state >= pb_trip:
                if pb_high_since is None:pb_high_since=t_s
                if t_s-pb_high_since >= pb_delay-1e-10:
                    mechanism="backpressure_protection";detail="vacuum setpoint sustained for declared delay"
            else:pb_high_since=None
            if mechanism is None and strategy == RIDE_DOWN and drain_basin and p_capability<p_min_frac*model.p_rated_mw-1e-9 and p_state<=p_min_frac*model.p_rated_mw+.5:
                mechanism="technical_minimum";detail="capability below technical minimum"
        if mechanism is not None:
            res.p_before_trip_mw=float(p_state)
            res.trip=TripEvent(t_s/3600,mechanism,detail)
            record(p_capability,tripped=True)
            break
        if t_s >= next_sample-1e-8 or t_s >= t_max_s-1e-8:
            record(p_capability)
            if t_s >= next_sample-1e-8:next_sample += float(sample_every_s)
    res.t_derate_start_h=derate_start
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
