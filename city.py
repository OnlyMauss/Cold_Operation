# city.py
import random
import math
import pygame
from collections import deque
from config import *
from id_gen import next_id

def _point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    nx = x1 + t * dx
    ny = y1 + t * dy
    return math.hypot(px - nx, py - ny)


def _object_center(obj):
    if hasattr(obj, 'width') and hasattr(obj, 'height'):
        return obj.x + obj.width / 2, obj.y + obj.height / 2
    return obj.x + UNIT_WIDTH / 2, obj.y + UNIT_HEIGHT / 2


class City:
    def __init__(self, vertices, center):
        self.vertices = vertices
        self.center = center
        self.id = next_id() 
        self.owner = None
        self.contested = False
        self.capture_progress = 0.0
        self.capturing_faction = None
        self.bbox = self._calc_bbox()
        self.sample_points = self._generate_sample_points(CITY_CAPTURE_POINTS)
        self.supply_hp = CITY_INITIAL_SUPPLY
        self.distance_red = 9999
        self.distance_blue = 9999
  
    def _calc_bbox(self):
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        return (min(xs), min(ys), max(xs), max(ys))

    def _generate_sample_points(self, num_points):
        points = []
        x_min, y_min, x_max, y_max = self.bbox
        while len(points) < num_points:
            x = random.uniform(x_min, x_max)
            y = random.uniform(y_min, y_max)
            if self.point_in_polygon(x, y):
                points.append((x, y))
        return points

    def point_in_polygon(self, x, y):
        n = len(self.vertices)
        inside = False
        p1x, p1y = self.vertices[0]
        for i in range(n + 1):
            p2x, p2y = self.vertices[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def update(self, red_units, blue_units, influence_grid, outposts_red=None, outposts_blue=None):
        if influence_grid is None:
            return
        if outposts_red is None: outposts_red = []
        if outposts_blue is None: outposts_blue = []

        cols = WIDTH // INFLUENCE_CELL_SIZE + 1
        rows = HEIGHT // INFLUENCE_CELL_SIZE + 1

        red_dom = 0
        blue_dom = 0
        total_points = 0
        step = 10
        x_min, y_min, x_max, y_max = self.bbox
        for x in range(int(x_min), int(x_max) + 1, step):
            for y in range(int(y_min), int(y_max) + 1, step):
                if self.point_in_polygon(x, y):
                    col = min(cols - 1, max(0, x // INFLUENCE_CELL_SIZE))
                    row = min(rows - 1, max(0, y // INFLUENCE_CELL_SIZE))
                    r = influence_grid[row][col]['red']
                    b = influence_grid[row][col]['blue']
                    if r > b + INFLUENCE_THRESHOLD:
                        red_dom += 1
                    elif b > r + INFLUENCE_THRESHOLD:
                        blue_dom += 1
                    total_points += 1

        if total_points > 0:
            red_percent = red_dom / total_points
            blue_percent = blue_dom / total_points
        else:
            red_percent = 0.0
            blue_percent = 0.0

        red_inside = [u for u in red_units + outposts_red if self.point_in_polygon(u.x, u.y)]
        blue_inside = [u for u in blue_units + outposts_blue if self.point_in_polygon(u.x, u.y)]
        self.contested = len(red_inside) > 0 and len(blue_inside) > 0

        has_red_units = len(red_inside) > 0
        has_blue_units = len(blue_inside) > 0

        new_owner = self.owner
        dominant = None
        if red_percent > blue_percent:
            dominant = 'red'
            progress = red_percent
        elif blue_percent > red_percent:
            dominant = 'blue'
            progress = blue_percent
        else:
            progress = 0.0

        if not has_red_units and not has_blue_units:
            new_owner = None
            self.capture_progress = 0.0
            self.capturing_faction = None
        elif has_red_units and not has_blue_units:
            if red_percent >= CAPTURE_THRESHOLD:
                new_owner = 'red'
                self.capture_progress = 0.0
                self.capturing_faction = None
            elif self.owner == 'red' and red_percent < 0.55:
                new_owner = None
                self.capture_progress = 0.0
                self.capturing_faction = None
            else:
                if self.owner != 'red':
                    new_owner = None
                if red_percent >= 0.55:
                    self.capture_progress = 0.0
                    self.capturing_faction = None
                else:
                    self.capture_progress = red_percent / CAPTURE_THRESHOLD
                    self.capturing_faction = 'red'
        elif has_blue_units and not has_red_units:
            if blue_percent >= CAPTURE_THRESHOLD:
                new_owner = 'blue'
                self.capture_progress = 0.0
                self.capturing_faction = None
            elif self.owner == 'blue' and blue_percent < 0.55:
                new_owner = None
                self.capture_progress = 0.0
                self.capturing_faction = None
            else:
                if self.owner != 'blue':
                    new_owner = None
                if blue_percent >= 0.55:
                    self.capture_progress = 0.0
                    self.capturing_faction = None
                else:
                    self.capture_progress = blue_percent / CAPTURE_THRESHOLD
                    self.capturing_faction = 'blue'
        else:
            if red_percent >= CAPTURE_THRESHOLD:
                new_owner = 'red'
                self.capture_progress = 0.0
                self.capturing_faction = None
            elif blue_percent >= CAPTURE_THRESHOLD:
                new_owner = 'blue'
                self.capture_progress = 0.0
                self.capturing_faction = None
            else:
                if self.owner and ((self.owner == 'red' and red_percent < 0.55) or
                                    (self.owner == 'blue' and blue_percent < 0.55)):
                    new_owner = None
                    self.capture_progress = 0.0
                    self.capturing_faction = None
                else:
                    if dominant:
                        self.capture_progress = progress / CAPTURE_THRESHOLD
                        self.capturing_faction = dominant
                    else:
                        self.capture_progress = 0.0
                        self.capturing_faction = None

        self.owner = new_owner

        # Лечение юнитов в городе
        if not self.contested and self.owner is not None:
            if self.owner == 'red':
                for u in red_units:
                    if self.point_in_polygon(u.x, u.y) and u.hp < u.max_hp and self.supply_hp > 0:
                        heal_amount = min(HEAL_PER_FRAME, u.max_hp - u.hp, self.supply_hp)
                        u.hp += heal_amount
                        self.supply_hp -= heal_amount
            else:
                for u in blue_units:
                    if self.point_in_polygon(u.x, u.y) and u.hp < u.max_hp and self.supply_hp > 0:
                        heal_amount = min(HEAL_PER_FRAME, u.max_hp - u.hp, self.supply_hp)
                        u.hp += heal_amount
                        self.supply_hp -= heal_amount

    @staticmethod
    def update_supply_chain(cities, roads, red_base, blue_base,
                            red_units=None, blue_units=None,
                            outposts_red=None, outposts_blue=None):
        if red_units is None: red_units = []
        if blue_units is None: blue_units = []
        if outposts_red is None: outposts_red = []
        if outposts_blue is None: outposts_blue = []

        # Живые враги для блокировки дорог
        enemies_for_red = [e for e in list(blue_units) + list(outposts_blue)
                            if getattr(e, 'hp', 1) > 0]
        enemies_for_blue = [e for e in list(red_units) + list(outposts_red)
                             if getattr(e, 'hp', 1) > 0]

        # Граф вершин дорог
        adj = {}
        for road in roads:
            for i in range(len(road.vertices) - 1):
                a = (round(road.vertices[i][0]), round(road.vertices[i][1]))
                b = (round(road.vertices[i + 1][0]), round(road.vertices[i + 1][1]))
                if a == b:
                    continue
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)

        def edge_blocked(a, b, enemies):
            for e in enemies:
                ex, ey = _object_center(e)
                if _point_to_segment_distance(ex, ey, a[0], a[1], b[0], b[1]) <= ROAD_BLOCK_RADIUS:
                    return True
            return False

        def base_connected_to_graph(base):
            """База привязывается к ближайшему сегменту дороги."""
            if not base or not base.active or not roads:
                return None
            bx, by = _object_center(base)
            best_dist = float('inf')
            best_vertex = None
            for road in roads:
                for i in range(len(road.vertices) - 1):
                    ax, ay = road.vertices[i]
                    bxx, byy = road.vertices[i + 1]
                    if ax == bxx and ay == byy:
                        continue
                    d = _point_to_segment_distance(bx, by, ax, ay, bxx, byy)
                    if d < best_dist:
                        best_dist = d
                        a_pt = (round(ax), round(ay))
                        b_pt = (round(bxx), round(byy))
                        da = math.hypot(a_pt[0] - bx, a_pt[1] - by)
                        db = math.hypot(b_pt[0] - bx, b_pt[1] - by)
                        best_vertex = a_pt if da <= db else b_pt
            if best_vertex is None or best_dist > ROAD_ATTACH_DIST:
                return None
            return best_vertex

        def bfs(base, enemies):
            if not base or not base.active or not adj:
                return set()
            start = base_connected_to_graph(base)
            if start is None:
                return set()
            visited = {start}
            queue = deque([start])
            while queue:
                cur = queue.popleft()
                for nb in adj[cur]:
                    if nb in visited:
                        continue
                    if edge_blocked(cur, nb, enemies):
                        continue
                    visited.add(nb)
                    queue.append(nb)
            return visited

        red_reach = bfs(red_base, enemies_for_red)
        blue_reach = bfs(blue_base, enemies_for_blue)

        def city_reachable(city, reachable):
            """Город снабжается, если хотя бы одна достижимая вершина связана с ним."""
            if not reachable:
                return False
            cx, cy = city.center

            # Вершина внутри города
            for v in reachable:
                if city.point_in_polygon(v[0], v[1]):
                    return True

            # Вершина рядом с центром
            for v in reachable:
                if math.hypot(v[0] - cx, v[1] - cy) <= ROAD_ATTACH_DIST:
                    return True

            # Сегмент дороги пересекает город, и хотя бы один конец достижим
            city_rect = pygame.Rect(city.bbox[0], city.bbox[1],
                                    city.bbox[2] - city.bbox[0],
                                    city.bbox[3] - city.bbox[1])
            for road in roads:
                for i in range(len(road.vertices) - 1):
                    p1 = road.vertices[i]
                    p2 = road.vertices[i + 1]
                    if city_rect.clipline(p1, p2):
                        a = (round(p1[0]), round(p1[1]))
                        b = (round(p2[0]), round(p2[1]))
                        if a in reachable or b in reachable:
                            return True
            return False

        for city in cities:
            city.distance_red = 9999
            city.distance_blue = 9999
            if city.owner == 'red' and city_reachable(city, red_reach):
                city.distance_red = 1
            if city.owner == 'blue' and city_reachable(city, blue_reach):
                city.distance_blue = 1

        # Прирост снабжения — ТОЛЬКО городам, напрямую соединённым с базой.
        # Цепочка "город → город → город" больше не работает.
        if red_base and red_base.active:
            for city in cities:
                if city.owner == 'red' and city.distance_red == 1:
                    city.supply_hp += SUPPLY_RATE_PER_FRAME
        if blue_base and blue_base.active:
            for city in cities:
                if city.owner == 'blue' and city.distance_blue == 1:
                    city.supply_hp += SUPPLY_RATE_PER_FRAME