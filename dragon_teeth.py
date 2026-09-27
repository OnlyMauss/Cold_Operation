# dragon_teeth.py
import pygame
from config import *
from id_gen import next_id

class DragonTeeth:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.unit_type = 'dragon_teeth'
        self.max_hp = DRAGON_TEETH_HP
        self.hp = self.max_hp
        self.width = DRAGON_TEETH_RADIUS * 2
        self.height = DRAGON_TEETH_RADIUS * 2
        self.selected = False
        self.current_defense = 0.0
        self.attack_range = 0
        self.attack_damage = 0
        self.can_attack = False
        self.attack_cooldown = 0

    def get_rect(self):
        return pygame.Rect(self.x - DRAGON_TEETH_RADIUS,
                           self.y - DRAGON_TEETH_RADIUS,
                           DRAGON_TEETH_RADIUS * 2,
                           DRAGON_TEETH_RADIUS * 2)

    def update(self, *args, **kwargs):
        # Зубья не атакуют и не двигаются.
        pass