# outpost.py
import math
import pygame
from config import *
from unit import Bullet
from id_gen import next_id

class Outpost:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.unit_type = 'outpost'
        cfg = UNIT_TYPES['outpost']
        self.max_hp = cfg['hp']
        self.hp = self.max_hp
        self.attack_range = cfg['attack_range']
        self.attack_damage = cfg['attack_damage']
        self.attack_cooldown_max = cfg['attack_cooldown_max']
        self.heal_cost_per_2hp = cfg['heal_cost_per_2hp']
        self.supply_capacity = cfg['supply_capacity']
        self.self_heal_rate = cfg['self_heal_rate']

        self.attack_cooldown = 0
        self.selected = False
        self.supply_hp = 0.0
        self.width = UNIT_WIDTH
        self.height = UNIT_HEIGHT
        self.can_attack = True
        self.current_defense = 0.0
        self.influence_radius = int(self.attack_range * INFLUENCE_UNIT_FACTOR)

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def _heal_from_supply(self, target, rate_per_frame, reserve=0.0):
        available = self.supply_hp - reserve
        if available <= 0 or target.hp >= target.max_hp:
            return 0.0
        heal_amount = min(rate_per_frame, target.max_hp - target.hp)
        cost_per_hp = getattr(target, 'heal_cost_per_2hp', 1) / 2.0
        cost = heal_amount * cost_per_hp
        if available >= cost:
            target.hp += heal_amount
            self.supply_hp -= cost
            return heal_amount
        else:
            actual_heal = available / cost_per_hp if cost_per_hp > 0 else 0
            actual_heal = min(actual_heal, target.max_hp - target.hp)
            if actual_heal > 0:
                target.hp += actual_heal
                self.supply_hp -= actual_heal * cost_per_hp
            return actual_heal

    def update(self, enemies, allies, bullets, killed_enemies, roads=None, cities=None, forests=None):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # Самовосстановление
        if self.hp < self.max_hp and self.supply_hp > 0:
            self._heal_from_supply(self, self.self_heal_rate, reserve=0.0)

        # Раздача снабжения союзникам
        if self.supply_hp > OUTPOST_SUPPLY_RESERVE and allies:
            for ally in allies:
                if ally is self:
                    continue
                if getattr(ally, 'unit_type', None) == 'outpost':
                    continue
                if hasattr(ally, 'active') and not ally.active:
                    continue
                if not (hasattr(ally, 'hp') and hasattr(ally, 'max_hp')):
                    continue
                if ally.hp >= ally.max_hp:
                    continue
                dist = math.hypot(self.x - ally.x, self.y - ally.y)
                if dist > OUTPOST_SUPPLY_RADIUS:
                    continue
                if self.supply_hp <= OUTPOST_SUPPLY_RESERVE:
                    break
                self._heal_from_supply(
                    ally,
                    OUTPOST_HEAL_PER_FRAME,
                    reserve=OUTPOST_SUPPLY_RESERVE
                )

        # Защита от местности — по типу 'outpost'
        if cities and forests:
            from terrain import get_defense
            self.current_defense = get_defense(self.x, self.y, 'outpost', cities, forests)
        else:
            self.current_defense = 0.0

        # Атака
        if self.can_attack:
            target = None
            min_dist = 9999
            for enemy in enemies:
                dist = math.hypot(self.x - enemy.x, self.y - enemy.y)
                if dist < min_dist:
                    min_dist = dist
                    target = enemy
            if target and min_dist <= self.attack_range and self.attack_cooldown == 0:
                target_def = target.current_defense if hasattr(target, 'current_defense') else 0.0
                actual_damage = int(self.attack_damage * (1 - target_def))
                if actual_damage < 1:
                    actual_damage = 1
                target.hp -= actual_damage
                self.attack_cooldown = self.attack_cooldown_max
                bullets.append(Bullet(self.x, self.y, target.x, target.y))

                if target.hp <= 0:
                    if not hasattr(target, 'cargo'):
                        if target not in killed_enemies:
                            killed_enemies.append(target)