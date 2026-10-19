"""Multi-timescale exchange helpers between cold-end and grid models.

The cold-end state evolves over minutes to hours, whereas a DC-OPF is an
algebraic snapshot.  This module therefore does *not* force both layers onto
one time step.  It builds grid snapshot times from a regular macro-step plus
the cold-end trajectory's physical event breakpoints (derating onset,
protection action and trip).  The resulting piecewise-linear exchange is the
interface used by the tier-B adequacy assessment.

The helpers in this module are dependency-free; solving the OPF remains in
:mod:`grid.opf`.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

DEFAULT_MACRO_STEP_H = 5.0 / 60.0


def _finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def trajectory_event_times(trajectory: Any) -> list[float]:
    """Return sorted physical event times exposed by a trajectory.

    Both :class:`cooling.dynamics.TimeseriesResult` and
    :class:`cooling.benchmarks.BenchmarkTrajectory` are supported.  Event
    times are deliberately read from named attributes rather than inferred
    from a change in sampled power, so a protection or level event cannot be
    lost by down-sampling.
    """
    candidates: list[float | None] = [
        _finite_float(getattr(trajectory, "t_derate_start_h", None)),
        _finite_float(getattr(trajectory, "t_trip_h", None)),
        _finite_float(getattr(trajectory, "trip_h", None)),
    ]
    trip = getattr(trajectory, "trip", None)
    if trip is not None:
        candidates.append(_finite_float(getattr(trip, "t_h", None)))
    return _sorted_unique([t for t in candidates if t is not None and t >= 0.0])


def _sorted_unique(values: Iterable[float], *, tol: float = 1e-9) -> list[float]:
    out: list[float] = []
    for value in sorted(float(v) for v in values):
        if not out or abs(value - out[-1]) > tol:
            out.append(float(value))
    return out


def event_aware_time_nodes(
    trajectory: Any,
    *,
    t_end_h: float,
    macro_step_h: float = DEFAULT_MACRO_STEP_H,
    extra_times: Sequence[float] = (),
    include_events: bool = True,
) -> list[float]:
    """Build regular macro-step nodes augmented with trajectory events.

    Parameters
    ----------
    trajectory
        Cold-end trajectory exposing event attributes and, normally,
        ``p_avail_at(t_h)``.
    t_end_h
        End of the exchange horizon in hours.
    macro_step_h
        Regular grid snapshot spacing.  Five minutes is the default for the
        adequacy layer; it is an exchange step, not the cold-end integration
        step.
    extra_times
        Additional scenario times that must be represented exactly.
    include_events
        Whether to insert derating/protection/trip event times.
    """
    if macro_step_h <= 0:
        raise ValueError("macro_step_h must be positive")
    if t_end_h < 0:
        raise ValueError("t_end_h must be non-negative")

    nodes = [0.0]
    t = float(macro_step_h)
    # Include the regular node just beyond the end, then clip it below.  This
    # avoids a long final interval when t_end is not a macro-step multiple.
    while t < t_end_h - 1e-12:
        nodes.append(float(t))
        t += float(macro_step_h)
    nodes.append(float(t_end_h))

    extras = [_finite_float(v) for v in extra_times]
    nodes.extend(v for v in extras if v is not None)
    if include_events:
        nodes.extend(trajectory_event_times(trajectory))

    clipped = [min(max(float(v), 0.0), float(t_end_h)) for v in nodes]
    return _sorted_unique(clipped)


def integrate_time_series(times: Sequence[float], values: Sequence[float]) -> float:
    """Trapezoidal integral of a sampled series."""
    if len(times) != len(values):
        raise ValueError("times/values length mismatch")
    if not all(math.isfinite(float(v)) for v in [*times, *values]):
        raise ValueError("non-finite integration sample")
    if any(b < a for a,b in zip(times,times[1:])):
        raise ValueError("times must be nondecreasing; duplicate left/right event times are allowed")
    if len(times) < 2:
        return 0.0
    return sum(
        0.5 * (float(values[i - 1]) + float(values[i])) * (float(times[i]) - float(times[i - 1]))
        for i in range(1, len(times))
    )


def event_aware_time_samples(trajectory: Any, *, t_end_h: float,
                             macro_step_h: float = DEFAULT_MACRO_STEP_H) -> list[tuple[float, str]]:
    """Ordered (time, side) samples: duplicate each trip with zero time width.

    A left/right pair prevents trapezoidal quadrature from smearing a step
    across the preceding interval. Event inclusion alone is insufficient.
    The callback trajectory must expose p_avail_at(t, side=...).
    """
    nodes = event_aware_time_nodes(trajectory, t_end_h=t_end_h, macro_step_h=macro_step_h)
    trip = _finite_float(getattr(trajectory, "t_trip_h", None))
    if trip is None:
        trip = _finite_float(getattr(trajectory, "trip_h", None))
    out = []
    for t in nodes:
        if trip is not None and t == trip and t > 0:
            out.append((t, "left"))
        out.append((t, "right"))
    return out
