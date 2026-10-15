"""Map cold-end evaluation to generator available power for IEEE39 OPF."""

from __future__ import annotations

from .prototype_500mw import PrototypeResult


def available_power_mw(result: PrototypeResult, pmax_mw: float | None = None) -> float:
    """
    Clamp cold-end Pavail to unit Pmax (and non-negative).

    Use this value to overwrite MATPOWER/Pandapower generator Pmax for OPF.
    """
    cap = result.p_rated_mw if pmax_mw is None else pmax_mw
    return float(max(0.0, min(cap, result.p_avail_mw)))
