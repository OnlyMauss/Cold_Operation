# unit.py
import math
import random
from config import *
from terrain import get_defense, get_speed_multiplier
from road import find_road_path
from id_gen import next_id

class Rect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def colliderect(self, other):
        return (self.x < other.x + other.w and
                self.x + self.w > other.x and
                self.y < other.y + other.h and
                self.y + self.h > other.y)


class Bullet:
    def __init__(self, start_x, start_y, end_x, end_y):
        self.start = (start_x + UNIT_WIDTH // 2, start_y + UNIT_HEIGHT // 2)
        self.end = (end_x + UNIT_WIDTH // 2, end_y + UNIT_HEIGHT // 2)
        self.life = 10


class Unit:
    def __init__(self, x, y, team, unit_type='infantry'):
        self.x = x
        self.y = y
        self.team = team
        self.id = next_id()
        self.unit_type = unit_type

        cfg = UNIT_TYPES[unit_type]
        self.max_hp = cfg['hp']
        self.hp = self.max_hp
        self.speed = cfg['speed']
        self.attack_range = cfg['attack_range']
        self.attack_damage = cfg['attack_damage']
        self.attack_cooldown_max = cfg['attack_cooldown_max']
        self.heal_cost_per_2hp = cfg['heal_cost_per_2hp']

        self.can_attack = (unit_type not in ('engineer', 'artillery'))

        factor = INFLUENCE_UNIT_FACTOR_BY_TYPE.get(unit_type, INFLUENCE_UNIT_FACTOR)
        if self.attack_range > 0:
            self.influence_radius = int(self.attack_range * factor)
        else:
            self.influence_radius = 40

        self.attack_cooldown = 0
        self.selected = False
        self.waypoints = []
        self.current_defense = 0.0
        self.encircled = False
        self.fed_by_city = False

        # Окапывание
        self.entrenchment = 0.0
        self.can_dig_in = (unit_type in DIG_IN_TYPES)
        self.hold_position = False

        # Логистика (инженер)
        self.logistics = 0.0
        self.max_logistics = ENGINEER_MAX_LOGISTICS

        # Инженер — постройка
        self.building = False
        self.build_timer = 0
        self.build_complete = False
        self.building_type = None

        # Задача инженера
        self.engineer_task = None
        self.work_progress = 0.0
        self.just_completed_build = None
        self.just_demolished = None

        # Артиллерия
        self.artillery_state = 'idle'
        self.artillery_timer = 0
        self.artillery_target_area = []
        self.artillery_explosions = []
        self.artillery_shots_remaining = 0
        self.artillery_shot_interval = 1
        self.artillery_shot_timer = 0

    def move_to_path(self, path_points):
        if self.unit_type == 'artillery' and self.artillery_state in ('preparing', 'firing'):
            self.artillery_state = 'idle'
            self.artillery_timer = 0
            self.artillery_target_area = []
            self.artillery_explosions = []
            self.artillery_shots_remaining = 0
            self.artillery_shot_timer = 0
        self.waypoints = path_points[:]
        self.hold_position = False
        if self.unit_type == 'engineer' and self.engineer_task:
            self.engineer_task = None
            self.work_progress = 0.0

    def move_to_road_path(self, target_point, roads):
        if not roads:
            self.waypoints = []
            return
        start = (self.x, self.y)
        path = find_road_path(start, target_point, roads)
        if path:
            if len(path) > 1 and math.hypot(path[0][0] - self.x, path[0][1] - self.y) < 2:
                path.pop(0)
            self.waypoints = path
            self.hold_position = False
            if self.unit_type == 'engineer' and self.engineer_task:
                self.engineer_task = None
                self.work_progress = 0.0
        else:
            self.waypoints = []

    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        near_x = x1 + t * dx
        near_y = y1 + t * dy
        return math.hypot(px - near_x, py - near_y)

    def _near_road(self, roads):
        if not roads:
            return False
        for road in roads:
            for i in range(len(road.vertices) - 1):
                x1, y1 = road.vertices[i]
                x2, y2 = road.vertices[i + 1]
                if self._point_to_segment_distance(self.x, self.y, x1, y1, x2, y2) <= 20:
                    return True
        return False

    def _get_attack_multiplier(self):
        """FIX: +5% урона из окопа (пропорционально уровню окапывания)."""
        if not self.can_dig_in:
            return 1.0
        if self.entrenchment <= 0:
            return 1.0
        return 1.0 + DIG_IN_DAMAGE_BONUS * (self.entrenchment / DIG_IN_MAX_BONUS)

    def set_artillery_target(self, area_points):
        if self.unit_type != 'artillery':
            return False
        if not area_points or len(area_points) < 3:
            return False

        any_inside = False
        for p in area_points:
            if math.hypot(self.x - p[0], self.y - p[1]) <= self.attack_range:
                any_inside = True
                break
        if not any_inside:
            return False

        self.artillery_state = 'idle'
        self.artillery_timer = 0
        self.artillery_target_area = []
        self.artillery_explosions = []
        self.artillery_shots_remaining = 0
        self.artillery_shot_timer = 0

        self.artillery_target_area = area_points
        self.artillery_state = 'preparing'
        cfg = UNIT_TYPES['artillery']
        self.artillery_timer = cfg['prepare_time']
        self.waypoints = []
        return True

    def _point_in_polygon(self, px, py, polygon):
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if py > min(p1y, p2y):
                if py <= max(p1y, p2y):
                    if px <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or px <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def _polygon_area(self, poly):
        area = 0.0
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2.0

    def _update_engineer_task(self, enemies):
        if not self.engineer_task:
            return
        task = self.engineer_task
        kind = task['kind']

        if kind == 'build':
            if task['idx'] >= len(task['positions']):
                self.engineer_task = None
                self.work_progress = 0.0
                return
            pos = task['positions'][task['idx']]
            time_per_obj = BUILD_OBJECT_TIME

            if task.get('type') == 'mines' and 'work_pos' in task:
                eng_target = task['work_pos']
            else:
                eng_target = pos
        else:
            if task['idx'] >= len(task['targets']):
                self.engineer_task = None
                self.work_progress = 0.0
                return
            tgt = task['targets'][task['idx']]
            if getattr(tgt, 'hp', 1) <= 0:
                task['idx'] += 1
                self.work_progress = 0.0
                return
            if hasattr(tgt, 'width') and hasattr(tgt, 'height'):
                pos = (tgt.x + tgt.width // 2, tgt.y + tgt.height // 2)
            else:
                pos = (tgt.x + UNIT_WIDTH // 2, tgt.y + UNIT_HEIGHT // 2)
            eng_target = pos
            time_per_obj = DEMOLISH_TIME

        cx = self.x + UNIT_WIDTH // 2
        cy = self.y + UNIT_HEIGHT // 2
        dist = math.hypot(eng_target[0] - cx, eng_target[1] - cy)

        if dist > ENGINEER_NEAR_DIST:
            self.waypoints = [eng_target]
            self.work_progress = 0.0
            task['stuck_timer'] = task.get('stuck_timer', 0) + 1
            if task['stuck_timer'] > ENGINEER_PATH_TIMEOUT:
                self.logistics = min(self.max_logistics,
                                     self.logistics + task.get('cost', 0))
                self.engineer_task = None
                self.work_progress = 0.0
            return

        self.waypoints = []
        task['stuck_timer'] = 0

        if kind == 'demolish':
            for e in enemies:
                if getattr(e, 'hp', 1) <= 0:
                    continue
                ex = e.x + UNIT_WIDTH // 2
                ey = e.y + UNIT_HEIGHT // 2
                if math.hypot(ex - cx, ey - cy) <= DEMOLISH_ENEMY_PROXIMITY:
                    return

        step = 1.0 / time_per_obj
        self.work_progress += step
        if self.work_progress >= 1.0:
            self.work_progress = 0.0
            if kind == 'build':
                self.just_completed_build = (task['type'], pos[0], pos[1])
            else:
                self.just_demolished = tgt
            task['idx'] += 1
            if task['idx'] >= len(task['positions' if kind == 'build' else 'targets']):
                self.engineer_task = None

    def update(self, enemies, allies, bullets, killed_enemies,
               enemy_bases=None, roads=None, cities=None, forests=None, obstacles=None):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if cities is not None and forests is not None:
            terrain_def = get_defense(self.x, self.y, self.unit_type, cities, forests)
        else:
            terrain_def = 0.0

        if self.artillery_explosions:
            new_explosions = []
            for ex, ey, timer in self.artillery_explosions:
                timer -= 1
                if timer > 0:
                    new_explosions.append((ex, ey, timer))
            self.artillery_explosions = new_explosions

        if self.building:
            self.build_timer -= 1
            if self.build_timer <= 0:
                self.build_timer = 0
                self.build_complete = True
            return

        # Артиллерия
        if self.unit_type == 'artillery':
            if self.artillery_state == 'preparing':
                self.artillery_timer -= 1
                if self.artillery_timer <= 0:
                    self.artillery_state = 'firing'
                    cfg = UNIT_TYPES['artillery']
                    self.artillery_timer = cfg['fire_duration']
                    area = self._polygon_area(self.artillery_target_area)
                    total_shots = max(1, min(30, int(area / 5000)))
                    self.artillery_shots_remaining = total_shots
                    self.artillery_shot_interval = max(1, cfg['fire_duration'] // total_shots)
                    self.artillery_shot_timer = 0
                    self.artillery_explosions = []
            elif self.artillery_state == 'firing':
                self.artillery_timer -= 1

                if self.artillery_shots_remaining > 0:
                    self.artillery_shot_timer -= 1
                    if self.artillery_shot_timer <= 0:
                        self.artillery_shots_remaining -= 1
                        self.artillery_shot_timer = self.artillery_shot_interval

                        xs = [p[0] for p in self.artillery_target_area]
                        ys = [p[1] for p in self.artillery_target_area]
                        minx, maxx = min(xs), max(xs)
                        miny, maxy = min(ys), max(ys)
                        explosion_pos = None
                        for _ in range(50):
                            rx = random.uniform(minx, maxx)
                            ry = random.uniform(miny, maxy)
                            if self._point_in_polygon(rx, ry, self.artillery_target_area) and \
                               math.hypot(rx - self.x, ry - self.y) <= self.attack_range:
                                explosion_pos = (rx, ry)
                                break
                        if explosion_pos:
                            self.artillery_explosions.append((explosion_pos[0], explosion_pos[1], 20))

                if self.artillery_timer <= 0:
                    area = self._polygon_area(self.artillery_target_area)
                    cfg = UNIT_TYPES['artillery']
                    max_area = cfg['max_area']
                    base_dmg = cfg['attack_damage']
                    attack_mult = self._get_attack_multiplier()
                    for enemy in enemies:
                        if self._point_in_polygon(enemy.x, enemy.y, self.artillery_target_area):
                            dist_to_enemy = math.hypot(enemy.x - self.x, enemy.y - self.y)
                            if dist_to_enemy > self.attack_range:
                                continue
                            if area > 0:
                                dmg_factor = max(0.2, 1.0 - (area / max_area))
                            else:
                                dmg_factor = 1.0
                            dmg = base_dmg * dmg_factor * random.uniform(0.8, 1.2)
                            if random.random() < 0.2:
                                continue
                            # FIX: артиллерия пробивает 30% защиты
                            target_def = enemy.current_defense if hasattr(enemy, 'current_defense') else 0.0
                            effective_def = target_def * (1 - ARTILLERY_FORTIFICATION_PENETRATION)
                            final_dmg = dmg * (1 - effective_def) * attack_mult
                            enemy.hp -= int(final_dmg)
                            if enemy.hp <= 0 and enemy not in killed_enemies:
                                killed_enemies.append(enemy)
                    self.artillery_state = 'idle'
                    self.artillery_target_area = []
                    self.artillery_shots_remaining = 0
                    self.artillery_shot_timer = 0

        can_move = not (self.unit_type == 'artillery' and self.artillery_state != 'idle')
        moved_this_frame = False

        if can_move:
            if not self.hold_position:
                my_rect = Rect(self.x, self.y, UNIT_WIDTH, UNIT_HEIGHT)
                for ally in allies:
                    if ally is self:
                        continue
                    if getattr(ally, 'hold_position', False):
                        continue
                    ally_rect = Rect(ally.x, ally.y, UNIT_WIDTH, UNIT_HEIGHT)
                    if my_rect.colliderect(ally_rect):
                        dx = self.x - ally.x
                        dy = self.y - ally.y
                        dist = math.hypot(dx, dy)
                        if dist > 0:
                            push_force = 0.8
                            self.x += (dx / dist) * push_force
                            self.y += (dy / dist) * push_force
                            my_rect = Rect(self.x, self.y, UNIT_WIDTH, UNIT_HEIGHT)

            if self.waypoints:
                target_x, target_y = self.waypoints[0]
                dx = target_x - self.x
                dy = target_y - self.y
                distance = math.hypot(dx, dy)
                if distance > 5:
                    if cities is not None and forests is not None:
                        terrain_mult = get_speed_multiplier(self.x, self.y, self.unit_type, cities, forests)
                    else:
                        terrain_mult = 1.0

                    teeth_mult = 1.0
                    if obstacles:
                        my_rect = Rect(self.x, self.y, UNIT_WIDTH, UNIT_HEIGHT)
                        for ob in obstacles:
                            if getattr(ob, 'hp', 1) <= 0:
                                continue
                            if getattr(ob, 'unit_type', None) != 'dragon_teeth':
                                continue
                            ob_rect = Rect(ob.x - DRAGON_TEETH_RADIUS,
                                           ob.y - DRAGON_TEETH_RADIUS,
                                           DRAGON_TEETH_RADIUS * 2,
                                           DRAGON_TEETH_RADIUS * 2)
                            if my_rect.colliderect(ob_rect):
                                if self.unit_type in ('tank', 'motorized'):
                                    teeth_mult = min(teeth_mult, DRAGON_TEETH_SLOW_TANK)
                                else:
                                    teeth_mult = min(teeth_mult, DRAGON_TEETH_SLOW_INFANTRY)

                    current_speed = self.speed * terrain_mult * teeth_mult
                    if roads and self._near_road(roads):
                        current_speed += ROAD_SPEED_BONUS
                    step_x = (dx / distance) * current_speed
                    step_y = (dy / distance) * current_speed
                    self.x += step_x
                    self.y += step_y
                    moved_this_frame = True
                else:
                    self.waypoints.pop(0)

        if self.unit_type == 'engineer' and not self.building:
            self._update_engineer_task(enemies)

        # Окапывание
        if self.can_dig_in and self.hold_position and not moved_this_frame:
            gain = DIG_IN_MAX_BONUS / (DIG_IN_TIME * FPS)
            self.entrenchment = min(DIG_IN_MAX_BONUS, self.entrenchment + gain)
        elif moved_this_frame or not self.hold_position:
            self.entrenchment = 0.0

        self.current_defense = min(MAX_TOTAL_DEFENSE, terrain_def + self.entrenchment)

        if self.can_attack:
            target = None
            min_dist = 9999
            for enemy in enemies:
                dist = math.hypot(self.x - enemy.x, self.y - enemy.y)
                if dist < min_dist:
                    min_dist = dist
                    target = enemy
            if enemy_bases:
                for obj in enemy_bases:
                    if hasattr(obj, 'active') and not obj.active:
                        continue
                    if obj.hp <= 0:
                        continue
                    dist = math.hypot(self.x - obj.x, self.y - obj.y)
                    if dist < min_dist:
                        min_dist = dist
                        target = obj
            if target and min_dist <= self.attack_range and self.attack_cooldown == 0:
                target_def = target.current_defense if hasattr(target, 'current_defense') else 0.0
                attack_mult = self._get_attack_multiplier()
                actual_damage = int(self.attack_damage * (1 - target_def) * attack_mult)
                if actual_damage < 1:
                    actual_damage = 1
                target.hp -= actual_damage
                bullets.append(Bullet(self.x, self.y, target.x, target.y))
                self.attack_cooldown = self.attack_cooldown_max

                if target.hp <= 0:
                    if hasattr(target, 'active'):
                        target.active = False
                        target.respawn_timer = SUPPLY_BASE_RESPAWN_TIME
                        target.waypoints.clear()
                    elif not hasattr(target, 'cargo'):
                        if target not in killed_enemies:
                            killed_enemies.append(target)

    @staticmethod
    def apply_damage_and_cleanup(units, enemies, bullets, enemy_bases=None,
                                  roads=None, cities=None, forests=None, obstacles=None):
        killed = []
        for unit in units[:]:
            unit.update(enemies, units, bullets, killed, enemy_bases, roads, cities, forests, obstacles)
        for dead in killed:
            if dead in enemies:
                enemies.remove(dead)
        for unit in units[:]:
            if unit.hp <= 0:
                units.remove(unit)