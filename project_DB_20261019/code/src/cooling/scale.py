"""Scale the 500 MW wet-recirc prototype to IEEE39 unit ratings."""

from __future__ import annotations

from dataclasses import replace

from .prototype_500mw import WetRecircPrototype500


def scale_prototype_to_unit(
    prototype: WetRecircPrototype500,
    pmax_mw: float,
    gen_id: str | None = None,
) -> WetRecircPrototype500:
    """
    Capacity scaling for the reference template.

    Extensive quantities scale with ``s = Pmax / P_rated``:

    * design circulating-water flow;
    * condenser heat rejection (through rated power);
    * basin plan area (hence inventory at fixed level datum).

    Intensive/calibration quantities remain fixed unless a unit parameter
    package overrides them after scaling: efficiency, tower/condenser
    characteristics, wet-bulb reference, CoC, water levels, pump NPSH and
    protection/control settings.  This is a modelling assumption, not a
    substitute for unit-specific plant calibration.
    """
    ref = prototype.p_rated_mw
    if ref <= 0:
        raise ValueError("prototype.p_rated_mw must be positive")
    s = pmax_mw / ref
    return replace(
        prototype,
        p_rated_mw=pmax_mw,
        qcw_design_m3s=prototype.qcw_design_m3s * s,
        basin_area_m2=prototype.basin_area_m2 * s,
        gen_id=gen_id if gen_id is not None else prototype.gen_id,
    )
