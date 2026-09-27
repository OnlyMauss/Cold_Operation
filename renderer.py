# renderer.py
import math
import pygame
from config import *


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))


def load_texture(path, fallback_color):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (UNIT_WIDTH, UNIT_HEIGHT))
    except (pygame.error, FileNotFoundError):
        surf = pygame.Surface((UNIT_WIDTH, UNIT_HEIGHT))
        surf.fill(fallback_color)
        c_x, c_y = UNIT_WIDTH // 2, UNIT_HEIGHT // 2
        pygame.draw.line(surf, (0, 0, 0), (c_x - 5, c_y - 5), (c_x + 5, c_y + 5), 2)
        pygame.draw.line(surf, (0, 0, 0), (c_x - 5, c_y + 5), (c_x + 5, c_y - 5), 2)
        return surf


def load_texture_hq(path, fallback_color):
    """Загрузка текстуры Штаба (HQ_WIDTH × HQ_HEIGHT)."""
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (HQ_WIDTH, HQ_HEIGHT))
    except (pygame.error, FileNotFoundError):
        surf = pygame.Surface((HQ_WIDTH, HQ_HEIGHT))
        surf.fill(fallback_color)
        cx, cy = HQ_WIDTH // 2, HQ_HEIGHT // 2
        pygame.draw.circle(surf, (255, 220, 0), (cx, cy), 6)
        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), 6, 1)
        return surf


def load_flag_texture(path, fallback_color):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (20, 20))
    except (pygame.error, FileNotFoundError):
        surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(surf, fallback_color, (10, 10), 8)
        pygame.draw.circle(surf, (0, 0, 0), (10, 10), 8, 2)
        return surf


def draw_arrow(surface, color, start, end, size=12):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return
    angle = math.atan2(dy, dx)
    arrow_p1 = (end[0] - size * math.cos(angle - math.pi / 6),
                end[1] - size * math.sin(angle - math.pi / 6))
    arrow_p2 = (end[0] - size * math.cos(angle + math.pi / 6),
                end[1] - size * math.sin(angle + math.pi / 6))
    pygame.draw.polygon(surface, color, [end, arrow_p1, arrow_p2])


