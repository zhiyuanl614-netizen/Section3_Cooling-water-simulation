"""Scale 500 MW wet-recirc prototype to IEEE39 unit ratings."""

from __future__ import annotations

from dataclasses import replace

from .prototype_500mw import WetRecircPrototype500


def scale_prototype_to_unit(
    prototype: WetRecircPrototype500,
    pmax_mw: float,
) -> WetRecircPrototype500:
    """
    Capacity scaling: flow and heat scale with P; intensive temps / approach / CoC stay fixed.
    """
    ref = prototype.p_rated_mw
    if ref <= 0:
        raise ValueError("prototype.p_rated_mw must be positive")
    s = pmax_mw / ref
    return replace(
        prototype,
        p_rated_mw=pmax_mw,
        qcw_design_m3s=prototype.qcw_design_m3s * s,
    )
