"""TV4 GĐ2: chạy solver có sẵn và xuất trace JSON version 1.

Chạy tách tiến trình khỏi Tkinter để GUI không bị treo, và tránh số đo bộ
nhớ bị lẫn với các đối tượng giao diện. Không sửa thuật toán của TV1/TV2/TV3.

Ví dụ:
    python -m gui.live_runner --puzzle kakurasu --algorithm astar \
      --input data/kakurasu_4x4_easy.json --output traces/my_run.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from core.metrics import measure
from core.search import Limits, astar, dfs, hill_climbing
from core.trace import Trace
from puzzles.kakurasu import Kakurasu
from puzzles.pipes import Pipes

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUTS = {
    "pipes": ROOT / "data" / "input_pipes_4x4.json",
    "kakurasu": ROOT / "data" / "kakurasu_4x4_easy.json",
}
ALGORITHMS = {
    "pipes": {"dfs": dfs, "hill_climbing": hill_climbing},
    "kakurasu": {"dfs": dfs, "astar": astar},
}


def run_live_trace(
    puzzle: str,
    algorithm: str,
    input_path: Optional[str] = None,
    *,
    max_nodes: int = 50000,
    time_limit: float = 5.0,
    max_steps: int = 10000,
    seed: int = 0,
    track_memory: bool = True,
    kakurasu_prune: str = "basic",
) -> Dict[str, Any]:
    """Chạy một bài 4x4 bằng solver thật và trả trace tương thích Viewer.

    Bộ nhớ là tracemalloc peak trong một lần chạy LẶP LẠI, không chứa trace;
    thời gian trong `result.elapsed` của lần chạy đầu có ghi trace, không
    thay thế benchmark chính thức của TV5.
    """
    if puzzle not in ALGORITHMS:
        raise ValueError("Bài toán phải là pipes hoặc kakurasu.")
    if algorithm not in ALGORITHMS[puzzle]:
        raise ValueError("Giải thuật '{}' không hỗ trợ cho {}.".format(algorithm, puzzle))
    if max_nodes < 1 or time_limit <= 0 or max_steps < 1:
        raise ValueError("max_nodes, time_limit và max_steps phải lớn hơn 0.")

    src = Path(input_path) if input_path else DEFAULT_INPUTS[puzzle]
    if input_path and not src.is_absolute() and not src.exists():
        src = ROOT / src
    src = src.resolve()
    if not src.is_file():
        raise FileNotFoundError("Không tìm thấy input: {}".format(src))

    if puzzle == "pipes":
        problem = Pipes.from_file(str(src))
        rows, cols = problem.rows, problem.cols
    else:
        problem = Kakurasu.from_file(str(src), prune=kakurasu_prune)
        rows, cols = problem.n, problem.m
    if (rows, cols) != (4, 4):
        raise ValueError("GUI hiện chỉ hỗ trợ input 4x4 (file này là {}x{}).".format(rows, cols))

    try:
        readable_input = str(src.relative_to(ROOT))
    except ValueError:
        readable_input = str(src)
    readable_input = readable_input.replace("\\", "/")

    tracer = Trace(problem, algorithm, max_steps=max_steps, input_name=readable_input)
    kwargs = {"seed": seed} if algorithm == "hill_climbing" else {}
    metric = measure(
        ALGORITHMS[puzzle][algorithm], problem,
        limits=Limits(max_nodes=max_nodes, time_limit=time_limit),
        input_name=readable_input, track_memory=track_memory,
        trace=tracer, **kwargs
    )
    data = tracer.to_dict()
    # Thêm dữ liệu tùy chọn vào result của trace v1, không đổi core/trace.py.
    data["result"]["peak_kb"] = (round(metric.peak_kb, 2)
                                   if metric.peak_kb is not None else None)
    data["result"]["measured_time_s"] = round(metric.time_s, 6)
    data["result"]["memory_method"] = (
        "tracemalloc_peak_second_run_without_trace" if track_memory else None
    )
    data["result"]["input_name"] = readable_input
    data["result"]["kakurasu_prune"] = kakurasu_prune if puzzle == "kakurasu" else None
    data["result"]["random_seed"] = seed if algorithm == "hill_climbing" else None
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy solver và ghi trace 4x4 cho GUI TV4.")
    parser.add_argument("--puzzle", choices=sorted(ALGORITHMS), required=True)
    parser.add_argument("--algorithm", required=True,
                        help="pipes: dfs/hill_climbing; kakurasu: dfs/astar")
    parser.add_argument("--input", dest="input_path", default=None)
    parser.add_argument("--output", required=True, help="Đường dẫn JSON đầu ra")
    parser.add_argument("--max-nodes", type=int, default=50000)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--max-steps", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--memory", action="store_true",
                        help="Đo thêm bộ nhớ bằng lần chạy thứ hai (tracemalloc)")
    parser.add_argument("--prune", choices=("none", "basic", "full"), default="basic",
                        help="Mức cắt tỉa Kakurasu; mặc định basic để khớp trace mẫu TV3")
    args = parser.parse_args()

    try:
        data = run_live_trace(
            args.puzzle, args.algorithm, args.input_path,
            max_nodes=args.max_nodes, time_limit=args.time_limit,
            max_steps=args.max_steps, seed=args.seed,
            track_memory=args.memory, kakurasu_prune=args.prune,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, "Không chạy được solver: {}\n".format(exc))

    result = data["result"]
    print("{} / {}: {}, {} node, {} step -> {}".format(
        args.puzzle, args.algorithm, result["status"],
        result["nodes_expanded"], len(data["steps"]), output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