def draw_unit_path(screen, unit):
    if not unit.waypoints:
        return
    w = getattr(unit, 'width', UNIT_WIDTH)
    h = getattr(unit, 'height', UNIT_HEIGHT)
    start = (unit.x + w // 2, unit.y + h // 2)
    if len(unit.waypoints) > 1:
        full_path = [start] + list(unit.waypoints)
        pygame.draw.lines(screen, PATH_DOT_COLOR, False, full_path, 2)
        draw_arrow(screen, PATH_DOT_COLOR, unit.waypoints[-2], unit.waypoints[-1])
    elif len(unit.waypoints) == 1:
        end = unit.waypoints[0]
        pygame.draw.line(screen, PATH_DOT_COLOR, start, end, 2)
        draw_arrow(screen, PATH_DOT_COLOR, start, end)


def draw_city(screen, city, flag_textures):
    neutral_color = (150, 150, 150, 50)
    red_color = (200, 0, 0, 50)
    blue_color = (0, 0, 200, 50)

    if city.capturing_faction is not None:
        if city.owner is None:
            fill_color = lerp_color(neutral_color,
                                    red_color if city.capturing_faction == 'red' else blue_color,
                                    city.capture_progress)
        elif city.owner == 'red':
            fill_color = lerp_color(red_color, blue_color, city.capture_progress) if city.capturing_faction == 'blue' else red_color
        else:
            fill_color = lerp_color(blue_color, red_color, city.capture_progress) if city.capturing_faction == 'red' else blue_color
    else:
        if city.owner == 'red':
            fill_color = red_color
        elif city.owner == 'blue':
            fill_color = blue_color
        else:
            fill_color = neutral_color

    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(s, fill_color, city.vertices)
    screen.blit(s, (0, 0))
    pygame.draw.polygon(screen, WHITE, city.vertices, 2)
    flag_key = city.owner if city.owner else 'neutral'
    flag_img = flag_textures[flag_key]
    flag_rect = flag_img.get_rect(center=city.center)
    screen.blit(flag_img, flag_rect)


def draw_roads(screen, roads):
    for road in roads:
        if len(road.vertices) >= 2:
            pygame.draw.lines(screen, ROAD_COLOR, False, road.vertices, 4)


def draw_supply_base(screen, base, textures):
    if not base.active:
        return
    tex = textures.get(f'supply_{base.team}')
    if tex:
        screen.blit(tex, (base.x, base.y))
    else:
        pygame.draw.rect(screen, RED if base.team == 'red' else BLUE,
                         (base.x, base.y, base.width, base.height))
        font = pygame.font.SysFont("Arial", 16)
        text = font.render("S", True, WHITE)
        screen.blit(text, (base.x + 8, base.y + 4))


def draw(screen, red_units, blue_units, bullets, input_handler, textures, flag_textures, cities,
         airstrikes, plane_texture_red, plane_texture_blue, cursor_texture,
         roads, red_base, blue_base, highlight_bases,
         red_convoys, blue_convoys, panel, forests, outposts_red, outposts_blue, hud_panel,
         artillery_cursor_texture=None, frontline_data=None,
         dragon_teeth_red=None, dragon_teeth_blue=None,
         mines_red=None, mines_blue=None, player_team='red',
         red_hq=None, blue_hq=None, command_points=None):
    if dragon_teeth_red is None: dragon_teeth_red = []
    if dragon_teeth_blue is None: dragon_teeth_blue = []
    if mines_red is None: mines_red = []
    if mines_blue is None: mines_blue = []
    if command_points is None:
        command_points = {'red': 0.0, 'blue': 0.0}

    # Фон и сетка
    screen.fill(BG_COLOR)
    for i in range(0, WIDTH, 50):
        pygame.draw.line(screen, GRID_COLOR, (i, 0), (i, HEIGHT), 1)
    for i in range(0, HEIGHT, 50):
        pygame.draw.line(screen, GRID_COLOR, (0, i), (WIDTH, i), 1)

    # Зона баз
    if panel and panel.items[3]["active"]:
        zone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        zone_color = (0, 200, 0, 40)
        pygame.draw.rect(zone_surf, zone_color, (0, 0, BORDER_MARGIN, HEIGHT))
        pygame.draw.rect(zone_surf, zone_color, (WIDTH - BORDER_MARGIN, 0, BORDER_MARGIN, HEIGHT))
        pygame.draw.rect(zone_surf, zone_color, (0, 0, WIDTH, BORDER_MARGIN))
        pygame.draw.rect(zone_surf, zone_color, (0, HEIGHT - BORDER_MARGIN, WIDTH, BORDER_MARGIN))
        screen.blit(zone_surf, (0, 0))

    # Дороги
    draw_roads(screen, roads)

    # Линия фронта
    if panel and panel.items[5]["active"] and frontline_data is not None:
        f_zone_surf, f_lines = frontline_data[0], frontline_data[1]
        screen.blit(f_zone_surf, (0, 0))
        for (x1, y1, x2, y2) in f_lines:
            pygame.draw.line(screen, WHITE, (x1, y1), (x2, y2), 2)

    # Леса
    for forest in forests:
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(s, (0, 100, 0, 80), forest.vertices)
        screen.blit(s, (0, 0))

    # Города
    for city in cities:
        draw_city(screen, city, flag_textures)

    # Ресурсы городов
    if panel and panel.items[2]["active"]:
        font = pygame.font.SysFont("Arial", 16)
        for city in cities:
            if city.owner is not None:
                text = font.render(str(int(city.supply_hp)), True, WHITE)
                text_rect = text.get_rect(centerx=city.center[0], centery=city.center[1] - 20)
                screen.blit(text, text_rect)

    # Жёлтые круги вокруг городов
    if any(c.selected for c in red_convoys) or any(c.selected for c in blue_convoys):
        for city in cities:
            pygame.draw.circle(screen, YELLOW, city.center, 10, 2)

    # Зоны атаки
    if panel and panel.items[0]["active"]:
        for unit in red_units + blue_units:
            if unit.selected:
                center = (int(unit.x + UNIT_WIDTH // 2), int(unit.y + UNIT_HEIGHT // 2))
                pygame.draw.circle(screen, WHITE, center, unit.attack_range, 2)

    # Маршруты — включая Штабы
    all_path_units = list(red_units) + list(blue_units)
    if red_hq is not None and red_hq.active:
        all_path_units.append(red_hq)
    if blue_hq is not None and blue_hq.active:
        all_path_units.append(blue_hq)

    if panel and panel.items[1]["active"]:
        for unit in all_path_units:
            draw_unit_path(screen, unit)
    else:
        for unit in all_path_units:
            if unit.selected and unit.waypoints:
                draw_unit_path(screen, unit)
                break

    # Текущий маршрут
    if input_handler.is_pathing and len(input_handler.current_path) > 1:
        pygame.draw.lines(screen, PATH_DOT_COLOR, False, input_handler.current_path, 3)
        if len(input_handler.current_path) >= 2:
            draw_arrow(screen, PATH_DOT_COLOR,
                       input_handler.current_path[-2], input_handler.current_path[-1])

    # Пули
    for bullet in bullets:
        pygame.draw.line(screen, YELLOW, bullet.start, bullet.end, 3)

    # Область артиллерии
    if input_handler.mode == 'artillery_aim' and input_handler.current_path:
        if len(input_handler.current_path) >= 3:
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(surf, (255, 255, 0, 30), input_handler.current_path)
            screen.blit(surf, (0, 0))
            pygame.draw.polygon(screen, YELLOW, input_handler.current_path, 2)

    # Предпросмотр линии
    if input_handler.mode in ('build_dragon_teeth', 'build_mines', 'demolish'):
        mx, my = pygame.mouse.get_pos()
        if input_handler.line_drawing and input_handler.line_start and input_handler.line_end:
            sx, sy = input_handler.line_start
            ex, ey = input_handler.line_end
            dist = math.hypot(ex - sx, ey - sy)
            is_over_limit = dist >= MAX_LINE_LENGTH - 0.5
            if input_handler.mode == 'demolish':
                base_color = (255, 100, 100) if not is_over_limit else (255, 0, 0)
            else:
                base_color = (255, 60, 60) if is_over_limit else (60, 255, 60)
            pygame.draw.line(screen, base_color, (sx, sy), (ex, ey), 3)
            if input_handler.mode in ('build_dragon_teeth', 'build_mines'):
                spacing = DRAGON_TEETH_SPACING if input_handler.mode == 'build_dragon_teeth' else MINE_SPACING
                n_steps = max(1, int(dist // spacing))
                for i in range(n_steps + 1):
                    t = i / n_steps if n_steps > 0 else 0
                    px = sx + (ex - sx) * t
                    py = sy + (ey - sy) * t
                    if input_handler.mode == 'build_dragon_teeth':
                        pygame.draw.polygon(screen, base_color, [
                            (px, py - 5), (px - 4, py + 3), (px + 4, py + 3)])
                    else:
                        pygame.draw.circle(screen, base_color, (int(px), int(py)), 3)
        else:
            if input_handler.mode == 'demolish':
                pygame.draw.rect(screen, (255, 60, 60), (mx - 8, my - 8, 16, 16))
                pygame.draw.rect(screen, (0, 0, 0), (mx - 8, my - 8, 16, 16), 2)
            elif input_handler.mode == 'build_dragon_teeth':
                pygame.draw.polygon(screen, (60, 255, 60), [
                    (mx, my - 8), (mx - 6, my + 4), (mx + 6, my + 4)])
                pygame.draw.polygon(screen, (0, 0, 0), [
                    (mx, my - 8), (mx - 6, my + 4), (mx + 6, my + 4)], 1)
            else:
                pygame.draw.circle(screen, (60, 255, 60), (mx, my), 5)
                pygame.draw.circle(screen, (0, 0, 0), (mx, my), 5, 1)

    # Зубья дракона
    for tooth in dragon_teeth_red + dragon_teeth_blue:
        if tooth.hp <= 0:
            continue
        base_color = (60, 60, 60)
        outline_color = (20, 20, 20)
        hp_percent = tooth.hp / tooth.max_hp
        if hp_percent < 1.0:
            c = int(60 + (1 - hp_percent) * 60)
            base_color = (c, c, c)
        cx = tooth.x
        cy = tooth.y
        pygame.draw.polygon(screen, base_color, [
            (cx, cy - DRAGON_TEETH_RADIUS),
            (cx - DRAGON_TEETH_RADIUS, cy + DRAGON_TEETH_RADIUS),
            (cx + DRAGON_TEETH_RADIUS, cy + DRAGON_TEETH_RADIUS)])
        pygame.draw.polygon(screen, outline_color, [
            (cx, cy - DRAGON_TEETH_RADIUS),
            (cx - DRAGON_TEETH_RADIUS, cy + DRAGON_TEETH_RADIUS),
            (cx + DRAGON_TEETH_RADIUS, cy + DRAGON_TEETH_RADIUS)], 1)

    # Мины
    for m in mines_red + mines_blue:
        visible = (m.team == player_team) or m.discovered.get(player_team, False)
        if not visible:
            continue
        color = (200, 60, 60) if m.team == 'red' else (60, 60, 200)
        cx = int(m.x)
        cy = int(m.y)
        pygame.draw.circle(screen, color, (cx, cy), 4)
        pygame.draw.circle(screen, (0, 0, 0), (cx, cy), 4, 1)
        pygame.draw.circle(screen, (0, 0, 0), (cx, cy), 1)

    # Штабы
    for hq in (red_hq, blue_hq):
        if hq is None or not hq.active:
            continue
        tex = textures.get(f'headquarters_{hq.team}')
        if tex:
            screen.blit(tex, (hq.x, hq.y))
        else:
            color = (180, 30, 30) if hq.team == 'red' else (30, 30, 180)
            pygame.draw.rect(screen, color, (hq.x, hq.y, hq.width, hq.height))
            pygame.draw.rect(screen, (0, 0, 0), (hq.x, hq.y, hq.width, hq.height), 2)
            cx = hq.x + hq.width // 2
            cy = hq.y + hq.height // 2
            pygame.draw.circle(screen, (255, 220, 0), (cx, cy), 6)
            pygame.draw.circle(screen, (0, 0, 0), (cx, cy), 6, 1)

        hp_pct = hq.hp / hq.max_hp if hq.max_hp else 0
        pygame.draw.rect(screen, (60, 60, 60), (hq.x, hq.y - 6, hq.width, 3))
        pygame.draw.rect(screen, (0, 200, 0), (hq.x, hq.y - 6, int(hq.width * hp_pct), 3))

        if hq.selected:
            pygame.draw.rect(screen, WHITE,
                             (hq.x - 2, hq.y - 2, hq.width + 4, hq.height + 4), 2)

    # Юниты
    for unit in red_units + blue_units:
        tex = textures.get(f'{unit.unit_type}_{unit.team}')
        if tex:
            screen.blit(tex, (unit.x, unit.y))
        else:
            pygame.draw.rect(screen, RED if unit.team == 'red' else BLUE,
                             (unit.x, unit.y, UNIT_WIDTH, UNIT_HEIGHT))

        hp_percent = unit.hp / unit.max_hp
        if hp_percent < 1.0:
            dark_overlay = pygame.Surface((UNIT_WIDTH, UNIT_HEIGHT), pygame.SRCALPHA)
            dark_overlay.set_alpha(int((1 - hp_percent) * 200))
            dark_overlay.fill((0, 0, 0))
            screen.blit(dark_overlay, (unit.x, unit.y))

        if unit.selected:
            pygame.draw.rect(screen, WHITE,
                             (unit.x - 2, unit.y - 2, UNIT_WIDTH + 4, UNIT_HEIGHT + 4), 2)

        if getattr(unit, 'entrenchment', 0) > 0:
            progress = unit.entrenchment / DIG_IN_MAX_BONUS
            bar_w = int(UNIT_WIDTH * progress)
            bar_x = unit.x
            bar_y = unit.y + UNIT_HEIGHT + 2
            pygame.draw.rect(screen, (60, 40, 20), (bar_x, bar_y, UNIT_WIDTH, 3))
            pygame.draw.rect(screen, (150, 100, 40), (bar_x, bar_y, bar_w, 3))

        if getattr(unit, 'unit_type', None) == 'engineer' and getattr(unit, 'engineer_task', None):
            progress = min(1.0, getattr(unit, 'work_progress', 0.0))
            bar_w = int(UNIT_WIDTH * progress)
            bar_x = unit.x
            bar_y = unit.y + UNIT_HEIGHT + 6
            pygame.draw.rect(screen, (40, 40, 60), (bar_x, bar_y, UNIT_WIDTH, 3))
            pygame.draw.rect(screen, (100, 200, 255), (bar_x, bar_y, bar_w, 3))

        if getattr(unit, 'encircled', False):
            if getattr(unit, 'fed_by_city', False):
                pygame.draw.rect(screen, YELLOW,
                                 (unit.x - 3, unit.y - 3, UNIT_WIDTH + 6, UNIT_HEIGHT + 6), 2)
            else:
                pulse = 128 + int(127 * abs(math.sin(pygame.time.get_ticks() * 0.005)))
                color = (pulse, 0, 0)
                pygame.draw.rect(screen, color,
                                 (unit.x - 3, unit.y - 3, UNIT_WIDTH + 6, UNIT_HEIGHT + 6), 2)

        shield_visible = (unit.current_defense > 0
                          and (not panel or panel.items[4]["active"]))
        shield_img = textures.get('shield')
        fully_dig_in = getattr(unit, 'entrenchment', 0) >= DIG_IN_MAX_BONUS * 0.99

        if shield_visible and shield_img:
            small_shield = pygame.transform.scale(
                shield_img,
                (shield_img.get_width() // 2, shield_img.get_height() // 2))
            shield_x = unit.x
            shield_y = unit.y + UNIT_HEIGHT - small_shield.get_height()
            screen.blit(small_shield, (shield_x, shield_y))
            if fully_dig_in:
                font_plus = pygame.font.SysFont("Arial", 11, bold=True)
                plus = font_plus.render("+", True, (0, 220, 0))
                screen.blit(plus,
                            (shield_x + small_shield.get_width() + 4,
                             shield_y + small_shield.get_height() // 2 - 7))
        elif fully_dig_in:
            font_plus = pygame.font.SysFont("Arial", 11, bold=True)
            plus = font_plus.render("+", True, (0, 220, 0))
            screen.blit(plus, (unit.x + UNIT_WIDTH - 10, unit.y + UNIT_HEIGHT - 12))

        if getattr(unit, 'unit_type', None) == 'engineer' and unit.selected:
            font_log = pygame.font.SysFont("Arial", 11, bold=True)
            log_text = font_log.render(f"L:{int(unit.logistics)}/{unit.max_logistics}",
                                       True, (100, 200, 255))
            screen.blit(log_text, (unit.x, unit.y - 14))

        if unit.unit_type == 'artillery' and unit.artillery_explosions:
            for (ex, ey, timer) in unit.artillery_explosions:
                radius = max(2, 20 - timer)
                alpha = max(0, min(255, timer * 12))
                if radius > 0 and alpha > 0:
                    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (255, 200, 0, alpha), (radius, radius), radius)
                    screen.blit(surf, (ex - radius, ey - radius))

    # Опорники и склады
    mouse_pos = pygame.mouse.get_pos()
    convoy_red_sel = any(c.selected for c in red_convoys)
    convoy_blue_sel = any(c.selected for c in blue_convoys)

    for outpost in outposts_red + outposts_blue:
        if getattr(outpost, 'unit_type', None) == 'warehouse':
            tex = textures.get(f'warehouse_{outpost.team}')
            if tex:
                screen.blit(tex, (outpost.x, outpost.y))
            else:
                color = (150, 100, 50) if outpost.team == 'red' else (50, 100, 150)
                pygame.draw.rect(screen, color,
                                 (outpost.x, outpost.y, outpost.width, outpost.height))
                pygame.draw.rect(screen, (0, 0, 0),
                                 (outpost.x, outpost.y, outpost.width, outpost.height), 1)
                font = pygame.font.SysFont("Arial", 10, bold=True)
                text = font.render("W", True, WHITE)
                text_rect = text.get_rect(center=(outpost.x + outpost.width // 2,
                                                  outpost.y + outpost.height // 2))
                screen.blit(text, text_rect)
        else:
            tex = textures.get(f'outpost_{outpost.team}')
            if tex:
                screen.blit(tex, (outpost.x, outpost.y))
            else:
                pygame.draw.rect(screen, RED if outpost.team == 'red' else BLUE,
                                 (outpost.x, outpost.y, outpost.width, outpost.height))

        hp_percent = outpost.hp / outpost.max_hp if outpost.max_hp else 0
        if hp_percent < 1.0:
            dark_overlay = pygame.Surface((outpost.width, outpost.height), pygame.SRCALPHA)
            dark_overlay.set_alpha(int((1 - hp_percent) * 200))
            dark_overlay.fill((0, 0, 0))
            screen.blit(dark_overlay, (outpost.x, outpost.y))

        bar_w = outpost.width
        bar_h = 3
        bar_x = outpost.x
        bar_y = outpost.y - 6
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(screen, (0, 200, 0),
                         (bar_x, bar_y, int(bar_w * hp_percent), bar_h))

        if outpost.current_defense > 0 and (not panel or panel.items[4]["active"]):
            shield_img = textures.get('shield')
            if shield_img:
                small_shield = pygame.transform.scale(
                    shield_img,
                    (shield_img.get_width() // 2, shield_img.get_height() // 2))
                shield_x = outpost.x
                shield_y = outpost.y + outpost.height - small_shield.get_height()
                screen.blit(small_shield, (shield_x, shield_y))

        if outpost.selected:
            pygame.draw.rect(screen, WHITE,
                             (outpost.x - 2, outpost.y - 2,
                              outpost.width + 4, outpost.height + 4), 2)
            if getattr(outpost, 'unit_type', None) != 'warehouse':
                center = (int(outpost.x + outpost.width // 2),
                          int(outpost.y + outpost.height // 2))
                pygame.draw.circle(screen, (0, 255, 100),
                                   center, OUTPOST_SUPPLY_RADIUS, 1)

        if (convoy_red_sel and outpost.team == 'red') or (convoy_blue_sel and outpost.team == 'blue'):
            expanded = pygame.Rect(outpost.x - 5, outpost.y - 5,
                                   outpost.width + 10, outpost.height + 10)
            if expanded.collidepoint(mouse_pos):
                pygame.draw.rect(screen, YELLOW, expanded, 2)

        if outpost.supply_hp > 0:
            font = pygame.font.SysFont("Arial", 10)
            text = font.render(str(int(outpost.supply_hp)), True, WHITE)
            screen.blit(text, (outpost.x, outpost.y - 18))

    # Базы
    if red_base:
        draw_supply_base(screen, red_base, textures)
        if red_base in highlight_bases:
            pygame.draw.rect(screen, (255, 0, 255), red_base.get_rect(), 2)
    if blue_base:
        draw_supply_base(screen, blue_base, textures)
        if blue_base in highlight_bases:
            pygame.draw.rect(screen, (255, 0, 255), blue_base.get_rect(), 2)

    # Конвои
    for convoy in red_convoys + blue_convoys:
        if convoy.hp <= 0:
            continue
        tex = textures.get(f'convoy_{convoy.team}')
        if tex:
            screen.blit(tex, (convoy.x, convoy.y))
        else:
            pygame.draw.rect(screen, RED if convoy.team == 'red' else BLUE,
                             (convoy.x, convoy.y, convoy.width, convoy.height))
            font = pygame.font.SysFont("Arial", 12)
            text = font.render(str(convoy.cargo), True, WHITE)
            screen.blit(text, (convoy.x + 2, convoy.y + 2))
        if convoy.selected:
            pygame.draw.rect(screen, WHITE,
                             (convoy.x - 2, convoy.y - 2, convoy.width + 4, convoy.height + 4), 2)
        if convoy.transferring:
            progress = 1 - (convoy.transfer_timer / CONVOY_TRANSFER_TIME)
            bar_width = int(convoy.width * progress)
            color = WHITE if convoy.transfer_mode == 'unload' else YELLOW
            pygame.draw.rect(screen, color, (convoy.x, convoy.y - 6, bar_width, 4))
        if convoy.cargo > 0:
            font = pygame.font.SysFont("Arial", 12)
            text = font.render(str(convoy.cargo), True, WHITE)
            text_rect = text.get_rect(centerx=convoy.x + convoy.width // 2,
                                      centery=convoy.y - 10)
            screen.blit(text, text_rect)

    # Авиаудары
    for strike in airstrikes:
        if strike.started and not strike.finished:
            pos = strike.get_position()
            angle = strike.get_angle()
            plane_texture = plane_texture_red if getattr(strike, 'team', 'red') == 'red' else plane_texture_blue
            rotated = pygame.transform.rotate(plane_texture, angle)
            rot_rect = rotated.get_rect(center=pos)
            screen.blit(rotated, rot_rect)
        if strike.arrived and strike.explosion_timer > 0:
            progress = 1 - (strike.explosion_timer / 15.0)
            radius = int(AIRSTRIKE_RADIUS * progress)
            if radius > 0:
                surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 200, 0, 150), (radius, radius), radius)
                screen.blit(surf, (strike.target[0] - radius, strike.target[1] - radius))

    # Рамка выделения
    if input_handler.selection_rect:
        pygame.draw.rect(screen, WHITE, input_handler.selection_rect, 1)

    # Курсор авиаудара
    if input_handler.mode == 'airstrike':
        mx, my = pygame.mouse.get_pos()
        screen.blit(cursor_texture,
                    (mx - cursor_texture.get_width() // 2,
                     my - cursor_texture.get_height() // 2))

    # Курсор артиллерии
    if input_handler.mode == 'artillery_aim' and artillery_cursor_texture:
        mx, my = pygame.mouse.get_pos()
        screen.blit(artillery_cursor_texture,
                    (mx - artillery_cursor_texture.get_width() // 2,
                     my - artillery_cursor_texture.get_height() // 2))

    # HUD панель
    if hud_panel:
        hud_panel.draw(screen)

    # Панель настроек
    if panel:
        panel.draw(screen)

    # Подсказки
    if input_handler.mode in ('action_load', 'action_unload'):
        mx, my = pygame.mouse.get_pos()
        font = pygame.font.SysFont("Arial", 16)
        if input_handler.mode == 'action_load':
            msg = "Погрузка: кликните на город"
        else:
            msg = "Разгрузка: кликните на город, опорник или инженера"
        txt = font.render(msg, True, YELLOW)
        pad = 4
        bg = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad * 2),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (mx + 20, my - 10))
        screen.blit(txt, (mx + 20 + pad, my - 10 + pad))

    if input_handler.mode in ('build_dragon_teeth', 'build_mines', 'demolish'):
        mx, my = pygame.mouse.get_pos()
        font = pygame.font.SysFont("Arial", 14)
        if input_handler.mode == 'build_dragon_teeth':
            msg = "Зубья: ЛКМ-удержание - линия, ПКМ/ESC - отмена"
        elif input_handler.mode == 'build_mines':
            msg = "Мины: ЛКМ-удержание - линия, ПКМ/ESC - отмена"
        else:
            msg = "Снос: ЛКМ-удержание - линия, ПКМ/ESC - отмена"
        txt = font.render(msg, True, YELLOW)
        pad = 4
        bg = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad * 2),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        screen.blit(bg, (mx + 20, my - 10))
        screen.blit(txt, (mx + 20 + pad, my - 10 + pad))

    # Индикатор КП
    if command_points:
        font_cp = pygame.font.SysFont("Arial", 16, bold=True)
        cp_text = f"КП: {int(command_points.get(player_team, 0))}"
        txt = font_cp.render(cp_text, True, (255, 255, 255))
        bg = pygame.Surface((txt.get_width() + 14, txt.get_height() + 8), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 170))
        screen.blit(bg, (WIDTH - txt.get_width() - 20, 30))
        screen.blit(txt, (WIDTH - txt.get_width() - 13, 34))