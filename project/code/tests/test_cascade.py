"""IEEE 39 cascading outlet (Phase B)."""

from __future__ import annotations

from grid.cascade import IEEE39CascadeGrid, cascade_from_unit_outputs


def _base_pg() -> dict[int, float]:
    g = IEEE39CascadeGrid()
    return {int(gen["bus"]): float(gen["Pg"]) for gen in g.generators}


def test_intact_case_has_no_cascade():
    pg = _base_pg()
    result = cascade_from_unit_outputs(pg)
    assert result.cascade_triggered is False
    assert result.n_removed == 0


def test_single_bus33_trip_does_not_cascade():
    pg = _base_pg()
    pg[33] = 0.0
    grid = IEEE39CascadeGrid()
    result = grid.solve_cascade(pg)
    assert result.cascade_triggered is False
    # N-1 style margin: peak loading stays at or below rating.
    assert grid.max_loading(result.line_flows_mw) <= 1.0 + 1e-6


def test_dual_bus33_34_trip_can_cascade():
    pg = _base_pg()
    pg[33] = 0.0
    pg[34] = 0.0
    result = cascade_from_unit_outputs(pg)
    assert result.cascade_triggered is True
    assert result.n_removed >= 5
    assert len(result.stages) >= 1


def test_line_count_matches_matpower_case39():
    grid = IEEE39CascadeGrid()
    assert len(grid.buses) == 39
    assert len(grid.generators) == 10
    assert len(grid.lines) == 46
