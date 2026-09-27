# road.py
import math
from collections import deque
from config import MAX_ROAD_ATTACH_DIST


class Road:
    def __init__(self, vertices):
        self.vertices = vertices  # список кортежей (x, y)

    def intersects_rect(self, rect):
        for i in range(len(self.vertices) - 1):
            p1 = self.vertices[i]
            p2 = self.vertices[i + 1]
            if rect.clipline(p1, p2):
                return True
        return False


def build_road_graph(roads):
    """Строит граф дорог: узел (x,y) -> список соседних узлов."""
    graph = {}
    nodes = set()
    for road in roads:
        for i in range(len(road.vertices) - 1):
            a = tuple(road.vertices[i])
            b = tuple(road.vertices[i + 1])
            nodes.add(a)
            nodes.add(b)
            if a not in graph:
                graph[a] = []
            if b not in graph:
                graph[b] = []
            if b not in graph[a]:
                graph[a].append(b)
            if a not in graph[b]:
                graph[b].append(a)
    return graph, list(nodes)


def _project_point_to_segment(px, py, ax, ay, bx, by):
    """Возвращает (proj_x, proj_y), distance — проекцию точки (px,py) на отрезок [a,b]."""
    dx = bx - ax
    dy = by - ay
    sq = dx * dx + dy * dy
    if sq == 0:
        return (ax, ay), math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / sq
    t = max(0.0, min(1.0, t))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return (proj_x, proj_y), dist


def _closest_point_on_roads(pos, roads):
    """Ближайшая точка на любой дороге. Возвращает (point, road_idx, seg_idx, dist) или None."""
    best = None
    best_dist = float('inf')
    for ri, road in enumerate(roads):
        for si in range(len(road.vertices) - 1):
            ax, ay = road.vertices[si]
            bx, by = road.vertices[si + 1]
            proj, d = _project_point_to_segment(pos[0], pos[1], ax, ay, bx, by)
            if d < best_dist:
                best_dist = d
                best = (proj, ri, si, d)
    return best


def _build_graph_with_inserts(roads, inserts):
    """Строит граф дорог, вставляя точки inserts как временные узлы."""
    graph, _ = build_road_graph(roads)

    per_segment = {}
    for point, ri, si in inserts:
        per_segment.setdefault((ri, si), []).append(tuple(point))

    for (ri, si), points in per_segment.items():
        a = tuple(roads[ri].vertices[si])
        b = tuple(roads[ri].vertices[si + 1])

        if b in graph.get(a, []):
            graph[a].remove(b)
        if a in graph.get(b, []):
            graph[b].remove(a)

        ab_x = b[0] - a[0]
        ab_y = b[1] - a[1]
        sq = ab_x * ab_x + ab_y * ab_y

        def t_of(p):
            if sq == 0:
                return 0.0
            return ((p[0] - a[0]) * ab_x + (p[1] - a[1]) * ab_y) / sq

        uniq = []
        seen = set()
        for p in sorted(points, key=t_of):
            if p == a or p == b:
                continue
            if p in seen:
                continue
            seen.add(p)
            uniq.append(p)

        chain = [a] + uniq + [b]

        for i in range(len(chain) - 1):
            u = chain[i]
            v = chain[i + 1]
            if u not in graph:
                graph[u] = []
            if v not in graph:
                graph[v] = []
            if v not in graph[u]:
                graph[u].append(v)
            if u not in graph[v]:
                graph[v].append(u)

    return graph


def find_road_path(start_pos, end_pos, roads):
    """Ищет кратчайший путь по дорогам от start_pos до end_pos."""
    if not roads:
        return None

    start_proj = _closest_point_on_roads(start_pos, roads)
    end_proj = _closest_point_on_roads(end_pos, roads)
    if start_proj is None or end_proj is None:
        return None

    if start_proj[3] > MAX_ROAD_ATTACH_DIST or end_proj[3] > MAX_ROAD_ATTACH_DIST:
        return None

    start_pt, start_ri, start_si, _ = start_proj
    end_pt, end_ri, end_si, _ = end_proj

    graph = _build_graph_with_inserts(
        roads,
        [(start_pt, start_ri, start_si), (end_pt, end_ri, end_si)]
    )

    start_node = tuple(start_pt)
    end_node = tuple(end_pt)

    if start_node == end_node:
        path = [start_node]
        if math.hypot(start_pos[0] - path[0][0], start_pos[1] - path[0][1]) > 2:
            path.insert(0, start_pos)
        if math.hypot(end_pos[0] - path[-1][0], end_pos[1] - path[-1][1]) > 2:
            path.append(end_pos)
        return path

    queue = deque()
    queue.append(start_node)
    visited = {start_node: None}

    while queue:
        current = queue.popleft()
        if current == end_node:
            break
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = current
                queue.append(neighbor)

    if end_node not in visited:
        return None

    path = []
    node = end_node
    while node is not None:
        path.append(node)
        node = visited[node]
    path.reverse()

    if math.hypot(start_pos[0] - path[0][0], start_pos[1] - path[0][1]) > 2:
        path.insert(0, start_pos)
    if math.hypot(end_pos[0] - path[-1][0], end_pos[1] - path[-1][1]) > 2:
        path.append(end_pos)

    return path