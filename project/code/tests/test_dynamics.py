"""Plant-calibratable basin-drain dynamics."""

from __future__ import annotations

import pytest

from cooling.dynamics import simulate_makeup_interrupt
from cooling.prototype_500mw import WetRecircPrototype500


def _proto(**kw) -> WetRecircPrototype500:
    return WetRecircPrototype500(**kw)


def test_trajectory_is_monotone_and_trips():
    ts = simulate_makeup_interrupt(_proto(), strategy="ride_down")
    assert ts.t_trip_h is not None
    assert ts.t_h[0] == 0.0
    for a, b in zip(ts.p_avail_mw, ts.p_avail_mw[1:]):
        assert b <= a + 1e-9
    for a, b in zip(ts.level_m, ts.level_m[1:]):
        assert b <= a + 1e-9
    assert ts.p_avail_mw[-1] == pytest.approx(0.0)
    assert ts.p_avail_at(0.0) == pytest.approx(ts.p_rated_mw, rel=1e-6)


def test_derate_starts_hours_after_fault_not_at_the_old_level_band_only():
    ts = simulate_makeup_interrupt(_proto(), strategy="ride_down")
    assert ts.t_derate_start_h is not None
    assert 2.0 < ts.t_derate_start_h < 3.5


def test_reference_ride_down_ends_at_pump_level_after_sop_shed():
    ts = simulate_makeup_interrupt(_proto(), strategy="ride_down")
    assert ts.trip_mechanism == "pump_level"
    assert ts.t_trip_h == pytest.approx(5.07, abs=0.25)
    # The SOP has brought the unit close to technical minimum by pump trip.
    assert ts.p_avail_at(ts.t_trip_h - 0.05) < 220.0


def test_reference_hold_load_also_reaches_pump_level_with_reference_pump_curve():
    ts = simulate_makeup_interrupt(_proto(), strategy="hold_load")
    assert ts.trip_mechanism == "pump_level"
    assert ts.t_trip_h == pytest.approx(4.29, abs=0.25)


def test_strategies_now_differ_materially_in_timing():
    a = simulate_makeup_interrupt(_proto(), strategy="ride_down")
    b = simulate_makeup_interrupt(_proto(), strategy="hold_load")
    assert abs(a.t_trip_h - b.t_trip_h) * 60 > 30.0


def test_low_vacuum_protection_can_still_act_first():
    m = _proto()
    ts = simulate_makeup_interrupt(m, strategy="hold_load", pb_trip_kpa=7.8)
    assert ts.trip_mechanism == "backpressure_protection"
    assert ts.t_trip_h < simulate_makeup_interrupt(m, strategy="hold_load").t_trip_h


def test_pump_trip_when_sop_and_other_limits_are_disabled():
    ts = simulate_makeup_interrupt(
        _proto(),
        strategy="ride_down",
        pump_model="level_band",
        derate_lo_m=0.0,
        derate_hi_m=0.0,
        use_operator_sop=False,
        p_min_tech_frac=0.0,
        pb_trip_kpa=1.0e9,
    )
    assert ts.trip_mechanism == "pump_level"
    assert 3.5 < ts.t_trip_h < 5.5


def test_design_frozen_loss_reproduces_the_analytic_drain_time():
    m = _proto()
    ts = simulate_makeup_interrupt(
        m,
        strategy="ride_down",
        loss_basis="design_frozen",
        pump_model="level_band",
        derate_lo_m=0.0,
        derate_hi_m=0.0,
        use_operator_sop=False,
        p_min_tech_frac=0.0,
        pb_trip_kpa=1.0e9,
    )
    assert ts.t_trip_h == pytest.approx(m.time_to_trip_after_makeup_stop_h(), abs=0.05)


def test_blowdown_isolation_conserves_inventory():
    m = _proto()
    common = dict(
        strategy="ride_down",
        pump_model="level_band",
        derate_lo_m=0.0,
        derate_hi_m=0.0,
        use_operator_sop=False,
        p_min_tech_frac=0.0,
        pb_trip_kpa=1.0e9,
    )
    maintain = simulate_makeup_interrupt(m, blowdown_policy="maintain", **common)
    isolate = simulate_makeup_interrupt(m, blowdown_policy="isolate_on_detection", **common)
    assert isolate.t_trip_h > maintain.t_trip_h + 0.5


def test_ramp_limit_bounds_the_delivered_power_slope():
    m = _proto()
    ts = simulate_makeup_interrupt(m, strategy="ride_down")
    max_step = m.max_ramp_frac_per_min * m.p_rated_mw * (ts.sample_dt_s / 60.0)
    diffs = [a - b for a, b in zip(ts.p_avail_mw, ts.p_avail_mw[1:])]
    # Ignore the terminal protection/pump-trip sample, which is a true trip.
    assert max(diffs[:-1]) <= max_step + 1e-6


def test_timeseries_rows_include_calibration_outputs():
    ts = simulate_makeup_interrupt(_proto(), strategy="ride_down")
    rows = ts.rows()
    assert rows and set(rows[0]) >= {
        "gen_id", "t_h", "p_avail_mw", "p_capability_mw", "qcw_frac",
        "tin_c", "tout_c", "evaporation_m3s", "water_loss_m3s",
    }
    assert all(isinstance(r["t_h"], float) for r in rows)


def test_unknown_strategy_is_rejected():
    with pytest.raises(ValueError):
        simulate_makeup_interrupt(_proto(), strategy="nonsense")  # type: ignore[arg-type]


def test_higher_operating_wet_bulb_reduces_hold_load_margin():
    cool = simulate_makeup_interrupt(_proto(), strategy="hold_load", twb_op_c=18.0)
    hot = simulate_makeup_interrupt(_proto(), strategy="hold_load", twb_op_c=28.0)
    assert hot.t_trip_h <= cool.t_trip_h
    assert hot.p_avail_at(0.0) < cool.p_avail_at(0.0)


def test_no_trip_within_a_short_horizon_is_reported_explicitly():
    ts = simulate_makeup_interrupt(
        _proto(basin_area_m2=1.0e6), strategy="ride_down", t_max_h=0.25
    )
    assert ts.trip is None
    assert ts.t_trip_h is None
    assert ts.trip_mechanism == "no_trip_within_horizon"


def test_sampled_volume_is_consistent_with_level_and_area():
    m = _proto()
    ts = simulate_makeup_interrupt(m, strategy="ride_down")
    area = m.basin_area_effective_m2()
    assert all(v == pytest.approx(area * h, rel=1e-12) for v, h in zip(ts.volume_m3, ts.level_m))
    assert ts.level_m[0] == pytest.approx(m.basin_level_normal_m)
    assert ts.level_m[-1] <= m.basin_level_trip_m + 1e-12
