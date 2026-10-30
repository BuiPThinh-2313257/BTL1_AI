"""Build the report's illustrative figure and excerpt tables from saved inputs.

Requires Pillow for PNG drawing. Does not modify solvers or experiment evidence.
Run from any directory: python tools/build_tv3_report_figures.py
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/bao_cao_tv3_kakurasu.md"
OUTPUT = ROOT / "docs/images/kakurasu_de_va_loi_giai.png"
START = "<!-- TRACE_TABLES -->"
END = "<!-- END_TRACE_TABLES -->"


def load_trace(algorithm):
    path = ROOT / f"traces/example_kakurasu_4x4_{algorithm}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def trace_table(algorithm):
    trace = load_trace(algorithm)
    extra = " | h | f" if algorithm == "astar" else ""
    title = "A*" if algorithm == "astar" else "DFS"
    lines = [f"### 7.{'2' if algorithm == 'astar' else '1'}. Trích trace {title}", "",
             "| i | Sự kiện | Tiền tố s | Độ sâu | g" + extra + " |",
             "|---:|---|---|---:|---:" + ("|---:|---:" if extra else "") + "|"]
    for step in trace["steps"][:5] + trace["steps"][-2:]:
        flat = [v for row in step["state"]["grid"] for v in row if v is not None]
        state = "s_đích" if len(flat) == 16 else "(" + ",".join(map(str, flat)) + ("," if len(flat) == 1 else "") + ")"
        values = [str(step["i"]), step["event"], f"`{state}`",
                  str(step["depth"]), f"{step['g']:g}"]
        if extra:
            values += [f"{step[k]:g}" if k in step else "—" for k in ("h", "f")]
        lines.append("| " + " | ".join(values) + " |")
    if extra:
        lines += ["", "Dấu —: sự kiện `goal` trong JSON không lưu lại h/f; không phải giá trị 0."]
    return "\n".join(lines)


def build_figure():
    data = json.loads((ROOT / "data/kakurasu_4x4_easy.json").read_text(encoding="utf-8"))
    grid = load_trace("astar")["solution"][-1]["grid"]
    assert all(type(v) is int and v in (0, 1) for row in grid for v in row)
    assert [sum((j + 1) * v for j, v in enumerate(row)) for row in grid] == data["row_clues"]
    assert [sum((i + 1) * grid[i][j] for i in range(4)) for j in range(4)] == data["col_clues"]
    scale = 2
    canvas = Image.new("RGB", (1800 * scale, 900 * scale), "#f4f7fa")
    draw = ImageDraw.Draw(canvas)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    bold_path = Path("C:/Windows/Fonts/arialbd.ttf")

    def font(size, bold=False):
        return ImageFont.truetype(str(bold_path if bold else font_path), size * scale)

    def text(x, y, message, size=28, fill="#243348", bold=False, anchor="mm"):
        draw.text((x * scale, y * scale), message, font=font(size, bold), fill=fill, anchor=anchor)

    def rect(box, fill, outline=None, width=1):
        draw.rectangle(tuple(v * scale for v in box), fill=fill, outline=outline, width=width * scale)

    text(900, 58, "KAKURASU 4 × 4", 42, bold=True)
    text(900, 108, "Trọng số hàng và cột được đánh số từ 1", 26, fill="#526279")
    for x0, solved in ((110, False), (1010, True)):
        rect((x0 - 55, 160, x0 + 685, 790), "white", "#dbe3ec", 2)
        text(x0 + 310, 200, "LỜI GIẢI" if solved else "ĐỀ MẪU", 32, bold=True)
        cell, top = 100, 300
        for j in range(4):
            text(x0 + cell * (j + .5), top - 35, str(j + 1), 25, fill="#617287")
        text(x0 - 10, top - 74, "Chỉ số cột", 23, anchor="lm", fill="#617287")
        text(x0 + 520, top - 35, "Tổng hàng", 23, fill="#187968", bold=True)
        for i in range(4):
            text(x0 - 28, top + cell * (i + .5), str(i + 1), 25, fill="#617287")
            for j in range(4):
                x, y = x0 + cell * j, top + cell * i
                black = solved and grid[i][j]
                rect((x, y, x + cell, y + cell), "#25364a" if black else ("white" if solved else "#edf3f8"), "#738399", 2)
                if not solved:
                    text(x + cell / 2, y + cell / 2, "?", 32, fill="#8394a8")
            text(x0 + 520, top + cell * (i + .5), str(data["row_clues"][i]), 34, fill="#187968", bold=True)
        for j in range(4):
            text(x0 + cell * (j + .5), top + 440, str(data["col_clues"][j]), 34, fill="#187968", bold=True)
        text(x0 + 520, top + 440, "Tổng cột", 23, fill="#187968", bold=True)
    text(900, 830, "?  Chưa quyết định     |     Ô đen: được chọn     |     Ô trắng: không chọn", 27)
    text(900, 872, "Dựng từ input 4x4_easy · ID 9272227 · Lời giải đã kiểm tra tổng hàng/cột", 24, fill="#526279")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT)


def main():
    build_figure()
    report = REPORT.read_text(encoding="utf-8")
    tables = START + "\n\n" + trace_table("dfs") + "\n\n" + trace_table("astar") + "\n\n" + END
    if END in report:
        first = report.index(START)
        last = report.index(END) + len(END)
        report = report[:first] + tables + report[last:]
    else:
        assert report.count(START) == 1
        report = report.replace(START, tables)
    REPORT.write_text(report, encoding="utf-8")
    print("Built figure and trace excerpts from saved input/solution/events.")


if __name__ == "__main__":
    main()
