"""Plant-calibratable cold-end invariants and physical closure checks."""

from __future__ import annotations

import math

import pytest

from cooling.prototype_500mw import (
    WetRecircPrototype500,
    _sat_pressure_kpa,
    _sat_temperature_c,
    band_factors,
)


def test_reference_point_is_exactly_consistent_in_base_band():
    m = WetRecircPrototype500(band="base")
    r = m.evaluate()
    assert r.p_avail_mw == pytest.approx(m.p_rated_mw, abs=1e-6)
    assert r.tin_c == pytest.approx(m.design_inlet_c())
    assert r.condenser_ttd_c == pytest.approx(m.ttd_design_c)


def test_band_degrades_equipment_without_moving_reference_point():
    base = WetRecircPrototype500(band="base")
    low = WetRecircPrototype500(band="low")
    high = WetRecircPrototype500(band="high")
    assert low.reference_backpressure_kpa() == pytest.approx(base.reference_backpressure_kpa())
    assert low.evaluate().p_avail_mw < base.evaluate().p_avail_mw
    # High band may have thermal capability above rated, but delivered
    # available power is capped at the setpoint/rating.
    assert high.evaluate().p_avail_mw == pytest.approx(high.p_rated_mw)


def test_reference_backpressure_is_derived_from_fixed_chain():
    m = WetRecircPrototype500()
    expected = _sat_pressure_kpa(
        m.design_inlet_c() + m.design_delta_t_c() + m.ttd_design_c
    )
    assert m.reference_backpressure_kpa() == pytest.approx(expected, rel=1e-12)
    assert m.reference_backpressure_kpa() == pytest.approx(7.5623, abs=1e-3)


def test_explicit_reference_override_is_possible_but_capped():
    m = WetRecircPrototype500(pb_ref_kpa=9.5)
    assert m.reference_backpressure_kpa() == pytest.approx(9.5)
    # Thermal capability can exceed the nameplate under the inconsistent
    # override, but evaluate() must not deliver above the setpoint.
    assert m.predict_cold_end().p_avail_mw > m.p_rated_mw
    assert m.evaluate().p_avail_mw == pytest.approx(m.p_rated_mw)


def test_operating_weather_is_separate_from_reference_point():
    m = WetRecircPrototype500()
    ref = m.reference_backpressure_kpa()
    hot = m.evaluate(twb_c=28.5)
    assert m.reference_backpressure_kpa() == pytest.approx(ref)
    assert hot.p_avail_mw < m.p_rated_mw
    assert hot.backpressure_kpa > ref


def test_saturation_helpers_are_inverse():
    for t in (20.0, 35.0, 40.46, 55.0):
        p = _sat_pressure_kpa(t)
        assert _sat_temperature_c(p) == pytest.approx(t, abs=1e-6)


def test_evaporation_closes_the_tower_heat_balance():
    m = WetRecircPrototype500()
    q = m.heat_reject_mw_th()
    e, b, d, makeup = m.water_balance_m3s(q, m.qcw_design_m3s, m.design_inlet_c())
    latent_mw = e * m.rho * m.latent_heat_j_per_kg(m.design_inlet_c()) / 1e6
    assert latent_mw / q == pytest.approx(m.evap_heat_fraction, rel=1e-9)
    assert 0.20 < e < 0.30  # m3/s for the 500 MW reference point
    assert makeup == pytest.approx(e + b + d)
    # Salt balance with explicit drift: CoC = M/(B+D).
    assert makeup / (b + d) == pytest.approx(m.cycles_of_concentration, rel=1e-12)
    assert makeup == pytest.approx(e * m.cycles_of_concentration / (m.cycles_of_concentration - 1.0))


def test_part_load_heat_rate_worsens():
    m = WetRecircPrototype500()
    design_ratio = m.heat_reject_mw_th(500.0) / 500.0
    partload_ratio = m.heat_reject_mw_th(200.0) / 200.0
    assert partload_ratio > design_ratio


def test_tower_and_condenser_parameters_are_really_wired():
    base = WetRecircPrototype500()
    poor_tower = WetRecircPrototype500(tower_characteristic_mult=0.8)
    dirty_condenser = WetRecircPrototype500(condenser_cleanliness=0.85)
    assert poor_tower.predict_cold_end().tin_c > base.predict_cold_end().tin_c
    assert dirty_condenser.predict_cold_end().condenser_ttd_c > base.predict_cold_end().condenser_ttd_c
    assert dirty_condenser.predict_cold_end().backpressure_kpa > base.predict_cold_end().backpressure_kpa


