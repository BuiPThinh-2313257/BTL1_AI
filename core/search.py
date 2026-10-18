"""Các giải thuật tìm kiếm dùng chung cho mọi bài toán.

Tìm kiếm mù:      dfs, bfs
Tìm kiếm có thông tin: astar, greedy
Tìm kiếm cục bộ:  hill_climbing, simulated_annealing

Mọi hàm đều nhận một `Problem` (xem core/problem.py), một `Limits` tuỳ chọn
và một `Trace` tuỳ chọn, rồi trả về `SearchResult`.

Ví dụ:
    from core.search import bfs, astar, Limits
    res = astar(problem, limits=Limits(time_limit=30))
    print(res.status, res.nodes_expanded, len(res.path))
"""

from __future__ import annotations

import heapq
import itertools
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .problem import Problem

# Các giá trị của SearchResult.status
SOLVED = "solved"
NO_SOLUTION = "no_solution"      # đã duyệt hết mà không có lời giải
NODE_LIMIT = "node_limit"        # dừng vì vượt Limits.max_nodes
TIME_LIMIT = "time_limit"        # dừng vì vượt Limits.time_limit
STUCK = "stuck"                  # tìm kiếm cục bộ hết lượt restart mà vẫn chưa giải được


@dataclass
class Limits:
    """Giới hạn để giải thuật không chạy mãi hoặc tràn bộ nhớ."""
    max_nodes: Optional[int] = None      # số node được mở rộng tối đa
    time_limit: Optional[float] = None   # giây
    max_depth: Optional[int] = None      # chỉ áp dụng cho DFS


@dataclass
class SearchResult:
    algorithm: str
    status: str
    path: List[Any] = field(default_factory=list)      # các state từ đầu tới đích
    actions: List[Any] = field(default_factory=list)
    cost: float = 0.0
    nodes_expanded: int = 0      # số node đã mở rộng (gọi successors / xét lân cận)
    nodes_generated: int = 0     # số node con được sinh ra
    max_frontier: int = 0        # kích thước lớn nhất của frontier (stack/queue/heap)
    max_depth: int = 0           # độ sâu lớn nhất đã chạm tới
    restarts: int = 0            # chỉ dùng cho tìm kiếm cục bộ
    elapsed: float = 0.0         # giây (đo bên trong giải thuật, không gồm tracemalloc)
    final_state: Any = None

    @property
    def found(self) -> bool:
        return self.status == SOLVED

    def summary(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "status": self.status,
            "found": self.found,
            "solution_length": max(len(self.path) - 1, 0),
            "cost": self.cost,
            "nodes_expanded": self.nodes_expanded,
            "nodes_generated": self.nodes_generated,
            "max_frontier": self.max_frontier,
            "max_depth": self.max_depth,
            "restarts": self.restarts,
            "elapsed": round(self.elapsed, 6),
        }


class _Guard:
    """Kiểm tra giới hạn số node và thời gian."""

    def __init__(self, limits: Optional[Limits]):
        self.limits = limits or Limits()
        self.start = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self.start

    def check(self, expanded: int) -> Optional[str]:
        lim = self.limits
        if lim.max_nodes is not None and expanded >= lim.max_nodes:
            return NODE_LIMIT
        # perf_counter rẻ, nhưng vẫn chỉ kiểm tra mỗi 256 node
        if lim.time_limit is not None and (expanded & 255) == 0 \
                and self.elapsed() >= lim.time_limit:
            return TIME_LIMIT
        return None


def _rebuild(parent: Dict[Any, Any], goal) -> tuple:
    """Dựng lại đường đi từ bảng parent: state -> (parent_state, action)."""
    states, actions = [goal], []
    s = goal
    while parent[s] is not None:
        p, a = parent[s]
        states.append(p)
        actions.append(a)
        s = p
    states.reverse()
    actions.reverse()
    return states, actions


