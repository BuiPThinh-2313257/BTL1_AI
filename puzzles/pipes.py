import json
import random
from core.problem import Problem

# Danh sách các hướng xoay theo chiều kim đồng hồ
DIRS = ["up", "right", "down", "left"]
DIR_MAP = {"up": 0, "right": 1, "down": 2, "left": 3}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

def rotate_connections(connections, rotations):
    """Xoay mảng các hướng kết nối 90 độ x số lần xoay."""
    return tuple(DIRS[(DIR_MAP[c] + rotations) % 4] for c in connections)

class Pipes(Problem):
    name = "pipes"

    def __init__(self, grid_data):
        self.rows = grid_data['grid_size']['rows']
        self.cols = grid_data['grid_size']['cols']
        self.grid = []
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid.append(grid_data['grid'][r][c])

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(data)

    def initial_state(self):
        """Trạng thái ban đầu cho DFS/A*: tuple rỗng (chưa gán ô nào)."""
        return ()

    def successors(self, state):
        """Sinh trạng thái kề: gán xoay cho ô trống tiếp theo."""
        idx = len(state)
        if idx >= len(self.grid):
            return

        cell = self.grid[idx]
        r, c = divmod(idx, self.cols)
        
        # Các hướng có thể xoay (nếu không xoay được thì chỉ có 0)
        possible_rotations = range(4) if cell['rotatable'] else [0]
        
        # Lọc bớt các góc xoay trùng lặp cho ống thẳng (I) và chữ thập (Cross)
        if cell['type'] == 'I-shape' and cell['rotatable']:
            possible_rotations = [0, 1]

        for rot in possible_rotations:
            new_conns = tuple(rotate_connections(cell['connections'], rot))
            
            # Cắt tỉa 1: Tránh chĩa ra ngoài biên
            if r == 0 and "up" in new_conns: continue
            if r == self.rows - 1 and "down" in new_conns: continue
            if c == 0 and "left" in new_conns: continue
            if c == self.cols - 1 and "right" in new_conns: continue

            # Cắt tỉa 2: Phải khớp với ô bên trái (nếu có)
            if c > 0:
                left_cell_conns = state[idx - 1]
                if ("right" in left_cell_conns) != ("left" in new_conns):
                    continue
                    
            # Cắt tỉa 3: Phải khớp với ô bên trên (nếu có)
            if r > 0:
                top_cell_conns = state[idx - self.cols]
                if ("down" in top_cell_conns) != ("up" in new_conns):
                    continue

            yield (rot, state + (new_conns,), 1.0)

    def is_goal(self, state):
        """Chỉ thành công khi đã gán đủ tất cả các ô và thoả mãn cắt tỉa."""
        return len(state) == len(self.grid)

    def to_view(self, state):
        """Trả về dạng lưới để ghi log/trace cho giao diện."""
        view = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                idx = r * self.cols + c
                if idx < len(state):
                    row.append(list(state[idx]))
                else:
                    row.append(None) # Chưa gán
            view.append(row)
        return view

    # --- TÌM KIẾM CỤC BỘ (HILL CLIMBING / SIMULATED ANNEALING) ---

    def local_initial_state(self, rng: random.Random):
        """Khởi tạo toàn bộ lưới ngẫu nhiên nhưng giữ nguyên ô không được xoay."""
        state = []
        for cell in self.grid:
            if not cell['rotatable']:
                state.append(tuple(cell['connections']))
            else:
                rot = rng.choice(range(4))
                state.append(rotate_connections(cell['connections'], rot))
        return tuple(state)

    def local_neighbors(self, state):
        """Sinh lân cận bằng cách xoay 90 độ 1 ô bất kỳ được phép xoay."""
        state_list = list(state)
        for idx, cell in enumerate(self.grid):
            if cell['rotatable']:
                for rot in [1, 2, 3]: # Xoay thêm 1, 2, hoặc 3 lần 90 độ
                    new_conns = rotate_connections(state_list[idx], rot)
                    new_state = state_list.copy()
                    new_state[idx] = new_conns
                    yield (f"rotate_{idx}_by_{rot}", tuple(new_state))

    def local_cost(self, state):
        """Heuristic: số đầu nối lệch + (số mạng rời - 1)."""
        mismatches = 0
        
        # 1. Đếm số mối nối lệch và chĩa ra biên
        for r in range(self.rows):
            for c in range(self.cols):
                idx = r * self.cols + c
                conns = state[idx]
                
                if r == 0 and "up" in conns: mismatches += 1
                if r == self.rows - 1 and "down" in conns: mismatches += 1
                if c == 0 and "left" in conns: mismatches += 1
                if c == self.cols - 1 and "right" in conns: mismatches += 1

                if c < self.cols - 1:
                    if ("right" in conns) != ("left" in state[idx + 1]):
                        mismatches += 1
                if r < self.rows - 1:
                    if ("down" in conns) != ("up" in state[idx + self.cols]):
                        mismatches += 1

        # 2. Đếm số mạng rời (connected components) bằng BFS
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
                        
                        # Lan truyền sang các ô kề nếu ống khớp nhau
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
                                
        return mismatches + max(0, components - 1) 