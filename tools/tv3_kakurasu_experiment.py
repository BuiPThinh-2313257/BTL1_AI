"""Reproduce the TV3 Kakurasu report only; the group benchmark belongs to TV5.

Standard library only. Run from any directory with --output <new-directory>.
Timing and Python allocation peaks are measured in separate solver executions.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core import Limits, astar, bfs, dfs
from puzzles.kakurasu import Kakurasu, verify

ALGORITHMS = {"dfs": dfs, "bfs": bfs, "astar": astar}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = [*sorted((ROOT / "core").glob("*.py")),
             ROOT / "puzzles/kakurasu.py", Path(__file__).resolve()]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_case(path, algorithm, prune, phase, repeat, args):
    # Include model construction and subset-table preprocessing in both measures.
    gc.collect()
    if phase == "memory":
        tracemalloc.start()
    started = time.perf_counter()
    try:
        problem = Kakurasu.from_file(path, prune=prune)
        result = ALGORITHMS[algorithm](problem, limits=Limits(
            max_nodes=args.max_nodes,
            time_limit=args.memory_time_limit if phase == "memory" else args.time_limit))
        elapsed = time.perf_counter() - started
        peak_kib = tracemalloc.get_traced_memory()[1] / 1024 if phase == "memory" else None
    finally:
        if phase == "memory":
            tracemalloc.stop()
    valid = None
    if result.found:
        valid = (problem.is_goal(result.final_state)
                 and verify(problem.to_grid(result.final_state),
                            problem.row_clues, problem.col_clues)
                 and result.cost == sum(result.final_state)
                 and len(result.actions) == problem.size)
        if not valid:
            raise RuntimeError("Invalid solved result: " + path.name)
    row = {
        "input": path.stem, "algorithm": algorithm, "prune": prune,
        "phase": phase, "repeat": repeat, "status": result.status,
        "valid": valid, "elapsed_s": elapsed, "peak_python_kib": peak_kib,
        "nodes_expanded": result.nodes_expanded, "nodes_generated": result.nodes_generated,
        "max_frontier": result.max_frontier, "cost": result.cost if result.found else None,
    }
    signature = (result.status, result.nodes_expanded, result.nodes_generated,
                 result.max_frontier, result.cost, result.final_state)
    return row, signature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwrite evidence")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-nodes", type=int, default=50000)
    parser.add_argument("--time-limit", type=float, default=5.0)
    parser.add_argument("--memory-time-limit", type=float, default=30.0)
    parser.add_argument("--inputs", nargs="*", help="Optional filenames from data/ for a smoke run")
    args = parser.parse_args()
    if args.repeats < 1 or args.max_nodes < 1 or min(args.time_limit, args.memory_time_limit) <= 0:
        parser.error("Counts and limits must be positive")
    paths = sorted((ROOT / "data").glob("kakurasu_*.json"))
    if args.inputs is not None:
        wanted = set(args.inputs)
        paths = [p for p in paths if p.name in wanted]
        if {p.name for p in paths} != wanted or not paths:
            parser.error("--inputs must name existing Kakurasu JSON files")
    if not paths:
        parser.error("No Kakurasu inputs")
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = source_hashes()
    metadata = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv], "python": sys.version,
        "platform": platform.platform(), "processor": platform.processor(),
        "logical_cpus": os.cpu_count(), "git_head": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"), "git_status": git("status", "--porcelain"),
        "source_sha256": snapshot,
        "data_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in paths},
        "parameters": {"repeats": args.repeats, "max_nodes": args.max_nodes,
                       "time_limit_s": args.time_limit, "memory_time_limit_s": args.memory_time_limit},
        "method": "serial, no trace; fresh model each run; model construction included; no warmup; "
                  "timing without tracemalloc; one separate memory run per case; KiB=1024 bytes; "
                  "Python allocation peak, not process RSS; valid=None for unsolved",
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    raw, summaries = [], []
    for path in paths:
        for prune in ("basic", "full"):
            for algorithm in ALGORITHMS:
                timings, signatures = [], []
                for repeat in range(1, args.repeats + 1):
                    row, signature = run_case(path, algorithm, prune, "time", repeat, args)
                    raw.append(row)
                    timings.append(row)
                    signatures.append(signature)
                mem, mem_signature = run_case(path, algorithm, prune, "memory", 1, args)
                raw.append(mem)
                same_time = all(s == signatures[0] for s in signatures)
                same_mem = same_time and mem_signature == signatures[0]
                summaries.append({
                    "input": path.stem, "algorithm": algorithm, "prune": prune,
                    "time_statuses": "/".join(r["status"] for r in timings),
                    "time_runs_match": same_time,
                    "time_median_s": statistics.median(r["elapsed_s"] for r in timings),
                    "time_min_s": min(r["elapsed_s"] for r in timings),
                    "time_max_s": max(r["elapsed_s"] for r in timings),
                    "nodes_expanded": timings[0]["nodes_expanded"] if same_time else None,
                    "nodes_generated": timings[0]["nodes_generated"] if same_time else None,
                    "max_frontier": timings[0]["max_frontier"] if same_time else None,
                    "cost": timings[0]["cost"] if same_time else None,
                    "all_solutions_valid": all(r["valid"] is not False for r in timings + [mem]),
                    "memory_status": mem["status"], "memory_nodes_expanded": mem["nodes_expanded"],
                    "memory_run_matches_time": same_mem, "peak_python_kib": mem["peak_python_kib"],
                })
                # Checkpoint after each case so partial evidence is inspectable.
                write_csv(args.output / "raw.csv", raw)
                write_csv(args.output / "summary.csv", summaries)
                print(path.stem, prune, algorithm, summaries[-1]["time_statuses"],
                      "nodes=", summaries[-1]["nodes_expanded"], "memory_match=", same_mem, flush=True)
    if source_hashes() != snapshot or any(digest(ROOT / p) != h for p, h in metadata["data_sha256"].items()):
        raise RuntimeError("Inputs or source changed while measuring; discard this run")
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["completed_cases"] = len(summaries)
    metadata["raw_runs"] = len(raw)
    (args.output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("COMPLETE", len(summaries), "cases;", len(raw), "runs", flush=True)


if __name__ == "__main__":
    main()