def _finish(res: SearchResult, guard: _Guard, trace) -> SearchResult:
    res.elapsed = guard.elapsed()
    if trace is not None:
        trace.finish(res)
    return res


# ======================================================================
# Tìm kiếm mù
# ======================================================================

def dfs(problem: Problem, limits: Optional[Limits] = None, trace=None) -> SearchResult:
    """Depth-First Search dạng graph search (không mở lại state đã thăm)."""
    guard = _Guard(limits)
    max_depth = guard.limits.max_depth
    res = SearchResult("dfs", NO_SOLUTION)
    start = problem.initial_state()
    if trace is not None:
        trace.start(start)

    # mỗi phần tử: (state, parent_state, action, depth, cost)
    stack = [(start, None, None, 0, 0.0)]
    parent: Dict[Any, Any] = {}

    while stack:
        state, par, act, depth, g = stack.pop()
        if state in parent:
            continue
        parent[state] = None if par is None else (par, act)

        stop = guard.check(res.nodes_expanded)
        if stop:
            res.status = stop
            break

        res.max_depth = max(res.max_depth, depth)
        if trace is not None:
            trace.record("expand", state, depth=depth, g=g,
                         frontier=len(stack), explored=len(parent))

        if problem.is_goal(state):
            res.status = SOLVED
            res.path, res.actions = _rebuild(parent, state)
            res.cost, res.final_state = g, state
            if trace is not None:
                trace.record("goal", state, depth=depth, g=g)
            break

        res.nodes_expanded += 1
        if max_depth is not None and depth >= max_depth:
            continue

        children = [c for c in problem.successors(state) if c[1] not in parent]
        res.nodes_generated += len(children)
        # đảo ngược để successor đầu tiên được duyệt trước (giống DFS đệ quy)
        for a, s2, c in reversed(children):
            stack.append((s2, state, a, depth + 1, g + c))
        res.max_frontier = max(res.max_frontier, len(stack))

    return _finish(res, guard, trace)


def bfs(problem: Problem, limits: Optional[Limits] = None, trace=None) -> SearchResult:
    """Breadth-First Search; kiểm tra đích ngay khi sinh node con."""
    guard = _Guard(limits)
    res = SearchResult("bfs", NO_SOLUTION)
    start = problem.initial_state()
    if trace is not None:
        trace.start(start)

    parent: Dict[Any, Any] = {start: None}
    depth_of: Dict[Any, int] = {start: 0}
    cost_of: Dict[Any, float] = {start: 0.0}

    def found(s):
        res.status = SOLVED
        res.path, res.actions = _rebuild(parent, s)
        res.cost, res.final_state = cost_of[s], s
        res.max_depth = max(res.max_depth, depth_of[s])
        if trace is not None:
            trace.record("goal", s, depth=depth_of[s], g=cost_of[s])

    if problem.is_goal(start):
        found(start)
        return _finish(res, guard, trace)

    queue = deque([start])
    while queue:
        stop = guard.check(res.nodes_expanded)
        if stop:
            res.status = stop
            break

        state = queue.popleft()
        d = depth_of.pop(state)
        g = cost_of[state]
        res.max_depth = max(res.max_depth, d)
        if trace is not None:
            trace.record("expand", state, depth=d, g=g,
                         frontier=len(queue), explored=len(parent))
        res.nodes_expanded += 1

        for a, s2, c in problem.successors(state):
            if s2 in parent:
                continue
            parent[s2] = (state, a)
            depth_of[s2] = d + 1
            cost_of[s2] = g + c
            res.nodes_generated += 1
            if problem.is_goal(s2):
                found(s2)
                return _finish(res, guard, trace)
            queue.append(s2)
        res.max_frontier = max(res.max_frontier, len(queue))

    return _finish(res, guard, trace)


# ======================================================================
# Tìm kiếm có thông tin
# ======================================================================

