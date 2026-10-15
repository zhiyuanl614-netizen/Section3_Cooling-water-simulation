"""Framework v0.3 scenario registry and cascade coupling."""

from __future__ import annotations

from scenarios.framework_coupling import (
    get_scenario,
    load_framework_scenarios,
    run_framework_scenario,
)


def test_registry_loads_expected_ids():
    specs = load_framework_scenarios()
    ids = {s.scenario_id for s in specs}
    assert {"S0", "S1a", "S2", "G1", "G2", "G4"} <= ids


def test_s2_full_pump_trips_on_backpressure():
    result = run_framework_scenario("S2")
    assert result.units[0].trip_mechanism == "backpressure_protection"
    assert result.units[0].t_trip_h is not None
    assert result.units[0].t_trip_h * 60.0 < 5.0


def test_g1_single_trip_no_cascade():
    result = run_framework_scenario("G1")
    assert result.cascade is not None
    assert result.cascade.cascade_triggered is False
    assert result.final_pg[33] == 0.0


def test_g2_dual_pump_trip_cascades():
    result = run_framework_scenario("G2")
    assert result.cascade is not None
    assert result.cascade.cascade_triggered is True
    assert result.cascade.n_removed >= 5
    assert result.final_pg[33] == 0.0
    assert result.final_pg[34] == 0.0


def test_s1a_isolates_later_than_s1b():
    a = run_framework_scenario("S1a")
    b = run_framework_scenario(get_scenario("S1b"))
    assert a.units[0].t_trip_h is not None
    assert b.units[0].t_trip_h is not None
    assert a.units[0].t_trip_h > b.units[0].t_trip_h + 0.4
