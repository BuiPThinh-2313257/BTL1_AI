import json
import random
from core.problem import Problem

DIRS = ["up", "right", "down", "left"]
DIR_MAP = {"up": 0, "right": 1, "down": 2, "left": 3}

def rotate_connections(connections, rotations):
    return tuple(DIRS[(DIR_MAP[c] + rotations) % 4] for c in connections)

class Pipes(Problem):
    name = "pipes"

    def __init__(self, grid_data):
        self.rows = grid_data['grid_size']['rows']
        self.cols = grid_data['grid_size']['cols']
        # Trải lưới 2 chiều thành danh sách 1 chiều theo thứ tự hàng (ô idx = r*cols + c)
        self.grid = [grid_data['grid'][r][c]
                     for r in range(self.rows) for c in range(self.cols)]

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def initial_state(self):
        return ()

    def successors(self, state):
        idx = len(state)
        if idx >= len(self.grid): return

        cell = self.grid[idx]
        r, c = divmod(idx, self.cols)
        
        possible_rotations = range(4) if cell['rotatable'] else [0]
        if cell['type'] == 'I-shape' and cell['rotatable']:
            possible_rotations = [0, 1]

        for rot in possible_rotations:
            new_conns = tuple(rotate_connections(cell['connections'], rot))
            
            if r == 0 and "up" in new_conns: continue
            if r == self.rows - 1 and "down" in new_conns: continue
            if c == 0 and "left" in new_conns: continue
            if c == self.cols - 1 and "right" in new_conns: continue

            if c > 0:
                if ("right" in state[idx - 1]) != ("left" in new_conns): continue
            if r > 0:
                if ("down" in state[idx - self.cols]) != ("up" in new_conns): continue

            yield (rot, state + (new_conns,), 1.0)

    def is_goal(self, state):
        if len(state) != len(self.grid):
            return False
            
        # 1. Kiểm tra tổng số mối nối (Tổng đầu nối chia 2 phải bằng số ô - 1)
        total_ends = sum(len(conns) for conns in state)
        if total_ends // 2 != len(self.grid) - 1:
            return False
            
        # 2. Kiểm tra tính liên thông bằng BFS
        visited = set([0])
        queue = [0]
        
        while queue:
            curr = queue.pop(0)
            cr, cc = divmod(curr, self.cols)
            curr_conns = state[curr]
            
            if "right" in curr_conns and cc < self.cols - 1:
                nxt = curr + 1
                if "left" in state[nxt] and nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
            if "down" in curr_conns and cr < self.rows - 1:
                nxt = curr + self.cols
                if "up" in state[nxt] and nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
            if "left" in curr_conns and cc > 0:
                nxt = curr - 1
                if "right" in state[nxt] and nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
            if "up" in curr_conns and cr > 0:
                nxt = curr - self.cols
                if "down" in state[nxt] and nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
                    
        return len(visited) == len(self.grid)

    def to_view(self, state):
        view = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                idx = r * self.cols + c
                row.append(list(state[idx]) if idx < len(state) else None)
            view.append(row)
        return view

    def local_initial_state(self, rng: random.Random):
        state = []
        for cell in self.grid:
            rot = rng.choice(range(4)) if cell['rotatable'] else 0
            state.append(rotate_connections(cell['connections'], rot))
        return tuple(state)

    def local_neighbors(self, state):
        state_list = list(state)
        for idx, cell in enumerate(self.grid):
            if cell['rotatable']:
                for rot in [1, 2, 3]:
                    new_conns = rotate_connections(state_list[idx], rot)
                    new_state = state_list.copy()
                    new_state[idx] = new_conns
                    yield (f"rotate_{idx}_{rot}", tuple(new_state))

    def local_cost(self, state):
        mismatches = 0
        valid_edges = 0
        
        # Đếm lệch biên, lệch khớp nối và số mối nối hợp lệ
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                conns = state[idx]
                
                if r == 0 and "up" in conns: mismatches += 1
                if r == self.rows - 1 and "down" in conns: mismatches += 1
                if c == 0 and "left" in conns: mismatches += 1
                if c == self.cols - 1 and "right" in conns: mismatches += 1

                if c < self.cols - 1:
                    right_conns = state[idx + 1]
                    if ("right" in conns) != ("left" in right_conns):
                        mismatches += 1
                    elif "right" in conns and "left" in right_conns:
                        valid_edges += 1
                        
                if r < self.rows - 1:
                    bottom_conns = state[idx + self.cols]
                    if ("down" in conns) != ("up" in bottom_conns):
                        mismatches += 1
                    elif "down" in conns and "up" in bottom_conns:
                        valid_edges += 1

        # Đếm số mạng rời (components) bằng BFS
        visited = set()
        components = 0
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                if idx not in visited:
                    components += 1
                    queue = [idx]
                    visited.add(idx)
                    while queue:
                        curr = queue.pop(0)
                        cr, cc = divmod(curr, self.cols)
                        curr_conns = state[curr]
                        if "right" in curr_conns and cc < self.cols - 1 and "left" in state[curr + 1] and (curr + 1) not in visited:
                            visited.add(curr + 1); queue.append(curr + 1)
                        if "down" in curr_conns and cr < self.rows - 1 and "up" in state[curr + self.cols] and (curr + self.cols) not in visited:
                            visited.add(curr + self.cols); queue.append(curr + self.cols)
                        if "left" in curr_conns and cc > 0 and "right" in state[curr - 1] and (curr - 1) not in visited:
                            visited.add(curr - 1); queue.append(curr - 1)
                        if "up" in curr_conns and cr > 0 and "down" in state[curr - self.cols] and (curr - self.cols) not in visited:
                            visited.add(curr - self.cols); queue.append(curr - self.cols)
                                
        # Số vòng thừa = Số mối nối hợp lệ - Số ô + 1
        extra_cycles = max(0, valid_edges - len(self.grid) + 1)
                                
        return mismatches + max(0, components - 1) + extra_cycles