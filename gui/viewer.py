"""TV4 – GĐ2: GUI xem trace mẫu hoặc chạy solver thật cho hai bài 4x4.

Chạy: python gui/viewer.py
Solver chạy qua tiến trình con (gui.live_runner), không chặn giao diện.
Không sửa core, puzzles hay benchmark của các thành viên khác.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.trace import load_trace
from gui.live_runner import DEFAULT_INPUTS

# Trace THẬT đã có trong repository của nhóm, không phải trace tự tạo.
TRACES = {
    "pipes": {
        "DFS": "pipes_4x4_dfs.json",
        "Hill Climbing": "pipes_4x4_hc.json",
    },
    "kakurasu": {
        "DFS": "example_kakurasu_4x4_dfs.json",
        "A*": "example_kakurasu_4x4_astar.json",
    },
}

COL = {
    "bg": "#0B1220", "panel": "#121F33", "tile": "#17283E",
    "tile_alt": "#1D3049", "border": "#2A3E59", "text": "#EDF4FF",
    "muted": "#A3B4CB", "accent": "#55ABFF", "accent_dim": "#193D61",
    "green": "#40DCAB", "yellow": "#FDCB70", "red": "#FE8290",
    "black_cell": "#375F92", "white_cell": "#E3EBF5",
}

EVENTS = {
    "initial": ("TRẠNG THÁI BAN ĐẦU", "Đây là dữ liệu đầu vào, trước sự kiện tìm kiếm đầu tiên."),
    "expand": ("EXPAND · MỞ RỘNG NODE", "Giải thuật đang lấy trạng thái này ra để xem xét."),
    "goal": ("GOAL · ĐẠT ĐÍCH", "Thuật toán đã tìm được trạng thái thỏa mãn yêu cầu."),
    "move": ("MOVE · DI CHUYỂN", "Hill Climbing đang chuyển sang trạng thái lân cận."),
    "restart": ("RESTART · KHỞI ĐỘNG LẠI", "Giải thuật tìm kiếm cục bộ bắt đầu lại."),
    "stuck": ("STUCK · BỊ KẸT", "Giải thuật không tìm thấy trạng thái tốt hơn."),
    "solution": ("SOLUTION PATH", "Một trạng thái nằm trên đường đi từ đầu đến đích."),
}
DIRECTIONS = {"up": (0, -1), "right": (1, 0), "down": (0, 1), "left": (-1, 0)}


def _matrix_4x4(value: Any) -> bool:
    return (isinstance(value, list) and len(value) == 4 and
            all(isinstance(row, list) and len(row) == 4 for row in value))


def validate_trace(data: Dict[str, Any]) -> None:
    """Kiểm tra phần cần thiết cho GUI; tránh crash với file JSON bị sai."""
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Trace phải là JSON object, version = 1.")
    puzzle = data.get("puzzle")
    if puzzle not in TRACES:
        raise ValueError("Giao diện hiện chỉ hỗ trợ 'pipes' và 'kakurasu'.")
    if not isinstance(data.get("steps"), list) or not isinstance(data.get("solution"), list):
        raise ValueError("Thiếu danh sách 'steps' hoặc 'solution'.")

    def check_state(state: Any) -> None:
        if puzzle == "pipes":
            if not _matrix_4x4(state):
                raise ValueError("Pipes phải là ma trận 4×4.")
            for row in state:
                for cell in row:
                    if cell is not None and (not isinstance(cell, list) or
                            any(direction not in DIRECTIONS for direction in cell)):
                        raise ValueError("Ống phải là null hoặc danh sách hướng hợp lệ.")
        else:
            if not isinstance(state, dict) or not _matrix_4x4(state.get("grid")):
                raise ValueError("Kakurasu cần object có 'grid' 4×4.")
            if (not isinstance(state.get("rows"), (list, tuple)) or len(state["rows"]) != 4 or
                    not isinstance(state.get("cols"), (list, tuple)) or len(state["cols"]) != 4):
                raise ValueError("Kakurasu cần 'rows' và 'cols', mỗi trường 4 số.")
            if any(cell not in (0, 1, None) for row in state["grid"] for cell in row):
                raise ValueError("Ô Kakurasu chỉ được là 0, 1 hoặc null.")

    check_state(data.get("initial"))
    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict) or "state" not in step or "event" not in step:
            raise ValueError("Bước số {} thiếu 'state' hoặc 'event'.".format(i))
        check_state(step["state"])
    for state in data["solution"]:
        check_state(state)


def get_frames(data: Dict[str, Any], mode: str) -> List[Dict[str, Any]]:
    """Chuẩn hoá cả trace-search và solution thành danh sách frame để phát lại."""
    if mode == "solution" and data["solution"]:
        result = []
        for i, state in enumerate(data["solution"]):
            result.append({"event": "solution", "state": state, "i": i,
                           "path_position": i})
        return result
    return ([{"event": "initial", "state": data["initial"], "i": -1}] +
            data["steps"])


def changed_cells(before: Any, after: Any, puzzle: str) -> List[Tuple[int, int]]:
    """Xác định các ô đã thay đổi giữa 2 frame liên tiếp."""
    if before is None:
        return []
    old = before if puzzle == "pipes" else before["grid"]
    new = after if puzzle == "pipes" else after["grid"]
    return [(r, c) for r in range(4) for c in range(4) if old[r][c] != new[r][c]]


def fmt_number(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    if isinstance(value, int):
        return "{:,}".format(value)
    if isinstance(value, float):
        return "{:,.2f}".format(value)
    return str(value)


class Viewer(tk.Tk):
    """Tkinter app: chọn puzzle/algorithm, xem trace, phát lại từng bước."""

    def __init__(self) -> None:
        super().__init__()
        self.title("AI Search Visualizer  |  Pipes & Kakurasu 4×4")
        self.geometry("1150x800")
        self.minsize(940, 680)
        self.configure(bg=COL["bg"])

        self.puzzle = "pipes"
        self.algorithm = "DFS"
        self.mode = "search"
        self.trace: Dict[str, Any] = {}
        self.frames: List[Dict[str, Any]] = []
        self.position = 0
        self.is_playing = False
        self.after_id: Optional[str] = None
        self.slider_update = False
        self.current_path = ""
        self.selected_input: Optional[Path] = None
        self.running_solver = False
        self.solver_process: Optional[subprocess.Popen] = None
        self.solver_temp_path: Optional[Path] = None
        self.solver_poll_id: Optional[str] = None

        self._create_widgets()
        self._load_builtin()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _label(self, parent: tk.Widget, text: str, size: int = 11,
               color: str = "text", bold: bool = False, **kwargs: Any) -> tk.Label:
        return tk.Label(parent, text=text, bg=parent.cget("bg"),
                        fg=COL.get(color, color), anchor="w",
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        **kwargs)

    def _button(self, parent: tk.Widget, text: str, command: Any,
                prominent: bool = False, width: int = 0) -> tk.Button:
        return tk.Button(parent, text=text, command=command, width=width,
                         font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
                         highlightthickness=0, cursor="hand2", padx=13, pady=10,
                         bg=COL["accent_dim"] if prominent else COL["tile_alt"],
                         fg=COL["text"], activebackground=COL["accent_dim"],
                         activeforeground=COL["text"])

    def _panel(self, parent: tk.Widget) -> tk.Frame:
        return tk.Frame(parent, bg=COL["panel"], highlightthickness=1,
                        highlightbackground=COL["border"])

    def _create_widgets(self) -> None:
        header = tk.Frame(self, bg=COL["bg"])
        header.pack(fill="x", padx=24, pady=(19, 13))
        tk.Label(header, text="AI", bg=COL["accent_dim"], fg=COL["accent"],
                 font=("Segoe UI", 17, "bold"), width=3, height=2).pack(side="left", padx=(0, 12))
        title_block = tk.Frame(header, bg=COL["bg"])
        title_block.pack(side="left")
        self._label(title_block, "AI SEARCH VISUALIZER", 20, bold=True).pack(anchor="w")
        self._label(title_block, "BTL1  ·  TV4 – Giao diện  ·  Pipes & Kakurasu 4×4",
                    10, "muted").pack(anchor="w")
        self.save_button = self._button(header, "LƯU TRACE", self._save_json)
        self.save_button.pack(side="right", padx=(7, 0))
        self.open_button = self._button(header, "MỞ TRACE JSON", self._open_json)
        self.open_button.pack(side="right")

        selectors = self._panel(self)
        selectors.pack(fill="x", padx=24, pady=(0, 13), ipady=8)
        chooser = tk.Frame(selectors, bg=COL["panel"])
        chooser.pack(side="left", padx=16)
        self._label(chooser, "BÀI TOÁN", 9, "muted", bold=True).pack(anchor="w", pady=(0, 5))
        self.puzzle_buttons = tk.Frame(chooser, bg=COL["panel"])
        self.puzzle_buttons.pack(anchor="w")

        algorithms = tk.Frame(selectors, bg=COL["panel"])
        algorithms.pack(side="left", padx=(20, 16))
        self._label(algorithms, "GIẢI THUẬT", 9, "muted", bold=True).pack(anchor="w", pady=(0, 5))
        self.algorithm_buttons = tk.Frame(algorithms, bg=COL["panel"])
        self.algorithm_buttons.pack(anchor="w")
        self._update_selectors()

        input_area = tk.Frame(selectors, bg=COL["panel"])
        input_area.pack(side="right", padx=(16, 16))
        self._label(input_area, "INPUT 4×4", 9, "muted", bold=True).pack(anchor="w", pady=(0, 5))
        input_buttons = tk.Frame(input_area, bg=COL["panel"])
        input_buttons.pack(anchor="e")
        self.input_button = self._button(input_buttons, "CHỌN INPUT", self._choose_input)
        self.input_button.pack(side="left", padx=(0, 7))
        self.run_button = self._button(input_buttons, "▶ CHẠY SOLVER", self._run_solver, prominent=True)
        self.run_button.pack(side="left")
        self.input_caption = self._label(input_area, "", 9, "muted")
        self.input_caption.pack(anchor="e", pady=(4, 0))
        self._refresh_input_caption()

        main = tk.Frame(self, bg=COL["bg"])
        main.pack(fill="both", expand=True, padx=24)
        board_panel = self._panel(main)
        board_panel.pack(side="left", fill="both", expand=True)
        head = tk.Frame(board_panel, bg=COL["panel"])
        head.pack(fill="x", padx=20, pady=(15, 4))
        self.board_title = self._label(head, "PIPES · BẢNG 4×4", 14, bold=True)
        self.board_title.pack(side="left")
        self.board_hint = self._label(head, "", 10, "muted")
        self.board_hint.pack(side="right")
        self.canvas = tk.Canvas(board_panel, bg=COL["panel"], bd=0,
                                relief="flat", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=4)
        self.canvas.bind("<Configure>", lambda event: self._draw_board())
        legend = tk.Frame(board_panel, bg=COL["panel"])
        legend.pack(fill="x", padx=20, pady=(2, 12))
        self.legend_text = self._label(legend, "", 9, "muted")
        self.legend_text.pack(anchor="w")

        side = self._panel(main)
        side.configure(width=300)
        side.pack(side="right", fill="y", padx=(13, 0))
        side.pack_propagate(False)
        self._label(side, "THÔNG TIN TRACE", 11, bold=True).pack(anchor="w", padx=18, pady=(12, 7))
        self.file_text = self._label(side, "", 10, "muted", wraplength=258, justify="left")
        self.file_text.pack(fill="x", padx=18, pady=(0, 7))

        sep = tk.Frame(side, bg=COL["border"], height=1)
        sep.pack(fill="x", padx=18)
        self.event_label = self._label(side, "TRẠNG THÁI BAN ĐẦU", 11, "accent", bold=True)
        self.event_label.pack(fill="x", padx=18, pady=(9, 4))
        self.event_detail = self._label(side, "", 10, "muted", wraplength=255, justify="left")
        self.event_detail.pack(fill="x", padx=18)
        self.meta_label = self._label(side, "", 10, "text", wraplength=255,
                                      justify="left")
        self.meta_label.pack(fill="x", padx=18, pady=(7, 7))
        tk.Frame(side, bg=COL["border"], height=1).pack(fill="x", padx=18)
        self._label(side, "TỔNG KẾT SOLVER", 10, "muted", bold=True).pack(
            anchor="w", padx=18, pady=(8, 4))
        self.metrics: Dict[str, tk.StringVar] = {}
        for caption, key in (("Kết quả", "status"), ("Node mở rộng", "expanded"),
                             ("Node đã sinh", "generated"), ("Độ dài lời giải", "length"),
                             ("Thời gian thuật toán", "elapsed"), ("Bộ nhớ", "memory")):
            row = tk.Frame(side, bg=COL["panel"])
            row.pack(fill="x", padx=18, pady=1)
            self._label(row, caption, 10, "muted").pack(side="left")
            value = tk.StringVar(value="—")
            self.metrics[key] = value
            tk.Label(row, textvariable=value, bg=COL["panel"], fg=COL["text"],
                     font=("Segoe UI", 10, "bold")).pack(side="right")

        player = self._panel(self)
        player.pack(fill="x", padx=24, pady=(13, 12))
        player_top = tk.Frame(player, bg=COL["panel"])
        player_top.pack(fill="x", padx=15, pady=(12, 7))
        self.mode_buttons = tk.Frame(player_top, bg=COL["panel"])
        self.mode_buttons.pack(side="left")
        self._update_modes()
        self.counter = self._label(player_top, "BƯỚC 0 / 0", 10, "muted", bold=True)
        self.counter.pack(side="right")

        self.seek = tk.Scale(player, from_=0, to=1, orient="horizontal",
                             command=self._seek_to, bg=COL["panel"], fg=COL["text"],
                             troughcolor=COL["tile_alt"], activebackground=COL["accent"],
                             highlightthickness=0, bd=0, sliderrelief="flat", showvalue=False,
                             length=600)
        self.seek.pack(fill="x", padx=15)

        player_bottom = tk.Frame(player, bg=COL["panel"])
        player_bottom.pack(fill="x", padx=15, pady=(3, 12))
        self._button(player_bottom, "|◀", self._reset, width=4).pack(side="left", padx=(0, 6))
        self._button(player_bottom, "◀", self._prev, width=4).pack(side="left", padx=(0, 6))
        self.play_button = self._button(player_bottom, "▶  PHÁT", self._toggle_play,
                                        prominent=True, width=11)
        self.play_button.pack(side="left", padx=(0, 6))
        self._button(player_bottom, "▶|", self._next, width=4).pack(side="left")
        self.speed_var = tk.IntVar(value=5)
        self._label(player_bottom, "TỐC ĐỘ", 9, "muted", bold=True).pack(
            side="left", padx=(24, 5))
        self.speed = tk.Scale(player_bottom, from_=1, to=20, orient="horizontal",
                              variable=self.speed_var, bg=COL["panel"], fg=COL["text"],
                              troughcolor=COL["tile_alt"], activebackground=COL["accent"],
                              highlightthickness=0, bd=0, sliderrelief="flat", length=150,
                              showvalue=False, command=lambda unused: self._refresh_speed())
        self.speed.pack(side="left")
        self.speed_label = self._label(player_bottom, "5 bước/s", 9, "muted")
        self.speed_label.pack(side="left", padx=(4, 0))
        self.status_line = self._label(self, "", 9, "muted")
        self.status_line.pack(fill="x", padx=26, pady=(0, 6))

    def _refresh_input_caption(self) -> None:
        path = self.selected_input or DEFAULT_INPUTS[self.puzzle]
        self.input_caption.configure(text=path.name)

    def _choose_input(self) -> None:
        if self.running_solver:
            return
        path = filedialog.askopenfilename(
            title="Chọn input {} 4×4".format(self.puzzle),
            initialdir=str(ROOT / "data"),
            filetypes=[("JSON input", "*.json"), ("Tất cả file", "*.*")])
        if path:
            self.selected_input = Path(path)
            self._refresh_input_caption()

    def _run_solver(self) -> None:
        """Chạy solver trong tiến trình con; Tk vẫn phản hồi khi solver chạy."""
        if self.running_solver:
            return
        self._stop()
        self.running_solver = True
        self.run_button.configure(state="disabled", text="ĐANG CHẠY...")
        self.input_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status_line.configure(text="Đang giải {} / {} trên input thật...".format(
            self.puzzle, self.algorithm))

        fd, fname = tempfile.mkstemp(prefix="tv4_solver_", suffix=".json")
        os.close(fd)
        self.solver_temp_path = Path(fname)
        selected_algo = self.algorithm.lower().replace(" ", "_").replace("*", "star")
        # Dùng trực tiếp tên hàm trong core/search.py.
        if self.algorithm == "A*":
            selected_algo = "astar"
        command = [
            sys.executable, "-m", "gui.live_runner",
            "--puzzle", self.puzzle,
            "--algorithm", selected_algo,
            "--input", str(self.selected_input or DEFAULT_INPUTS[self.puzzle]),
            "--output", fname,
            "--max-nodes", "50000",
            "--time-limit", "5",
            "--max-steps", "10000",
            "--seed", "0",
            "--memory",
        ]
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.solver_process = subprocess.Popen(
                command, cwd=str(ROOT), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                creationflags=flags)
            self.solver_poll_id = self.after(100, self._poll_solver)
        except OSError as exc:
            self._finish_run()
            messagebox.showerror("Không chạy được solver", str(exc))

    def _poll_solver(self) -> None:
        self.solver_poll_id = None
        process = self.solver_process
        if process is None:
            return
        if process.poll() is None:
            self.solver_poll_id = self.after(100, self._poll_solver)
            return
        stdout, stderr = process.communicate()
        target = self.solver_temp_path
        self._finish_run(clear_temp=False)
        if process.returncode != 0:
            messagebox.showerror("Solver báo lỗi", (stderr or stdout or
                                  "Không nhận được kết quả từ solver.")[-1800:])
            self.status_line.configure(text="Chạy solver thất bại; trace trước đó vẫn còn.")
            if target is not None:
                target.unlink(missing_ok=True)
            self.solver_temp_path = None
            return
        try:
            if target is None:
                raise ValueError("Không có tệp kết quả của solver")
            data = load_trace(str(target))
            validate_trace(data)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Trace mới không hợp lệ", str(exc))
            return
        finally:
            if target is not None:
                target.unlink(missing_ok=True)
            self.solver_temp_path = None
        self._apply_trace_data(data, "LIVE · " + str(data.get("input") or "input"))
        status = data.get("result", {}).get("status", "?")
        warning = " · Trace bị cắt" if data.get("truncated") else ""
        self.status_line.configure(text="Solver thật: {} / {} · {}{}".format(
            self.puzzle, self.algorithm, status.upper(), warning))

    def _finish_run(self, clear_temp: bool = True) -> None:
        self.running_solver = False
        if self.solver_poll_id is not None:
            self.after_cancel(self.solver_poll_id)
            self.solver_poll_id = None
        self.solver_process = None
        if clear_temp and self.solver_temp_path is not None:
            try:
                self.solver_temp_path.unlink()
            except OSError:
                pass
            self.solver_temp_path = None
        self.run_button.configure(state="normal", text="▶ CHẠY SOLVER")
        self.input_button.configure(state="normal")
        self.open_button.configure(state="normal")
        self.save_button.configure(state="normal")

    def _save_json(self) -> None:
        if self.running_solver or not self.trace:
            return
        name = "{}_{}_live.json".format(
            self.puzzle, self.trace.get("algorithm", "search"))
        dest = filedialog.asksaveasfilename(
            title="Lưu trace để chia sẻ / thuyết trình", defaultextension=".json",
            initialdir=str(ROOT / "traces"), initialfile=name,
            filetypes=[("JSON", "*.json")])
        if not dest:
            return
        try:
            with open(dest, "w", encoding="utf-8") as handle:
                json.dump(self.trace, handle, ensure_ascii=False, indent=2)
            self.status_line.configure(text="Đã lưu trace: {}".format(dest))
        except OSError as exc:
            messagebox.showerror("Không lưu được trace", str(exc))

    def _refresh_speed(self) -> None:
        self.speed_label.configure(text="{} bước/s".format(self.speed_var.get()))

    def _selection_button(self, parent: tk.Widget, text: str, selected: bool,
                          command: Any) -> None:
        button = self._button(parent, text, command, prominent=selected)
        if selected:
            button.configure(fg=COL["accent"], bg=COL["accent_dim"])
        button.pack(side="left", padx=(0, 5))

    def _update_selectors(self) -> None:
        for w in self.puzzle_buttons.winfo_children():
            w.destroy()
        for puzzle, name in (("pipes", "Pipes 4×4"), ("kakurasu", "Kakurasu 4×4")):
            self._selection_button(self.puzzle_buttons, name, puzzle == self.puzzle,
                                   lambda p=puzzle: self._choose_puzzle(p))
        self._update_algorithms()

    def _update_algorithms(self) -> None:
        for w in self.algorithm_buttons.winfo_children():
            w.destroy()
        for algo in TRACES[self.puzzle]:
            self._selection_button(self.algorithm_buttons, algo, self.algorithm == algo,
                                   lambda a=algo: self._choose_algo(a))

    def _update_modes(self) -> None:
        for w in self.mode_buttons.winfo_children():
            w.destroy()
        for mode, name in (("search", "QUÁ TRÌNH TÌM KIẾM"),
                           ("solution", "ĐƯỜNG ĐI LỜI GIẢI")):
            self._selection_button(self.mode_buttons, name, mode == self.mode,
                                   lambda m=mode: self._choose_mode(m))

    def _choose_puzzle(self, puzzle: str) -> None:
        if self.running_solver or puzzle == self.puzzle:
            return
        self.puzzle = puzzle
        self.selected_input = None
        self._refresh_input_caption()
        self.algorithm = "DFS"
        self.mode = "search"
        self._update_selectors()
        self._update_modes()
        self._load_builtin()

    def _choose_algo(self, algorithm: str) -> None:
        if self.running_solver or algorithm == self.algorithm:
            return
        self.algorithm = algorithm
        self._update_algorithms()
        self._load_builtin()

    def _choose_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        if mode == "solution" and not self.trace.get("solution"):
            messagebox.showinfo("Chưa có lời giải", "Trace này không chứa đường đi lời giải.")
            return
        self._stop()
        self.mode = mode
        self._update_modes()
        self._set_frames()

    def _load_builtin(self) -> None:
        path = ROOT / "traces" / TRACES[self.puzzle][self.algorithm]
        self._read_trace(path)

    def _open_json(self) -> None:
        if self.running_solver:
            return
        path = filedialog.askopenfilename(
            title="Chọn trace JSON", initialdir=str(ROOT / "traces"),
            filetypes=[("JSON trace", "*.json"), ("Tất cả file", "*.*")])
        if path:
            self._read_trace(Path(path))

    def _read_trace(self, path: Path) -> None:
        try:
            data = load_trace(str(path))
            validate_trace(data)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            messagebox.showerror("Không mở được trace", "{}\n\n{}".format(path, exc))
            return
        self._apply_trace_data(data, path.name)
        extra = "  ·  TRACE ĐÃ BỊ CẮT" if data.get("truncated") else ""
        self.status_line.configure(text="Đang đọc: {}{}".format(path.name, extra))

    def _apply_trace_data(self, data: Dict[str, Any], source_name: str) -> None:
        self._stop()
        self.trace = data
        self.current_path = source_name
        if self.puzzle != data["puzzle"]:
            self.selected_input = None
        self.puzzle = data["puzzle"]
        algorithm = data.get("algorithm", "").lower()
        algo_ids = {"DFS": "dfs", "A*": "astar", "Hill Climbing": "hill_climbing"}
        self.algorithm = next((name for name in TRACES[self.puzzle]
                               if algorithm == algo_ids.get(name)),
                              algorithm or "Khác")
        self._update_selectors()
        self._update_algorithms()
        self._refresh_input_caption()
        if self.mode == "solution" and not data["solution"]:
            self.mode = "search"
        self._update_modes()
        self._set_frames()
        prune = (data.get("result") or {}).get("kakurasu_prune")
        self.file_text.configure(text="{}\n{} · {}{}".format(
            source_name, self.puzzle.upper(), data.get("algorithm", "?"),
            " · prune=" + prune if prune else ""))
        self._show_metrics()

    def _set_frames(self) -> None:
        self.frames = get_frames(self.trace, self.mode)
        self.position = 0
        self.slider_update = True
        self.seek.configure(from_=0, to=max(0, len(self.frames) - 1))
        self.seek.set(0)
        self.slider_update = False
        self._render()

    def _show_metrics(self) -> None:
        info = self.trace.get("result") or {}
        self.metrics["status"].set(str(info.get("status", "—")).upper())
        self.metrics["expanded"].set(fmt_number(info.get("nodes_expanded")))
        self.metrics["generated"].set(fmt_number(info.get("nodes_generated")))
        self.metrics["length"].set(fmt_number(info.get("solution_length")))
        elapsed = info.get("elapsed")
        self.metrics["elapsed"].set("{:.3f} ms".format(elapsed * 1000)
                                    if isinstance(elapsed, (int, float)) else "—")
        peak_kb = info.get("peak_kb")
        self.metrics["memory"].set("{:.1f} KB".format(peak_kb)
                                   if isinstance(peak_kb, (int, float))
                                   else "Không có dữ liệu")

    def _seek_to(self, value: str) -> None:
        if not self.slider_update and self.frames:
            self.position = min(max(int(float(value)), 0), len(self.frames) - 1)
            self._render()

    def _move_to(self, value: int) -> None:
        if not self.frames:
            return
        self.position = min(max(0, value), len(self.frames) - 1)
        self.slider_update = True
        self.seek.set(self.position)
        self.slider_update = False
        self._render()

    def _prev(self) -> None:
        self._stop()
        self._move_to(self.position - 1)

    def _next(self) -> None:
        self._stop()
        self._move_to(self.position + 1)

    def _reset(self) -> None:
        self._stop()
        self._move_to(0)

    def _toggle_play(self) -> None:
        if self.is_playing:
            self._stop()
            return
        if not self.frames:
            return
        if self.position >= len(self.frames) - 1:
            self._move_to(0)
        self.is_playing = True
        self.play_button.configure(text="Ⅱ  TẠM DỪNG")
        self._tick()

    def _tick(self) -> None:
        self.after_id = None
        if not self.is_playing:
            return
        if self.position >= len(self.frames) - 1:
            self._stop()
            return
        self._move_to(self.position + 1)
        self.after_id = self.after(int(1000 / self.speed_var.get()), self._tick)

    def _stop(self) -> None:
        self.is_playing = False
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        if hasattr(self, "play_button"):
            self.play_button.configure(text="▶  PHÁT")

    def _render(self) -> None:
        if not self.frames:
            return
        frame = self.frames[self.position]
        event = str(frame.get("event", "?")).lower()
        title, explain = EVENTS.get(event, (event.upper(), "Sự kiện chưa được định nghĩa."))
        self.event_label.configure(text=title,
                                   fg=COL["green"] if event == "goal" else
                                      COL["yellow"] if event in ("restart", "stuck") else COL["accent"])
        self.event_detail.configure(text=explain)
        details = []
        for key, label in (("i", "Event i"), ("depth", "Độ sâu"),
                           ("g", "g(n)"), ("h", "h(n)"), ("f", "f(n)"),
                           ("frontier", "Frontier"), ("explored", "Đã xét"),
                           ("cost", "Cost"), ("action", "Action"),
                           ("restart", "Restart")):
            if key in frame and not (key == "i" and event == "initial"):
                details.append("{}: {}".format(label, fmt_number(frame[key])))
        if self.mode == "solution":
            details.append("Vị trí đường đi: {} / {}".format(
                self.position, max(0, len(self.frames)-1)))
        self.meta_label.configure(text="\n".join(details))
        self.counter.configure(text="FRAME {} / {}".format(self.position+1, len(self.frames)))
        self.board_title.configure(text="{} · 4×4".format(self.puzzle.upper()))
        self.board_hint.configure(text="DFS / Heuristic demo" if self.puzzle == "pipes"
                                  else "Trọng số hàng/cột: 1–4")
        self.legend_text.configure(text=(
            "● xanh: ống đã gán     ? : chưa gán     viền sáng: ô thay đổi"
            if self.puzzle == "pipes" else
            "■ xanh: ô đen     □ trắng: ô trắng     ? : chưa quyết định     viền sáng: thay đổi"))
        self._draw_board()

    def _draw_board(self) -> None:
        if not self.frames or not hasattr(self, "canvas"):
            return
        cv = self.canvas
        cv.delete("all")
        w, h = max(1, cv.winfo_width()), max(1, cv.winfo_height())
        frame = self.frames[self.position]
        old = self.frames[self.position - 1]["state"] if self.position > 0 else None
        modified = set(changed_cells(old, frame["state"], self.puzzle))
        goal = frame["event"] == "goal" or (self.mode == "solution" and
                                               self.position == len(self.frames)-1)
        if self.puzzle == "pipes":
            self._draw_pipes(cv, w, h, frame["state"], modified, goal)
        else:
            self._draw_kakurasu(cv, w, h, frame["state"], modified, goal)

    def _draw_pipes(self, cv: tk.Canvas, w: int, h: int, state: List[Any],
                    modified: set, goal: bool) -> None:
        gap = 10
        cell = max(30, min(100, int((w - 85 - 3 * gap) / 4),
                            int((h - 65 - 3 * gap) / 4)))
        square = 4*cell + 3*gap
        x0, y0 = (w-square)/2, (h-square)/2
        for r in range(4):
            for c in range(4):
                x, y = x0 + c*(cell+gap), y0 + r*(cell+gap)
                connections = state[r][c]
                outline = (COL["green"] if goal else COL["accent"])
                is_modified = (r, c) in modified
                cv.create_rectangle(x, y, x+cell, y+cell,
                                    fill=COL["tile_alt"] if is_modified else COL["tile"],
                                    outline=outline if is_modified else COL["border"],
                                    width=2 if is_modified else 1)
                if connections is None:
                    cv.create_text(x+cell/2, y+cell/2, text="?", fill=COL["muted"],
                                   font=("Segoe UI", int(cell*.33), "bold"))
                    continue
                cx, cy = x+cell/2, y+cell/2
                size = cell*0.47
                for direction in connections:
                    dx, dy = DIRECTIONS[direction]
                    cv.create_line(cx, cy, cx+dx*size, cy+dy*size,
                                   fill="#0A2037", width=max(6,int(cell*.27)),
                                   capstyle=tk.ROUND)
                    cv.create_line(cx, cy, cx+dx*size, cy+dy*size,
                                   fill=COL["green"] if goal else COL["accent"],
                                   width=max(4,int(cell*.17)), capstyle=tk.ROUND)
                dot = max(5, int(cell*.12))
                cv.create_oval(cx-dot, cy-dot, cx+dot, cy+dot,
                               fill=COL["green"] if goal else COL["accent"], outline="")
        cv.create_text(w/2, max(12, y0-19), text="MẠNG LƯỚI ĐƯỜNG ỐNG",
                       fill=COL["muted"], font=("Segoe UI", 10, "bold"))

    def _draw_kakurasu(self, cv: tk.Canvas, w: int, h: int, state: Dict[str, Any],
                       modified: set, goal: bool) -> None:
        gap = 8
        cell = max(28, min(90, int((w - 180 - 3*gap)/4),
                            int((h - 160 - 3*gap)/4)))
        square = 4*cell + 3*gap
        x0, y0 = (w-square)/2-8, (h-square)/2-5
        grid = state["grid"]
        for c in range(4):
            cv.create_text(x0+c*(cell+gap)+cell/2, y0-28, text=str(c+1),
                           font=("Segoe UI", 11, "bold"), fill=COL["muted"])
        for r in range(4):
            cv.create_text(x0-27, y0+r*(cell+gap)+cell/2, text=str(r+1),
                           font=("Segoe UI", 11, "bold"), fill=COL["muted"])
            running_row = sum(c+1 for c in range(4) if grid[r][c] == 1)
            for c in range(4):
                x, y = x0 + c*(cell+gap), y0 + r*(cell+gap)
                value = grid[r][c]
                color = (COL["tile"] if value is None else
                         COL["black_cell"] if value == 1 else COL["white_cell"])
                changed = (r, c) in modified
                cv.create_rectangle(x, y, x+cell, y+cell, fill=color,
                                    outline=COL["green"] if goal and changed else
                                            COL["accent"] if changed else COL["border"],
                                    width=3 if changed else 1)
                if value is None:
                    cv.create_text(x+cell/2, y+cell/2, text="?", fill=COL["muted"],
                                   font=("Segoe UI", int(cell*.33), "bold"))
                elif value == 1:
                    cv.create_text(x+cell/2, y+cell/2, text="●", fill="#CBEAFF",
                                   font=("Segoe UI", int(cell*.26), "bold"))
            cy = y0+r*(cell+gap)+cell/2
            cv.create_text(x0+square+34, cy-9, text=str(state["rows"][r]),
                           fill=COL["text"], font=("Segoe UI", 12, "bold"))
            cv.create_text(x0+square+34, cy+10, text="({})".format(running_row),
                           fill=COL["green"] if goal else COL["muted"],
                           font=("Segoe UI", 9))
        for c in range(4):
            current_col = sum(r+1 for r in range(4) if grid[r][c] == 1)
            cx = x0+c*(cell+gap)+cell/2
            cv.create_text(cx, y0+square+24, text=str(state["cols"][c]),
                           fill=COL["text"], font=("Segoe UI", 12, "bold"))
            cv.create_text(cx, y0+square+43, text="({})".format(current_col),
                           fill=COL["green"] if goal else COL["muted"],
                           font=("Segoe UI", 9))
        cv.create_text(w/2, max(12, y0-53), text="KAKURASU · SỐ NGOÀI = TỔNG MỤC TIÊU",
                       fill=COL["muted"], font=("Segoe UI", 9, "bold"))

    def _on_close(self) -> None:
        self._stop()
        if self.solver_process is not None and self.solver_process.poll() is None:
            self.solver_process.terminate()
        if self.running_solver:
            self._finish_run()
        self.destroy()


def main() -> None:
    app = Viewer()
    if len(sys.argv) > 1:
        app._read_trace(Path(sys.argv[1]).resolve())
    app.mainloop()


if __name__ == "__main__":
    main()
