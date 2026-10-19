"""Finite-storage condenser surrogate with the existing UA–LMTD steady limit.

All heat rates MW, conductance MW/K, capacitance MJ/K, time seconds.
No protection setting appears in these process equations. This is a reference-
anchored lumped closure, not an empirically calibrated condenser model.
"""
from dataclasses import dataclass
import math
from .prototype_500mw import WetRecircPrototype500


class NoQuasiStaticEquilibrium(ValueError):
    """Positive steam duty and zero water removal have no finite steady state."""


@dataclass(frozen=True)
class CondenserExchange:
    water_capacity_mw_per_k: float
    conductance_mw_per_k: float

    def water_heat_mw(self, tsat_c: float, tin_c: float) -> float:
        return self.conductance_mw_per_k*(tsat_c-tin_c)

    def outlet_c(self, tsat_c: float, tin_c: float) -> float:
        if self.water_capacity_mw_per_k==0:
            return float('nan')  # no flowing outlet, not the steam saturation state
        return tin_c+self.water_heat_mw(tsat_c,tin_c)/self.water_capacity_mw_per_k


def condenser_exchange(model: WetRecircPrototype500, flow_m3s: float,
                       *, clean_design: bool=False) -> CondenserExchange:
    if not math.isfinite(flow_m3s) or flow_m3s<0:
        raise ValueError('finite nonnegative water flow required')
    w=model.rho*model.cp*flow_m3s/1e6
    if w==0:return CondenserExchange(0.,0.)
    x=flow_m3s/model.qcw_design_m3s
    clean=1. if clean_design else model._condenser_cleanliness_eff()
    ua=model.condenser_ua_design_mw_per_k()*clean*x**model.condenser_u_flow_exp
    g=w*(-math.expm1(-ua/w))
    return CondenserExchange(w,g)


def condenser_capacity_mj_per_k(model: WetRecircPrototype500, tau_s: float) -> float:
    if not math.isfinite(tau_s) or tau_s<0:raise ValueError('finite nonnegative reference tau required')
    return tau_s*condenser_exchange(model,model.qcw_design_m3s,clean_design=True).conductance_mw_per_k


@dataclass(frozen=True)
class ThermalAdvance:
    tsat_c: float
    mean_water_heat_mw: float
    energy_residual_mj: float


def advance_condenser(tsat_c: float, tin_c: float, steam_mw: float,
                      conductance_mw_per_k: float, capacity_mj_per_k: float,
                      dt_s: float) -> ThermalAdvance:
    """Exact constant-input interval solution, including its integral water duty."""
    if not all(math.isfinite(x) for x in [tsat_c,tin_c,steam_mw,conductance_mw_per_k,capacity_mj_per_k,dt_s]):
        raise ValueError('non-finite condenser state/input')
    if min(steam_mw,conductance_mw_per_k,capacity_mj_per_k)<0 or dt_s<=0:
        raise ValueError('nonnegative heat/G/C and positive dt required')
    g,c=conductance_mw_per_k,capacity_mj_per_k
    if c==0:
        if g==0:
            if steam_mw>0:raise NoQuasiStaticEquilibrium('zero flow/zero storage/positive steam: no finite quasi-static condenser state')
            return ThermalAdvance(tsat_c,0.,0.)
        return ThermalAdvance(tin_c+steam_mw/g,steam_mw,0.)
    z=g*dt_s/c
    if z<1e-7:
        phi=1-z/2+z*z/6-z*z*z/24
        one_minus_phi=z/2-z*z/6+z*z*z/24
    else:
        phi=-math.expm1(-z)/z
        one_minus_phi=1-phi
    alpha=-math.expm1(-z)
    new=tsat_c+alpha*(tin_c-tsat_c)+(steam_mw/c)*dt_s*phi
    removed=g*(tsat_c-tin_c)*phi+steam_mw*one_minus_phi
    residual=c*(new-tsat_c)-dt_s*(steam_mw-removed)
    return ThermalAdvance(new,removed,residual)