def _best_first(problem: Problem, name: str, priority: Callable[[float, float], float],
                limits: Optional[Limits], trace) -> SearchResult:
    guard = _Guard(limits)
    res = SearchResult(name, NO_SOLUTION)
    start = problem.initial_state()
    if trace is not None:
        trace.start(start)

    counter = itertools.count()   # phá hoà để heap không phải so sánh state
    h0 = problem.heuristic(start)
    heap = [(priority(0.0, h0), h0, next(counter), start)]
    g_of: Dict[Any, float] = {start: 0.0}
    depth_of: Dict[Any, int] = {start: 0}
    parent: Dict[Any, Any] = {start: None}
    closed = set()

    while heap:
        f, h, _, state = heapq.heappop(heap)
        if state in closed:
            continue          # bản cũ trong heap, đã có đường tốt hơn
        closed.add(state)

        stop = guard.check(res.nodes_expanded)
        if stop:
            res.status = stop
            break

        g = g_of[state]
        d = depth_of[state]
        res.max_depth = max(res.max_depth, d)
        if trace is not None:
            trace.record("expand", state, depth=d, g=g, h=h, f=f,
                         frontier=len(heap), explored=len(closed))

        if problem.is_goal(state):
            res.status = SOLVED
            res.path, res.actions = _rebuild(parent, state)
            res.cost, res.final_state = g, state
            if trace is not None:
                trace.record("goal", state, depth=d, g=g)
            break

        res.nodes_expanded += 1
        for a, s2, c in problem.successors(state):
            g2 = g + c
            if s2 in closed and g2 >= g_of.get(s2, math.inf):
                continue
            if g2 < g_of.get(s2, math.inf):
                closed.discard(s2)    # mở lại nếu tìm được đường rẻ hơn
                g_of[s2] = g2
                depth_of[s2] = d + 1
                parent[s2] = (state, a)
                h2 = problem.heuristic(s2)
                heapq.heappush(heap, (priority(g2, h2), h2, next(counter), s2))
                res.nodes_generated += 1
        res.max_frontier = max(res.max_frontier, len(heap))

    return _finish(res, guard, trace)


def astar(problem: Problem, limits: Optional[Limits] = None, trace=None) -> SearchResult:
    """A*: f = g + h. Cho lời giải tối ưu nếu h admissible và consistent."""
    return _best_first(problem, "astar", lambda g, h: g + h, limits, trace)


def greedy(problem: Problem, limits: Optional[Limits] = None, trace=None) -> SearchResult:
    """Greedy Best-First Search: f = h. Nhanh nhưng không đảm bảo tối ưu."""
    return _best_first(problem, "greedy", lambda g, h: h, limits, trace)


# ======================================================================
# Tìm kiếm cục bộ
# ======================================================================

