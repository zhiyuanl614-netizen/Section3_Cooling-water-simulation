"""Event-aware multi-timescale exchange between cold-end and grid layers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from grid.coupling import (
    event_aware_time_nodes,
    integrate_time_series,
    trajectory_event_times,
)


def _trajectory():
    return SimpleNamespace(t_derate_start_h=2.5606, t_trip_h=5.0728, trip_h=None, trip=None)


def test_event_times_are_collected_from_named_attributes():
    assert trajectory_event_times(_trajectory()) == pytest.approx([2.5606, 5.0728])


def test_event_aware_nodes_include_events_and_exact_end():
    nodes = event_aware_time_nodes(_trajectory(), t_end_h=8.0, macro_step_h=0.5)
    assert nodes[0] == 0.0
    assert nodes[-1] == 8.0
    assert any(abs(t - 2.5606) < 1e-9 for t in nodes)
    assert any(abs(t - 5.0728) < 1e-9 for t in nodes)
    assert nodes == sorted(nodes)
    assert len(nodes) == len(set(nodes))
    # Regular spacing is retained away from inserted events.
    assert max(b - a for a, b in zip(nodes, nodes[1:])) <= 0.5 + 1e-9


def test_event_aware_nodes_reject_nonpositive_macro_step():
    with pytest.raises(ValueError):
        event_aware_time_nodes(_trajectory(), t_end_h=8.0, macro_step_h=0.0)


def test_integrate_time_series_is_trapezoidal():
    assert integrate_time_series([0.0, 1.0, 3.0], [0.0, 2.0, 2.0]) == pytest.approx(5.0)
