# headquarters.py
import math
import pygame
from config import *
from id_gen import next_id


class Headquarters:
    """Штаб — юнит для вызова войск. Может двигаться как инженер."""

    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.unit_type = 'headquarters'
        self.id = next_id()

        self.max_hp = HQ_HP
        self.hp = self.max_hp
        self.width = HQ_WIDTH
        self.height = HQ_HEIGHT

        self.selected = False
        self.active = True
        self.respawn_timer = 0

        # Движение
        self.speed = 0.5
        self.waypoints = []

        self.can_attack = False
        self.attack_range = 0
        self.attack_damage = 0
        self.attack_cooldown = 0
        self.current_defense = 0.0
        self.influence_radius = 80

        # Совместимость с юнитом-инженером
        self.can_dig_in = False
        self.hold_position = False
        self.logistics = 0.0
        self.max_logistics = 0.0
        self.encircled = False
        self.fed_by_city = False
        self.entrenchment = 0.0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def move_to_path(self, path_points):
        self.waypoints = path_points[:]

    def update(self, enemies, allies, bullets, killed,
               roads=None, cities=None, forests=None):
        if not self.active:
            return

        if cities and forests:
            from terrain import get_defense
            self.current_defense = get_defense(
                self.x, self.y, 'outpost', cities, forests)
        else:
            self.current_defense = 0.0

        # Движение по waypoints
        if self.waypoints:
            tx, ty = self.waypoints[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 5:
                step = self.speed
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
            else:
                self.waypoints.pop(0)