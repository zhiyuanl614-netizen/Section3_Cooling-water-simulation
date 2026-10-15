"""Phase B contingency extensions: pump failure, quasi-static, wet-bulb."""

from __future__ import annotations

import pytest

from cooling.dynamics import simulate_cold_end, simulate_makeup_interrupt
from cooling.prototype_500mw import WetRecircPrototype500


def _proto(**kw) -> WetRecircPrototype500:
    return WetRecircPrototype500(**kw)


def test_makeup_wrapper_still_matches_cold_end_entry():
    m = _proto()
    a = simulate_makeup_interrupt(m, strategy="ride_down")
    b = simulate_cold_end(m, fault_type="makeup_interrupt", strategy="ride_down")
    assert a.t_trip_h == pytest.approx(b.t_trip_h, abs=1e-9)
    assert a.trip_mechanism == b.trip_mechanism == "pump_level"


def test_full_pump_failure_trips_on_backpressure_within_minutes():
    ts = simulate_cold_end(
        _proto(),
        fault_type="pump_failure",
        pump_loss_frac=1.0,
        strategy="hold_load",
        t_max_h=1.0,
        sample_every_s=1.0,
    )
    assert ts.trip_mechanism == "backpressure_protection"
    assert ts.t_trip_h is not None
    assert ts.t_trip_h * 60.0 < 5.0  # minutes, not hours


def test_partial_pump_failure_derates_without_trip():
    ts = simulate_cold_end(
        _proto(),
        fault_type="pump_failure",
        pump_loss_frac=0.3,
        strategy="hold_load",
        t_max_h=1.0,
        sample_every_s=10.0,
    )
    assert ts.trip is None
    assert ts.p_avail_mw[-1] < ts.p_rated_mw
    assert ts.p_avail_mw[-1] > 0.9 * ts.p_rated_mw


def test_quasi_static_pump_outage_trips_no_later_than_dynamic():
    m = _proto()
    dyn = simulate_cold_end(
        m,
        fault_type="pump_failure",
        pump_loss_frac=1.0,
        strategy="hold_load",
        quasi_static=False,
        t_max_h=0.5,
        sample_every_s=1.0,
    )
    qs = simulate_cold_end(
        m,
        fault_type="pump_failure",
        pump_loss_frac=1.0,
        strategy="hold_load",
        quasi_static=True,
        t_max_h=0.5,
        sample_every_s=1.0,
    )
    assert dyn.t_trip_h is not None and qs.t_trip_h is not None
    assert qs.t_trip_h <= dyn.t_trip_h + 1e-9


def test_wet_bulb_rise_derates_without_requiring_trip():
    base = simulate_cold_end(
        _proto(),
        fault_type="none",
        strategy="hold_load",
        t_max_h=2.0,
        sample_every_s=60.0,
    )
    hot = simulate_cold_end(
        _proto(),
        fault_type="wet_bulb_increase",
        twb_rise_c=6.0,
        strategy="hold_load",
        t_max_h=2.0,
        sample_every_s=60.0,
    )
    assert base.trip is None and hot.trip is None
    assert hot.p_avail_mw[-1] < base.p_avail_mw[-1]
    assert hot.twb_c[-1] > hot.twb_c[0]


def test_baseline_none_holds_rated_power():
    ts = simulate_cold_end(
        _proto(),
        fault_type="none",
        strategy="hold_load",
        t_max_h=1.0,
        sample_every_s=60.0,
    )
    assert ts.trip is None
    assert ts.p_avail_mw[-1] == pytest.approx(ts.p_rated_mw, rel=1e-3)
