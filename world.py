# world.py
import math
import random
from config import *
from unit import Unit
from city import City
from airstrike import Airstrike
from road import Road
from supply import SupplyBase
from convoy import SupplyConvoy
from terrain import Forest
from outpost import Outpost
from warehouse import Warehouse
from dragon_teeth import DragonTeeth
from mine import Mine
from headquarters import Headquarters
from frontline import compute_influence_grid
from encirclement import compute_reachable, update_encirclement


class World:
    def __init__(self):
        # Базы
        self.red_base = SupplyBase(BORDER_MARGIN, HEIGHT // 2, 'red')
        self.blue_base = SupplyBase(WIDTH - BORDER_MARGIN, HEIGHT // 2, 'blue')

        # Штабы (рядом с базами)
        self.red_hq = Headquarters(
            self.red_base.x + HQ_OFFSET_FROM_BASE_X,
            self.red_base.y + HQ_OFFSET_FROM_BASE_Y,
            'red')
        self.blue_hq = Headquarters(
            self.blue_base.x - HQ_OFFSET_FROM_BASE_X - HQ_WIDTH,
            self.blue_base.y + HQ_OFFSET_FROM_BASE_Y,
            'blue')

        # Юниты (3 пехоты рядом с базой)
        self.red_units = []
        self.blue_units = []
        self._spawn_initial_units()

        # Постройки
        self.outposts_red = []
        self.outposts_blue = []
        self.dragon_teeth_red = []
        self.dragon_teeth_blue = []
        self.mines_red = []
        self.mines_blue = []

        # Конвои
        self.red_convoys = [SupplyConvoy(BORDER_MARGIN + 40, HEIGHT // 2, 'red')]
        self.blue_convoys = [SupplyConvoy(WIDTH - BORDER_MARGIN - 40, HEIGHT // 2, 'blue')]

        # Статика
        self.roads = [Road([(100, 150), (300, 200), (500, 300), (700, 200), (WIDTH - 100, 150)])]
        self.forests = [
            Forest([(200, 150), (300, 100), (400, 150), (350, 250), (250, 250)]),
            Forest([(600, 350), (750, 300), (800, 400), (650, 450)]),
        ]
        self.cities = [
            City(vertices=[(400, 200), (600, 200), (600, 400), (400, 400)], center=(500, 300)),
            City(vertices=[(700, 100), (900, 100), (800, 300)], center=(800, 200)),
        ]

        # Динамика
        self.bullets = []
        self.airstrikes = []

        # Территория (кэш)
        self.territory_team_grid = None
        self.territory_zone_surf = None
        self.territory_frontline_lines = []

        # Очки командования
        self.command_points = {
            'red': COMMAND_POINTS_START,
            'blue': COMMAND_POINTS_START,
        }

    def _spawn_initial_units(self):
        positions_red = [
            (self.red_base.x + 50, self.red_base.y - 40),
            (self.red_base.x + 50, self.red_base.y),
            (self.red_base.x + 50, self.red_base.y + 40),
        ]
        for px, py in positions_red:
            self.red_units.append(Unit(px, py, 'red', 'infantry'))

        positions_blue = [
            (self.blue_base.x - 50, self.blue_base.y - 40),
            (self.blue_base.x - 50, self.blue_base.y),
            (self.blue_base.x - 50, self.blue_base.y + 40),
        ]
        for px, py in positions_blue:
            self.blue_units.append(Unit(px, py, 'blue', 'infantry'))

    # ---------- Ссылки ----------

    def get_player_refs(self, player_team):
        if player_team == 'red':
            return {
                'units': self.red_units,
                'enemy_units': self.blue_units,
                'base': self.red_base,
                'convoys': self.red_convoys,
                'enemy_convoys': self.blue_convoys,
                'outposts': self.outposts_red,
                'enemy_outposts': self.outposts_blue,
                'hq': self.red_hq,
                'enemy_hq': self.blue_hq,
            }
        return {
            'units': self.blue_units,
            'enemy_units': self.red_units,
            'base': self.blue_base,
            'convoys': self.blue_convoys,
            'enemy_convoys': self.red_convoys,
            'outposts': self.outposts_blue,
            'enemy_outposts': self.outposts_red,
            'hq': self.blue_hq,
            'enemy_hq': self.red_hq,
        }

    def deselect_all(self):
        for obj in (self.red_units + self.blue_units +
                    self.red_convoys + self.blue_convoys +
                    self.outposts_red + self.outposts_blue):
            obj.selected = False
        self.red_base.selected = False
        self.blue_base.selected = False
        if self.red_hq:
            self.red_hq.selected = False
        if self.blue_hq:
            self.blue_hq.selected = False

    # ---------- Завершённые работы ----------

    def _process_completed_works(self):
        for unit in self.red_units + self.blue_units:
            if unit.unit_type != 'engineer':
                continue
            if unit.build_complete:
                unit.building = False
                unit.build_complete = False
                x, y = unit.x, unit.y
                btype = getattr(unit, 'building_type', 'outpost')
                obj = None
                if btype == 'outpost':
                    obj = Outpost(x, y, unit.team)
                elif btype == 'warehouse':
                    obj = Warehouse(x, y, unit.team)
                if obj is not None:
                    if unit.team == 'red':
                        self.outposts_red.append(obj)
                    else:
                        self.outposts_blue.append(obj)
                unit.building_type = None

            if unit.just_completed_build:
                btype, px, py = unit.just_completed_build
                if btype == 'dragon_teeth':
                    tooth = DragonTeeth(px, py, unit.team)
                    if unit.team == 'red':
                        self.dragon_teeth_red.append(tooth)
                    else:
                        self.dragon_teeth_blue.append(tooth)
                elif btype == 'mines':
                    m = Mine(px, py, unit.team)
                    if unit.team == 'red':
                        self.mines_red.append(m)
                    else:
                        self.mines_blue.append(m)
                unit.just_completed_build = None

            if unit.just_demolished:
                obj = unit.just_demolished
                for lst in (self.dragon_teeth_red, self.dragon_teeth_blue,
                            self.mines_red, self.mines_blue,
                            self.outposts_red, self.outposts_blue):
                    if obj in lst:
                        lst.remove(obj)
                        break
                unit.just_demolished = None

    def _discover_mines(self):
        for unit in self.red_units + self.blue_units:
            if unit.unit_type != 'engineer':
                continue
            cx = unit.x + UNIT_WIDTH // 2
            cy = unit.y + UNIT_HEIGHT // 2
            for m in self.mines_red + self.mines_blue:
                if m.exploded:
                    continue
                if m.team == unit.team:
                    continue
                if math.hypot(cx - m.x, cy - m.y) <= MINE_DISCOVERY_RADIUS:
                    m.discovered[unit.team] = True

    # ---------- Обновления ----------

    def _update_units(self):
        enemy_supply_for_red = []
        if self.blue_base.active:
            enemy_supply_for_red.append(self.blue_base)
        if self.blue_hq and self.blue_hq.active:
            enemy_supply_for_red.append(self.blue_hq)
        enemy_supply_for_red += self.blue_convoys + self.outposts_blue

        enemy_supply_for_blue = []
        if self.red_base.active:
            enemy_supply_for_blue.append(self.red_base)
        if self.red_hq and self.red_hq.active:
            enemy_supply_for_blue.append(self.red_hq)
        enemy_supply_for_blue += self.red_convoys + self.outposts_red

        all_teeth = self.dragon_teeth_red + self.dragon_teeth_blue

        Unit.apply_damage_and_cleanup(
            self.red_units, self.blue_units, self.bullets,
            enemy_supply_for_red, self.roads, self.cities, self.forests, all_teeth)
        Unit.apply_damage_and_cleanup(
            self.blue_units, self.red_units, self.bullets,
            enemy_supply_for_blue, self.roads, self.cities, self.forests, all_teeth)

    def _update_outposts(self):
        for outpost in self.outposts_red:
            outpost.update(self.blue_units + self.outposts_blue,
                           self.red_units + self.outposts_red,
                           self.bullets, [], self.roads, self.cities, self.forests)
        for outpost in self.outposts_blue:
            outpost.update(self.red_units + self.outposts_red,
                           self.blue_units + self.outposts_blue,
                           self.bullets, [], self.roads, self.cities, self.forests)

    def _update_mines(self):
        for m in self.mines_red + self.mines_blue:
            if m.exploded:
                continue
            if m.arm_timer > 0:
                m.arm_timer -= 1
                continue
            for u in self.red_units + self.blue_units:
                if u.hp <= 0:
                    continue
                if (getattr(u, 'unit_type', None) == 'engineer'
                        and getattr(u, 'engineer_task', None)):
                    continue
                cx = u.x + UNIT_WIDTH // 2
                cy = u.y + UNIT_HEIGHT // 2
                if math.hypot(cx - m.x, cy - m.y) <= MINE_TRIGGER_RADIUS:
                    dmg = random.randint(MINE_DAMAGE_MIN, MINE_DAMAGE_MAX)
                    u.hp -= dmg
                    m.exploded = True
                    break
        self.mines_red = [m for m in self.mines_red if not m.exploded and m.hp > 0]
        self.mines_blue = [m for m in self.mines_blue if not m.exploded and m.hp > 0]

    def _update_headquarters(self):
        """Обновление Штабов: респавн + движение."""
        for team in ('red', 'blue'):
            hq = self.red_hq if team == 'red' else self.blue_hq
            base = self.red_base if team == 'red' else self.blue_base
            if hq is None:
                continue

            # Уничтожен
            if hq.hp <= 0 and hq.active:
                hq.active = False
                hq.selected = False
                hq.waypoints = []
                hq.respawn_timer = HQ_RESPAWN_TIME

            # Респавн
            if not hq.active:
                if base.active:
                    hq.respawn_timer -= 1
                    if hq.respawn_timer <= 0:
                        offset_x = (HQ_OFFSET_FROM_BASE_X if team == 'red'
                                    else -HQ_OFFSET_FROM_BASE_X - HQ_WIDTH)
                        offset_y = HQ_OFFSET_FROM_BASE_Y
                        hq.x = base.x + offset_x
                        hq.y = base.y + offset_y
                        hq.hp = hq.max_hp
                        hq.active = True
                        hq.waypoints = []
                continue

            # Активный — обновляем (движение, защита)
            allies = self.red_units if team == 'red' else self.blue_units
            enemies = self.blue_units if team == 'red' else self.red_units
            hq.update(enemies, allies, self.bullets, [],
                      self.roads, self.cities, self.forests)

    def _update_bases_and_convoys(self):
        red_allies = self.red_units + [self.red_base] + self.red_convoys + self.outposts_red
        if self.red_hq and self.red_hq.active:
            red_allies.append(self.red_hq)
        if not self.red_base.active:
            red_allies = self.red_units + self.red_convoys + self.outposts_red
            if self.red_hq and self.red_hq.active:
                red_allies.append(self.red_hq)

        blue_allies = self.blue_units + [self.blue_base] + self.blue_convoys + self.outposts_blue
        if self.blue_hq and self.blue_hq.active:
            blue_allies.append(self.blue_hq)
        if not self.blue_base.active:
            blue_allies = self.blue_units + self.blue_convoys + self.outposts_blue
            if self.blue_hq and self.blue_hq.active:
                blue_allies.append(self.blue_hq)

        self.red_base.update(None, red_allies, self.bullets)
        self.blue_base.update(None, blue_allies, self.bullets)

        for convoy in self.red_convoys[:]:
            if convoy.hp > 0:
                convoy.update(red_allies, self.bullets)
            else:
                self.red_convoys.remove(convoy)
        for convoy in self.blue_convoys[:]:
            if convoy.hp > 0:
                convoy.update(blue_allies, self.bullets)
            else:
                self.blue_convoys.remove(convoy)

    def _update_supply_and_influence(self):
        City.update_supply_chain(self.cities, self.roads, self.red_base, self.blue_base,
                                 red_units=self.red_units, blue_units=self.blue_units,
                                 outposts_red=self.outposts_red,
                                 outposts_blue=self.outposts_blue)

        zone_surf, frontline_lines, influence_grid, team_grid = compute_influence_grid(
            self.red_units, self.blue_units, self.cities,
            self.red_base, self.blue_base,
            self.outposts_red, self.outposts_blue
        )
        for city in self.cities:
            city.update(self.red_units, self.blue_units, influence_grid,
                        self.outposts_red, self.outposts_blue)

        self.territory_team_grid = team_grid
        self.territory_zone_surf = zone_surf
        self.territory_frontline_lines = frontline_lines

        return zone_surf, frontline_lines, influence_grid, team_grid

    def _compute_territory_percent(self, team):
        grid = self.territory_team_grid
        if not grid:
            return 0.0
        red_count = 0
        blue_count = 0
        for row in grid:
            for cell in row:
                if cell == 'red':
                    red_count += 1
                elif cell == 'blue':
                    blue_count += 1
        total = red_count + blue_count
        if total == 0:
            return 0.0
        if team == 'red':
            return (red_count / total) * 100.0
        return (blue_count / total) * 100.0

    def _update_command_points(self):
        for team in ('red', 'blue'):
            territory_pct = self._compute_territory_percent(team)
            units = self.red_units if team == 'red' else self.blue_units
            unit_count = len(units)
            base = CP_BASE_RATE
            territory_bonus = (territory_pct / 100.0) * CP_TERRITORY_BONUS
            penalty = min(CP_UNIT_PENALTY_MAX, unit_count * CP_UNIT_PENALTY_PER)
            rate = (base + territory_bonus) * (1.0 - penalty)
            self.command_points[team] = min(
                COMMAND_POINTS_MAX,
                self.command_points[team] + rate
            )

    def _regenerate_logistics(self):
        for unit in self.red_units + self.blue_units:
            if unit.unit_type != 'engineer':
                continue
            if unit.logistics >= unit.max_logistics:
                continue
            cx = unit.x + UNIT_WIDTH // 2
            cy = unit.y + UNIT_HEIGHT // 2
            for city in self.cities:
                if city.owner != unit.team:
                    continue
                if city.contested:
                    continue
                if not city.point_in_polygon(cx, cy):
                    continue
                if city.supply_hp <= 0:
                    break
                amount = min(ENGINEER_LOGISTICS_RATE,
                             unit.max_logistics - unit.logistics,
                             city.supply_hp)
                unit.logistics += amount
                city.supply_hp -= amount * ENGINEER_REGEN_COST_PER_POINT
                break

    def _update_encirclement(self, team_grid):
        red_reach = compute_reachable(team_grid, 'red', self.cities,
                                      self.red_base, self.blue_base,
                                      self.outposts_red, self.outposts_blue)
        blue_reach = compute_reachable(team_grid, 'blue', self.cities,
                                       self.red_base, self.blue_base,
                                       self.outposts_red, self.outposts_blue)
        update_encirclement(self.red_units, self.blue_units,
                            red_reach, blue_reach,
                            self.cities, self.red_base, self.blue_base)

    def _update_airstrikes(self, commands):
        if commands.get('add_airstrike') is not None:
            team = commands.get('player_team', 'red')
            self.airstrikes.append(Airstrike(commands['add_airstrike'], team))
        for strike in self.airstrikes[:]:
            strike.update(
                self.red_units + self.blue_units,
                bases=[self.red_base, self.blue_base],
                convoys=self.red_convoys + self.blue_convoys,
                outposts=self.outposts_red + self.outposts_blue
            )
            if strike.finished:
                self.airstrikes.remove(strike)

    def _cleanup(self):
        self.red_units[:] = [u for u in self.red_units if u.hp > 0]
        self.blue_units[:] = [u for u in self.blue_units if u.hp > 0]

        self.outposts_red = [o for o in self.outposts_red if o.hp > 0]
        self.outposts_blue = [o for o in self.outposts_blue if o.hp > 0]
        self.dragon_teeth_red = [t for t in self.dragon_teeth_red if t.hp > 0]
        self.dragon_teeth_blue = [t for t in self.dragon_teeth_blue if t.hp > 0]

        for bullet in self.bullets[:]:
            bullet.life -= 1
            if bullet.life <= 0:
                self.bullets.remove(bullet)

    def _compute_highlight(self):
        highlight = []
        if (self.red_base.active and
                not any(road.intersects_rect(self.red_base.get_rect())
                        for road in self.roads)):
            highlight.append(self.red_base)
        if (self.blue_base.active and
                not any(road.intersects_rect(self.blue_base.get_rect())
                        for road in self.roads)):
            highlight.append(self.blue_base)
        return highlight

    # ---------- Покупка юнита ----------

    def buy_unit(self, team, unit_type):
        cost = UNIT_COSTS.get(unit_type, 0)
        if cost <= 0:
            return False
        if self.command_points.get(team, 0) < cost:
            return False
        base = self.red_base if team == 'red' else self.blue_base
        if not base.active:
            return False

        self.command_points[team] -= cost

        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(SPAWN_RADIUS_MIN, SPAWN_RADIUS_MAX)
        cx = base.x + base.width // 2
        cy = base.y + base.height // 2
        x = cx + math.cos(angle) * dist - UNIT_WIDTH // 2
        y = cy + math.sin(angle) * dist - UNIT_HEIGHT // 2
        x = max(10, min(WIDTH - UNIT_WIDTH - 10, x))
        y = max(10, min(HEIGHT - UNIT_HEIGHT - 10, y))

        new_unit = Unit(x, y, team, unit_type)
        if team == 'red':
            self.red_units.append(new_unit)
        else:
            self.blue_units.append(new_unit)
        return True

    # ---------- Апдейт ----------

    def update(self, commands):
        self._process_completed_works()
        self._discover_mines()

        self._update_units()
        self._update_headquarters()
        self._update_outposts()
        self._update_mines()
        self._update_bases_and_convoys()

        zone_surf, frontline_lines, influence_grid, team_grid = \
            self._update_supply_and_influence()

        self._update_command_points()
        self._regenerate_logistics()
        self._update_encirclement(team_grid)
        self._update_airstrikes(commands)
        self._cleanup()

        highlight = self._compute_highlight()

        return {
            'zone_surf': zone_surf,
            'frontline_lines': frontline_lines,
            'influence_grid': influence_grid,
            'highlight': highlight,
        }