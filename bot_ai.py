# bot_ai.py
import math
import random
import pygame
from config import *


class BotAI:
    def __init__(self, world, team, difficulty='sergeant'):
        self.world = world
        self.team = team
        self.difficulty = difficulty

        self.tick_counter = 0
        self.economy_counter = 0
        self.engineer_counter = 0
        self.convoy_counter = 0
        self.supply_counter = 0
        self.fire_counter = 0
        self.analyze_counter = 0
        self.probe_counter = 0

        if difficulty == 'sergeant':
            self.tick_interval = 30
            self.economy_interval = 90
            self.engineer_interval = 180
            self.convoy_interval = 90
            self.supply_interval = 60
            self.fire_interval = 20
            self.analyze_interval = 240
            self.probe_interval = 180
            self.max_units = 12
            self.cp_bonus = 1.05
            self.squad_size = 3
            self.garrison_size = 1
            self.attack_advantage = 1.7
            self.defense_trigger = 80
            self.heal_threshold = 0.6
            self.heal_full = 0.9
            self.use_artillery = False
            self.engineer_limit = 2
            self.frontline_push_bonus = 1.2
            self.num_flankers = 2
            self.num_line_holders = 3
            self.flank_retreat_ratio = 1.5
            self.base_threat_radius = 300
            self.retreat_ratio = 1.7
        else:
            self.tick_interval = 20
            self.economy_interval = 60
            self.engineer_interval = 120
            self.convoy_interval = 60
            self.supply_interval = 45
            self.fire_interval = 15
            self.analyze_interval = 180
            self.probe_interval = 150
            self.max_units = 20
            self.cp_bonus = 1.15
            self.squad_size = 4
            self.garrison_size = 2
            self.attack_advantage = 1.5
            self.defense_trigger = 100
            self.heal_threshold = 0.55
            self.heal_full = 0.9
            self.use_artillery = True
            self.engineer_limit = 3
            self.frontline_push_bonus = 1.15
            self.num_flankers = 3
            self.num_line_holders = 5
            self.flank_retreat_ratio = 1.5
            self.base_threat_radius = 400
            self.retreat_ratio = 1.6

        self.garrison_units = set()
        self.healing_units = set()
        self.engineer_built = 0
        self._last_hp = {}
        self._base_connected = False
        self.role_map = {}

        # НОВОЕ:
        self.start_time = None
        self.phase = 'build'          # 'build' | 'pressure' | 'push'
        self.enemy_profile = {
            'infantry': 0, 'motorized': 0, 'tank': 0,
            'artillery': 0, 'engineer': 0, 'total': 0,
        }
        self.probe_active = False
        self.probe_unit_id = None
        self.probe_start_time = 0
        self.probe_result = None

    # ---------- Утилиты ----------

    def _my_units(self):
        return self.world.red_units if self.team == 'red' else self.world.blue_units

    def _enemy_units(self):
        return self.world.blue_units if self.team == 'red' else self.world.red_units

    def _my_base(self):
        return self.world.red_base if self.team == 'red' else self.world.blue_base

    def _enemy_base(self):
        return self.world.blue_base if self.team == 'red' else self.world.red_base

    def _my_cities(self):
        return [c for c in self.world.cities if c.owner == self.team]

    def _enemy_cities(self):
        return [c for c in self.world.cities
                if c.owner is not None and c.owner != self.team]

    def _neutral_cities(self):
        return [c for c in self.world.cities if c.owner is None]

    def _my_outposts(self):
        return self.world.outposts_red if self.team == 'red' else self.world.outposts_blue

    def _my_convoys(self):
        return self.world.red_convoys if self.team == 'red' else self.world.blue_convoys

    @staticmethod
    def _unit_power(u):
        if u.hp <= 0:
            return 0.0
        dps = 0.0
        if u.attack_cooldown_max > 0:
            dps = u.attack_damage * FPS / u.attack_cooldown_max
        p = dps * 4.0 + u.max_hp * 0.08
        if u.unit_type == 'tank':
            p *= 1.6
        elif u.unit_type == 'artillery':
            p *= 1.5
        elif u.unit_type == 'engineer':
            p *= 0.5
        p *= (u.hp / u.max_hp)
        return p

    def _force_of(self, units):
        return sum(self._unit_power(u) for u in units)

    def _is_encircled(self, u):
        return getattr(u, 'encircled', False)

    def _city_is_cut(self, city):
        if self.team == 'red':
            return city.distance_red >= 9999
        return city.distance_blue >= 9999

    def _elapsed(self):
        if self.start_time is None:
            return 0.0
        return (pygame.time.get_ticks() - self.start_time) / 1000.0

    # ---------- Главный тик ----------

    def update(self):
        if self.start_time is None:
            self.start_time = pygame.time.get_ticks()

        self.tick_counter += 1
        if self.tick_counter < self.tick_interval:
            return
        self.tick_counter = 0

        self._update_phase()
        self._apply_cp_bonus()

        self.supply_counter += 1
        if self.supply_counter >= max(1, self.supply_interval // self.tick_interval):
            self.supply_counter = 0
            self._move_supply_base()

        self.economy_counter += 1
        if self.economy_counter >= max(1, self.economy_interval // self.tick_interval):
            self.economy_counter = 0
            self._update_economy()

        self.engineer_counter += 1
        if self.engineer_counter >= max(1, self.engineer_interval // self.tick_interval):
            self.engineer_counter = 0
            self._update_engineer()

        self.convoy_counter += 1
        if self.convoy_counter >= max(1, self.convoy_interval // self.tick_interval):
            self.convoy_counter = 0
            self._update_convoys()

        self.analyze_counter += 1
        if self.analyze_counter >= max(1, self.analyze_interval // self.tick_interval):
            self.analyze_counter = 0
            self._analyze_player_composition()

        self.probe_counter += 1
        if self.probe_counter >= max(1, self.probe_interval // self.tick_interval):
            self.probe_counter = 0
            if not self.probe_active and self.phase != 'build':
                self._start_probe()

        self.fire_counter += 1
        if self.fire_counter >= max(1, self.fire_interval // self.tick_interval):
            self.fire_counter = 0
            self._handle_under_fire()

        self._handle_probe()
        self._handle_encircled()
        self._handle_healing()
        self._handle_retreat_from_lost_battle()

        frontline = self._frontline_analysis()
        threats = self._threats()
        self._assign_roles(frontline, threats)
        self._execute_garrisons()
        self._execute_flanks(frontline, threats)
        self._execute_line_holders(frontline, threats)
        self._execute_strike(frontline, threats)

    # ---------- Фазы ----------

    def _update_phase(self):
        t = self._elapsed()
        old = self.phase
        if t < 120:
            self.phase = 'build'
        elif t < 360:
            self.phase = 'pressure'
        else:
            self.phase = 'push'

        if old != self.phase:
            # Переход в push — сбрасываем probe
            if self.phase == 'push' and self.probe_active:
                self._cancel_probe()

    # ---------- Анализ состава игрока ----------

    def _analyze_player_composition(self):
        enemies = [e for e in self._enemy_units() if e.hp > 0]
        profile = {
            'infantry': 0, 'motorized': 0, 'tank': 0,
            'artillery': 0, 'engineer': 0, 'total': len(enemies),
        }
        for e in enemies:
            profile[e.unit_type] = profile.get(e.unit_type, 0) + 1

        # Нормируем
        if profile['total'] > 0:
            for k in ('infantry', 'motorized', 'tank', 'artillery', 'engineer'):
                profile[k + '_ratio'] = profile[k] / profile['total']
        else:
            for k in ('infantry', 'motorized', 'tank', 'artillery', 'engineer'):
                profile[k + '_ratio'] = 0.0

        self.enemy_profile = profile

    def _player_dominant(self):
        """Определяет доминирующий тип врага."""
        p = self.enemy_profile
        if p.get('total', 0) < 3:
            return None
        best = None
        best_v = 0.4
        for k in ('tank', 'artillery', 'motorized', 'infantry'):
            v = p.get(k + '_ratio', 0)
            if v > best_v:
                best_v = v
                best = k
        return best

    # ---------- Пробная атака ----------

    def _start_probe(self):
        # Ищем дешёвого свободного юнита
        candidates = [u for u in self._my_units()
                      if u.hp > 0
                      and u.unit_type == 'infantry'
                      and self.role_map.get(id(u)) not in ('garrison', 'flank')
                      and not self._is_encircled(u)]
        if not candidates:
            return
        u = candidates[0]
        self.probe_active = True
        self.probe_unit_id = id(u)
        self.probe_start_time = pygame.time.get_ticks()
        self.probe_result = None

        # Отправляем в сторону базы врага
        enemy_base = self._enemy_base()
        if enemy_base and enemy_base.active:
            u.waypoints = [(enemy_base.x, enemy_base.y)]
        else:
            # Или к ближайшему вражескому городу
            enemies = self._enemy_cities()
            if enemies:
                u.waypoints = [enemies[0].center]

    def _handle_probe(self):
        if not self.probe_active:
            return
        # Ищем нашего разведчика
        probe = None
        for u in self._my_units():
            if id(u) == self.probe_unit_id and u.hp > 0:
                probe = u
                break
        if probe is None:
            # Погиб — фиксируем результат
            self.probe_active = False
            self.probe_unit_id = None
            self.probe_result = 'died'
            return

        elapsed = (pygame.time.get_ticks() - self.probe_start_time) / 1000.0
        if elapsed > 30:
            # Пора отзывать
            base = self._my_base()
            if base and base.active:
                probe.waypoints = [(base.x, base.y)]
            self.probe_active = False
            self.probe_unit_id = None
            self.probe_result = 'returned'

        # Во время probe — оцениваем врагов вокруг
        enemies_near = [e for e in self._enemy_units()
                        if e.hp > 0 and math.hypot(e.x - probe.x, e.y - probe.y) < 250]
        if enemies_near:
            # Фиксируем — где игрок держит войска
            self._last_probe_sighting = (probe.x, probe.y, len(enemies_near))

    def _cancel_probe(self):
        self.probe_active = False
        if self.probe_unit_id is not None:
            for u in self._my_units():
                if id(u) == self.probe_unit_id:
                    base = self._my_base()
                    if base and base.active:
                        u.waypoints = [(base.x, base.y)]
                    break
        self.probe_unit_id = None

    # ---------- Отход из проигранного боя ----------

    def _handle_retreat_from_lost_battle(self):
        """
        Если рядом с нашим юнитом враг в 1.7× сильнее — юнит отходит к базе.
        """
        base = self._my_base()
        if not base or not base.active:
            return
        base_pos = (base.x, base.y)
        enemies = [e for e in self._enemy_units() if e.hp > 0]

        for u in self._my_units():
            if u.hp <= 0:
                continue
            if u.unit_type in ('engineer', 'artillery'):
                continue
            if self.role_map.get(id(u)) in ('garrison', 'healing', 'flank', 'line'):
                # Эти роли не отступают приказом сверху
                continue
            if self._is_encircled(u):
                continue
            if getattr(u, 'building', False) or getattr(u, 'engineer_task', None):
                continue

            # Локальные силы
            near_enemies = [e for e in enemies
                            if math.hypot(e.x - u.x, e.y - u.y) < 200]
            if not near_enemies:
                continue
            en_power = self._force_of(near_enemies)
            my_power = self._unit_power(u)
            if en_power > my_power * self.retreat_ratio:
                u.waypoints = [base_pos]

    # ---------- Экономика ----------

    def _apply_cp_bonus(self):
        seconds = self.tick_interval / FPS
        mult = (self.cp_bonus - 1.0)
        territory_pct = self.world._compute_territory_percent(self.team)
        terr_mult = (territory_pct / 100.0) * 0.3
        extra_per_sec = CP_BASE_RATE * FPS * (mult + terr_mult)
        bonus = extra_per_sec * seconds
        self.world.command_points[self.team] = min(
            COMMAND_POINTS_MAX,
            self.world.command_points[self.team] + bonus
        )

    def _base_connected_to_road(self, base):
        if not base or not base.active:
            return False
        rect = base.get_rect()
        for road in self.world.roads:
            if road.intersects_rect(rect):
                return True
        return False

    def _move_supply_base(self):
        base = self._my_base()
        if not base or not base.active:
            return
        if self._base_connected_to_road(base):
            self._base_connected = True
            return
        self._base_connected = False
        if base.waypoints:
            return
        bx, by = base.x, base.y
        best_point = None
        best_dist = 99999
        for road in self.world.roads:
            for i in range(len(road.vertices) - 1):
                x1, y1 = road.vertices[i]
                x2, y2 = road.vertices[i + 1]
                dx = x2 - x1
                dy = y2 - y1
                if dx == 0 and dy == 0:
                    continue
                t = ((bx - x1) * dx + (by - y1) * dy) / (dx * dx + dy * dy)
                t = max(0, min(1, t))
                px = x1 + t * dx
                py = y1 + t * dy
                d = math.hypot(bx - px, by - py)
                if d < best_dist:
                    best_dist = d
                    best_point = (px, py)
        if best_point and best_dist > 5:
            base.waypoints = [best_point]

    def _update_economy(self):
        units = self._my_units()
        base = self._my_base()
        if not base.active:
            return

        base_bonus = 0 if self._base_connected else -3
        near_base = [e for e in self._enemy_units()
                     if e.hp > 0 and math.hypot(e.x - base.x, e.y - base.y) < 250]
        threat_bonus = 4 if near_base else 0
        # Фаза push — покупаем больше
        phase_bonus = 4 if self.phase == 'push' else 0

        limit = self.max_units + base_bonus + threat_bonus + phase_bonus
        if len(units) >= limit:
            return

        cp = self.world.command_points[self.team]
        unit_type = self._choose_unit_type(cp, units, near_base)
        if unit_type and cp >= UNIT_COSTS[unit_type]:
            self.world.buy_unit(self.team, unit_type)

    def _choose_unit_type(self, cp, units, near_base):
        count = {}
        for u in units:
            count[u.unit_type] = count.get(u.unit_type, 0) + 1
        total = sum(count.values())
        dominant = self._player_dominant()

        # Срочно — враг у базы
        if near_base:
            if cp >= UNIT_COSTS['infantry']:
                return 'infantry'
            return None

        # Фаза build — копим
        if self.phase == 'build':
            targets = [('engineer', 1)]
            if self.difficulty == 'lieutenant':
                targets.append(('motorized', 1))
        elif self.phase == 'pressure':
            targets = [('engineer', 1)]
            if self.difficulty == 'lieutenant':
                targets += [('artillery', 1), ('tank', 2), ('motorized', 3)]
            else:
                targets += [('tank', 1), ('motorized', 2)]
        else:  # push
            if self.difficulty == 'lieutenant':
                targets = [('engineer', 1), ('artillery', 2), ('tank', 3), ('motorized', 4)]
            else:
                targets = [('engineer', 1), ('tank', 2), ('motorized', 3)]

        # Адаптация под игрока
        if dominant == 'tank' and self.use_artillery:
            # Больше артиллерии против танков
            targets = [('engineer', 1), ('artillery', 3)] + [t for t in targets if t[0] != 'artillery']
        elif dominant == 'infantry':
            targets = [('engineer', 1), ('artillery', 2)] + [t for t in targets if t[0] != 'artillery']
        elif dominant == 'artillery':
            # Больше мото против артиллерии (быстрые)
            targets = [('motorized', max(2, count.get('motorized', 0) + 1))] + targets

        for utype, target in targets:
            have = count.get(utype, 0)
            if have >= target:
                continue
            cost = UNIT_COSTS[utype]
            if cp >= cost:
                return utype
            if total >= 3:
                return None

        if cp >= UNIT_COSTS['infantry']:
            return 'infantry'
        return None

    # ---------- Роли ----------

    def _assign_roles(self, frontline, threats):
        units = [u for u in self._my_units() if u.hp > 0]
        alive = {id(u) for u in units}
        self.role_map = {k: v for k, v in self.role_map.items() if k in alive}

        # Инженеры
        for u in units:
            if u.unit_type == 'engineer':
                self.role_map[id(u)] = 'engineer'

        # Лечение
        for u in units:
            if u.unit_type not in ('infantry', 'motorized', 'tank'):
                continue
            uid = id(u)
            hp_ratio = u.hp / u.max_hp
            if self._is_encircled(u):
                continue
            if hp_ratio < self.heal_threshold:
                if self.role_map.get(uid) == 'garrison':
                    continue
                self.role_map[uid] = 'healing'
            elif self.role_map.get(uid) == 'healing' and hp_ratio >= self.heal_full:
                self.role_map[uid] = None

        # Гарнизоны
        my_cities = self._my_cities()
        garrisons_by_city = {c: [] for c in my_cities}
        for u in units:
            if self.role_map.get(id(u)) != 'garrison':
                continue
            for city in my_cities:
                cx, cy = city.center
                if math.hypot(u.x - cx, u.y - cy) < 100:
                    garrisons_by_city[city].append(u)
                    break

        for city in my_cities:
            if self._city_is_cut(city):
                for u in garrisons_by_city[city]:
                    self.role_map[id(u)] = None
                continue
            have = len(garrisons_by_city[city])
            need = self.garrison_size - have
            if need <= 0:
                continue
            cx, cy = city.center
            candidates = [u for u in units
                          if u.unit_type in ('infantry', 'motorized', 'tank')
                          and self.role_map.get(id(u)) in (None, 'strike')
                          and not self._is_encircled(u)
                          and u.hp / u.max_hp >= self.heal_threshold
                          and id(u) != self.probe_unit_id]
            candidates.sort(key=lambda u: math.hypot(u.x - cx, u.y - cy))
            for u in candidates[:need]:
                self.role_map[id(u)] = 'garrison'

        combat = [u for u in units
                  if u.unit_type in ('infantry', 'motorized', 'tank')
                  and self.role_map.get(id(u)) is None
                  and not self._is_encircled(u)
                  and u.hp / u.max_hp >= self.heal_threshold
                  and id(u) != self.probe_unit_id]

        total_combat = len([u for u in units
                            if u.unit_type in ('infantry', 'motorized', 'tank')
                            and not self._is_encircled(u)])
        if total_combat < 6:
            for u in units:
                if self.role_map.get(id(u)) is None:
                    self.role_map[id(u)] = 'strike'
            return

        # Фланкеры
        current_flank = [u for u in units if self.role_map.get(id(u)) == 'flank']
        needed = self.num_flankers - len(current_flank)
        if needed > 0 and frontline.get('our_border'):
            def dist_to_border(u):
                best = 99999
                for (x, y) in frontline['our_border']:
                    d = math.hypot(u.x - x, u.y - y)
                    if d < best:
                        best = d
                return best
            combat.sort(key=dist_to_border)
            for u in combat[:needed]:
                self.role_map[id(u)] = 'flank'
            combat = [u for u in combat if self.role_map.get(id(u)) is None]

        # Линия
        current_line = [u for u in units if self.role_map.get(id(u)) == 'line']
        needed = self.num_line_holders - len(current_line)
        if needed > 0 and frontline.get('our_border'):
            def dist_to_border(u):
                best = 99999
                for (x, y) in frontline['our_border']:
                    d = math.hypot(u.x - x, u.y - y)
                    if d < best:
                        best = d
                return best
            combat.sort(key=dist_to_border)
            for u in combat[:needed]:
                self.role_map[id(u)] = 'line'

        for u in units:
            if self.role_map.get(id(u)) is None:
                self.role_map[id(u)] = 'strike'

    # ---------- Гарнизоны ----------

    def _execute_garrisons(self):
        for u in self._my_units():
            if u.hp <= 0:
                continue
            if self.role_map.get(id(u)) != 'garrison':
                continue
            city = self._nearest_own_city(u)
            if not city:
                continue
            cx, cy = city.center
            if math.hypot(u.x - cx, u.y - cy) > 60:
                if not u.waypoints:
                    u.waypoints = [(cx, cy)]
            else:
                u.waypoints = []

    def _nearest_own_city(self, unit):
        my_cities = self._my_cities()
        if not my_cities:
            return None
        return min(my_cities, key=lambda c: math.hypot(
            c.center[0] - unit.x, c.center[1] - unit.y))

    # ---------- Фланкеры ----------

    def _execute_flanks(self, frontline, threats):
        flankers = [u for u in self._my_units()
                    if self.role_map.get(id(u)) == 'flank' and u.hp > 0]
        if not flankers:
            return
        enemies = [e for e in self._enemy_units() if e.hp > 0]
        base = self._my_base()
        base_pos = (base.x, base.y) if base else (0, 0)
        for u in flankers:
            local_enemies = [e for e in enemies
                             if math.hypot(e.x - u.x, e.y - u.y) < 200]
            local_power = self._force_of(local_enemies)
            my_power = self._unit_power(u)
            if local_power > my_power * self.flank_retreat_ratio:
                self.role_map[id(u)] = 'strike'
                u.waypoints = [base_pos]
                continue
            if frontline.get('our_border'):
                nearest = min(frontline['our_border'],
                              key=lambda p: math.hypot(p[0] - u.x, p[1] - u.y))
                if math.hypot(u.x - nearest[0], u.y - nearest[1]) > 50:
                    if not u.waypoints:
                        u.waypoints = [nearest]
                else:
                    u.waypoints = []

    # ---------- Линия обороны ----------

    def _execute_line_holders(self, frontline, threats):
        line_units = [u for u in self._my_units()
                      if self.role_map.get(id(u)) == 'line' and u.hp > 0]
        if not line_units:
            return
        our_border = frontline.get('our_border', [])
        if not our_border:
            for u in line_units:
                self.role_map[id(u)] = 'strike'
            return

        base = self._my_base()
        base_threatened = False
        base_pos = None
        if base and base.active:
            base_pos = (base.x, base.y)
            for e in self._enemy_units():
                if e.hp <= 0:
                    continue
                if math.hypot(e.x - base.x, e.y - base.y) < self.base_threat_radius:
                    base_threatened = True
                    break

        if base_threatened and base_pos:
            nearest_to_base = min(our_border,
                                   key=lambda p: math.hypot(p[0] - base_pos[0],
                                                             p[1] - base_pos[1]))
            near_ids = set()
            for u in line_units:
                if math.hypot(u.x - nearest_to_base[0],
                              u.y - nearest_to_base[1]) < 120:
                    near_ids.add(id(u))
            need = max(0, 3 - len(near_ids))
            if need > 0:
                others = [u for u in line_units if id(u) not in near_ids]
                others.sort(key=lambda u: math.hypot(u.x - nearest_to_base[0],
                                                      u.y - nearest_to_base[1]))
                for u in others[:need]:
                    u.waypoints = [nearest_to_base]
                line_units = [u for u in line_units if id(u) not in near_ids][need:]

        used = []
        for u in line_units:
            best = None
            best_d = 99999
            for (x, y) in our_border:
                occupied = False
                for (ux, uy) in used:
                    if math.hypot(x - ux, y - uy) < 60:
                        occupied = True
                        break
                if occupied:
                    continue
                d = math.hypot(x - u.x, y - u.y)
                if d < best_d:
                    best_d = d
                    best = (x, y)
            if best is None:
                best = min(our_border,
                           key=lambda p: math.hypot(p[0] - u.x, p[1] - u.y))
            used.append(best)
            dist = math.hypot(u.x - best[0], u.y - best[1])
            if dist > 40:
                if not u.waypoints:
                    u.waypoints = [best]
            else:
                u.waypoints = []

    # ---------- Ударная группа ----------

    def _execute_strike(self, frontline, threats):
        weak_our = frontline.get('weak_our', [])
        weak_enemy = frontline.get('weak_enemy', [])

        strike_units = [u for u in self._my_units()
                        if u.hp > 0
                        and self.role_map.get(id(u)) == 'strike'
                        and not getattr(u, 'building', False)
                        and not getattr(u, 'engineer_task', None)]

        artillery = [u for u in strike_units if u.unit_type == 'artillery']
        combat = [u for u in strike_units if u.unit_type != 'artillery']

        # Артиллерия — поддержка городов или тыл
        self._execute_artillery(artillery)

        if not combat:
            return

        base = self._my_base()
        base_pos = (base.x, base.y) if base else (0, 0)
        handled = set()

        # 1. Угрозы
        if threats:
            for threat in threats[:2]:
                tc = threat['center']
                tp = threat['power']
                defenders_power = self._force_at(tc, 150)
                needed = max(0, tp * 1.4 - defenders_power)
                if needed <= 0:
                    continue
                available = [u for u in combat if id(u) not in handled]
                available.sort(key=lambda u: math.hypot(
                    u.x - tc[0], u.y - tc[1]))
                sent = 0.0
                for u in available:
                    if sent >= needed:
                        break
                    handled.add(id(u))
                    self._send_defend(u, tc)
                    sent += self._unit_power(u)

        # 2. База под угрозой — выравниваем фронт
        if base and base.active:
            base_threatened = any(
                math.hypot(e.x - base.x, e.y - base.y) < self.base_threat_radius
                for e in self._enemy_units() if e.hp > 0
            )
            if base_threatened and frontline.get('our_border'):
                nearest = min(frontline['our_border'],
                              key=lambda p: math.hypot(p[0] - base.x, p[1] - base.y))
                available = [u for u in combat if id(u) not in handled]
                available.sort(key=lambda u: math.hypot(
                    u.x - nearest[0], u.y - nearest[1]))
                for u in available[:3]:
                    handled.add(id(u))
                    self._send_defend(u, nearest)

        # 3. Слабые точки фронта
        if weak_our:
            for (x, y, danger) in weak_our[:2]:
                if danger < 3.0:
                    continue
                available = [u for u in combat if id(u) not in handled]
                if not available:
                    break
                available.sort(key=lambda u: math.hypot(u.x - x, u.y - y))
                for u in available[:2]:
                    handled.add(id(u))
                    self._send_defend(u, (x, y))

        # 4. Атака
        remaining = [u for u in combat if id(u) not in handled]
        if not remaining:
            return

        bx, by = base_pos
        remaining.sort(key=lambda u: math.hypot(u.x - bx, u.y - by))

        squads = []
        while remaining:
            leader = remaining.pop(0)
            group = [leader]
            remaining.sort(key=lambda u: math.hypot(u.x - leader.x, u.y - leader.y))
            while len(group) < self.squad_size and remaining:
                group.append(remaining.pop(0))
            squads.append(group)

        # 5. Цель для всех отрядов — одна (для атаки с двух сторон)
        target_city = self._pick_attack_target(squads, weak_enemy, base_pos)
        if target_city:
            self._execute_multi_squad_attack(squads, target_city, base_pos)
        else:
            for squad in squads:
                self._hold_at(squad, base_pos)

    def _pick_attack_target(self, squads, weak_enemy, base_pos):
        if not squads:
            return None
        # Суммарная сила
        total_force = sum(self._force_of(s) for s in squads)
        candidates = list(self._neutral_cities()) + list(self._enemy_cities())
        best_city = None
        best_score = -1.0
        bx, by = base_pos
        for city in candidates:
            defense = self._city_defense(city)
            required = defense * self.attack_advantage
            if total_force < required:
                continue
            dist = math.hypot(city.center[0] - bx, city.center[1] - by)
            score = (total_force - required) - dist / 200.0
            if score > best_score:
                best_score = score
                best_city = city
        return best_city

    def _execute_multi_squad_attack(self, squads, city, base_pos):
        """
        Атака с двух сторон: если 2+ отряда — заходят с разных углов.
        """
        n_squads = len(squads)
        cx, cy = city.center

        # Углы: при 2 отрядах — 0° и 180°, при 3 — 0°, 120°, 240°
        # Ориентация базы учитывается — первый заходит с нашей стороны
        bx, by = base_pos
        base_angle = math.atan2(by - cy, bx - cx)

        for i, squad in enumerate(squads):
            if n_squads == 1:
                angle = base_angle + math.pi  # с противоположной от базы стороны
            else:
                offset = 2 * math.pi * i / n_squads
                angle = base_angle + offset

            # Точка сбора за 100 px до цели
            spread = 100
            gather_x = cx + math.cos(angle) * spread
            gather_y = cy + math.sin(angle) * spread
            gather_x = max(20, min(WIDTH - 20, gather_x))
            gather_y = max(20, min(HEIGHT - 20, gather_y))

            # Каждый юнит в отряде занимает свою позицию вокруг точки сбора
            n = len(squad)
            for j, u in enumerate(squad):
                if n == 1:
                    px, py = gather_x, gather_y
                else:
                    a2 = 2 * math.pi * j / n
                    px = gather_x + math.cos(a2) * 40
                    py = gather_y + math.sin(a2) * 40
                px = max(20, min(WIDTH - 20, px))
                py = max(20, min(HEIGHT - 20, py))
                if not u.waypoints:
                    u.move_to_path([(px, py)])

    # ---------- Артиллерия ----------

    def _execute_artillery(self, artillery_units):
        """Артиллерия бьёт по скоплениям игрока или по осаждаемым городам."""
        if not artillery_units:
            return
        # Ищем цели: скопления врагов
        enemies = [e for e in self._enemy_units() if e.hp > 0]
        if not enemies:
            for u in artillery_units:
                self._send_artillery(u)
            return

        # Кластеризация врагов: ищем точки с 2+ юнитами рядом
        clusters = []
        for e in enemies:
            found = False
            for c in clusters:
                if math.hypot(c['cx'] - e.x, c['cy'] - e.y) < 80:
                    c['units'].append(e)
                    c['cx'] = sum(u.x for u in c['units']) / len(c['units'])
                    c['cy'] = sum(u.y for u in c['units']) / len(c['units'])
                    found = True
                    break
            if not found:
                clusters.append({'cx': e.x, 'cy': e.y, 'units': [e]})

        # Цель — самый крупный кластер в радиусе
        clusters.sort(key=lambda c: -len(c['units']))
        for u in artillery_units:
            if not u.can_attack and u.unit_type != 'artillery':
                continue
            # Если у артиллерии уже есть цель — не трогаем
            if u.artillery_state in ('preparing', 'firing'):
                continue
            # Ищем кластер в радиусе
            target_cluster = None
            for c in clusters:
                if len(c['units']) >= 2:
                    d = math.hypot(c['cx'] - u.x, c['cy'] - u.y)
                    if d <= u.attack_range:
                        target_cluster = c
                        break
            if target_cluster:
                # Формируем полигон вокруг центра кластера
                cx, cy = target_cluster['cx'], target_cluster['cy']
                area = [
                    (cx - 60, cy - 60), (cx + 60, cy - 60),
                    (cx + 60, cy + 60), (cx - 60, cy + 60),
                ]
                u.set_artillery_target(area)
            else:
                # Нет цели — в тыл
                self._send_artillery(u)

    # ---------- Окружение / обстрел / лечение ----------

    def _handle_encircled(self):
        base = self._my_base()
        if not base:
            return
        base_pos = (base.x, base.y)
        enemies = [e for e in self._enemy_units() if e.hp > 0]
        for u in self._my_units():
            if u.hp <= 0:
                continue
            if not self._is_encircled(u):
                continue
            if getattr(u, 'building', False) or getattr(u, 'engineer_task', None):
                continue
            nearest = None
            nearest_d = 99999
            for e in enemies:
                d = math.hypot(e.x - u.x, e.y - u.y)
                if d < nearest_d:
                    nearest_d = d
                    nearest = e
            if u.unit_type == 'artillery':
                u.waypoints = [base_pos]
                continue
            if nearest and nearest_d <= u.attack_range:
                if not u.waypoints:
                    u.waypoints = [(nearest.x, nearest.y)]
                continue
            if not u.waypoints:
                u.waypoints = [base_pos]

    def _handle_under_fire(self):
        enemies = [e for e in self._enemy_units() if e.hp > 0]
        alive_ids = {id(u) for u in self._my_units() if u.hp > 0}
        self._last_hp = {k: v for k, v in self._last_hp.items() if k in alive_ids}
        for u in self._my_units():
            if u.hp <= 0:
                continue
            if u.unit_type in ('engineer', 'artillery'):
                continue
            if self.role_map.get(id(u)) in ('garrison', 'healing'):
                continue
            if self._is_encircled(u):
                continue
            if getattr(u, 'building', False) or getattr(u, 'engineer_task', None):
                continue
            uid = id(u)
            prev_hp = self._last_hp.get(uid, u.hp)
            self._last_hp[uid] = u.hp
            if prev_hp - u.hp < 2:
                continue
            nearest = None
            nearest_dist = 99999
            for e in enemies:
                d = math.hypot(e.x - u.x, e.y - u.y)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest = e
            if nearest is None:
                continue
            if nearest_dist <= u.attack_range:
                continue
            dx = u.x - nearest.x
            dy = u.y - nearest.y
            dist = math.hypot(dx, dy) or 1
            perp_x = -dy / dist
            perp_y = dx / dist
            side = random.choice([-1, 1])
            new_x = u.x + perp_x * 80 * side + (dx / dist) * 60
            new_y = u.y + perp_y * 80 * side + (dy / dist) * 60
            new_x = max(20, min(WIDTH - 20, new_x))
            new_y = max(20, min(HEIGHT - 20, new_y))
            u.waypoints = [(new_x, new_y)]

    def _handle_healing(self):
        my_cities = self._my_cities()
        my_outposts = self._my_outposts()

        def find_heal_spot(u):
            best = None
            best_dist = 99999
            for city in my_cities:
                if self._city_is_cut(city):
                    continue
                d = math.hypot(u.x - city.center[0], u.y - city.center[1])
                if d < best_dist:
                    best_dist = d
                    best = city.center
            for op in my_outposts:
                if getattr(op, 'unit_type', None) == 'warehouse':
                    continue
                ox = op.x + op.width // 2
                oy = op.y + op.height // 2
                d = math.hypot(u.x - ox, u.y - oy)
                if d < best_dist:
                    best_dist = d
                    best = (ox, oy)
            if best is None:
                base = self._my_base()
                if base and base.active:
                    best = (base.x, base.y)
            return best

        def in_heal_zone(u):
            for city in my_cities:
                if self._city_is_cut(city):
                    continue
                if city.point_in_polygon(u.x, u.y):
                    return True
            for op in my_outposts:
                if getattr(op, 'unit_type', None) == 'warehouse':
                    continue
                ox = op.x + op.width // 2
                oy = op.y + op.height // 2
                if math.hypot(u.x - ox, u.y - oy) < OUTPOST_SUPPLY_RADIUS:
                    return True
            return False

        for u in self._my_units():
            if u.hp <= 0:
                continue
            if self.role_map.get(id(u)) != 'healing':
                continue
            if self._is_encircled(u):
                continue
            if getattr(u, 'building', False) or getattr(u, 'engineer_task', None):
                continue
            if in_heal_zone(u):
                u.waypoints = []
                continue
            spot = find_heal_spot(u)
            if spot and not u.waypoints:
                u.move_to_path([spot])

    # ---------- Конвои ----------

    def _update_convoys(self):
        convoys = self._my_convoys()
        my_cities = self._my_cities()
        if not convoys or not my_cities:
            return
        cities_with_supply = [c for c in my_cities
                              if c.supply_hp > 30 and not self._city_is_cut(c)]
        needy_cities = [c for c in my_cities
                        if c.supply_hp < 80 and not self._city_is_cut(c)]
        for convoy in convoys:
            if convoy.hp <= 0:
                continue
            if getattr(convoy, 'pending_action', False) or \
                    getattr(convoy, 'transferring', False):
                continue
            if convoy.waypoints:
                continue
            if convoy.cargo <= 20:
                if not cities_with_supply:
                    continue
                source = max(cities_with_supply, key=lambda c: c.supply_hp)
                convoy.set_pending_action(source, 'load', 'city')
            else:
                if not needy_cities:
                    continue
                target = min(needy_cities, key=lambda c: c.supply_hp)
                convoy.set_pending_action(target, 'unload', 'city')

    # ---------- Фронт ----------

    def _frontline_analysis(self):
        grid = getattr(self.world, 'territory_team_grid', None)
        if not grid:
            return {'weak_enemy': [], 'weak_our': [],
                    'our_border': [], 'enemy_border': []}
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        cell = INFLUENCE_CELL_SIZE
        our_border = []
        enemy_border = []
        for r in range(rows):
            for c in range(cols):
                here = grid[r][c]
                if here == self.team:
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr][nc] not in (self.team, None):
                                our_border.append(
                                    (c * cell + cell // 2, r * cell + cell // 2))
                                break
                elif here is not None:
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr][nc] == self.team:
                                enemy_border.append(
                                    (c * cell + cell // 2, r * cell + cell // 2))
                                break
        my_units = [u for u in self._my_units() if u.hp > 0]
        enemy_units = [u for u in self._enemy_units() if u.hp > 0]
        weak_enemy = []
        for (x, y) in enemy_border:
            our_p = self._force_of(
                [u for u in my_units if math.hypot(u.x - x, u.y - y) < 150])
            their_p = self._force_of(
                [u for u in enemy_units if math.hypot(u.x - x, u.y - y) < 150])
            if our_p > their_p * self.frontline_push_bonus and our_p > 2.0:
                weak_enemy.append((x, y, our_p - their_p))
        weak_enemy.sort(key=lambda t: -t[2])
        weak_our = []
        for (x, y) in our_border:
            our_p = self._force_of(
                [u for u in my_units if math.hypot(u.x - x, u.y - y) < 150])
            their_p = self._force_of(
                [u for u in enemy_units if math.hypot(u.x - x, u.y - y) < 150])
            if their_p > our_p * 1.3 and their_p > 2.0:
                weak_our.append((x, y, their_p - our_p))
        weak_our.sort(key=lambda t: -t[1])
        return {
            'weak_enemy': weak_enemy,
            'weak_our': weak_our,
            'our_border': our_border,
            'enemy_border': enemy_border,
        }

    def _threats(self):
        threats = []
        enemies = [u for u in self._enemy_units() if u.hp > 0]

        def scan(target, ttype):
            cx = target.center[0] if ttype == 'city' else target.x
            cy = target.center[1] if ttype == 'city' else target.y
            near = [e for e in enemies
                    if math.hypot(e.x - cx, e.y - cy) <= self.defense_trigger * 2]
            if not near:
                return
            threats.append({
                'target': target,
                'type': ttype,
                'enemies': near,
                'power': self._force_of(near),
                'center': (cx, cy),
            })
        for city in self._my_cities():
            scan(city, 'city')
        base = self._my_base()
        if base and base.active:
            scan(base, 'base')
        threats.sort(key=lambda t: -t['power'])
        return threats

    def _defenders_near(self, point, radius):
        cx, cy = point
        return [u for u in self._my_units()
                if u.hp > 0
                and math.hypot(u.x - cx, u.y - cy) <= radius
                and u.unit_type not in ('engineer', 'artillery')]

    def _force_at(self, point, radius=140):
        return self._force_of(self._defenders_near(point, radius))

    def _city_defense(self, city):
        return self._force_at(city.center, 140)

    # ---------- Хелперы движения ----------

    def _send_defend(self, unit, target_center):
        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(20, 60)
        px = target_center[0] + math.cos(angle) * r
        py = target_center[1] + math.sin(angle) * r
        px = max(20, min(WIDTH - 20, px))
        py = max(20, min(HEIGHT - 20, py))
        if math.hypot(unit.x - px, unit.y - py) > 30:
            unit.move_to_path([(px, py)])

    def _send_artillery(self, unit):
        base = self._my_base()
        if not base:
            return
        offset_x = 100 if self.team == 'red' else -100
        px = base.x + offset_x + random.randint(-30, 30)
        py = base.y + random.randint(-40, 40)
        px = max(20, min(WIDTH - 20, px))
        py = max(20, min(HEIGHT - 20, py))
        if math.hypot(unit.x - px, unit.y - py) > 40 and not unit.waypoints:
            unit.move_to_path([(px, py)])

    def _hold_at(self, squad, point, spread=50):
        n = len(squad)
        for i, u in enumerate(squad):
            if n == 1:
                px, py = point
            else:
                angle = 2 * math.pi * i / n
                px = point[0] + math.cos(angle) * spread
                py = point[1] + math.sin(angle) * spread
            px = max(20, min(WIDTH - 20, px))
            py = max(20, min(HEIGHT - 20, py))
            if math.hypot(u.x - px, u.y - py) < 20:
                u.waypoints = []
                continue
            if not u.waypoints:
                u.move_to_path([(px, py)])

    # ---------- Инженер ----------

    def _update_engineer(self):
        if self.engineer_built >= self.engineer_limit:
            return
        eng = None
        for u in self._my_units():
            if u.unit_type == 'engineer' and u.hp > 0:
                if getattr(u, 'building', False) or getattr(u, 'engineer_task', None):
                    continue
                if self._is_encircled(u):
                    continue
                eng = u
                break
        if not eng:
            return

        if eng.logistics < COST_WAREHOUSE:
            target_city = self._nearest_own_city(eng)
            if target_city and not eng.waypoints and not self._city_is_cut(target_city):
                cx, cy = target_city.center
                if math.hypot(eng.x - cx, eng.y - cy) > 30:
                    eng.move_to_path([(cx, cy)])
            return

        base = self._my_base()
        my_cities = [c for c in self._my_cities() if not self._city_is_cut(c)]
        if not base or not my_cities:
            return

        target_city = min(my_cities,
                          key=lambda c: math.hypot(
                              c.center[0] - eng.x, c.center[1] - eng.y))
        bx, by = base.x, base.y
        cx, cy = target_city.center
        mx = (bx + cx) / 2
        my = (by + cy) / 2

        best_point = (mx, my)
        best_dist = 99999
        for road in self.world.roads:
            for i in range(len(road.vertices) - 1):
                x1, y1 = road.vertices[i]
                x2, y2 = road.vertices[i + 1]
                dx = x2 - x1
                dy = y2 - y1
                if dx == 0 and dy == 0:
                    continue
                t = ((mx - x1) * dx + (my - y1) * dy) / (dx * dx + dy * dy)
                t = max(0, min(1, t))
                px = x1 + t * dx
                py = y1 + t * dy
                d = math.hypot(mx - px, my - py)
                if d < best_dist:
                    best_dist = d
                    best_point = (px, py)

        px, py = best_point
        px += random.choice([-40, 40])
        py += random.choice([-40, 40])
        px = max(20, min(WIDTH - 40, px))
        py = max(20, min(HEIGHT - 40, py))

        if math.hypot(eng.x - px, eng.y - py) > 25:
            eng.move_to_path([(px, py)])
            return

        eng.building = True
        eng.build_timer = ENGINEER_BUILD_TIME
        eng.build_complete = False
        eng.building_type = 'warehouse'
        eng.logistics -= COST_WAREHOUSE
        self.engineer_built += 1