def test_reduced_cw_flow_derates_through_backpressure_not_a_flow_cap():
    m = WetRecircPrototype500()
    r = m.evaluate(qcw_frac=0.6)
    # A direct P<=0.6*Prated cap would give <=300 MW.  The UA/tower model
    # instead gives a much smaller thermal derate at this flow.
    assert r.p_avail_mw > 400.0
    assert r.backpressure_kpa > m.reference_backpressure_kpa()


def test_basin_geometry_is_independent_and_holdup_is_derived():
    m = WetRecircPrototype500()
    assert m.basin_area_effective_m2() == pytest.approx(m.basin_area_m2)
    assert m.basin_design_volume_m3() == pytest.approx(
        m.basin_area_m2 * m.basin_level_normal_m
    )
    assert m.basin_vmin_m3() == pytest.approx(m.basin_area_m2 * m.basin_level_trip_m)
    assert m.basin_level_min_m() == pytest.approx(m.basin_level_trip_m)
    usable = m.basin_design_volume_m3() - m.basin_vmin_m3()
    assert m.basin_holdup_h == pytest.approx(
        usable / m.makeup_m3s(m.qcw_design_m3s) / 3600.0
    )
    assert m.time_to_trip_after_makeup_stop_h() == pytest.approx(m.basin_holdup_h)


def test_pump_flow_is_monotone_in_level_and_trips_at_low_level():
    m = WetRecircPrototype500()
    levels = [1.01, 1.5, 2.0, 2.5, 3.0, 3.5]
    flows = [m.pump_flow_fraction(h, 25.0) for h in levels]
    assert all(b >= a for a, b in zip(flows, flows[1:]))
    assert flows[-1] == pytest.approx(1.0)
    assert m.pump_flow_fraction(m.basin_level_trip_m, 25.0) == 0.0


def test_legacy_level_band_remains_available_as_fallback():
    m = WetRecircPrototype500()
    assert m.qcw_frac_from_level(2.0) == 1.0
    assert m.qcw_frac_from_level(1.2) == 0.0
    assert m.qcw_frac_from_level(1.45) == pytest.approx(0.5)


def test_band_factors_are_ordered_and_defined():
    low, base, high = (band_factors(b) for b in ("low", "base", "high"))
    assert low["tower"] < base["tower"] < high["tower"]
    assert low["condenser"] < base["condenser"] < high["condenser"]
    assert low["basin_area"] < base["basin_area"] < high["basin_area"]
    assert low["evap_heat"] > base["evap_heat"] > high["evap_heat"]
    with pytest.raises(ValueError):
        band_factors("nonsense")  # type: ignore[arg-type]


def test_heat_rejection_formula_uses_waste_heat_split():
    m = WetRecircPrototype500()
    expected = 500 * (1 / 0.38 - 1) * 0.92
    assert m.heat_reject_mw_th() == pytest.approx(expected)
    assert abs(m.design_delta_t_c() - m.range_design_c) < 1e-9
    assert not math.isnan(m.evaluate().t_sat_c)


def test_invalid_physical_parameters_are_rejected():
    with pytest.raises(ValueError):
        WetRecircPrototype500(cycles_of_concentration=1.0)
    with pytest.raises(ValueError):
        WetRecircPrototype500(basin_level_trip_m=3.5, basin_level_normal_m=3.5)
    with pytest.raises(ValueError):
        WetRecircPrototype500(basin_area_m2=0.0)


def test_zero_circulating_flow_is_a_clean_terminal_state():
    m = WetRecircPrototype500()
    r = m.evaluate(qcw_frac=0.0)
    assert r.p_avail_mw == 0.0
    assert r.qcw_m3s == 0.0
    assert r.evaporation_m3s == r.blowdown_m3s == r.drift_m3s == r.makeup_m3s == 0.0


def test_pump_npsh_parameter_changes_low_level_flow():
    base = WetRecircPrototype500()
    high_npshr = WetRecircPrototype500(pump_npshr_design_m=14.0)
    assert high_npshr.pump_flow_fraction(1.5, 25.0) < base.pump_flow_fraction(1.5, 25.0)
