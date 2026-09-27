# commands.py
import math
import pygame
from config import *
from helpers import point_to_segment_distance


# ---------- Сериализация для сети ----------

WORLD_COMMAND_KEYS = [
    'move_path', 'add_airstrike', 'convoy_unload', 'convoy_load',
    'artillery_fire', 'build', 'stop_units', 'use_road_path',
    'draw_build_line', 'demolish_line', 'cancel_engineer_task', 'toggle_hold',
    'buy_unit',
]

DEFAULT_COMMANDS = {
    'select_units': None,
    'move_path': None,
    'add_airstrike': None,
    'convoy_unload': None,
    'convoy_load': None,
    'build_outpost': False,
    'build': None,
    'stop_units': False,
    'use_road_path': False,
    'artillery_fire': None,
    'action_command': None,
    'draw_build_line': None,
    'demolish_line': None,
    'cancel_engineer_task': False,
    'toggle_hold': False,
    'buy_unit': None,
}


def has_world_commands(commands):
    for k in ['move_path', 'add_airstrike', 'convoy_unload', 'convoy_load',
              'artillery_fire', 'draw_build_line', 'demolish_line', 'buy_unit']:
        if commands.get(k) is not None:
            return True
    for k in ['stop_units', 'cancel_engineer_task', 'toggle_hold']:
        if commands.get(k):
            return True
    if commands.get('build'):
        return True
    return False


def serialize_client_commands(commands, selected_ids):
    out = {'selected_ids': list(selected_ids), 'commands': {}}
    for k in WORLD_COMMAND_KEYS:
        out['commands'][k] = commands.get(k)
    return out


def deserialize_client_commands(packet):
    src = packet.get('commands', {})
    out = dict(DEFAULT_COMMANDS)
    for k, v in src.items():
        if k in out:
            out[k] = v
    return out


