# convoy.py
import math
from config import *
from id_gen import next_id

class SupplyConvoy:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.hp = CONVOY_HP
        self.max_hp = CONVOY_HP
        self.speed = CONVOY_SPEED
        self.selected = False
        self.waypoints = []
        self.cargo = 0
        self.width = UNIT_WIDTH
        self.height = UNIT_HEIGHT
        self.attack_cooldown = 0
        self.can_attack = False

        self.transferring = False
        self.transfer_timer = 0
        self.transfer_target_city = None
        self.transfer_target_outpost = None
        self.transfer_target_engineer = None
        self.transfer_mode = None

        # Автоматическое выполнение действия после движения
        self.pending_action = False
        self.action_target = None
        self.action_mode = None
        self.action_type = None

    def get_rect(self):
        import pygame
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def move_to_path(self, path_points):
        if not self.transferring and not self.pending_action:
            self.waypoints = path_points[:]

    def set_pending_action(self, target, mode, target_type):
        self.pending_action = True
        self.action_target = target
        self.action_mode = mode
        self.action_type = target_type
        if target_type == 'city':
            tx, ty = target.center
        elif target_type == 'engineer':
            tx, ty = target.x + UNIT_WIDTH // 2, target.y + UNIT_HEIGHT // 2
        else:
            tx, ty = target.x + target.width // 2, target.y + target.height // 2
        self.waypoints = [(tx, ty)]

    def update(self, allies, bullets):
        if self.transferring:
            self.transfer_timer -= 1
            if self.transfer_timer <= 0:
                self._finish_transfer()
            return

        if self.pending_action:
            if self.waypoints:
                target_x, target_y = self.waypoints[0]
                dx = target_x - self.x
                dy = target_y - self.y
                distance = math.hypot(dx, dy)
                if distance > 30:
                    step_x = (dx / distance) * self.speed
                    step_y = (dy / distance) * self.speed
                    self.x += step_x
                    self.y += step_y
                else:
                    self.waypoints = []
                    self._start_pending_action()
            else:
                self._start_pending_action()
            return

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

        my_rect = self.get_rect()
        for ally in allies:
            if ally is self:
                continue
            ally_rect = ally.get_rect() if hasattr(ally, 'get_rect') else None
            if ally_rect and my_rect.colliderect(ally_rect):
                dx = self.x - ally.x
                dy = self.y - ally.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    push_force = 0.5
                    self.x += (dx / dist) * push_force
                    self.y += (dy / dist) * push_force
                    my_rect = self.get_rect()

        self.x = max(0, min(WIDTH, self.x))
        self.y = max(0, min(HEIGHT, self.y))

    def _start_pending_action(self):
        ok = False
        if self.action_type == 'city':
            ok = self.start_transfer_city(self.action_target, self.action_mode)
        elif self.action_type == 'engineer':
            ok = self.start_transfer_engineer(self.action_target, self.action_mode)
        else:
            ok = self.start_transfer_outpost(self.action_target, self.action_mode)
        if not ok:
            self.pending_action = False
            self.action_target = None
            self.action_type = None
            self.action_mode = None

    def start_transfer_city(self, city, mode):
        if self.transferring:
            return False
        if mode == 'load':
            if city.supply_hp <= 0 or self.cargo >= CONVOY_CAPACITY:
                return False
        else:
            if self.cargo <= 0:
                return False
        self.transferring = True
        self.transfer_timer = CONVOY_TRANSFER_TIME
        self.transfer_target_city = city
        self.transfer_target_outpost = None
        self.transfer_target_engineer = None
        self.transfer_mode = mode
        self.waypoints = []
        self.pending_action = False
        return True

    def start_transfer_outpost(self, outpost, mode):
        if self.transferring:
            return False
        if mode == 'unload':
            if self.cargo <= 0 or outpost.supply_hp >= outpost.supply_capacity:
                return False
        else:
            if outpost.supply_hp <= 0 or self.cargo >= CONVOY_CAPACITY:
                return False
        self.transferring = True
        self.transfer_timer = CONVOY_TRANSFER_TIME
        self.transfer_target_outpost = outpost
        self.transfer_target_city = None
        self.transfer_target_engineer = None
        self.transfer_mode = mode
        self.waypoints = []
        self.pending_action = False
        return True

    def start_transfer_engineer(self, engineer, mode):
        if self.transferring:
            return False
        if mode != 'unload':
            return False
        if self.cargo <= 0:
            return False
        if engineer.hp <= 0:
            return False
        if engineer.logistics >= engineer.max_logistics:
            return False
        self.transferring = True
        self.transfer_timer = CONVOY_TRANSFER_TIME
        self.transfer_target_engineer = engineer
        self.transfer_target_city = None
        self.transfer_target_outpost = None
        self.transfer_mode = mode
        self.waypoints = []
        self.pending_action = False
        return True

    def _finish_transfer(self):
        if self.transfer_target_city:
            city = self.transfer_target_city
            if self.transfer_mode == 'load':
                amount = int(min(CONVOY_CAPACITY - self.cargo, city.supply_hp, CONVOY_CAPACITY))
                self.cargo += amount
                city.supply_hp -= amount
            else:
                amount = min(self.cargo, CONVOY_CAPACITY)
                self.cargo -= amount
                city.supply_hp += amount
        elif self.transfer_target_outpost:
            outpost = self.transfer_target_outpost
            if self.transfer_mode == 'unload':
                amount = min(self.cargo, outpost.supply_capacity - outpost.supply_hp, CONVOY_CAPACITY)
                self.cargo -= amount
                outpost.supply_hp += amount
            else:
                amount = min(outpost.supply_hp, CONVOY_CAPACITY - self.cargo)
                self.cargo += amount
                outpost.supply_hp -= amount
        elif self.transfer_target_engineer:
            eng = self.transfer_target_engineer
            if eng.hp > 0:
                free = eng.max_logistics - eng.logistics
                amount = min(self.cargo, free, CONVOY_CAPACITY)
                self.cargo -= amount
                eng.logistics += amount
        self.transferring = False
        self.transfer_target_city = None
        self.transfer_target_outpost = None
        self.transfer_target_engineer = None
        self.transfer_mode = None