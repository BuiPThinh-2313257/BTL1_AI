"""TV5 - Tao bang va bieu do tu benchmark_summary.csv cua BTL1_AI.

Tai thu muc goc BTL1_AI:
    py -m pip install matplotlib
    py tools/tv5_make_charts.py --summary results/tv5-kakurasu-full/benchmark_summary.csv --output results/tv5-charts-kakurasu

Khong xem N/A (khong giai duoc) la so 0.
"""
import argparse
import csv
import math
from pathlib import Path


def read_rows(paths):
    rows = []
    keys = set()
    for filename in paths:
        path = Path(filename)
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row["puzzle"], row["input"], row["algorithm"])
                if key in keys:
                    raise ValueError(f"Trung cau hinh {key}; khong gop hai summary trung nhau")
                keys.add(key)
                rows.append(row)
    if not rows:
        raise ValueError("CSV khong co du lieu")
    return rows


def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


def pretty_input(filename):
    name = Path(filename).stem
    for prefix in ("kakurasu_", "input_pipes_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.replace("_", " ").title()


def sort_case(case):
    import re
    nums = [int(v) for v in re.findall(r"\d+", case)]
    return (nums, case)


def plot_puzzle(rows, puzzle, output):
    import matplotlib.pyplot as plt
    import numpy as np
    group = [r for r in rows if r["puzzle"] == puzzle]
    cases = sorted({r["input"] for r in group}, key=sort_case)
    algos = sorted({r["algorithm"] for r in group})
    lookup = {(r["input"], r["algorithm"]): r for r in group}
    specs = (
        ("median_time_valid_s", "Time (s) - valid runs only", "time_valid"),
        ("median_peak_kb_all", "Peak Python memory (KiB) - all runs", "memory_all"),
        ("median_expanded_valid", "Expanded nodes - valid runs only", "nodes_valid"),
        ("success_rate", "Verified success rate (%)", "success_rate"),
    )
    output.mkdir(parents=True, exist_ok=True)
    for column, ylabel, suffix in specs:
        fig, ax = plt.subplots(figsize=(max(9, len(cases) * 0.92), 5.2))
        all_values = []
        for item in group:
            v = number(item.get(column))
            if v is not None and v > 0:
                all_values.append(v)
        logarithmic = (column != "success_rate" and all_values
                       and max(all_values) / min(all_values) >= 100)
        if logarithmic:
            ax.set_yscale("log")
            ax.set_ylim(min(all_values) / 2, max(all_values) * 2)
            ylabel += " (log scale)"
        x = np.arange(len(cases))
        width = 0.82 / len(algos)
        for i, algo in enumerate(algos):
            heights = []
            missing = []
            for case in cases:
                r = lookup.get((case, algo))
                v = number(r.get(column)) if r else None
                if v is None:
                    missing.append(case)
                if v is not None and column == "success_rate":
                    v *= 100
                heights.append(0 if v is None else v)
            xoffset = x - 0.41 + width * (i + 0.5)
            bars = ax.bar(xoffset, heights, width, label=algo.upper())
            for case_idx, bar in enumerate(bars):
                if cases[case_idx] in missing:
                    baseline = min(all_values) / 2 if logarithmic else 0
                    ax.annotate("N/A", (bar.get_x() + bar.get_width()/2, baseline),
                                xytext=(0, 5), textcoords="offset points",
                                ha="center", va="bottom", fontsize=8,
                                rotation=90)
        ax.set_xticks(x)
        ax.set_xticklabels([pretty_input(s) for s in cases], rotation=40, ha="right")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{puzzle.title()} - {suffix.replace('_', ' ')}")
        ax.legend()
        if column == "success_rate":
            ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=0.22)
        fig.tight_layout()
        fig.savefig(output / f"{puzzle}_{suffix}.png", dpi=160)
        plt.close(fig)
    print(f"[OK] {puzzle}: {len(cases)} input, {len(algos)} thuat toan, 4 bieu do")


def main():
    p = argparse.ArgumentParser(description="TV5: tao bang va bieu do benchmark")
    p.add_argument("--summary", nargs="+", required=True, help="Cac file benchmark_summary.csv")
    p.add_argument("--output", required=True, help="Thu muc dau ra")
    a = p.parse_args()
    rows = read_rows(a.summary)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "benchmark_summary_combined.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for puzzle in sorted({r["puzzle"] for r in rows}):
        plot_puzzle(rows, puzzle, out)
    print(f"Da luu tai: {out.resolve()}")


if __name__ == "__main__":
    main()
