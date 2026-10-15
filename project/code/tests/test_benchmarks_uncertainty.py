"""Synthetic benchmark, Monte Carlo and global-sensitivity contracts."""

from __future__ import annotations

import pytest

from cooling.benchmarks import build_benchmark_trajectories
from cooling.prototype_500mw import WetRecircPrototype500
from cooling.uncertainty import (
    default_uncertainty_parameters,
    Morris_sensitivity,
    run_monte_carlo,
    sobol_sensitivity,
    summarise_monte_carlo,
)


def test_benchmark_trajectories_have_distinct_assumptions_and_metrics():
    trajectories = build_benchmark_trajectories(WetRecircPrototype500())
    by_name = {t.name: t for t in trajectories}
    assert by_name["instant_trip"].t_trip_h == 0.0
    assert by_name["instant_trip"].delivered_energy_mwh() == pytest.approx(0.0)
    assert by_name["fixed_holdup_trip"].p_avail_at(1.0) == pytest.approx(500.0)
    assert by_name["fixed_holdup_trip"].t_trip_h == pytest.approx(3.2925, abs=1e-3)
    assert by_name["linear_to_min_then_trip"].p_avail_at(1.0) < 500.0
    assert by_name["mechanistic_ride_down"].t_trip_h > by_name["fixed_holdup_trip"].t_trip_h
    assert by_name["mechanistic_ride_down"].delivered_energy_mwh() > by_name["linear_to_min_then_trip"].delivered_energy_mwh()


def test_monte_carlo_is_reproducible_and_summarised():
    model = WetRecircPrototype500()
    specs = default_uncertainty_parameters(model)
    a = run_monte_carlo(model, specs, n_samples=6, seed=123)
    b = run_monte_carlo(model, specs, n_samples=6, seed=123)
    assert a == b
    summary = summarise_monte_carlo(a)
    assert summary["n_samples"] == 6
    assert summary["outputs"]["t_trip_h"]["p05"] <= summary["outputs"]["t_trip_h"]["p50"]
    assert summary["outputs"]["t_trip_h"]["p50"] <= summary["outputs"]["t_trip_h"]["p95"]
    assert sum(v["n"] for v in summary["mechanisms"].values()) == 6


def test_global_sensitivity_methods_return_all_parameters():
    model = WetRecircPrototype500()
    specs = default_uncertainty_parameters(model)[:3]
    Morris = Morris_sensitivity(model, specs, n_trajectories=2, seed=5)
    assert {r["parameter"] for r in Morris} == {s.name for s in specs}
    assert all(r["mu_star_per_full_range"] >= 0 for r in Morris)

    sobol = sobol_sensitivity(model, specs, base_n=8, seed=17)
    initial_pb = [r for r in sobol if r["output"] == "initial_pb_kpa"]
    basin = next(r for r in initial_pb if r["parameter"] == "basin_area_m2")
    # Basin area cannot change the initial steady backpressure; its total
    # effect should therefore be near zero up to estimator error.
    assert basin["sobol_total_order"] == pytest.approx(0.0, abs=1e-12)
    assert max(r["sobol_total_order"] for r in initial_pb) > 0.05
