"""
Per-unit plant-calibration parameters.

The previous package manufactured basin volume from an assumed ``holdup``
time.  This package instead carries independently replaceable plant anchors:

* thermal anchors applied before capacity scaling (reference wet bulb, CoC,
  tower characteristic and condenser cleanliness);
* plant anchors applied after capacity scaling (actual basin area/levels,
  pump NPSHr and protection/control settings).

Every shipped row is marked ``reference_template_not_site_measured``.  Those
words are part of the data contract: replace the values with plant drawings,
manufacturer curves, protection settings and historian fits before calling
a unit site-calibrated.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path

from cooling.prototype_500mw import WetRecircPrototype500

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS_CSV = ROOT / "data" / "unit_thermal_hydraulic_params.csv"

REQUIRED_COLUMNS = (
    "package",
    "gen_id",
    "calibration_status",
    "twb_ref_c",
    "cycles_of_concentration",
    "basin_area_m2",
    "basin_level_normal_m",
    "basin_level_trip_m",
    "tower_characteristic_mult",
    "condenser_cleanliness",
    "pump_npshr_design_m",
    "p_min_tech_frac",
    "pb_trip_kpa",
    "source_note",
)


@dataclass(frozen=True)
class UnitIntensiveParams:
    """Plant-calibration anchors for one unit (name kept for API continuity)."""

    package: str
    gen_id: str
    calibration_status: str
    twb_ref_c: float
    cycles_of_concentration: float
    basin_area_m2: float
    basin_level_normal_m: float
    basin_level_trip_m: float
    tower_characteristic_mult: float
    condenser_cleanliness: float
    pump_npshr_design_m: float
    p_min_tech_frac: float
    pb_trip_kpa: float
    source_note: str = ""


def load_unit_params(
    package: str = "baseline",
    path: Path | str = DEFAULT_PARAMS_CSV,
) -> dict[str, UnitIntensiveParams]:
    """Load the plant-calibration parameter package for every unit."""
    out: dict[str, UnitIntensiveParams] = {}
    available: set[str] = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        for row in reader:
            available.add(row["package"])
            if row["package"] != package:
                continue
            out[row["gen_id"]] = UnitIntensiveParams(
                package=row["package"],
                gen_id=row["gen_id"],
                calibration_status=row["calibration_status"],
                twb_ref_c=float(row["twb_ref_c"]),
                cycles_of_concentration=float(row["cycles_of_concentration"]),
                basin_area_m2=float(row["basin_area_m2"]),
                basin_level_normal_m=float(row["basin_level_normal_m"]),
                basin_level_trip_m=float(row["basin_level_trip_m"]),
                tower_characteristic_mult=float(row["tower_characteristic_mult"]),
                condenser_cleanliness=float(row["condenser_cleanliness"]),
                pump_npshr_design_m=float(row["pump_npshr_design_m"]),
                p_min_tech_frac=float(row["p_min_tech_frac"]),
                pb_trip_kpa=float(row["pb_trip_kpa"]),
                source_note=row["source_note"],
            )
    if not out:
        raise ValueError(
            f"package {package!r} not found in {path}; available: {sorted(available)}"
        )
    return out


def apply_thermal_unit_params(
    model: WetRecircPrototype500,
    params: UnitIntensiveParams,
) -> WetRecircPrototype500:
    """Apply intensive thermal anchors before capacity scaling."""
    return replace(
        model,
        gen_id=params.gen_id,
        twb_ref_c=params.twb_ref_c,
        cycles_of_concentration=params.cycles_of_concentration,
        tower_characteristic_mult=params.tower_characteristic_mult,
        condenser_cleanliness=params.condenser_cleanliness,
    )


def apply_plant_unit_params(
    model: WetRecircPrototype500,
    params: UnitIntensiveParams,
) -> WetRecircPrototype500:
    """Apply actual plant geometry/protection anchors after scaling."""
    return replace(
        model,
        gen_id=params.gen_id,
        basin_area_m2=params.basin_area_m2,
        basin_level_normal_m=params.basin_level_normal_m,
        basin_level_trip_m=params.basin_level_trip_m,
        pump_npshr_design_m=params.pump_npshr_design_m,
        p_min_tech_frac=params.p_min_tech_frac,
        pb_trip_kpa=params.pb_trip_kpa,
    )


def apply_unit_params(
    model: WetRecircPrototype500,
    params: UnitIntensiveParams,
) -> WetRecircPrototype500:
    """Apply thermal and plant anchors to an already-sized model."""
    return apply_plant_unit_params(apply_thermal_unit_params(model, params), params)
