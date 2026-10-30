"""TV5 - Kiem thu tich hop va benchmark cho Pipes/Kakurasu.

Dat tai thu muc goc BTL1_AI (cung cap voi verify.py).
Vi du:
    py benchmark.py --puzzle kakurasu --inputs kakurasu_4x4_easy.json \
        --repeats 2 --output results/tv5-smoke-01
    py benchmark.py --puzzle pipes --inputs input_pipes_4x4.json \
        --repeats 1 --output results/tv5-pipes-check

Chuong trinh khong thay doi solver. Ket qua "solved" chi duoc coi la
thanh cong NEU verify_solution(data, final_state) tra True.

Do luong theo core.metrics.measure(): 1 lan do thoi gian, sau do chay LAI
voi tracemalloc de do dinh bo nho Python (khong phai RAM toan bo tien trinh).
Loi giai chi duoc xac thuc tren lan do thoi gian; voi HC dung seed co dinh.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import Limits, astar, dfs, hill_climbing, measure
from puzzles.kakurasu import Kakurasu
from puzzles.pipes import Pipes
from verify import validate_input, verify_solution

ROOT = Path(__file__).resolve().parent
DEFAULT_ALGORITHMS = {
    "kakurasu": ("dfs", "astar"),
    "pipes": ("dfs", "hill_climbing"),
}
ALGORITHMS = {"dfs": dfs, "astar": astar, "hill_climbing": hill_climbing}
RAW_FIELDS = (
    "puzzle", "input", "algorithm", "run", "status", "found", "verified",
    "valid_solution", "time_s", "peak_kb", "nodes_expanded", "nodes_generated",
    "max_frontier", "max_depth", "solution_length", "restarts", "seed", "error",
)
SUMMARY_FIELDS = (
    "puzzle", "input", "algorithm", "runs", "valid_runs", "invalid_runs",
    "unsolved_runs", "error_runs", "statuses", "success_rate",
    "median_time_all_s", "median_time_valid_s", "median_peak_kb_all",
    "median_expanded_all", "median_expanded_valid",
)
ISSUE_FIELDS = ("puzzle", "input", "algorithm", "run", "issue", "detail")


def load_case(path: Path, prune: str = "basic"):
    """Doc JSON, kiem tra schema va tao model dung loai."""
    data = json.loads(path.read_text(encoding="utf-8"))
    kind = validate_input(data)
    if kind == "kakurasu":
        problem = Kakurasu.from_file(str(path), prune=prune)
    elif kind == "pipes":
        problem = Pipes.from_file(str(path))
    else:
        raise ValueError(f"Puzzle chua ho tro: {kind}")
    return kind, data, problem


def selected_inputs(puzzle: str, names: list[str] | None, all_inputs: bool) -> list[Path]:
    data_dir = ROOT / "data"
    if bool(names) == all_inputs:
        raise ValueError("Chi chon --inputs ... HOAC --all-inputs")
    paths = sorted(data_dir.glob("*.json"))
    if names:
        wanted = set(names)
        found = {p.name for p in paths}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError("Khong tim thay JSON: " + ", ".join(missing))
        paths = [p for p in paths if p.name in wanted]
    selected = []
    for path in paths:
        kind, _, _ = load_case(path)
        if puzzle == "both" or kind == puzzle:
            selected.append(path)
        elif names:
            raise ValueError(f"{path.name} la {kind}, khong phai {puzzle}")
    if not selected:
        raise ValueError("Khong co file dau vao phu hop trong data/")
    return selected


def algorithms_for(kind: str, requested: list[str] | None) -> tuple[str, ...]:
    choices = DEFAULT_ALGORITHMS[kind]
    if requested is None:
        return choices
    bad = set(requested) - set(choices)
    if bad:
        raise ValueError(
            f"{kind} chi dung {', '.join(choices)} trong pipeline hien tai; "
            f"khong dung: {', '.join(sorted(bad))}"
        )
    return tuple(dict.fromkeys(requested))


def run_one(path: Path, algorithm: str, *, run: int = 1,
            max_nodes: int = 50000, time_limit: float = 5.0,
            prune: str = "basic", seed: int = 0,
            track_memory: bool = True) -> dict[str, Any]:
    """Tra ve mot hang CSV; luon tach 'solved' khoi 'verified=True'."""
    kind, data, problem = load_case(path, prune=prune)
    algorithms_for(kind, [algorithm])
    kwargs = {"seed": seed} if algorithm == "hill_climbing" else {}
    metrics = measure(
        ALGORITHMS[algorithm], problem,
        limits=Limits(max_nodes=max_nodes, time_limit=time_limit),
        input_name=path.name, track_memory=track_memory, trace=None, **kwargs,
    )
    res = metrics.result
    verified = verify_solution(data, res.final_state) if res.found else None
    record = metrics.row()
    record.update({
        "run": run,
        "verified": verified,
        "valid_solution": bool(res.found and verified),
        "seed": seed if algorithm == "hill_climbing" else "",
        "error": "",
    })
    return {key: record.get(key) for key in RAW_FIELDS}


def failure_row(path: Path, kind: str, algorithm: str, run: int, error: Exception):
    record = {field: "" for field in RAW_FIELDS}
    record.update({"puzzle": kind, "input": path.name, "algorithm": algorithm,
                   "run": run, "status": "exception", "found": False,
                   "verified": None, "valid_solution": False,
                   "error": f"{type(error).__name__}: {error}"})
    return record


def issue_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    base = {key: row[key] for key in ("puzzle", "input", "algorithm", "run")}
    if row["status"] == "exception":
        return {**base, "issue": "exception", "detail": row["error"]}
    if row["found"] and row["verified"] is not True:
        return {**base, "issue": "invalid_solution",
                "detail": "Solver bao solved nhung verify_solution tra False"}
    return None


def _median(values):
    return round(statistics.median(values), 6) if values else ""


def summarize(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for row in raw:
        groups[(row["puzzle"], row["input"], row["algorithm"])].append(row)
    summary = []
    for (puzzle, inp, algorithm), rows in sorted(groups.items()):
        valid = [r for r in rows if r["valid_solution"] is True]
        invalid = [r for r in rows if r["found"] and r["verified"] is False]
        error = [r for r in rows if r["status"] == "exception"]
        unsolved = [r for r in rows if not r["found"] and r["status"] != "exception"]
        times = [r["time_s"] for r in rows if isinstance(r["time_s"], (float, int))]
        mems = [r["peak_kb"] for r in rows if isinstance(r["peak_kb"], (float, int))]
        expanded = [r["nodes_expanded"] for r in rows
                    if isinstance(r["nodes_expanded"], int)]
        summary.append({
            "puzzle": puzzle, "input": inp, "algorithm": algorithm,
            "runs": len(rows), "valid_runs": len(valid),
            "invalid_runs": len(invalid), "unsolved_runs": len(unsolved),
            "error_runs": len(error),
            "statuses": ";".join(f"{name}:{n}" for name, n in
                                 sorted(Counter(r["status"] for r in rows).items())),
            "success_rate": round(len(valid) / len(rows), 4),
            "median_time_all_s": _median(times),
            "median_time_valid_s": _median([r["time_s"] for r in valid]),
            "median_peak_kb_all": _median(mems),
            "median_expanded_all": _median(expanded),
            "median_expanded_valid": _median([r["nodes_expanded"] for r in valid]),
        })
    return summary


def save_csv(path: Path, rows, fields) -> None:
    # BOM giup Excel Windows mo CSV UTF-8 de hon.
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TV5: test solver + benchmark + verify")
    parser.add_argument("--puzzle", choices=("kakurasu", "pipes", "both"),
                        default="kakurasu")
    parser.add_argument("--inputs", nargs="+", help="Ten cac file JSON trong data/")
    parser.add_argument("--all-inputs", action="store_true")
    parser.add_argument("--algorithms", nargs="+", choices=tuple(ALGORITHMS),
                        help="Khong truyen: Kakurasu=dfs+astar, Pipes=dfs+hill_climbing")
    parser.add_argument("--prune", choices=("none", "basic", "full"), default="basic")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=50000)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-memory", action="store_true",
                        help="Chay nhanh, khong do bo nho")
    parser.add_argument("--strict", action="store_true",
                        help="Thoat ma 2 neu co exception hoac solved sai")
    parser.add_argument("--output", type=Path, default=Path("results/tv5-smoke"))
    args = parser.parse_args(argv)
    if args.repeats < 1 or args.max_nodes < 1 or args.time_limit <= 0:
        parser.error("repeats, max-nodes, time-limit phai > 0")
    try:
        paths = selected_inputs(args.puzzle, args.inputs, args.all_inputs)
        choices = {path: algorithms_for(load_case(path, args.prune)[0], args.algorithms)
                   for path in paths}
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    out = (ROOT / args.output).resolve()
    if out.exists():
        parser.error(f"Output da ton tai: {out}. Hay chon ten --output moi.")
    out.mkdir(parents=True)
    meta = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in paths},
        "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
                          (ROOT / "benchmark.py", ROOT / "verify.py",
                           ROOT / "core" / "search.py", ROOT / "core" / "metrics.py",
                           ROOT / "puzzles" / "kakurasu.py", ROOT / "puzzles" / "pipes.py")},
        "settings": {
            "puzzle": args.puzzle, "algorithms": args.algorithms,
            "prune": args.prune, "repeats": args.repeats,
            "max_nodes": args.max_nodes, "time_limit": args.time_limit,
            "seed": args.seed, "track_memory": not args.no_memory,
        },
        "measurement": "core.metrics.measure(): time and memory are separate runs; "
                       "peak_kb = Python tracemalloc allocations (not RSS); "
                       "time excludes file loading and GUI tracing. "
                       "Only the timed run is independently verified.",
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                       encoding="utf-8")

    raw, issues = [], []
    for path in paths:
        kind = load_case(path, args.prune)[0]
        for name in choices[path]:
            for repeat in range(1, args.repeats + 1):
                try:
                    row = run_one(path, name, run=repeat,
                                  max_nodes=args.max_nodes, time_limit=args.time_limit,
                                  prune=args.prune, seed=args.seed,
                                  track_memory=not args.no_memory)
                except Exception as exc:
                    row = failure_row(path, kind, name, repeat, exc)
                raw.append(row)
                issue = issue_from_row(row)
                if issue is not None:
                    issues.append(issue)
                print(f"[{kind}] {path.name} | {name} | run {repeat}: "
                      f"status={row['status']}, verified={row['verified']}, "
                      f"nodes={row['nodes_expanded']}, time_s={row['time_s']}", flush=True)

                # Ghi sau moi case: neu dung giua chung van con ket qua da chay.
                save_csv(out / "benchmark_raw.csv", raw, RAW_FIELDS)
                save_csv(out / "integration_issues.csv", issues, ISSUE_FIELDS)
    save_csv(out / "benchmark_summary.csv", summarize(raw), SUMMARY_FIELDS)
    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    meta["runs"] = len(raw)
    meta["issues"] = len(issues)
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    print("\nDa luu tai:", out)
    print("- benchmark_raw.csv: ket qua moi lan chay")
    print("- benchmark_summary.csv: tong hop")
    print("- integration_issues.csv: solved sai / loi phat sinh")
    print("- metadata.json: cau hinh va checksum")
    if issues:
        print(f"CANH BAO: {len(issues)} loi can xem lai. Khong su dung ket qua sai cho bao cao!")
    else:
        print("Khong phat hien loi tich hop trong cac luot da chay.")
    return 2 if issues and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
