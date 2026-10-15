"""
Plant-calibratable wet-recirculating cold-end model for a coal unit.

Model intent (v0.3)
-------------------
This module is a *plant-calibratable* mechanistic model, not a claim that the
reference numbers below are measurements from a specific power plant.  The
model separates four things that the previous version conflated:

1. reference/design calibration (rated point and manufacturer-style anchors);
2. operating environment (operating wet-bulb temperature and tower air flow);
3. equipment state (cooling-tower characteristic, condenser UA, pump NPSH,
   basin geometry and protection/control settings); and
4. scenario assumptions (uncertainty band, load strategy and blowdown policy).

Physical sub-models
-------------------
* Steam-cycle heat rejection uses net efficiency with a part-load heat-rate
  penalty and an explicit fraction of waste heat rejected to the condenser.
* The cooling tower is a design-calibrated effectiveness/NTU surrogate:
  the design NTU is inferred from design range/approach and then varied with
  air-to-water ratio and a calibratable tower characteristic multiplier.
* The condenser is a UA-LMTD exchanger.  UA is inferred at the design point;
  off-design UA varies with circulating-water velocity and cleanliness, so
  TTD is an output rather than a constant.
* Evaporation follows the tower heat balance (evaporative heat fraction and
  latent heat), drift follows circulating flow, and blowdown follows the salt
  balance for the stated cycles of concentration.
* Basin inventory is a level state with explicit plan area, normal level and
  pump-trip level.  ``holdup hours'' is a derived diagnostic, not an input
  that manufactures the basin volume.
* Circulating-pump flow is estimated from a pump/system-head balance plus an
  NPSH availability factor.  A legacy level-band transfer function remains
  available only as an explicitly labelled fallback.

Reference values are a transparent calibration template.  They must be
replaced by plant drawings, manufacturer curves, protection settings and
historian data before the model is described as site-calibrated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

UncertaintyBand = Literal["base", "low", "high"]

# Scenario band: equipment/inventory uncertainty multipliers.  These do NOT
# move the reference design point.  "low" is adverse, "high" is favourable.
_BAND_FACTORS: dict[str, dict[str, float]] = {
    "low": {
        "tower": 0.85,
        "condenser": 0.90,
        "basin_area": 0.85,
        "evap_heat": 1.05,
        "pump_npshr": 1.10,
    },
    "base": {
        "tower": 1.00,
        "condenser": 1.00,
        "basin_area": 1.00,
        "evap_heat": 1.00,
        "pump_npshr": 1.00,
    },
    "high": {
        "tower": 1.15,
        "condenser": 1.05,
        "basin_area": 1.15,
        "evap_heat": 0.95,
        "pump_npshr": 0.90,
    },
}

_G = 9.80665


def band_factors(band: UncertaintyBand) -> dict[str, float]:
    """Return uncertainty-band multipliers for equipment/inventory state."""
    try:
        return dict(_BAND_FACTORS[band])
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown band {band!r}; expected one of {tuple(_BAND_FACTORS)}") from exc


@dataclass(frozen=True)
class PrototypeResult:
    """Steady-state / snapshot cold-end evaluation."""

    cooling_type: str
    p_rated_mw: float
    p_avail_mw: float
    qcw_m3s: float
    tin_c: float
    tout_c: float
    t_sat_c: float
    backpressure_kpa: float
    heat_reject_mw_th: float
    basin_volume_m3: float = float("nan")
    basin_vmin_m3: float = float("nan")
    basin_level_m: float = float("nan")
    basin_level_min_m: float = float("nan")
    pb_design_kpa: float = float("nan")
    time_to_trip_h: float = float("nan")
    evaporation_m3s: float = float("nan")
    blowdown_m3s: float = float("nan")
    drift_m3s: float = float("nan")
    makeup_m3s: float = float("nan")
    tower_approach_c: float = float("nan")
    condenser_ttd_c: float = float("nan")
    notes: str = ""


def _sat_pressure_kpa(t_sat_c: float) -> float:
    """Saturation pressure of water (Magnus form; adequate for 5-80 C)."""
    return 0.6108 * math.exp(17.27 * t_sat_c / (t_sat_c + 237.3))


def _sat_temperature_c(p_kpa: float) -> float:
    """Inverse of :func:`_sat_pressure_kpa`."""
    if p_kpa <= 0:
        raise ValueError("pressure must be positive")
    ratio = math.log(p_kpa / 0.6108)
    return 237.3 * ratio / (17.27 - ratio)


@dataclass
class WetRecircPrototype500:
    """Wet-recirculating cold-end prototype with plant-calibration anchors.

    ``p_rated_mw`` is net electrical output at the reference point.  The
    reference point is fixed by the fields marked ``*_ref_*`` / ``*_design_*``;
    operating weather is passed to evaluation functions and does not silently
    re-normalise the unit rating.
    """

    # ---------------------------------------------------------- steam cycle
    p_rated_mw: float = 500.0
    eta_net_design: float = 0.38
    partload_heatrate_penalty: float = 0.25
    condenser_waste_heat_frac: float = 0.92

    # ------------------------------------------------------ reference state
    qcw_design_m3s: float = 15.77
    twb_ref_c: float = 20.0
    approach_design_c: float = 5.55
    ttd_design_c: float = 3.5
    pb_ref_kpa: float | None = None

    # ------------------------------------------------------ cooling tower
    tower_characteristic_mult: float = 1.0
    tower_ntu_exp: float = 0.45

    # --------------------------------------------------------- condenser
    condenser_cleanliness: float = 1.0
    condenser_u_flow_exp: float = 0.8
    condenser_air_partial_pressure_kpa: float = 0.0

    # ------------------------------------------------------------- water
    evap_heat_fraction: float = 0.82
    drift_frac: float = 0.00005
    cycles_of_concentration: float = 4.0
    rho: float = 997.0
    cp: float = 4180.0

    # ------------------------------------------- turbine backpressure curve
    backpressure_sens_per_kpa: float = 0.007
    backpressure_sens_high_per_kpa: float = 0.014
    backpressure_break_dp_kpa: float = 5.0
    backpressure_bonus_per_kpa: float = 0.002
    backpressure_bonus_cap: float = 0.02

    # ------------------------------------------------------------- basin
    # Reference-template geometry (replace from plant drawings).  The level
    # datum is the basin floor used by the plant level instrument.
    basin_area_m2: float = 1600.0
    basin_level_normal_m: float = 3.5
    basin_level_trip_m: float = 1.0

    # ------------------------------------------------------ circulating pumps
    site_atm_pressure_kpa: float = 101.325
    pump_design_head_m: float = 22.0
    pump_static_lift_design_m: float = 10.0
    pump_shutoff_factor: float = 1.30
    pump_eye_elevation_m: float = -1.0
    pump_suction_loss_m: float = 1.2
    pump_npshr_design_m: float = 8.0
    pump_npsh_margin_req_m: float = 1.0

    # ------------------------------------------------------ control / protection
    operator_shed_start_level_m: float | None = None
    max_ramp_frac_per_min: float = 0.02
    p_min_tech_frac: float = 0.40
    pb_trip_kpa: float = 15.0
    pb_trip_delay_s: float = 3.0

    # ------------------------------------------------------ thermal inertia
    tower_tau_s: float = 300.0
    condenser_tau_s: float = 90.0
    # Circulating-flow first-order lag (pump trip / runback hydraulics).
    # Anchored to seconds-scale CW hydraulics; used by contingency dynamics.
    pump_tau_s: float = 10.0
    # Ambient wet-bulb first-order lag for environmental contingencies.
    wet_bulb_tau_s: float = 900.0

    band: UncertaintyBand = "base"
    gen_id: str = "prototype"

    # ------------------------------------------------------------ validation
    def __post_init__(self) -> None:
        if self.p_rated_mw <= 0 or self.qcw_design_m3s <= 0:
            raise ValueError("rated power and design circulating flow must be positive")
        if not (0.05 < self.eta_net_design < 0.65):
            raise ValueError("eta_net_design outside plausible net-efficiency range")
        if not (0.0 < self.condenser_waste_heat_frac <= 1.0):
            raise ValueError("condenser_waste_heat_frac must be in (0, 1]")
        if self.cycles_of_concentration <= 1.0:
            raise ValueError("cycles_of_concentration must exceed 1")
        if self.basin_area_m2 <= 0:
            raise ValueError("basin_area_m2 must be positive")
        if not (0.0 <= self.basin_level_trip_m < self.basin_level_normal_m):
            raise ValueError("require 0 <= basin_level_trip_m < basin_level_normal_m")
        if not (0.0 < self.p_min_tech_frac < 1.0):
            raise ValueError("p_min_tech_frac must be in (0, 1)")

    # ------------------------------------------------------- legacy aliases
    @property
    def eta_net(self) -> float:
        return self.eta_net_design

    @property
    def twb_design_c(self) -> float:
        return self.twb_ref_c

    @property
    def ttd_c(self) -> float:
        return self.ttd_design_c

    @property
    def backpressure_sens(self) -> float:
        return self.backpressure_sens_per_kpa

    @property
    def range_design_c(self) -> float:
        return self.design_delta_t_c()

    @property
    def evap_frac(self) -> float:
        """Design evaporation as a fraction of design circulating flow."""
        e, _, _, _ = self.water_balance_m3s(
            self.heat_reject_mw_th(), self.qcw_design_m3s, self.design_inlet_c()
        )
        return e / self.qcw_design_m3s

    @property
    def basin_vmin_frac(self) -> float:
        return self.basin_level_trip_m / self.basin_level_normal_m

    @property
    def basin_effective_depth_m(self) -> float:
        return self.basin_level_normal_m

    @property
    def basin_holdup_h(self) -> float:
        """Derived usable-inventory hours at the design makeup rate."""
        usable = self.basin_design_volume_m3() - self.basin_vmin_m3()
        return usable / max(self.makeup_m3s(self.qcw_design_m3s), 1e-12) / 3600.0

    # ------------------------------------------------------------------ band
    def _band(self) -> dict[str, float]:
        return band_factors(self.band)

    def _tower_mult_eff(self) -> float:
        return self.tower_characteristic_mult * self._band()["tower"]

    def _condenser_cleanliness_eff(self) -> float:
        return self.condenser_cleanliness * self._band()["condenser"]

    def _evap_heat_fraction_eff(self) -> float:
        return self.evap_heat_fraction * self._band()["evap_heat"]

    def _pump_npshr_mult_eff(self) -> float:
        return self._band()["pump_npshr"]

    # -------------------------------------------------------------- steam cycle
    def net_efficiency(self, p_mw: float | None = None) -> float:
        """Part-load net efficiency implied by the heat-rate penalty."""
        p = self.p_rated_mw if p_mw is None else max(p_mw, 0.0)
        if p <= 0:
            return self.eta_net_design
        f = min(1.0, p / self.p_rated_mw)
        heat_rate_mult = 1.0 + self.partload_heatrate_penalty * (1.0 - f) ** 2
        return self.eta_net_design / heat_rate_mult

    def heat_reject_mw_th(self, p_mw: float | None = None) -> float:
        """Condenser heat rejection at net output ``p_mw``."""
        p = self.p_rated_mw if p_mw is None else max(p_mw, 0.0)
        if p <= 0:
            return 0.0
        eta = max(self.net_efficiency(p), 1e-6)
        total_waste = p * (1.0 / eta - 1.0)
        return total_waste * self.condenser_waste_heat_frac

    # -------------------------------------------------------------- cold end
    def design_delta_t_c(self) -> float:
        """Circulating-water temperature rise at the rated point."""
        return self.heat_reject_mw_th() * 1e6 / (self.rho * self.cp * self.qcw_design_m3s)

    def design_inlet_c(self) -> float:
        """Cooling-tower outlet (= condenser inlet) temperature at reference."""
        return self.twb_ref_c + self.approach_design_c

    def tower_design_ntu(self) -> float:
        """Tower NTU inferred from design range and approach."""
        r = self.design_delta_t_c()
        a = max(self.approach_design_c, 1e-9)
        effectiveness = r / (r + a)
        return -math.log(max(1.0 - effectiveness, 1e-9))

    def tower_outlet_c(
        self,
        twb_op_c: float,
        heat_reject_mw_th: float,
        qcw_m3s: float,
        airflow_ratio: float = 1.0,
    ) -> float:
        """Tower cold-water temperature from the effectiveness/NTU surrogate."""
        if qcw_m3s <= 0:
            return float("nan")
        rng = max(heat_reject_mw_th, 0.0) * 1e6 / (self.rho * self.cp * qcw_m3s)
        if rng <= 0:
            return float(twb_op_c)
        x = max(qcw_m3s / self.qcw_design_m3s, 1e-9)
        air_water_ratio = max(airflow_ratio, 0.0) / x
        ntu = (
            self.tower_design_ntu()
            * self._tower_mult_eff()
            * air_water_ratio**self.tower_ntu_exp
        )
        effectiveness = min(0.999, 1.0 - math.exp(-max(ntu, 0.0)))
        approach = rng * (1.0 - effectiveness) / effectiveness
        return float(twb_op_c) + approach

    def condenser_ua_design_mw_per_k(self) -> float:
        """Design condenser UA inferred from design Q, range and TTD."""
        q = self.heat_reject_mw_th()
        r = self.design_delta_t_c()
        ttd = max(self.ttd_design_c, 1e-9)
        lmtd = r / math.log((r + ttd) / ttd)
        return q / lmtd

    def condenser_state(
        self,
        heat_reject_mw_th: float,
        qcw_m3s: float,
        tin_c: float,
    ) -> tuple[float, float, float, float]:
        """Return Tout, Tsat, total backpressure and instantaneous TTD."""
        if qcw_m3s <= 0:
            return float("nan"), float("nan"), float("nan"), float("nan")
        q = max(heat_reject_mw_th, 0.0)
        rng = q * 1e6 / (self.rho * self.cp * qcw_m3s)
        tout = tin_c + rng
        if q <= 0:
            t_sat = tin_c
            return tout, t_sat, _sat_pressure_kpa(t_sat) + self.condenser_air_partial_pressure_kpa, 0.0
        x = max(qcw_m3s / self.qcw_design_m3s, 1e-9)
        ua = (
            self.condenser_ua_design_mw_per_k()
            * self._condenser_cleanliness_eff()
            * x**self.condenser_u_flow_exp
        )
        exponent = ua * rng / q
        ttd = rng / math.expm1(exponent) if exponent > 1e-9 else rng / max(exponent, 1e-9)
        t_sat = tout + ttd
        pb = _sat_pressure_kpa(t_sat) + self.condenser_air_partial_pressure_kpa
        return tout, t_sat, pb, ttd

    def reference_backpressure_kpa(self) -> float:
        """Backpressure at the fixed reference/design calibration point."""
        if self.pb_ref_kpa is not None:
            return float(self.pb_ref_kpa)
        t_sat = self.design_inlet_c() + self.design_delta_t_c() + self.ttd_design_c
        return _sat_pressure_kpa(t_sat) + self.condenser_air_partial_pressure_kpa

    def design_backpressure_kpa(self) -> float:
        """Backward-compatible alias for :meth:`reference_backpressure_kpa`."""
        return self.reference_backpressure_kpa()

    def backpressure_power_factor(self, pb_kpa: float) -> float:
        """Piecewise turbine correction relative to the reference point."""
        ref = self.reference_backpressure_kpa()
        if pb_kpa != pb_kpa:  # NaN
            return 0.0
        if pb_kpa <= ref:
            return min(
                1.0 + self.backpressure_bonus_cap,
                1.0 + self.backpressure_bonus_per_kpa * (ref - pb_kpa),
            )
        dp = pb_kpa - ref
        low = min(dp, self.backpressure_break_dp_kpa)
        high = max(0.0, dp - self.backpressure_break_dp_kpa)
        loss = self.backpressure_sens_per_kpa * low + self.backpressure_sens_high_per_kpa * high
        return max(0.0, 1.0 - loss)

    def _power_derate_from_backpressure(self, pb_kpa: float) -> float:
        return self.p_rated_mw * self.backpressure_power_factor(pb_kpa)

    # ------------------------------------------------------------------ water
    def latent_heat_j_per_kg(self, water_temp_c: float) -> float:
        """Approximate latent heat of vaporisation at tower temperature."""
        return max(2.20e6, (2501.0 - 2.43 * water_temp_c) * 1000.0)

    def water_balance_m3s(
        self,
        heat_reject_mw_th: float,
        qcw_m3s: float,
        tin_c: float,
    ) -> tuple[float, float, float, float]:
        """Return evaporation, blowdown, drift and makeup (all m3/s).

        Salt balance: with S = B + D and CoC = M/S, S = E/(CoC-1).  The
        total makeup remains E*CoC/(CoC-1); drift is explicit rather than
        hidden in the wording of the balance.
        """
        q = max(heat_reject_mw_th, 0.0)
        evap = (
            self._evap_heat_fraction_eff()
            * q
            * 1e6
            / (self.rho * self.latent_heat_j_per_kg(tin_c))
        )
        drift = self.drift_frac * max(qcw_m3s, 0.0)
        liquid_salt_out = evap / max(self.cycles_of_concentration - 1.0, 0.05)
        blowdown = max(0.0, liquid_salt_out - drift)
        makeup = evap + blowdown + drift
        return evap, blowdown, drift, makeup

    def makeup_m3s(
        self,
        qcw_m3s: float,
        heat_reject_mw_th: float | None = None,
        tin_c: float | None = None,
    ) -> float:
        """Makeup corresponding to a stated flow/heat state (design default)."""
        if heat_reject_mw_th is None:
            heat_reject_mw_th = self.heat_reject_mw_th() * (qcw_m3s / self.qcw_design_m3s)
        if tin_c is None:
            tin_c = self.design_inlet_c()
        return self.water_balance_m3s(heat_reject_mw_th, qcw_m3s, tin_c)[3]

    # ------------------------------------------------------------------ basin
    def basin_area_effective_m2(self) -> float:
        return self.basin_area_m2 * self._band()["basin_area"]

    def basin_design_volume_m3(self) -> float:
        """Volume at the normal operating level (not a manufactured holdup)."""
        return self.basin_area_effective_m2() * self.basin_level_normal_m

    def basin_vmin_m3(self) -> float:
        return self.basin_area_effective_m2() * self.basin_level_trip_m

    def basin_level_m(self, volume_m3: float) -> float:
        return max(volume_m3, 0.0) / max(self.basin_area_effective_m2(), 1e-9)

    def basin_volume_from_level(self, level_m: float) -> float:
        return max(level_m, 0.0) * self.basin_area_effective_m2()

    def basin_level_min_m(self) -> float:
        return self.basin_level_trip_m

    def operator_shed_start_level(self) -> float:
        if self.operator_shed_start_level_m is not None:
            return float(self.operator_shed_start_level_m)
        return self.basin_level_trip_m + 1.0

    def time_to_trip_after_makeup_stop_h(self, qcw_frac: float = 1.0) -> float:
        """
        Analytic drain time at design loss with blowdown maintained.

        This is a screening identity using independently specified basin
        geometry; it is no longer ``holdup*(1-vmin)`` by construction.
        """
        if qcw_frac <= 0:
            return float("inf")
        loss = self.makeup_m3s(self.qcw_design_m3s * qcw_frac)
        if loss <= 0:
            return float("inf")
        usable = self.basin_design_volume_m3() - self.basin_vmin_m3()
        return usable / loss / 3600.0

    # ------------------------------------------------------------- behaviour
    def pump_flow_fraction(self, level_m: float, tin_c: float) -> float:
        """
        Circulating-flow fraction from pump/system head plus NPSH margin.

        The pump and system curves are both anchored at the design point.
        Falling basin level increases static lift; cavitation risk enters
        through NPSHa relative to a flow-scaled NPSHr.  Plant calibration
        should replace these reference coefficients with pump-curve data.
        """
        if level_m <= self.basin_level_trip_m:
            return 0.0
        shutoff = self.pump_design_head_m * self.pump_shutoff_factor
        denom = max(shutoff - self.pump_static_lift_design_m, 1e-9)
        static = self.pump_static_lift_design_m + (self.basin_level_normal_m - level_m)
        x_hyd = math.sqrt(max(shutoff - static, 0.0) / denom)

        atm_head = self.site_atm_pressure_kpa * 1000.0 / (self.rho * _G)
        vap_head = _sat_pressure_kpa(tin_c) * 1000.0 / (self.rho * _G)
        npsha = atm_head - vap_head + (level_m - self.pump_eye_elevation_m) - self.pump_suction_loss_m
        npshr = self.pump_npshr_design_m * self._pump_npshr_mult_eff() * x_hyd**2
        if npsha >= npshr + self.pump_npsh_margin_req_m:
            x_npsh = 1.0
        elif npsha <= 0:
            x_npsh = 0.0
        else:
            x_npsh = min(1.0, max(0.0, npsha / max(npshr + self.pump_npsh_margin_req_m, 1e-9)))
        return max(0.0, min(x_hyd, x_npsh))

    def qcw_frac_from_level(
        self,
        level_m: float,
        derate_lo_m: float = 1.2,
        derate_hi_m: float = 1.7,
    ) -> float:
        """
        Legacy level-band transfer function (fallback / sensitivity only).

        It is not used by the default pump model; it remains so old studies
        can be reproduced and explicitly compared with the NPSH model.
        """
        if level_m <= derate_lo_m:
            return 0.0
        if level_m >= derate_hi_m:
            return 1.0
        return (level_m - derate_lo_m) / (derate_hi_m - derate_lo_m)

    # ------------------------------------------------------------- prediction
    def predict_cold_end(
        self,
        p_mw: float | None = None,
        *,
        qcw_m3s: float | None = None,
        qcw_frac: float = 1.0,
        twb_c: float | None = None,
        airflow_ratio: float = 1.0,
        basin_volume_m3: float | None = None,
    ) -> PrototypeResult:
        """Predict cold-end state at a specified delivered power.

        This is the calibration-facing equation: measured/assumed P, Qcw and
        wet bulb go in; Tin, Tout, Tsat, backpressure and water losses come
        out.  ``p_avail_mw`` in the result is the thermal capability implied
        by that backpressure before any setpoint cap is applied.
        """
        p = self.p_rated_mw if p_mw is None else max(float(p_mw), 0.0)
        qcw = self.qcw_design_m3s * qcw_frac if qcw_m3s is None else max(float(qcw_m3s), 0.0)
        twb_op = self.twb_ref_c if twb_c is None else float(twb_c)
        q = self.heat_reject_mw_th(p)
        if qcw <= 0:
            tin = tout = t_sat = float("nan")
            pb = float("nan")
            ttd = float("nan")
            p_thermal = 0.0
            evap = blow = drift = makeup = 0.0
        else:
            tin = self.tower_outlet_c(twb_op, q, qcw, airflow_ratio)
            tout, t_sat, pb, ttd = self.condenser_state(q, qcw, tin)
            p_thermal = self._power_derate_from_backpressure(pb)
            evap, blow, drift, makeup = self.water_balance_m3s(q, qcw, tin)
        v0 = self.basin_design_volume_m3()
        vol = v0 if basin_volume_m3 is None else basin_volume_m3
        return PrototypeResult(
            cooling_type="wet_recirc",
            p_rated_mw=self.p_rated_mw,
            p_avail_mw=max(0.0, p_thermal),
            qcw_m3s=qcw,
            tin_c=tin,
            tout_c=tout,
            t_sat_c=t_sat,
            backpressure_kpa=pb,
            heat_reject_mw_th=q,
            basin_volume_m3=vol,
            basin_vmin_m3=self.basin_vmin_m3(),
            basin_level_m=self.basin_level_m(vol),
            basin_level_min_m=self.basin_level_min_m(),
            pb_design_kpa=self.reference_backpressure_kpa(),
            time_to_trip_h=self.time_to_trip_after_makeup_stop_h(),
            evaporation_m3s=evap,
            blowdown_m3s=blow,
            drift_m3s=drift,
            makeup_m3s=makeup,
            tower_approach_c=(tin - twb_op) if tin == tin else float("nan"),
            condenser_ttd_c=ttd,
            notes=(
                f"plant-calibratable cold end; Twb_op={twb_op:.2f}C; "
                f"pb_ref={self.reference_backpressure_kpa():.2f} kPa"
            ),
        )

    def evaluate(
        self,
        *,
        twb_c: float | None = None,
        qcw_frac: float = 1.0,
        qcw_m3s: float | None = None,
        airflow_ratio: float = 1.0,
        p_setpoint_mw: float | None = None,
        forced_outage: bool = False,
        basin_volume_m3: float | None = None,
        time_to_trip_h: float | None = None,
        notes_extra: str = "",
    ) -> PrototypeResult:
        """Solve available power self-consistently at a stated CW flow.

        Unlike the previous version, reduced circulating flow is not also
        imposed as a direct ``P <= P_rated*x`` cap.  Flow affects power only
        through tower/condenser temperatures and turbine backpressure.
        """
        v0 = self.basin_design_volume_m3()
        vmin = self.basin_vmin_m3()
        pb_ref = self.reference_backpressure_kpa()
        t_trip = self.time_to_trip_after_makeup_stop_h() if time_to_trip_h is None else time_to_trip_h
        twb_op = self.twb_ref_c if twb_c is None else float(twb_c)

        if forced_outage:
            note = "forced outage"
            if notes_extra:
                note = f"{note}; {notes_extra}"
            vol = vmin if basin_volume_m3 is None else basin_volume_m3
            return PrototypeResult(
                cooling_type="wet_recirc",
                p_rated_mw=self.p_rated_mw,
                p_avail_mw=0.0,
                qcw_m3s=0.0,
                tin_c=twb_op + self.approach_design_c,
                tout_c=twb_op + self.approach_design_c,
                t_sat_c=float("nan"),
                backpressure_kpa=float("nan"),
                heat_reject_mw_th=0.0,
                basin_volume_m3=vol,
                basin_vmin_m3=vmin,
                basin_level_m=self.basin_level_m(vol),
                basin_level_min_m=self.basin_level_min_m(),
                pb_design_kpa=pb_ref,
                time_to_trip_h=t_trip,
                notes=note,
            )

        qcw = self.qcw_design_m3s * qcw_frac if qcw_m3s is None else max(float(qcw_m3s), 0.0)
        p_limit = self.p_rated_mw if p_setpoint_mw is None else max(float(p_setpoint_mw), 0.0)
        if qcw <= 1e-12 or p_limit <= 0:
            result = self.predict_cold_end(
                0.0, qcw_m3s=max(qcw, 0.0), twb_c=twb_op, airflow_ratio=airflow_ratio,
                basin_volume_m3=basin_volume_m3,
            )
            return replace(result, p_avail_mw=0.0, time_to_trip_h=t_trip)

        p = p_limit
        result = self.predict_cold_end(
            p, qcw_m3s=qcw, twb_c=twb_op, airflow_ratio=airflow_ratio,
            basin_volume_m3=basin_volume_m3,
        )
        for _ in range(80):
            p_new = min(p_limit, result.p_avail_mw)
            # Damping prevents oscillation at very low CW flow.
            p_new = 0.5 * p + 0.5 * p_new
            if abs(p_new - p) < 1e-7:
                p = p_new
                break
            p = p_new
            result = self.predict_cold_end(
                p, qcw_m3s=qcw, twb_c=twb_op, airflow_ratio=airflow_ratio,
                basin_volume_m3=basin_volume_m3,
            )
        result = self.predict_cold_end(
            p, qcw_m3s=qcw, twb_c=twb_op, airflow_ratio=airflow_ratio,
            basin_volume_m3=basin_volume_m3,
        )
        note = (
            f"self-consistent cold end; approach={result.tower_approach_c:.2f}C; "
            f"TTD={result.condenser_ttd_c:.2f}C; pb_ref={pb_ref:.2f} kPa; "
            f"makeup={result.makeup_m3s:.4f} m3/s"
        )
        if notes_extra:
            note = f"{note}; {notes_extra}"
        return replace(
            result,
            p_avail_mw=max(0.0, min(p_limit, p)),
            time_to_trip_h=t_trip,
            notes=note,
        )

    def evaluate_makeup_basin_interrupt(
        self,
        t_eval_h: float | None = None,
        qcw_frac: float = 1.0,
    ) -> PrototypeResult:
        """
        Static/screening snapshot after external makeup stops.

        The level is advanced at the design loss (blowdown maintained), then
        pump flow and the self-consistent cold end are evaluated at that
        level.  For control/protection dynamics use ``cooling.dynamics``.
        """
        t_trip = self.time_to_trip_after_makeup_stop_h(qcw_frac=qcw_frac)
        v0 = self.basin_design_volume_m3()
        vmin = self.basin_vmin_m3()
        loss = self.makeup_m3s(self.qcw_design_m3s * qcw_frac)

        if t_eval_h is None:
            return self.evaluate(
                forced_outage=True,
                basin_volume_m3=vmin,
                time_to_trip_h=t_trip,
                notes_extra=(
                    f"makeup interrupt: basin depleted "
                    f"(t_trip={t_trip:.2f} h, V0={v0:.0f} m3, Vmin={vmin:.0f} m3, "
                    f"level_min={self.basin_level_min_m():.2f} m)"
                ),
            )

        vol = max(vmin, v0 - loss * t_eval_h * 3600.0)
        level = self.basin_level_m(vol)
        if t_eval_h >= t_trip or level <= self.basin_level_min_m() + 1e-12:
            return self.evaluate(
                forced_outage=True,
                basin_volume_m3=vmin,
                time_to_trip_h=t_trip,
                notes_extra=(
                    f"makeup interrupt at t={t_eval_h:.2f} h: "
                    f"basin at/below trip level (t_trip={t_trip:.2f} h)"
                ),
            )

        x_pump = self.pump_flow_fraction(level, self.design_inlet_c())
        return self.evaluate(
            qcw_frac=x_pump,
            basin_volume_m3=vol,
            time_to_trip_h=t_trip,
            notes_extra=(
                f"makeup interrupt at t={t_eval_h:.2f} h: "
                f"basin above trip level (V={vol:.0f} m3, "
                f"level={level:.2f} m, pump flow fraction={x_pump:.3f}, "
                f"t_trip={t_trip:.2f} h)"
            ),
        )

    def with_band(self, band: UncertaintyBand) -> "WetRecircPrototype500":
        return replace(self, band=band)


# Backward-compatible private name used by the previous dynamics module.
def _power_derate_from_backpressure(
    p_rated_mw: float,
    pb_kpa: float,
    pb_design_kpa: float,
    sens_per_kpa: float = 0.007,
) -> float:
    """Legacy linear helper retained for external reproducibility only."""
    dp = max(0.0, pb_kpa - pb_design_kpa)
    factor = max(0.0, 1.0 - sens_per_kpa * dp)
    if pb_kpa < pb_design_kpa:
        factor = min(1.02, 1.0 + 0.3 * sens_per_kpa * (pb_design_kpa - pb_kpa))
    return p_rated_mw * factor
