# mine.py
from config import *
from id_gen import next_id

class Mine:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.unit_type = 'mine'
        self.hp = 1
        self.max_hp = 1
        self.width = MINE_TRIGGER_RADIUS * 2
        self.height = MINE_TRIGGER_RADIUS * 2
        self.selected = False
        self.current_defense = 0.0
        self.can_attack = False
        self.attack_range = 0
        self.attack_damage = 0
        self.attack_cooldown = 0
        self.arm_timer = MINE_ARM_TIME
        self.exploded = False
        # FIX: этап 5 — обнаружение
        self.discovered = {'red': False, 'blue': False}

    def update(self, *args, **kwargs):
        pass