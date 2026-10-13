"""
500 MWe coal wet-recirculating cold-end prototype (engineering calibration).

Includes a collecting-basin (集水池) water-balance model for external makeup
interruption: when the external source stops feeding the basin, inventory
declines with evaporation + blowdown until the minimum operating level,
then circulating pumps trip and available power goes to zero.

Design points follow EPRI / NETL / IECM order-of-magnitude values.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal


UncertaintyBand = Literal["base", "low", "high"]


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
    time_to_trip_h: float = float("nan")
    notes: str = ""


def _band_factor(band: UncertaintyBand) -> float:
    return {"base": 1.0, "low": 0.8, "high": 1.2}[band]


def _sat_pressure_kpa(t_sat_c: float) -> float:
    """Magnus approximation for water vapor pressure (valid ~20–60 C)."""
    return 0.6108 * (2.718281828 ** (17.27 * t_sat_c / (t_sat_c + 237.3)))


def _power_derate_from_backpressure(
    p_rated_mw: float,
    pb_kpa: float,
    pb_design_kpa: float,
    sens_per_kpa: float = 0.007,
) -> float:
    dp = max(0.0, pb_kpa - pb_design_kpa)
    factor = max(0.0, 1.0 - sens_per_kpa * dp)
    if pb_kpa < pb_design_kpa:
        factor = min(1.02, 1.0 + 0.3 * sens_per_kpa * (pb_design_kpa - pb_kpa))
    return p_rated_mw * factor


@dataclass
class WetRecircPrototype500:
    """Wet recirculating (湿冷循环) cooling prototype for a 500 MWe coal unit."""

    p_rated_mw: float = 500.0
    eta_net: float = 0.38
    aux_frac: float = 0.05
    qcw_design_m3s: float = 15.77
    range_design_c: float = 11.1
    approach_design_c: float = 5.55
    twb_design_c: float = 20.0
    ttd_c: float = 3.5
    pb_design_kpa: float = 9.5
    rho: float = 997.0
    cp: float = 4180.0
    me_design: float = 1.6
    evap_frac: float = 0.00155
    cycles_of_concentration: float = 4.0
    backpressure_sens: float = 0.007
    band: UncertaintyBand = "base"
    # Collecting basin (集水池): useful holdup expressed as hours of design makeup
    basin_holdup_h: float = 6.0
    basin_vmin_frac: float = 0.15

    def heat_reject_mw_th(self, p_mw: float | None = None) -> float:
        p = self.p_rated_mw if p_mw is None else p_mw
        eta = max(self.eta_net, 1e-6)
        return p * (1.0 - eta - self.aux_frac) / eta

    def makeup_m3s(self, qcw_m3s: float) -> float:
        """Design makeup = evaporation + blowdown (drift neglected)."""
        e = self.evap_frac * qcw_m3s
        b = e / max(self.cycles_of_concentration - 1.0, 0.1)
        return e + b

    def basin_design_volume_m3(self) -> float:
        """Useful basin volume ≈ holdup_hours × design makeup rate."""
        return self.makeup_m3s(self.qcw_design_m3s) * self.basin_holdup_h * 3600.0

    def basin_vmin_m3(self) -> float:
        return self.basin_vmin_frac * self.basin_design_volume_m3()

    def time_to_trip_after_makeup_stop_h(self, qcw_frac: float = 1.0) -> float:
        """
        Hours from makeup interrupt (外来水源停止) until basin hits Vmin.

        Net loss rate ≈ evaporation + blowdown at the circulating flow still running.
        """
        loss = self.makeup_m3s(self.qcw_design_m3s * max(qcw_frac, 1e-6))
        if loss <= 0:
            return float("inf")
        usable = self.basin_design_volume_m3() - self.basin_vmin_m3()
        return usable / loss / 3600.0

    def _approach(self, me: float, qcw_frac: float) -> float:
        me_eff = max(me, 0.2)
        return self.approach_design_c * (self.me_design / me_eff) * (0.85 + 0.15 * qcw_frac)

    def evaluate(
        self,
        *,
        twb_c: float | None = None,
        qcw_frac: float = 1.0,
        qcw_m3s: float | None = None,
        me_frac: float = 1.0,
        forced_outage: bool = False,
        basin_volume_m3: float | None = None,
        time_to_trip_h: float | None = None,
        notes_extra: str = "",
    ) -> PrototypeResult:
        v0 = self.basin_design_volume_m3()
        vmin = self.basin_vmin_m3()
        t_trip = (
            self.time_to_trip_after_makeup_stop_h()
            if time_to_trip_h is None
            else time_to_trip_h
        )

        if forced_outage:
            twb = self.twb_design_c if twb_c is None else twb_c
            note = "forced outage"
            if notes_extra:
                note = f"{note}; {notes_extra}"
            return PrototypeResult(
                cooling_type="wet_recirc",
                p_rated_mw=self.p_rated_mw,
                p_avail_mw=0.0,
                qcw_m3s=0.0,
                tin_c=twb + self.approach_design_c,
                tout_c=twb + self.approach_design_c,
                t_sat_c=float("nan"),
                backpressure_kpa=float("nan"),
                heat_reject_mw_th=0.0,
                basin_volume_m3=vmin if basin_volume_m3 is None else basin_volume_m3,
                basin_vmin_m3=vmin,
                time_to_trip_h=t_trip,
                notes=note,
            )

        twb = self.twb_design_c if twb_c is None else twb_c
        qcw = self.qcw_design_m3s * qcw_frac if qcw_m3s is None else qcw_m3s
        qcw = max(qcw, 1e-6)

        me = self.me_design * me_frac * _band_factor(self.band)
        approach = self._approach(me, qcw / self.qcw_design_m3s)
        tin = twb + approach

        qc_w = self.heat_reject_mw_th() * 1e6
        delta_t = qc_w / (self.rho * self.cp * qcw)
        tout = tin + delta_t
        t_sat = tout + self.ttd_c
        pb = _sat_pressure_kpa(t_sat)

        p_therm = _power_derate_from_backpressure(
            self.p_rated_mw, pb, self.pb_design_kpa, self.backpressure_sens
        )
        hyd_cap = min(1.0, qcw / self.qcw_design_m3s)

        if qcw / self.qcw_design_m3s <= 0.05:
            p_avail = 0.0
            note = "CW flow below trip threshold"
        else:
            p_avail = p_therm * hyd_cap
            note = (
                f"wet-recirc; approach={approach:.2f}C; "
                f"makeup_des~={self.makeup_m3s(qcw):.4f} m3/s"
            )
        if notes_extra:
            note = f"{note}; {notes_extra}"

        return PrototypeResult(
            cooling_type="wet_recirc",
            p_rated_mw=self.p_rated_mw,
            p_avail_mw=max(0.0, p_avail),
            qcw_m3s=qcw,
            tin_c=tin,
            tout_c=tout,
            t_sat_c=t_sat,
            backpressure_kpa=pb,
            heat_reject_mw_th=self.heat_reject_mw_th(),
            basin_volume_m3=v0 if basin_volume_m3 is None else basin_volume_m3,
            basin_vmin_m3=vmin,
            time_to_trip_h=t_trip,
            notes=note,
        )

    def evaluate_makeup_basin_interrupt(
        self,
        t_eval_h: float | None = None,
        qcw_frac: float = 1.0,
    ) -> PrototypeResult:
        """
        External makeup source stops feeding the collecting basin.

        - t_eval_h is None  → evaluate terminal state after basin trip (Pavail=0)
        - t_eval_h given    → snapshot at that hour after interrupt
        """
        t_trip = self.time_to_trip_after_makeup_stop_h(qcw_frac=qcw_frac)
        v0 = self.basin_design_volume_m3()
        vmin = self.basin_vmin_m3()
        loss = self.makeup_m3s(self.qcw_design_m3s * qcw_frac)

        if t_eval_h is None:
            return self.evaluate(
                qcw_frac=qcw_frac,
                forced_outage=True,
                basin_volume_m3=vmin,
                time_to_trip_h=t_trip,
                notes_extra=(
                    f"makeup interrupt: basin depleted "
                    f"(t_trip={t_trip:.2f} h, V0={v0:.0f} m3, Vmin={vmin:.0f} m3)"
                ),
            )

        vol = max(vmin, v0 - loss * t_eval_h * 3600.0)
        if t_eval_h >= t_trip or vol <= vmin + 1e-9:
            return self.evaluate(
                qcw_frac=qcw_frac,
                forced_outage=True,
                basin_volume_m3=vmin,
                time_to_trip_h=t_trip,
                notes_extra=(
                    f"makeup interrupt at t={t_eval_h:.2f} h: "
                    f"basin at/below Vmin (t_trip={t_trip:.2f} h)"
                ),
            )

        return self.evaluate(
            qcw_frac=qcw_frac,
            basin_volume_m3=vol,
            time_to_trip_h=t_trip,
            notes_extra=(
                f"makeup interrupt at t={t_eval_h:.2f} h: "
                f"basin still above Vmin (V={vol:.0f} m3, t_trip={t_trip:.2f} h)"
            ),
        )

    def with_band(self, band: UncertaintyBand) -> "WetRecircPrototype500":
        return replace(self, band=band)
