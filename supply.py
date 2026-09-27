# supply.py
import math
from config import *
from id_gen import next_id
class SupplyBase:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.hp = SUPPLY_BASE_HP
        self.max_hp = SUPPLY_BASE_HP
        self.speed = SUPPLY_BASE_SPEED
        self.selected = False
        self.waypoints = []
        self.active = True
        self.respawn_timer = 0
        self.width = SUPPLY_BASE_WIDTH
        self.height = SUPPLY_BASE_HEIGHT
        self.attack_cooldown = 0
        self.can_attack = False

    def get_rect(self):
        import pygame
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def _clamp_to_zone(self, x, y):
        """Возвращает ближайшую точку внутри зелёной зоны (первые 2 клетки от краёв)."""
        # Границы зоны
        left_x = BORDER_MARGIN
        right_x = WIDTH - BORDER_MARGIN
        top_y = BORDER_MARGIN
        bottom_y = HEIGHT - BORDER_MARGIN

        # Если точка уже в зоне, оставляем как есть
        if (x <= left_x or x >= right_x or y <= top_y or y >= bottom_y):
            return (x, y)

        # Иначе находим ближайшую точку на периметре
        candidates = [
            (left_x, y),   # левый край
            (right_x, y),  # правый край
            (x, top_y),    # верхний край
            (x, bottom_y)  # нижний край
        ]
        best = min(candidates, key=lambda pt: math.hypot(pt[0]-x, pt[1]-y))
        return best

    def _determine_edge(self, x, y):
        """Определяет, на каком ребре зоны находится точка."""
        left = x <= BORDER_MARGIN
        right = x >= WIDTH - BORDER_MARGIN
        top = y <= BORDER_MARGIN
        bottom = y >= HEIGHT - BORDER_MARGIN

        if (left and top) or (left and bottom) or (right and top) or (right and bottom):
            return 'corner'
        if left:
            return 'left'
        if right:
            return 'right'
        if top:
            return 'top'
        if bottom:
            return 'bottom'
        return 'unknown'

    def _corner_between(self, edge1, edge2):
        """Возвращает координаты угла, соединяющего два ребра."""
        corners = {
            ('left', 'top'): (BORDER_MARGIN, BORDER_MARGIN),
            ('top', 'left'): (BORDER_MARGIN, BORDER_MARGIN),
            ('left', 'bottom'): (BORDER_MARGIN, HEIGHT - BORDER_MARGIN),
            ('bottom', 'left'): (BORDER_MARGIN, HEIGHT - BORDER_MARGIN),
            ('right', 'top'): (WIDTH - BORDER_MARGIN, BORDER_MARGIN),
            ('top', 'right'): (WIDTH - BORDER_MARGIN, BORDER_MARGIN),
            ('right', 'bottom'): (WIDTH - BORDER_MARGIN, HEIGHT - BORDER_MARGIN),
            ('bottom', 'right'): (WIDTH - BORDER_MARGIN, HEIGHT - BORDER_MARGIN),
        }
        return corners.get((edge1, edge2))

    def move_to_path(self, path_points):
        corrected = []
        cur_x, cur_y = self.x, self.y

        for target in path_points:
            tx, ty = target

            # 1. Проецируем целевую точку на зону
            if not (tx <= BORDER_MARGIN or tx >= WIDTH - BORDER_MARGIN or 
                    ty <= BORDER_MARGIN or ty >= HEIGHT - BORDER_MARGIN):
                # Точка вне зоны – находим ближайшую точку на периметре
                dist_left = tx
                dist_right = WIDTH - tx
                dist_top = ty
                dist_bottom = HEIGHT - ty
                min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
                if min_dist == dist_left:
                    tx, ty = BORDER_MARGIN, ty
                elif min_dist == dist_right:
                    tx, ty = WIDTH - BORDER_MARGIN, ty
                elif min_dist == dist_top:
                    tx, ty = tx, BORDER_MARGIN
                else:
                    tx, ty = tx, HEIGHT - BORDER_MARGIN
            # Теперь (tx, ty) гарантированно в зоне

            # 2. Проверяем, нужно ли добавить угловую точку
            edge_cur = self._determine_edge(cur_x, cur_y)
            edge_target = self._determine_edge(tx, ty)

            if edge_cur != edge_target and edge_cur != 'corner' and edge_target != 'corner':
                # Разные ребра – добавляем угол
                corner = self._corner_between(edge_cur, edge_target)
                if corner:
                    corrected.append(corner)
            corrected.append((tx, ty))
            cur_x, cur_y = tx, ty

        self.waypoints = corrected

    def update(self, enemies, allies, bullets):
        if not self.active:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                self.active = True
                self.hp = self.max_hp
                self.waypoints = []
                self.selected = False
                if self.team == 'red':
                    self.x, self.y = BORDER_MARGIN, HEIGHT // 2
                else:
                    self.x, self.y = WIDTH - BORDER_MARGIN, HEIGHT // 2
            return

        # Коллизия с союзниками
        my_rect = self.get_rect()
        for ally in allies:
            if ally is self:
                continue
            ally_rect = ally.get_rect() if hasattr(ally, 'get_rect') else None
            if ally_rect is None:
                continue
            if my_rect.colliderect(ally_rect):
                dx = self.x - ally.x
                dy = self.y - ally.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    push_force = 0.8
                    self.x += (dx / dist) * push_force
                    self.y += (dy / dist) * push_force
                    my_rect = self.get_rect()

        # Движение по маршруту
        if self.waypoints:
            target_x, target_y = self.waypoints[0]
            dx = target_x - self.x
            dy = target_y - self.y
            distance = math.hypot(dx, dy)
            if distance > 2:
                step_x = (dx / distance) * self.speed
                step_y = (dy / distance) * self.speed
                self.x += step_x
                self.y += step_y
            else:
                self.waypoints.pop(0)

        # Жёсткая коррекция положения (чтобы точно не вылезти)
        self.x, self.y = self._clamp_to_zone(self.x, self.y)