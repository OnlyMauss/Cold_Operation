# airstrike.py
import math
import random
from config import *


class Airstrike:
    def __init__(self, target_pos, team='red'):
        self.target = target_pos
        self.team = team
        self.delay_timer = AIRSTRIKE_DELAY
        self.started = False
        self.start = None
        self.end = None
        self.total_dist = 0
        self.progress = 0.0
        self.speed = AIRSTRIKE_SPEED
        self.damage = AIRSTRIKE_DAMAGE
        self.radius = AIRSTRIKE_RADIUS
        self.arrived = False
        self.finished = False
        self.explosion_timer = 0

    def update(self, units, bases=None, convoys=None, outposts=None):
        """
        Наносит урон всем объектам в радиусе: юнитам, базам, конвоям, опорникам.
        Все параметры – списки объектов, могут быть None.
        """
        if self.finished:
            return True
        if self.delay_timer > 0:
            self.delay_timer -= 1
            return False
        if not self.started:
            self._init_flight_path()
            self.started = True

        self.progress += self.speed / self.total_dist
        if self.progress >= 1.0:
            self.finished = True
            return True

        dist_to_target = math.hypot(self.target[0] - self.start[0],
                                     self.target[1] - self.start[1])
        if not self.arrived and self.progress * self.total_dist >= dist_to_target:
            self.arrived = True
            self._apply_damage(units, bases, convoys, outposts)
            self.explosion_timer = 15

        if self.explosion_timer > 0:
            self.explosion_timer -= 1

        return False

    def _init_flight_path(self):
        side = random.choice(['left', 'right', 'top', 'bottom'])
        tx, ty = self.target
        if side == 'left':
            self.start = (0, random.randint(0, HEIGHT))
        elif side == 'right':
            self.start = (WIDTH, random.randint(0, HEIGHT))
        elif side == 'top':
            self.start = (random.randint(0, WIDTH), 0)
        else:
            self.start = (random.randint(0, WIDTH), HEIGHT)

        dx = tx - self.start[0]
        dy = ty - self.start[1]
        t_max = 1000.0
        if dx > 0:
            t_max = min(t_max, (WIDTH - self.start[0]) / dx)
        elif dx < 0:
            t_max = min(t_max, (0 - self.start[0]) / dx)
        if dy > 0:
            t_max = min(t_max, (HEIGHT - self.start[1]) / dy)
        elif dy < 0:
            t_max = min(t_max, (0 - self.start[1]) / dy)
        t_exit = t_max * 1.05
        self.end = (self.start[0] + dx * t_exit, self.start[1] + dy * t_exit)
        self.total_dist = math.hypot(self.end[0] - self.start[0],
                                     self.end[1] - self.start[1])
        if self.total_dist < 1:
            self.total_dist = 1

    def _get_center(self, obj):
        if hasattr(obj, 'width'):
            w = obj.width
            h = obj.height
        else:
            w = UNIT_WIDTH
            h = UNIT_HEIGHT
        return (obj.x + w / 2, obj.y + h / 2)

    def _apply_damage(self, units, bases, convoys, outposts):
        all_targets = []
        if units:
            all_targets.extend(units)
        if bases:
            all_targets.extend([b for b in bases if b.active])
        if convoys:
            all_targets.extend([c for c in convoys if c.hp > 0])
        if outposts:
            all_targets.extend([o for o in outposts if o.hp > 0])

        for obj in all_targets:
            cx, cy = self._get_center(obj)
            d = math.hypot(cx - self.target[0], cy - self.target[1])
            if d <= self.radius:
                obj.hp -= self.damage
                if obj.hp <= 0:
                    if hasattr(obj, 'active'):
                        obj.active = False
                        obj.respawn_timer = SUPPLY_BASE_RESPAWN_TIME
                        obj.waypoints.clear()

    def get_position(self):
        if not self.started:
            return self.target
        if self.finished:
            return self.end
        sx, sy = self.start
        ex, ey = self.end
        x = sx + (ex - sx) * self.progress
        y = sy + (ey - sy) * self.progress
        return (x, y)

    def get_angle(self):
        if not self.started:
            return 0
        ex, ey = self.end
        sx, sy = self.start
        dx = ex - sx
        dy = ey - sy
        return math.degrees(math.atan2(-dy, dx))