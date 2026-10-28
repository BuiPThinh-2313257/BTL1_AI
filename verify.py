"""TV5: kiểm tra định dạng input và xác thực lời giải độc lập với solver.

Đặt file ở THƯ MỤC GỐC của BTL1_AI và chạy: python verify.py
"""

import json
from pathlib import Path

DIRECTIONS = ("up", "right", "down", "left")
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_input(data):
    """Kiểm tra cấu trúc JSON; KHÔNG khẳng định puzzle có lời giải."""
    _require(isinstance(data, dict), "JSON phải là object")
    if data.get("puzzle") == "kakurasu":
        n, m = data.get("rows"), data.get("cols")
        _require(type(n) is int and n > 0 and type(m) is int and m > 0,
                 "Kakurasu: rows/cols phải là số nguyên dương")
        for key, count, maximum in (("row_clues", n, m * (m + 1) // 2),
                                    ("col_clues", m, n * (n + 1) // 2)):
            clues = data.get(key)
            _require(isinstance(clues, list) and len(clues) == count,
                     "Kakurasu: %s sai độ dài" % key)
            _require(all(type(v) is int and 0 <= v <= maximum for v in clues),
                     "Kakurasu: %s có giá trị không hợp lệ" % key)
        return "kakurasu"

    if "grid_size" in data and "grid" in data:
        size = data["grid_size"]
        _require(isinstance(size, dict), "Pipes: grid_size phải là object")
        n, m = size.get("rows"), size.get("cols")
        _require(type(n) is int and n > 0 and type(m) is int and m > 0,
                 "Pipes: rows/cols không hợp lệ")
        grid = data["grid"]
        _require(isinstance(grid, list) and len(grid) == n,
                 "Pipes: sai số hàng")
        for r, row in enumerate(grid):
            _require(isinstance(row, list) and len(row) == m,
                     "Pipes: hàng %s có số ô không đúng" % r)
            for c, cell in enumerate(row):
                _require(isinstance(cell, dict), "Pipes: ô không phải object")
                conns = cell.get("connections")
                _require(isinstance(conns, list) and conns and
                         len(set(conns)) == len(conns) and
                         all(d in DIRECTIONS for d in conns),
                         "Pipes: connections không hợp lệ tại (%s,%s)" % (r, c))
                _require(type(cell.get("rotatable")) is bool,
                         "Pipes: thiếu rotatable tại (%s,%s)" % (r, c))
                _require(cell.get("row") == r and cell.get("col") == c,
                         "Pipes: tọa độ ô không đúng tại (%s,%s)" % (r, c))
        return "pipes"

    raise ValueError("Không nhận dạng được puzzle: cần puzzle=kakurasu hoặc grid_size/grid")


def verify_kakurasu(data, state):
    """State: tuple/list n*m số 0/1 theo thứ tự từ trái qua phải, trên xuống dưới."""
    try:
        n, m = data["rows"], data["cols"]
        if state is None or len(state) != n * m:
            return False
        if any(type(v) is not int or v not in (0, 1) for v in state):
            return False
        for r in range(n):
            if sum((c + 1) * state[r * m + c] for c in range(m)) != data["row_clues"][r]:
                return False
        for c in range(m):
            if sum((r + 1) * state[r * m + c] for r in range(n)) != data["col_clues"][c]:
                return False
        return True
    except (KeyError, TypeError, IndexError, ValueError):
        return False


def _rotated(connections, turns):
    return frozenset(DIRECTIONS[(DIRECTIONS.index(d) + turns) % 4]
                     for d in connections)


def verify_pipes(data, state):
    """Kiểm tra hướng xoay, biên, nối khớp, liên thông VÀ không có chu trình."""
    try:
        n = data["grid_size"]["rows"]
        m = data["grid_size"]["cols"]
        cells = [cell for row in data["grid"] for cell in row]
        if state is None or len(state) != n * m or len(cells) != n * m:
            return False

        conns = []
        for cell, directions in zip(cells, state):
            if not isinstance(directions, (tuple, list)):
                return False
            if len(set(directions)) != len(directions) or any(d not in DIRECTIONS for d in directions):
                return False
            chosen = frozenset(directions)
            turns = range(4) if cell["rotatable"] else (0,)
            if chosen not in {_rotated(cell["connections"], t) for t in turns}:
                return False
            conns.append(chosen)

        adjacency = [set() for _ in range(n * m)]
        delta = {"up": (-1, 0), "right": (0, 1),
                 "down": (1, 0), "left": (0, -1)}
        for idx, directions in enumerate(conns):
            r, c = divmod(idx, m)
            for d in directions:
                dr, dc = delta[d]
                rr, cc = r + dr, c + dc
                if not (0 <= rr < n and 0 <= cc < m):
                    return False  # Ống chĩa ra ngoài biên
                nxt = rr * m + cc
                if OPPOSITE[d] not in conns[nxt]:
                    return False  # Mối nối không khớp
                adjacency[idx].add(nxt)
                adjacency[nxt].add(idx)

        # Một đồ thị vô hướng liên thông, không chu trình phải có V - 1 cạnh.
        seen, pending = set(), [0]
        while pending:
            idx = pending.pop()
            if idx in seen:
                continue
            seen.add(idx)
            pending.extend(adjacency[idx] - seen)
        edge_count = sum(len(x) for x in adjacency) // 2
        return len(seen) == n * m and edge_count == n * m - 1
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def verify_solution(data, state):
    """Xác thực lời giải từ SearchResult.final_state."""
    kind = validate_input(data)
    if kind == "kakurasu":
        return verify_kakurasu(data, state)
    return verify_pipes(data, state)


def main():
    paths = sorted(Path("data").glob("*.json"))
    if not paths:
        print("Không tìm thấy JSON. Hãy chạy ở thư mục gốc BTL1_AI.")
        return 1
    failed = 0
    for path in paths:
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
            kind = validate_input(data)
            print("[OK]  %s (%s, cấu trúc JSON)" % (path, kind))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            failed += 1
            print("[ERR] %s: %s" % (path, exc))
    print("\nTổng: %d file, %d file lỗi cấu trúc." % (len(paths), failed))
    print("Chú ý: [OK] KHÔNG có nghĩa là bài toán giải được hoặc đáp án đúng.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())