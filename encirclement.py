# encirclement.py
import math
from collections import deque
from config import *


def compute_reachable(team_grid, team, cities, red_base, blue_base,
                      outposts_red=None, outposts_blue=None):
    """
    BFS от базы по клеткам своей территории (team_grid == team).
    Если база уничтожена — возвращает пустой grid (никто не снабжён).
    """
    cols = WIDTH // INFLUENCE_CELL_SIZE + 1
    rows = HEIGHT // INFLUENCE_CELL_SIZE + 1
    reachable = [[False] * cols for _ in range(rows)]
    queue = deque()

    own_base = red_base if team == 'red' else blue_base
    if not own_base or not own_base.active:
        return reachable

    bx = own_base.x + own_base.width // 2
    by = own_base.y + own_base.height // 2
    col = max(0, min(cols - 1, int(bx) // INFLUENCE_CELL_SIZE))
    row = max(0, min(rows - 1, int(by) // INFLUENCE_CELL_SIZE))
    reachable[row][col] = True
    queue.append((row, col))

    while queue:
        r, c = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not reachable[nr][nc]:
                if team_grid[nr][nc] == team:
                    reachable[nr][nc] = True
                    queue.append((nr, nc))
    return reachable


def update_encirclement(red_units, blue_units, red_reach, blue_reach,
                        cities, red_base, blue_base):
    """
    1. Определяет encircled для каждого юнита.
    2. Если юнит окружён и стоит внутри своего города с supply_hp > 0 —
       город тратит снабжение, юнит НЕ теряет HP (fed_by_city = True).
    3. Иначе — юнит теряет ENCIRCLEMENT_DAMAGE_PER_FRAME HP.

    Скорость расхода города: 1 очко/сек на юнита (обычно),
    0.5 очка/сек на юнита (если город contested).
    """
    cols = WIDTH // INFLUENCE_CELL_SIZE + 1
    rows = HEIGHT // INFLUENCE_CELL_SIZE + 1

    def cell_of(u):
        cx = u.x + UNIT_WIDTH // 2
        cy = u.y + UNIT_HEIGHT // 2
        col = max(0, min(cols - 1, int(cx) // INFLUENCE_CELL_SIZE))
        row = max(0, min(rows - 1, int(cy) // INFLUENCE_CELL_SIZE))
        return row, col

    def process(units, reach, team):
        for u in units:
            if u.hp <= 0:
                continue
            r, c = cell_of(u)
            if reach[r][c]:
                u.encircled = False
                u.fed_by_city = False
                continue
            u.encircled = True
            fed = False
            cx = u.x + UNIT_WIDTH / 2
            cy = u.y + UNIT_HEIGHT / 2
            for city in cities:
                if city.owner != team:
                    continue
                if not city.point_in_polygon(cx, cy):
                    continue
                rate = 0.5 if city.contested else 1.0
                cost = rate / FPS
                if city.supply_hp >= cost:
                    city.supply_hp -= cost
                    fed = True
                    break
            if fed:
                u.fed_by_city = True
            else:
                u.fed_by_city = False
                u.hp -= ENCIRCLEMENT_DAMAGE_PER_FRAME

    process(red_units, red_reach, 'red')
    process(blue_units, blue_reach, 'blue')