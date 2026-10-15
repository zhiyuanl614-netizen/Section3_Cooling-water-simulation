"""Calibration registry and historian-fitting engine."""

from __future__ import annotations

from dataclasses import replace

import pytest

from cooling.calibration import PARAMETER_SPECS, calibrate_model, calibration_metrics
from cooling.prototype_500mw import WetRecircPrototype500


def _synthetic_rows(model: WetRecircPrototype500) -> list[dict[str, float]]:
    rows = []
    for p in (250.0, 350.0, 500.0):
        for x in (0.7, 1.0):
            for twb in (18.0, 24.0):
                pred = model.predict_cold_end(p, qcw_frac=x, twb_c=twb)
                rows.append(
                    {
                        "p_net_mw": p,
                        "qcw_m3s": model.qcw_design_m3s * x,
                        "twb_c": twb,
                        "tin_c": pred.tin_c,
                        "tout_c": pred.tout_c,
                        "pb_kpa": pred.backpressure_kpa,
                    }
                )
    return rows


def test_registry_parameters_exist_on_model():
    m = WetRecircPrototype500()
    for name in PARAMETER_SPECS:
        assert hasattr(m, name), name


def test_calibration_recovers_a_tower_characteristic_offset():
    truth = replace(WetRecircPrototype500(), tower_characteristic_mult=0.85)
    rows = _synthetic_rows(truth)
    start = WetRecircPrototype500()
    result = calibrate_model(start, rows, ["tower_characteristic_mult"], max_sweeps=10)
    assert result.final_metrics["objective"] < result.initial_metrics["objective"]
    assert result.model.tower_characteristic_mult == pytest.approx(0.85, abs=0.05)


def test_calibration_metrics_are_zero_on_generating_model():
    m = WetRecircPrototype500()
    metrics = calibration_metrics(m, _synthetic_rows(m))
    assert metrics["objective"] == pytest.approx(0.0, abs=1e-12)


def test_unregistered_parameter_is_rejected():
    m = WetRecircPrototype500()
    with pytest.raises(ValueError):
        calibrate_model(m, _synthetic_rows(m), ["not_a_parameter"])


def test_makeup_observation_makes_evaporation_fraction_identifiable():
    base = WetRecircPrototype500()
    rows = []
    truth = WetRecircPrototype500(evap_heat_fraction=0.90)
    for p in (300.0, 400.0, 500.0):
        pred = truth.predict_cold_end(p)
        rows.append({
            "p_net_mw": p,
            "qcw_m3s": truth.qcw_design_m3s,
            "twb_c": truth.twb_ref_c,
            "makeup_m3s": pred.makeup_m3s,
        })
    metrics = calibration_metrics(base, rows)
    assert metrics["makeup_m3s_n"] == 3.0
    assert metrics["makeup_m3s_rmse"] > 0.0
    result = calibrate_model(base, rows, ["evap_heat_fraction"], max_sweeps=16)
    assert abs(result.model.evap_heat_fraction - 0.90) < 0.03
