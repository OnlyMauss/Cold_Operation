# warehouse.py
import pygame
from config import *
from id_gen import next_id

class Warehouse:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.unit_type = 'warehouse'
        self.max_hp = WAREHOUSE_HP
        self.hp = self.max_hp
        self.supply_hp = 0.0
        self.supply_capacity = WAREHOUSE_SUPPLY_CAPACITY
        self.width = WAREHOUSE_WIDTH
        self.height = WAREHOUSE_HEIGHT
        self.selected = False
        self.attack_range = 0
        self.attack_damage = 0
        self.attack_cooldown = 0
        self.can_attack = False
        self.current_defense = 0.0
        self.influence_radius = WAREHOUSE_INFLUENCE_RADIUS

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self, enemies, allies, bullets, killed_enemies,
               roads=None, cities=None, forests=None):
        # Склад не атакует и не лечит. Только считает защиту местности.
        if cities and forests:
            from terrain import get_defense
            self.current_defense = get_defense(self.x, self.y, 'outpost', cities, forests)
        else:
            self.current_defense = 0.0