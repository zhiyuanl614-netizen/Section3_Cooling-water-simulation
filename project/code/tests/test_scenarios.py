"""Scenario layer: loader discipline, API compatibility, heterogeneity, bands."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scenarios import (
    COAL_WR_IDS,
    evaluate_scenario,
    load_scenarios,
    load_unit_config,
    load_unit_params,
)
from scenarios.fault_makeup_basin import build_unit_model

ROOT = Path(__file__).resolve().parents[1]


def test_unit_config_selects_exactly_the_two_mapped_units():
    units = load_unit_config()
    modelled = [u for u, c in units.items() if c.include_cold_end]
    assert sorted(modelled) == sorted(COAL_WR_IDS)
    assert all(units[u].cooling_type == "wet_recirc" for u in COAL_WR_IDS)


def test_scenario_loader_enforces_single_unit_scope():
    """G6: the documented hard limits stay hard."""
    rows = list(csv.DictReader(open(ROOT / "data" / "fault_scenarios_makeup_basin.csv", encoding="utf-8")))
    assert all(r["n_faulted"] == "1" for r in rows)
    assert {r["unit1_fault_mode"] for r in rows} == {"makeup_basin_interrupt"}

    bad = ROOT / "tests" / "_tmp_bad_scenarios.csv"
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        r = dict(rows[0])
        r["n_faulted"] = "2"
        r["faulted_units"] = "G33|G34"
        w.writerow(r.values())
    try:
        with pytest.raises(ValueError):
            load_scenarios(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_loader_rejects_unknown_band():
    bad = ROOT / "tests" / "_tmp_bad_band.csv"
    rows = list(csv.DictReader(open(ROOT / "data" / "fault_scenarios_makeup_basin.csv", encoding="utf-8")))
    with open(bad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        r = dict(rows[0])
        r["band"] = "medium"
        w.writerow(r)
    try:
        with pytest.raises(ValueError):
            load_scenarios(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_api_backward_compatibility():
    """G5: the documented keys are still there with the documented semantics."""
    from scenarios.fault_makeup_basin import ScenarioResult

    sc = load_scenarios()[0]
    out = evaluate_scenario(sc)
    assert isinstance(out, ScenarioResult)
    d = out.as_dict()
    for key in (
        "scenario_id",
        "fault_pattern",
        "n_faulted",
        "faulted_units",
        "capacity_lost_mw",
        "pavail_mw",
        "unit_details",
        "description",
    ):
        assert key in d
    assert d["n_faulted"] == 1
    assert set(d["pavail_mw"]) == set(load_unit_config())
    # dict-style access used by the original demo script
    assert out["scenario_id"] == sc.scenario_id
    assert out["pavail_mw"] == d["pavail_mw"]


def test_terminal_scenario_zeroes_the_faulted_unit_only():
    units = load_unit_config()
    for sc in load_scenarios():
        out = evaluate_scenario(sc)
        faulted = sc.faulted_units[0]
        assert out.pavail_mw[faulted] == pytest.approx(0.0)
        assert out.capacity_lost_mw == pytest.approx(units[faulted].pmax_mw)
        for uid, unit in units.items():
            if uid != faulted and unit.include_cold_end:
                assert out.pavail_mw[uid] == pytest.approx(unit.pmax_mw)


def test_timeseries_mode_returns_a_trajectory():
    sc = load_scenarios()[0]
    out = evaluate_scenario(sc, timeseries=True)
    faulted = sc.faulted_units[0]
    ts = out.timeseries[faulted]
    assert len(ts.t_h) > 10
    assert out.unit_details[faulted]["trip_mechanism"] in (
        "technical_minimum",
        "backpressure_protection",
        "pump_level",
    )
    assert out.unit_details[faulted]["time_to_trip_h"] == pytest.approx(ts.t_trip_h)


def test_midway_snapshot_is_positive_and_below_rated():
    sc = load_scenarios()[0]
    out = evaluate_scenario(sc, timeseries=True)
    faulted = sc.faulted_units[0]
    ts = out.timeseries[faulted]
    # a snapshot inside the derate window
    t_mid = (ts.t_derate_start_h or 0.0) + 0.2
    if t_mid < (ts.t_trip_h or 0.0):
        p = ts.p_avail_at(t_mid)
        assert 0.0 < p < ts.p_rated_mw


def test_heterogeneity_makes_the_units_distinct():
    """G4: the regional package differentiates the two mapped units."""
    sc_by_unit = {sc.faulted_units[0]: sc for sc in load_scenarios()}
    base = {u: evaluate_scenario(sc).unit_details[u]["time_to_trip_h"] for u, sc in sc_by_unit.items()}
    regional = {
        u: evaluate_scenario(sc, package="regional").unit_details[u]["time_to_trip_h"]
        for u, sc in sc_by_unit.items()
    }
    assert len({round(v, 3) for v in base.values()}) == 1, (
        "baseline package is intentionally homogeneous"
    )
    assert len({round(v, 3) for v in regional.values()}) == 2, (
        f"regional package must differentiate: {regional}"
    )


def test_band_orders_the_trip_time():
    """G4: the uncertainty band must actually move the failure timing."""
    from dataclasses import replace as dc_replace

    sc = load_scenarios()[0]
    fa = sc.faulted_units[0]
    trips = {}
    for band in ("low", "base", "high"):
        out = evaluate_scenario(dc_replace(sc, band=band), timeseries=True)
        trips[band] = out.unit_details[fa]["time_to_trip_h"]
        assert out.pavail_mw[fa] == pytest.approx(0.0)  # terminal state stays zero
    assert trips["low"] < trips["base"] < trips["high"], trips


def test_unit_params_loader_validates_packages():
    assert set(load_unit_params("baseline")) == set(COAL_WR_IDS)
    assert set(load_unit_params("regional")) == set(COAL_WR_IDS)
    with pytest.raises(ValueError):
        load_unit_params("does-not-exist")


def test_regional_package_carries_source_notes():
    for p in load_unit_params("regional").values():
        assert "GB/T 50102" in p.source_note
        assert p.calibration_status == "reference_template_not_site_measured"
        assert len(p.source_note) > 40


def test_model_builder_applies_site_parameters():
    units = load_unit_config()
    params = load_unit_params("regional")
    m = build_unit_model(units["G33"], band="base", params=params)
    assert m.twb_ref_c == pytest.approx(25.5)
    assert m.basin_area_m2 == pytest.approx(3600.0)
    assert m.tower_characteristic_mult == pytest.approx(0.98)
    assert m.condenser_cleanliness == pytest.approx(0.98)
    assert m.p_rated_mw == pytest.approx(652.0)
    # scaling still holds: flow scales with capacity, intensities do not
    assert m.qcw_design_m3s == pytest.approx(15.77 * 652 / 500)
    assert m.basin_level_min_m() == pytest.approx(1.0)
    assert m.basin_holdup_h > 0  # derived diagnostic, not a package input
