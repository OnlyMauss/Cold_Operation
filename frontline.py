# frontline.py
import math
import pygame
from collections import deque
from config import *


def compute_influence_grid(red_units, blue_units, cities, red_base, blue_base,
                            outposts_red=None, outposts_blue=None):
    if outposts_red is None:
        outposts_red = []
    if outposts_blue is None:
        outposts_blue = []

    cols = WIDTH // INFLUENCE_CELL_SIZE + 1
    rows = HEIGHT // INFLUENCE_CELL_SIZE + 1

    # ---- 0. Сырое влияние (числа) — нужно City.update ----
    grid = [[{'red': 0.0, 'blue': 0.0} for _ in range(cols)] for _ in range(rows)]

    def add_influence(cx, cy, radius, strength, team):
        if radius <= 0:
            return
        min_col = max(0, int((cx - radius) // INFLUENCE_CELL_SIZE))
        max_col = min(cols - 1, int((cx + radius) // INFLUENCE_CELL_SIZE))
        min_row = max(0, int((cy - radius) // INFLUENCE_CELL_SIZE))
        max_row = min(rows - 1, int((cy + radius) // INFLUENCE_CELL_SIZE))
        for row in range(min_row, max_row + 1):
            gy = row * INFLUENCE_CELL_SIZE + INFLUENCE_CELL_SIZE // 2
            for col in range(min_col, max_col + 1):
                gx = col * INFLUENCE_CELL_SIZE + INFLUENCE_CELL_SIZE // 2
                d = math.hypot(gx - cx, gy - cy)
                if d <= radius:
                    factor = 1.0 - (d / radius)
                    if team == 'red':
                        grid[row][col]['red'] += strength * factor
                    else:
                        grid[row][col]['blue'] += strength * factor

    for city in cities:
        if city.owner is not None:
            add_influence(city.center[0], city.center[1],
                          INFLUENCE_RADIUS_CITY, 1.0, city.owner)

    if red_base and red_base.active:
        add_influence(red_base.x + red_base.width // 2,
                      red_base.y + red_base.height // 2,
                      INFLUENCE_RADIUS_BASE, 0.8, 'red')
    if blue_base and blue_base.active:
        add_influence(blue_base.x + blue_base.width // 2,
                      blue_base.y + blue_base.height // 2,
                      INFLUENCE_RADIUS_BASE, 0.8, 'blue')

    for unit in red_units:
        if unit.hp > 0:
            add_influence(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                          unit.influence_radius, 0.6, 'red')
    for unit in blue_units:
        if unit.hp > 0:
            add_influence(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                          unit.influence_radius, 0.6, 'blue')

    for o in outposts_red:
        if o.hp > 0:
            add_influence(o.x + o.width // 2, o.y + o.height // 2,
                          o.influence_radius, 0.6, 'red')
    for o in outposts_blue:
        if o.hp > 0:
            add_influence(o.x + o.width // 2, o.y + o.height // 2,
                          o.influence_radius, 0.6, 'blue')

    dominant = [[None] * cols for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            r = grid[row][col]['red']
            b = grid[row][col]['blue']
            if r > b + INFLUENCE_THRESHOLD:
                dominant[row][col] = 'red'
            elif b > r + INFLUENCE_THRESHOLD:
                dominant[row][col] = 'blue'

    # ---- 1. Маски ZOC ----
    red_range = [[False] * cols for _ in range(rows)]
    blue_range = [[False] * cols for _ in range(rows)]

    def mark_range(cx, cy, radius, mask):
        if radius <= 0:
            return
        min_col = max(0, int((cx - radius) // INFLUENCE_CELL_SIZE))
        max_col = min(cols - 1, int((cx + radius) // INFLUENCE_CELL_SIZE))
        min_row = max(0, int((cy - radius) // INFLUENCE_CELL_SIZE))
        max_row = min(rows - 1, int((cy + radius) // INFLUENCE_CELL_SIZE))
        for row in range(min_row, max_row + 1):
            gy = row * INFLUENCE_CELL_SIZE + INFLUENCE_CELL_SIZE // 2
            for col in range(min_col, max_col + 1):
                gx = col * INFLUENCE_CELL_SIZE + INFLUENCE_CELL_SIZE // 2
                if math.hypot(gx - cx, gy - cy) <= radius:
                    mask[row][col] = True

    if red_base and red_base.active:
        mark_range(red_base.x + red_base.width // 2,
                   red_base.y + red_base.height // 2,
                   INFLUENCE_RADIUS_BASE, red_range)
    if blue_base and blue_base.active:
        mark_range(blue_base.x + blue_base.width // 2,
                   blue_base.y + blue_base.height // 2,
                   INFLUENCE_RADIUS_BASE, blue_range)

    for unit in red_units:
        if unit.hp > 0 and unit.unit_type != 'artillery':
            mark_range(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                       unit.influence_radius, red_range)
    for unit in blue_units:
        if unit.hp > 0 and unit.unit_type != 'artillery':
            mark_range(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                       unit.influence_radius, blue_range)

    for o in outposts_red:
        if o.hp > 0:
            mark_range(o.x + o.width // 2, o.y + o.height // 2,
                       o.influence_radius, red_range)
    for o in outposts_blue:
        if o.hp > 0:
            mark_range(o.x + o.width // 2, o.y + o.height // 2,
                       o.influence_radius, blue_range)

    # ---- 2. Классификация клеток ----
    team_grid = [[None] * cols for _ in range(rows)]
    for row in range(rows):
        for col in range(cols):
            r = red_range[row][col]
            b = blue_range[row][col]
            if r and b:
                team_grid[row][col] = 'neutral'
            elif r:
                team_grid[row][col] = 'red'
            elif b:
                team_grid[row][col] = 'blue'

    # ---- 3. BFS: заполняем пустоты от КРАСНЫХ и СИНИХ клеток ----
    queue = deque()
    for row in range(rows):
        for col in range(cols):
            if team_grid[row][col] in ('red', 'blue'):
                queue.append((row, col))

    while queue:
        r, c = queue.popleft()
        team = team_grid[r][c]
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and team_grid[nr][nc] is None:
                team_grid[nr][nc] = team
                queue.append((nr, nc))

    # ---- 3.5. Личные радиусы юнитов ----
    # FIX: убрана проверка `if team_grid[row][col] is not None: continue`.
    # Теперь пятно юнита накладывается поверх любой территории —
    # включая нейтральную серую зону и чужую.
    # Это позволяет юниту "перекрашивать" локальный участок вокруг себя.
    personal_red = [[False] * cols for _ in range(rows)]
    personal_blue = [[False] * cols for _ in range(rows)]

    for unit in red_units:
        if unit.hp > 0:
            mark_range(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                       PERSONAL_CLAIM_RADIUS, personal_red)
    for unit in blue_units:
        if unit.hp > 0:
            mark_range(unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2,
                       PERSONAL_CLAIM_RADIUS, personal_blue)

    for row in range(rows):
        for col in range(cols):
            pr = personal_red[row][col]
            pb = personal_blue[row][col]
            if pr and pb:
                team_grid[row][col] = 'neutral'
            elif pr:
                team_grid[row][col] = 'red'
            elif pb:
                team_grid[row][col] = 'blue'
            # Если ни pr, ни pb — оставляем как было (после BFS)

    # ---- 4. Отрисовка ----
    zone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for row in range(rows):
        for col in range(cols):
            team = team_grid[row][col]
            if team == 'red':
                color = (200, 0, 0, 80)
            elif team == 'blue':
                color = (0, 0, 200, 80)
            elif team == 'neutral':
                color = NEUTRAL_COLOR
            else:
                continue
            rect = pygame.Rect(col * INFLUENCE_CELL_SIZE,
                               row * INFLUENCE_CELL_SIZE,
                               INFLUENCE_CELL_SIZE,
                               INFLUENCE_CELL_SIZE)
            pygame.draw.rect(zone_surf, color, rect)

    # ---- 5. Линия фронта ----
    frontline_lines = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            cur = team_grid[row][col]
            right = team_grid[row][col + 1]
            down = team_grid[row + 1][col]

            x1 = col * INFLUENCE_CELL_SIZE
            y1 = row * INFLUENCE_CELL_SIZE
            x2 = (col + 1) * INFLUENCE_CELL_SIZE
            y2 = (row + 1) * INFLUENCE_CELL_SIZE

            def border(a, b):
                if a is None or b is None or a == b:
                    return False
                return (a, b) in (
                    ('red', 'blue'), ('blue', 'red'),
                    ('red', 'neutral'), ('neutral', 'red'),
                    ('blue', 'neutral'), ('neutral', 'blue'),
                )

            if border(cur, right):
                frontline_lines.append((x2, y1, x2, y2))
            if border(cur, down):
                frontline_lines.append((x1, y2, x2, y2))

    return zone_surf, frontline_lines, grid, team_grid