class CommandProcessor:
    def __init__(self, world):
        self.world = world

    def process(self, commands, selectable, player_team):
        commands['player_team'] = player_team
        refs = self.world.get_player_refs(player_team)
        self._apply_selection(commands, selectable)
        self._apply_stop(commands, selectable)
        self._apply_cancel_task(commands, refs)
        self._apply_move(commands, selectable)
        self._apply_convoy_transfer(commands, refs)
        self._apply_artillery_fire(commands, refs)
        self._apply_build_line(commands, refs)
        self._apply_demolish_line(commands, refs)
        self._apply_build_single(commands, refs)
        self._apply_toggle_hold(commands, refs)
        self._apply_buy_unit(commands, player_team)

    # ---------- Обработчики ----------

    def _apply_selection(self, commands, selectable):
        if commands.get('select_units') is not None:
            for obj in selectable:
                obj.selected = False
            for obj in commands['select_units']:
                obj.selected = True

    def _apply_stop(self, commands, selectable):
        if not commands.get('stop_units'):
            return
        for obj in selectable:
            if not obj.selected:
                continue
            obj.waypoints = []
            if hasattr(obj, 'pending_action'):
                obj.pending_action = False
                obj.action_target = None
            if getattr(obj, 'unit_type', None) == 'engineer':
                obj.engineer_task = None
                obj.work_progress = 0.0

    def _apply_cancel_task(self, commands, refs):
        if not commands.get('cancel_engineer_task'):
            return
        for obj in refs['units']:
            if getattr(obj, 'unit_type', None) == 'engineer' and obj.selected:
                if obj.engineer_task:
                    cost = obj.engineer_task.get('cost', 0)
                    obj.logistics = min(obj.max_logistics, obj.logistics + cost)
                obj.engineer_task = None
                obj.work_progress = 0.0

    def _apply_toggle_hold(self, commands, refs):
        if not commands.get('toggle_hold'):
            return
        for u in refs['units']:
            if u.selected and getattr(u, 'can_dig_in', False):
                u.hold_position = not u.hold_position
                if u.hold_position:
                    u.waypoints = []
                break

    def _apply_buy_unit(self, commands, team):
        unit_type = commands.get('buy_unit')
        if not unit_type:
            return
        self.world.buy_unit(team, unit_type)

    def _apply_move(self, commands, selectable):
        if commands.get('move_path') is None:
            return
        path = commands['move_path']
        use_road = commands.get('use_road_path', False)
        for obj in selectable:
            if not obj.selected:
                continue
            if getattr(obj, 'unit_type', None) in ('outpost', 'warehouse'):
                continue
            if hasattr(obj, 'transferring') and obj.transferring:
                continue
            if hasattr(obj, 'speed') and obj.speed <= 0:
                continue
            if use_road and hasattr(obj, 'move_to_road_path'):
                obj.move_to_road_path(path[-1], self.world.roads)
            else:
                obj.move_to_path(path)

    def _apply_convoy_transfer(self, commands, refs):
        if commands.get('convoy_unload') is None and commands.get('convoy_load') is None:
            return
        mx, my = (commands['convoy_unload'] if commands['convoy_unload']
                  else commands['convoy_load'])
        mode = 'unload' if commands['convoy_unload'] else 'load'

        target = None
        target_type = None
        for outpost in self.world.outposts_red + self.world.outposts_blue:
            rect = pygame.Rect(outpost.x, outpost.y, outpost.width, outpost.height)
            if rect.inflate(40, 40).collidepoint(mx, my):
                target = outpost
                target_type = 'outpost'
                break
        if not target:
            for city in self.world.cities:
                if city.point_in_polygon(mx, my):
                    target = city
                    target_type = 'city'
                    break
        if not target and mode == 'unload':
            for unit in refs['units']:
                if unit.unit_type != 'engineer':
                    continue
                rect = pygame.Rect(unit.x, unit.y, UNIT_WIDTH, UNIT_HEIGHT)
                if rect.inflate(20, 20).collidepoint(mx, my):
                    target = unit
                    target_type = 'engineer'
                    break

        selected_convoy = None
        for obj in refs['convoys']:
            if obj.selected:
                selected_convoy = obj
                break
        if not (target and selected_convoy and hasattr(selected_convoy, 'set_pending_action')):
            return

        if target_type == 'outpost' and target.team == selected_convoy.team:
            selected_convoy.set_pending_action(target, mode, target_type)
        elif target_type == 'city' and (target.owner is None or target.owner == selected_convoy.team):
            selected_convoy.set_pending_action(target, mode, target_type)
        elif target_type == 'engineer' and target.team == selected_convoy.team and mode == 'unload':
            selected_convoy.set_pending_action(target, mode, target_type)

    def _apply_artillery_fire(self, commands, refs):
        if commands.get('artillery_fire') is None:
            return
        for unit in refs['units']:
            if unit.unit_type == 'artillery' and unit.selected:
                unit.set_artillery_target(commands['artillery_fire'])
                break

    def _apply_build_line(self, commands, refs):
        if not commands.get('draw_build_line'):
            return
        line_data = commands['draw_build_line']
        btype = line_data['type']
        start = line_data['start']
        end = line_data['end']

        eng = None
        for u in refs['units']:
            if u.selected and u.unit_type == 'engineer' and not u.building:
                eng = u
                break
        if not eng:
            return

        cost = COST_DRAGON_TEETH if btype == 'dragon_teeth' else COST_MINES
        if eng.logistics < cost:
            return

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.hypot(dx, dy)
        spacing = DRAGON_TEETH_SPACING if btype == 'dragon_teeth' else MINE_SPACING
        n = max(1, int(dist // spacing))
        positions = []
        for i in range(n + 1):
            t = i / n if n > 0 else 0
            positions.append((start[0] + dx * t, start[1] + dy * t))

        if btype == 'dragon_teeth':
            valid = []
            for px, py in positions:
                in_city = False
                for city in self.world.cities:
                    if city.point_in_polygon(px, py):
                        in_city = True
                        break
                if not in_city:
                    valid.append((px, py))
            positions = valid

        if not positions:
            return

        mx_l = (start[0] + end[0]) / 2
        my_l = (start[1] + end[1]) / 2
        line_len = math.hypot(dx, dy)
        if line_len > 0:
            perp_x = -dy / line_len
            perp_y = dx / line_len
            ex_e = eng.x + UNIT_WIDTH // 2
            ey_e = eng.y + UNIT_HEIGHT // 2
            if (ex_e - mx_l) * perp_x + (ey_e - my_l) * perp_y < 0:
                perp_x = -perp_x
                perp_y = -perp_y
            work_pos = (mx_l + perp_x * MINE_PLACE_OFFSET,
                        my_l + perp_y * MINE_PLACE_OFFSET)
        else:
            work_pos = (mx_l, my_l)

        ex = eng.x + UNIT_WIDTH // 2
        ey = eng.y + UNIT_HEIGHT // 2
        positions.sort(key=lambda p: math.hypot(p[0] - ex, p[1] - ey))
        eng.logistics -= cost
        eng.engineer_task = {
            'kind': 'build',
            'type': btype,
            'positions': positions,
            'work_pos': work_pos,
            'idx': 0,
            'cost': cost,
            'stuck_timer': 0,
        }
        eng.work_progress = 0.0

    def _apply_demolish_line(self, commands, refs):
        if not commands.get('demolish_line'):
            return
        line_data = commands['demolish_line']
        start = line_data['start']
        end = line_data['end']

        eng = None
        for u in refs['units']:
            if u.selected and u.unit_type == 'engineer' and not u.building:
                eng = u
                break
        if not eng or eng.engineer_task:
            return

        collected = []
        all_objs = (self.world.dragon_teeth_red + self.world.dragon_teeth_blue +
                    self.world.mines_red + self.world.mines_blue +
                    self.world.outposts_red + self.world.outposts_blue)
        for obj in all_objs:
            if getattr(obj, 'unit_type', None) == 'outpost':
                continue
            if hasattr(obj, 'width') and hasattr(obj, 'height'):
                ox = obj.x + obj.width // 2
                oy = obj.y + obj.height // 2
            else:
                ox = obj.x + UNIT_WIDTH // 2
                oy = obj.y + UNIT_HEIGHT // 2
            d = point_to_segment_distance(ox, oy, start[0], start[1], end[0], end[1])
            if d <= DEMOLISH_LINE_PICKUP:
                collected.append(obj)

        if not collected:
            return
        ex = eng.x + UNIT_WIDTH // 2
        ey = eng.y + UNIT_HEIGHT // 2
        collected.sort(key=lambda o: math.hypot(
            (o.x + getattr(o, 'width', UNIT_WIDTH) // 2) - ex,
            (o.y + getattr(o, 'height', UNIT_HEIGHT) // 2) - ey))
        eng.engineer_task = {
            'kind': 'demolish',
            'targets': collected,
            'idx': 0,
            'cost': 0,
            'stuck_timer': 0,
        }
        eng.work_progress = 0.0

    def _apply_build_single(self, commands, refs):
        if not commands.get('build'):
            return
        build_type = commands['build']
        cost_map = {'outpost': COST_OUTPOST, 'warehouse': COST_WAREHOUSE}
        cost = cost_map.get(build_type, 0)

        for unit in refs['units']:
            if not (unit.selected and unit.unit_type == 'engineer' and not unit.building):
                continue
            if unit.logistics < cost:
                break
            unit.building = True
            unit.build_timer = ENGINEER_BUILD_TIME
            unit.build_complete = False
            unit.building_type = build_type
            unit.logistics -= cost
            break