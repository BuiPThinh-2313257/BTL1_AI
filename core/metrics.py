"""Đo thời gian, bộ nhớ và số node của một lần chạy giải thuật.

Cách đo:
- Thời gian: time.perf_counter, chạy *không* bật tracemalloc (tracemalloc làm
  Python chậm đi vài lần nên không được đo chung).
- Bộ nhớ: chạy lại lần nữa với tracemalloc, lấy đỉnh (peak) bộ nhớ Python
  cấp phát trong lúc chạy, đơn vị KB.
- Số node: lấy từ SearchResult (nodes_expanded, nodes_generated, max_frontier).

Ví dụ:
    from core.metrics import measure, write_csv
    from core.search import astar, Limits
    m = measure(astar, problem, limits=Limits(time_limit=60), input_name="5x5_01")
    print(m.time_s, m.peak_kb, m.result.nodes_expanded)
    write_csv([m], "results/benchmark.csv")
"""

from __future__ import annotations

import csv
import gc
import os
import time
import tracemalloc
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from .search import Limits, SearchResult

CSV_FIELDS = [
    "puzzle", "input", "algorithm", "status", "found", "time_s", "peak_kb",
    "nodes_expanded", "nodes_generated", "max_frontier", "max_depth",
    "solution_length", "restarts",
]


@dataclass
class Metrics:
    puzzle: str
    input: str
    algorithm: str
    time_s: float
    peak_kb: Optional[float]
    result: SearchResult

    def row(self) -> Dict[str, Any]:
        s = self.result.summary()
        return {
            "puzzle": self.puzzle,
            "input": self.input,
            "algorithm": self.algorithm,
            "status": s["status"],
            "found": s["found"],
            "time_s": round(self.time_s, 6),
            "peak_kb": None if self.peak_kb is None else round(self.peak_kb, 1),
            "nodes_expanded": s["nodes_expanded"],
            "nodes_generated": s["nodes_generated"],
            "max_frontier": s["max_frontier"],
            "max_depth": s["max_depth"],
            "solution_length": s["solution_length"],
            "restarts": s["restarts"],
        }


def measure(algorithm: Callable[..., SearchResult], problem, *,
            limits: Optional[Limits] = None, input_name: str = "",
            track_memory: bool = True, trace=None, **kwargs) -> Metrics:
    """Chạy `algorithm(problem, limits=..., **kwargs)` và đo.

    track_memory=True sẽ chạy giải thuật 2 lần (1 lần đo giờ, 1 lần đo bộ nhớ).
    Với giải thuật ngẫu nhiên (hill_climbing, simulated_annealing) hãy truyền
    seed=... để hai lần chạy giống nhau.
    `trace` (nếu có) chỉ gắn vào lần đo thời gian. Ghi trace cũng tốn thời
    gian, nên khi chạy benchmark cho báo cáo thì để trace=None.
    """
    gc.collect()
    t0 = time.perf_counter()
    result = algorithm(problem, limits=limits, trace=trace, **kwargs)
    time_s = time.perf_counter() - t0

    peak_kb = None
    if track_memory:
        peak_kb = peak_memory_kb(algorithm, problem, limits=limits, **kwargs)

    return Metrics(
        puzzle=getattr(problem, "name", "problem"),
        input=input_name,
        algorithm=result.algorithm,
        time_s=time_s,
        peak_kb=peak_kb,
        result=result,
    )


def peak_memory_kb(algorithm: Callable[..., SearchResult], problem, *,
                   limits: Optional[Limits] = None, **kwargs) -> float:
    """Đỉnh bộ nhớ (KB) Python cấp phát trong một lần chạy."""
    gc.collect()
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    tracemalloc.reset_peak()
    base, _ = tracemalloc.get_traced_memory()
    try:
        algorithm(problem, limits=limits, trace=None, **kwargs)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not was_tracing:
            tracemalloc.stop()
    return (peak - base) / 1024


def write_csv(metrics: Iterable[Metrics], path: str, append: bool = False) -> None:
    """Ghi kết quả ra CSV (mỗi Metrics một dòng)."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    new_file = not append or not os.path.exists(path)
    with open(path, "a" if append else "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            w.writeheader()
        for m in metrics:
            w.writerow(m.row())


def format_table(metrics: List[Metrics]) -> str:
    """Bảng text gọn để in ra màn hình."""
    head = f"{'puzzle':<10}{'input':<16}{'algo':<20}{'status':<12}" \
           f"{'time(s)':>10}{'mem(KB)':>11}{'expanded':>11}{'len':>9}"
    lines = [head, "-" * len(head)]
    for m in metrics:
        r = m.row()
        mem = "-" if r["peak_kb"] is None else f"{r['peak_kb']:.1f}"
        lines.append(
            f"{r['puzzle']:<10}{r['input'][:15]:<16}{r['algorithm']:<20}{r['status']:<12}"
            f"{r['time_s']:>10.4f}{mem:>11}{r['nodes_expanded']:>11}{r['solution_length']:>9}"
        )
    return "\n".join(lines)