def hill_climbing(problem: Problem, limits: Optional[Limits] = None, trace=None,
                  max_restarts: int = 50, max_sideways: int = 20,
                  seed: Optional[int] = None) -> SearchResult:
    """Steepest-ascent Hill Climbing có random restart và cho phép đi ngang.

    Dùng problem.local_initial_state / local_neighbors / local_cost.
    - max_restarts: số lần bắt đầu lại khi kẹt ở cực trị địa phương.
    - max_sideways: số bước đi ngang (cost không đổi) liên tiếp tối đa,
      giúp thoát khỏi vùng bằng phẳng (plateau).
    """
    guard = _Guard(limits)
    rng = random.Random(seed)
    res = SearchResult("hill_climbing", STUCK)

    for attempt in range(max_restarts + 1):
        state = problem.local_initial_state(rng)
        cost = problem.local_cost(state)
        path, actions = [state], []
        sideways = 0
        if attempt == 0:
            if trace is not None:
                trace.start(state)
        else:
            res.restarts += 1
            if trace is not None:
                trace.record("restart", state, cost=cost, restart=attempt)

        while True:
            if cost == 0:
                res.status = SOLVED
                res.path, res.actions = path, actions
                res.cost, res.final_state = len(actions), state
                if trace is not None:
                    trace.record("goal", state, cost=cost)
                return _finish(res, guard, trace)

            stop = guard.check(res.nodes_expanded)
            if stop:
                res.status = stop
                res.path, res.actions, res.final_state = path, actions, state
                return _finish(res, guard, trace)

            res.nodes_expanded += 1
            best = []
            best_cost = math.inf
            for a, s2 in problem.local_neighbors(state):
                res.nodes_generated += 1
                c2 = problem.local_cost(s2)
                if c2 < best_cost:
                    best_cost, best = c2, [(a, s2)]
                elif c2 == best_cost:
                    best.append((a, s2))

            if not best or best_cost > cost:
                break                                   # cực đại địa phương
            if best_cost == cost:
                sideways += 1
                if sideways > max_sideways:
                    break                               # kẹt trên plateau
            else:
                sideways = 0

            a, state = rng.choice(best)
            cost = best_cost
            path.append(state)
            actions.append(a)
            res.max_depth = max(res.max_depth, len(actions))
            if trace is not None:
                trace.record("move", state, cost=cost, action=_safe(a))

        if trace is not None:
            trace.record("stuck", state, cost=cost)
        res.path, res.actions, res.final_state = path, actions, state

    return _finish(res, guard, trace)


def simulated_annealing(problem: Problem, limits: Optional[Limits] = None, trace=None,
                        t0: float = 2.0, cooling: float = 0.995, t_min: float = 1e-3,
                        max_restarts: int = 10, seed: Optional[int] = None) -> SearchResult:
    """Simulated Annealing: nhận bước xấu hơn với xác suất exp(-delta / T)."""
    guard = _Guard(limits)
    rng = random.Random(seed)
    res = SearchResult("simulated_annealing", STUCK)

    for attempt in range(max_restarts + 1):
        state = problem.local_initial_state(rng)
        cost = problem.local_cost(state)
        best_state, best_cost = state, cost
        path, actions = [state], []
        t = t0
        if attempt == 0:
            if trace is not None:
                trace.start(state)
        else:
            res.restarts += 1
            if trace is not None:
                trace.record("restart", state, cost=cost, restart=attempt)

        while t > t_min:
            if cost == 0:
                res.status = SOLVED
                res.path, res.actions = path, actions
                res.cost, res.final_state = len(actions), state
                if trace is not None:
                    trace.record("goal", state, cost=cost)
                return _finish(res, guard, trace)

            stop = guard.check(res.nodes_expanded)
            if stop:
                res.status = stop
                res.path, res.actions, res.final_state = path, actions, best_state
                return _finish(res, guard, trace)

            res.nodes_expanded += 1
            a, s2 = problem.local_random_neighbor(state, rng)
            res.nodes_generated += 1
            c2 = problem.local_cost(s2)
            delta = c2 - cost
            if delta <= 0 or rng.random() < math.exp(-delta / t):
                state, cost = s2, c2
                path.append(state)
                actions.append(a)
                res.max_depth = max(res.max_depth, len(actions))
                if cost < best_cost:
                    best_state, best_cost = state, cost
                if trace is not None:
                    trace.record("move", state, cost=cost, temp=round(t, 5), action=_safe(a))
            t *= cooling

        if trace is not None:
            trace.record("stuck", best_state, cost=best_cost)
        res.final_state = best_state

    return _finish(res, guard, trace)


def _safe(a):
    """Action có thể là tuple/obj; đổi sang dạng JSON được cho trace."""
    if isinstance(a, (str, int, float, bool)) or a is None:
        return a
    if isinstance(a, (tuple, list)):
        return [_safe(x) for x in a]
    return repr(a)


ALGORITHMS = {
    "dfs": dfs,
    "bfs": bfs,
    "astar": astar,
    "greedy": greedy,
    "hill_climbing": hill_climbing,
    "simulated_annealing": simulated_annealing,
}
