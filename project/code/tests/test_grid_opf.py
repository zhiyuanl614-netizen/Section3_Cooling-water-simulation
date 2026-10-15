"""Grid-side tier-B assessment (skipped when pandapower is unavailable)."""

from __future__ import annotations

import pytest

pandapower = pytest.importorskip("pandapower", reason="optional grid dependency")

from grid import baseline_no_fault, evaluate_grid_impact, evaluate_timeseries  # noqa: E402
from scenarios import evaluate_scenario, load_scenarios  # noqa: E402


def test_baseline_case_is_feasible_and_serves_all_load():
    r = baseline_no_fault()
    assert r.converged
    assert r.shed_load_mw == pytest.approx(0.0, abs=1e-6)
    assert r.total_load_mw == pytest.approx(6254.23, abs=1.0)


def test_pavail_is_applied_to_the_right_generator():
    r = evaluate_grid_impact({"G34": 100.0})
    assert r.applied_pmax_mw["G34"] == pytest.approx(100.0)
    assert r.generation_mw["G34"] <= 100.0 + 1e-6


def test_mapped_unit_loss_at_base_load_is_transfer_limited():
    """Losing the bus-33 generator loads the 2-3 corridor to its rating.

    The unserved load here is a transfer limit, not a capacity-margin effect:
    the case keeps ~15% generation margin, but the 500 MVA 2-3 branch becomes
    binding once the 632 MW injection at bus 33 disappears.
    """
    base = baseline_no_fault()
    out = evaluate_grid_impact({"G33": 0.0})
    assert base.shed_load_mw == pytest.approx(0.0, abs=1e-6)
    assert out.shed_load_mw > 100.0
    assert out.max_line_loading_percent == pytest.approx(100.0, abs=0.5)


def test_elevated_demand_exposes_the_adequacy_gap():
    base = baseline_no_fault(load_scale=1.15)
    out = evaluate_grid_impact({"G33": 0.0}, load_scale=1.15)
    assert out.shed_load_mw > base.shed_load_mw
    assert out.shed_load_mw > 500.0


def test_timeseries_sweep_uses_the_cold_end_trajectory():
    sc = load_scenarios()[0]
    out = evaluate_scenario(sc, timeseries=True)
    fa = sc.faulted_units[0]
    healthy = {u: sc_out for u, sc_out in out.pavail_mw.items() if u != fa}
    rows = evaluate_timeseries(
        out.timeseries,
        faulted_unit=fa,
        healthy_pmax_mw=healthy,
        load_scale=1.15,
        sample_step_h=1.0,
    )
    assert len(rows) >= 5
    pavails = [r["pavail_faulted_mw"] for r in rows]
    # G33 is the 652 MW mapped unit; its trajectory starts at rated power
    assert pavails[0] == pytest.approx(652.0, rel=1e-6)
    assert all(b <= a + 1e-6 for a, b in zip(pavails, pavails[1:])), pavails
    assert pavails[-1] == pytest.approx(0.0)  # terminal sample is the trip
    assert rows[-1]["t_h"] == pytest.approx(out.timeseries[fa].t_trip_h, abs=1e-3)
    assert rows[0]["trip_mechanism"] == out.timeseries[fa].trip_mechanism
