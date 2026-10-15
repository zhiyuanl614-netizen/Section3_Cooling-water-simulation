"""
IEEE 39-bus DC power-flow cascading outlet (Phase B).

Ported from project2's MATPOWER-aligned case39 parameters.  Core dependency
is the standard library only: a dense Gaussian elimination solves the reduced
B-theta system.  This tier answers whether cold-end capability loss (single or
dual unit) escalates into successive branch overloads.

Not claimed: AC security, remedial action, or relay settings replication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableSequence, Sequence, Tuple


def _solve_linear(a: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting (Ax = b)."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-14:
            return [0.0] * n
        if piv != col:
            m[col], m[piv] = m[piv], m[col]
        diag = m[col][col]
        for j in range(col, n + 1):
            m[col][j] /= diag
        for row in range(n):
            if row == col:
                continue
            factor = m[row][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                m[row][j] -= factor * m[col][j]
    return [m[i][n] for i in range(n)]


@dataclass
class CascadeResult:
    removed_lines: List[int]
    stages: List[List[int]]
    line_flows_mw: List[float]
    cascade_triggered: bool

    @property
    def n_removed(self) -> int:
        return len(self.removed_lines)


@dataclass
class IEEE39CascadeGrid:
    """MATPOWER case39 DC model with overload cascading."""

    base_mva: float = 100.0
    buses: List[Dict] = field(default_factory=list)
    generators: List[Dict] = field(default_factory=list)
    lines: List[Dict] = field(default_factory=list)
    failed_lines: MutableSequence[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.buses:
            self.buses = _default_buses()
        if not self.generators:
            self.generators = _default_generators()
        if not self.lines:
            self.lines = _default_lines()

    def reset(self) -> None:
        self.failed_lines = []

    def build_b_matrix(self) -> List[List[float]]:
        n = len(self.buses)
        bmat = [[0.0] * n for _ in range(n)]
        for i, line in enumerate(self.lines):
            if i in self.failed_lines:
                continue
            f = line["from"] - 1
            t = line["to"] - 1
            bb = 1.0 / line["x"]
            bmat[f][f] += bb
            bmat[t][t] += bb
            bmat[f][t] -= bb
            bmat[t][f] -= bb
        return bmat

    def injections_mw(self, gen_pg: Mapping[int, float] | None = None) -> List[float]:
        """Nodal active injections (MW). ``gen_pg`` overrides generator Pg by bus."""
        n = len(self.buses)
        p = [0.0] * n
        for bus in self.buses:
            p[bus["id"] - 1] -= float(bus["Pd"])
        overrides = {int(k): float(v) for k, v in (gen_pg or {}).items()}
        for gen in self.generators:
            bus = int(gen["bus"])
            pg = overrides[bus] if bus in overrides else float(gen["Pg"])
            p[bus - 1] += pg
        return p

    def dc_power_flow(
        self, gen_pg: Mapping[int, float] | None = None
    ) -> Tuple[List[float], List[float]]:
        n = len(self.buses)
        slack_idx = 30  # bus 31
        p = self.injections_mw(gen_pg)
        bmat = self.build_b_matrix()
        non_slack = [i for i in range(n) if i != slack_idx]
        br = [[bmat[i][j] for j in non_slack] for i in non_slack]
        pr = [p[i] / self.base_mva for i in non_slack]
        theta_r = _solve_linear(br, pr)
        theta = [0.0] * n
        for k, i in enumerate(non_slack):
            theta[i] = theta_r[k]
        flows = [0.0] * len(self.lines)
        for i, line in enumerate(self.lines):
            if i in self.failed_lines:
                continue
            f = line["from"] - 1
            t = line["to"] - 1
            flows[i] = (theta[f] - theta[t]) / line["x"] * self.base_mva
        return flows, theta

    def overloaded(self, flows: Sequence[float]) -> List[int]:
        out: List[int] = []
        for i, line in enumerate(self.lines):
            if i in self.failed_lines:
                continue
            if abs(flows[i]) > float(line["rate"]):
                out.append(i)
        return out

    def solve_cascade(
        self,
        gen_pg: Mapping[int, float],
        *,
        max_iters: int = 30,
    ) -> CascadeResult:
        """
        Event-driven cascade: resolve DC flow, trip all newly overloaded
        branches simultaneously, repeat until none appear.
        """
        stages: List[List[int]] = []
        removed: List[int] = []
        flows: List[float] = [0.0] * len(self.lines)
        for _ in range(max_iters):
            flows, _theta = self.dc_power_flow(gen_pg)
            new = [i for i in self.overloaded(flows) if i not in self.failed_lines]
            if not new:
                break
            self.failed_lines.extend(new)
            removed.extend(new)
            stages.append(list(new))
        return CascadeResult(
            removed_lines=removed,
            stages=stages,
            line_flows_mw=list(flows),
            cascade_triggered=bool(removed),
        )

    def max_loading(self, flows: Sequence[float] | None = None) -> float:
        if flows is None:
            flows, _ = self.dc_power_flow()
        peak = 0.0
        for i, line in enumerate(self.lines):
            if i in self.failed_lines:
                continue
            peak = max(peak, abs(flows[i]) / float(line["rate"]))
        return peak


def cascade_from_unit_outputs(
    outputs_mw: Mapping[int, float],
    *,
    grid: IEEE39CascadeGrid | None = None,
) -> CascadeResult:
    """Convenience: evaluate cascade under absolute generator outputs by bus."""
    g = IEEE39CascadeGrid() if grid is None else grid
    g.reset()
    return g.solve_cascade(outputs_mw)


def _default_buses() -> List[Dict]:
    pd = {
        1: 97.6, 3: 322.0, 4: 500.0, 7: 233.8, 8: 522.0, 9: 6.5, 12: 8.53,
        15: 320.0, 16: 329.0, 18: 158.0, 20: 680.0, 21: 274.0, 23: 247.5,
        24: 308.6, 25: 224.0, 26: 139.0, 27: 281.0, 28: 206.0, 29: 283.5,
        31: 9.2, 39: 1104.0,
    }
    # type: 1=PQ, 2=PV, 3=Slack
    types = {31: 3}
    for b in range(30, 40):
        types.setdefault(b, 2)
    out = []
    for i in range(1, 40):
        out.append({"id": i, "type": types.get(i, 1), "Pd": float(pd.get(i, 0.0))})
    return out


def _default_generators() -> List[Dict]:
    # Buses 33 and 34 are the mapped wet-recirc units; Pg/Pmax follow the
    # MATPOWER case39 solved case and generator ratings.
    return [
        {"bus": 30, "Pg": 250.0, "Pmax": 1040.0},
        {"bus": 31, "Pg": 677.87, "Pmax": 646.0},
        {"bus": 32, "Pg": 650.0, "Pmax": 725.0},
        {"bus": 33, "Pg": 632.0, "Pmax": 652.0},
        {"bus": 34, "Pg": 508.0, "Pmax": 508.0},
        {"bus": 35, "Pg": 650.0, "Pmax": 687.0},
        {"bus": 36, "Pg": 560.0, "Pmax": 580.0},
        {"bus": 37, "Pg": 540.0, "Pmax": 564.0},
        {"bus": 38, "Pg": 830.0, "Pmax": 865.0},
        {"bus": 39, "Pg": 1000.0, "Pmax": 1100.0},
    ]


def _default_lines() -> List[Dict]:
    raw: Iterable[Tuple[int, int, float, float]] = [
        (1, 2, 0.0411, 600), (1, 39, 0.0250, 1000), (2, 3, 0.0151, 500),
        (2, 25, 0.0086, 500), (3, 4, 0.0213, 500), (3, 18, 0.0133, 500),
        (4, 5, 0.0128, 600), (4, 14, 0.0129, 500), (5, 6, 0.0026, 1200),
        (5, 8, 0.0112, 900), (6, 7, 0.0092, 900), (6, 11, 0.0082, 480),
        (7, 8, 0.0046, 900), (8, 9, 0.0363, 900), (9, 39, 0.0250, 900),
        (10, 11, 0.0043, 600), (10, 13, 0.0043, 600), (13, 14, 0.0101, 600),
        (14, 15, 0.0217, 600), (15, 16, 0.0094, 600), (16, 17, 0.0089, 600),
        (16, 19, 0.0195, 600), (16, 21, 0.0135, 600), (16, 24, 0.0059, 600),
        (17, 18, 0.0082, 600), (17, 27, 0.0173, 600), (21, 22, 0.0140, 900),
        (22, 23, 0.0096, 600), (23, 24, 0.0350, 600), (25, 26, 0.0323, 600),
        (26, 27, 0.0147, 600), (26, 28, 0.0474, 600), (26, 29, 0.0625, 600),
        (28, 29, 0.0151, 600), (2, 30, 0.0181, 900), (6, 31, 0.0250, 1800),
        (10, 32, 0.0200, 900), (11, 12, 0.0435, 500), (12, 13, 0.0435, 500),
        (19, 20, 0.0138, 900), (19, 33, 0.0142, 900), (20, 34, 0.0180, 900),
        (22, 35, 0.0143, 900), (23, 36, 0.0272, 900), (25, 37, 0.0232, 900),
        (29, 38, 0.0156, 1200),
    ]
    return [
        {"from": f, "to": t, "x": x, "rate": float(rate)} for f, t, x, rate in raw
    ]
