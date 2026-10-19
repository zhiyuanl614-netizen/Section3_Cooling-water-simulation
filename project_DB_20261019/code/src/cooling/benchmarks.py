"""Benchmark trajectories for model-comparison studies.

The comparators in this module are deliberately simple and are *not*
alternative plant models.  They represent assumptions commonly used in
system studies -- instantaneous loss, full output until an inventory time,
and a prescribed linear derating -- so that the value (and limits) of the
mechanism-resolved trajectory can be measured rather than asserted.

All trajectories expose the small interface used by the grid layer:
``p_avail_at(t_h)``, ``t_trip_h`` and ``trip_mechanism``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import math

from .dynamics import TimeseriesResult, simulate_makeup_interrupt
from .prototype_500mw import WetRecircPrototype500


@dataclass
class BenchmarkTrajectory:
    """A sampled available-power trajectory with comparison metrics."""

    name: str
    label: str
    gen_id: str
    p_rated_mw: float
    t_h: list[float] = field(default_factory=list)
    p_avail_mw: list[float] = field(default_factory=list)
    t_derate_start_h: float | None = None
    trip_h: float | None = None
    trip_mechanism: str = "no_trip_within_horizon"
    p_trip_left_mw: float | None = None

    @property
    def t_trip_h(self) -> float | None:
        return self.trip_h

    def p_avail_at(self, t_h: float, *, side: str = "right") -> float:
        if not self.t_h:
            return float("nan")
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")
        if self.trip_h is not None and t_h >= self.trip_h:
            if side == "left" and t_h == self.trip_h and self.p_trip_left_mw is not None:
                return self.p_trip_left_mw
            return 0.0
        if t_h <= self.t_h[0]:
            return self.p_avail_mw[0]
        if t_h >= self.t_h[-1]:
            return self.p_avail_mw[-1]
        for i in range(1, len(self.t_h)):
            if self.t_h[i] >= t_h:
                t0, t1 = self.t_h[i - 1], self.t_h[i]
                p0, p1 = self.p_avail_mw[i - 1], self.p_avail_mw[i]
                if self.t_h[i] == self.trip_h and self.p_trip_left_mw is not None:
                    p1 = self.p_trip_left_mw
                if t1 <= t0:
                    return p1
                return p0 + (p1 - p0) * (t_h - t0) / (t1 - t0)
        return self.p_avail_mw[-1]

    def delivered_energy_mwh(self, horizon_h: float = 8.0) -> float:
        """Trapezoidal delivered energy from fault onset to ``horizon_h``."""
        if not self.t_h:
            return 0.0
        energy = 0.0
        prev_t = self.t_h[0]
        prev_p = self.p_avail_at(prev_t)
        end = max(float(horizon_h), prev_t)
        # Include every stored breakpoint and the requested horizon.
        points = [t for t in self.t_h if prev_t < t < end]
        if self.trip_h is not None and prev_t < self.trip_h < end:
            points.append(float(self.trip_h))
        points.append(end)
        for t in sorted(set(points)):
            # Left endpoint uses the right state; right endpoint the left state.
            # A protection discontinuity has zero duration, not a ramp.
            p_left = self.p_avail_at(t, side="left")
            energy += 0.5 * (prev_p + p_left) * (t - prev_t)
            prev_t, prev_p = t, self.p_avail_at(t)
        return energy

    def metrics(self, horizon_h: float = 8.0) -> dict[str, Any]:
        return {
            "benchmark": self.name,
            "label": self.label,
            "gen_id": self.gen_id,
            "p_rated_mw": round(self.p_rated_mw, 3),
            "t_derate_start_h": self.t_derate_start_h,
            "t_trip_h": self.trip_h,
            "trip_mechanism": self.trip_mechanism,
            "p_at_1h_mw": round(self.p_avail_at(1.0), 3),
            "p_at_3h_mw": round(self.p_avail_at(3.0), 3),
            "p_at_5h_mw": round(self.p_avail_at(5.0), 3),
            "delivered_energy_0_8h_mwh": round(self.delivered_energy_mwh(horizon_h), 2),
        }


def _finish(
    traj: BenchmarkTrajectory,
    *,
    derate_threshold: float = 0.995,
) -> BenchmarkTrajectory:
    if traj.t_derate_start_h is None:
        for t, p in zip(traj.t_h, traj.p_avail_mw):
            if p < derate_threshold * traj.p_rated_mw:
                traj.t_derate_start_h = float(t)
                break
    return traj


def from_timeseries(
    ts: TimeseriesResult,
    *,
    name: str,
    label: str,
) -> BenchmarkTrajectory:
    return BenchmarkTrajectory(
        name=name,
        label=label,
        gen_id=ts.gen_id,
        p_rated_mw=ts.p_rated_mw,
        t_h=list(ts.t_h),
        p_avail_mw=list(ts.p_avail_mw),
        t_derate_start_h=ts.t_derate_start_h,
        trip_h=ts.t_trip_h,
        trip_mechanism=ts.trip_mechanism,
        p_trip_left_mw=ts.p_before_trip_mw,
    )


def mechanistic_trajectory(
    model: WetRecircPrototype500,
    *,
    strategy: str = "ride_down",
    name: str | None = None,
    **dyn_kwargs: Any,
) -> BenchmarkTrajectory:
    """Run the full cold-end/pump/SOP/protection model."""
    ts = simulate_makeup_interrupt(model, strategy=strategy, **dyn_kwargs)  # type: ignore[arg-type]
    return from_timeseries(
        ts,
        name=name or f"mechanistic_{strategy}",
        label="Mechanism-resolved model",
    )


def simplified_level_band_trajectory(
    model: WetRecircPrototype500,
    **dyn_kwargs: Any,
) -> BenchmarkTrajectory:
    """Mechanistic heat balance with the legacy level-band pump fallback."""
    kwargs = {"pump_model": "level_band", **dyn_kwargs}
    ts = simulate_makeup_interrupt(model, strategy="ride_down", **kwargs)
    return from_timeseries(
        ts,
        name="simplified_level_band",
        label="Simplified level-band pump comparator",
    )


def _sampled(
    model: WetRecircPrototype500,
    *,
    name: str,
    label: str,
    t_max_h: float,
    sample_step_h: float,
    power_fn,
    trip_h: float | None,
    mechanism: str,
) -> BenchmarkTrajectory:
    times: list[float] = []
    powers: list[float] = []
    t = 0.0
    while t <= t_max_h + 1e-12:
        times.append(round(t, 10))
        powers.append(float(power_fn(t)))
        t += sample_step_h
    if trip_h is not None and trip_h not in times:
        times.append(float(trip_h))
        powers.append(0.0)
        pairs = sorted(zip(times, powers))
        times = [x for x, _ in pairs]
        powers = [y for _, y in pairs]
    traj = BenchmarkTrajectory(
        name=name,
        label=label,
        gen_id=model.gen_id,
        p_rated_mw=model.p_rated_mw,
        t_h=times,
        p_avail_mw=powers,
        trip_h=trip_h,
        p_trip_left_mw=(float(power_fn(math.nextafter(trip_h, -math.inf))) if trip_h is not None and trip_h > 0 else model.p_rated_mw),
        trip_mechanism=mechanism,
    )
    return _finish(traj)


def instant_trip_trajectory(
    model: WetRecircPrototype500,
    *,
    t_max_h: float = 8.0,
    sample_step_h: float = 0.05,
) -> BenchmarkTrajectory:
    """Conventional N-1 assumption: all capacity disappears at fault onset."""
    return _sampled(
        model,
        name="instant_trip",
        label="Instantaneous trip at fault onset",
        t_max_h=t_max_h,
        sample_step_h=sample_step_h,
        power_fn=lambda _t: 0.0,
        trip_h=0.0,
        mechanism="assumed_instant_trip",
    )


def fixed_holdup_trip_trajectory(
    model: WetRecircPrototype500,
    *,
    t_max_h: float = 8.0,
    sample_step_h: float = 0.05,
) -> BenchmarkTrajectory:
    """Full output until the analytic design-loss inventory time, then trip."""
    trip = model.time_to_trip_after_makeup_stop_h()
    rated = model.p_rated_mw
    return _sampled(
        model,
        name="fixed_holdup_trip",
        label="Full output to analytic inventory time, then trip",
        t_max_h=t_max_h,
        sample_step_h=sample_step_h,
        power_fn=lambda t: rated if t < trip else 0.0,
        trip_h=trip,
        mechanism="assumed_fixed_holdup_trip",
    )


def linear_derate_trajectory(
    model: WetRecircPrototype500,
    *,
    t_max_h: float = 8.0,
    sample_step_h: float = 0.05,
) -> BenchmarkTrajectory:
    """Linear derating to technical minimum at the analytic inventory time."""
    trip = model.time_to_trip_after_makeup_stop_h()
    rated = model.p_rated_mw
    p_min = model.p_min_tech_frac * rated

    def power(t: float) -> float:
        if t >= trip:
            return 0.0
        return rated + (p_min - rated) * (t / trip if trip > 0 else 1.0)

    return _sampled(
        model,
        name="linear_to_min_then_trip",
        label="Prescribed linear derate to technical minimum, then trip",
        t_max_h=t_max_h,
        sample_step_h=sample_step_h,
        power_fn=power,
        trip_h=trip,
        mechanism="assumed_linear_derate_trip",
    )


def build_benchmark_trajectories(
    model: WetRecircPrototype500,
    *,
    t_max_h: float = 8.0,
    include_hold_load: bool = True,
) -> list[BenchmarkTrajectory]:
    """Build the standard comparison set for one unit model."""
    out = [
        instant_trip_trajectory(model, t_max_h=t_max_h),
        fixed_holdup_trip_trajectory(model, t_max_h=t_max_h),
        linear_derate_trajectory(model, t_max_h=t_max_h),
        simplified_level_band_trajectory(model),
        mechanistic_trajectory(model, strategy="ride_down"),
    ]
    if include_hold_load:
        out.append(mechanistic_trajectory(model, strategy="hold_load"))
    return out
