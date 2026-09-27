# serialization.py
import math
import pygame
from config import *
from unit import Unit, Bullet
from outpost import Outpost
from warehouse import Warehouse
from supply import SupplyBase
from convoy import SupplyConvoy
from dragon_teeth import DragonTeeth
from mine import Mine
from headquarters import Headquarters


SNAPSHOT_INTERVAL_MS = 50


def _encode_team_grid(grid):
    if grid is None:
        return None
    out = []
    for row in grid:
        chars = []
        for c in row:
            if c == 'red':
                chars.append('r')
            elif c == 'blue':
                chars.append('b')
            elif c == 'neutral':
                chars.append('n')
            else:
                chars.append('.')
        out.append(''.join(chars))
    return out


def _decode_team_grid(str_list):
    if not str_list:
        return None
    grid = []
    for row_str in str_list:
        row = []
        for ch in row_str:
            if ch == 'r':
                row.append('red')
            elif ch == 'b':
                row.append('blue')
            elif ch == 'n':
                row.append('neutral')
            else:
                row.append(None)
        grid.append(row)
    return grid


def _rebuild_territory(team_grid):
    if not team_grid:
        return None, []
    rows = len(team_grid)
    cols = len(team_grid[0]) if rows > 0 else 0

    zone_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for row in range(rows):
        for col in range(cols):
            team = team_grid[row][col]
            if team == 'red':
                color = (200, 0, 0, 80)
            elif team == 'blue':
                color = (0, 0, 200, 80)
            elif team == 'neutral':
                color = NEUTRAL_COLOR
            else:
                continue
            rect = pygame.Rect(col * INFLUENCE_CELL_SIZE,
                               row * INFLUENCE_CELL_SIZE,
                               INFLUENCE_CELL_SIZE,
                               INFLUENCE_CELL_SIZE)
            pygame.draw.rect(zone_surf, color, rect)

    frontline_lines = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            cur = team_grid[row][col]
            right = team_grid[row][col + 1]
            down = team_grid[row + 1][col]

            x1 = col * INFLUENCE_CELL_SIZE
            y1 = row * INFLUENCE_CELL_SIZE
            x2 = (col + 1) * INFLUENCE_CELL_SIZE
            y2 = (row + 1) * INFLUENCE_CELL_SIZE

            def border(a, b):
                if a is None or b is None or a == b:
                    return False
                return (a, b) in (
                    ('red', 'blue'), ('blue', 'red'),
                    ('red', 'neutral'), ('neutral', 'red'),
                    ('blue', 'neutral'), ('neutral', 'blue'),
                )

            if border(cur, right):
                frontline_lines.append((x2, y1, x2, y2))
            if border(cur, down):
                frontline_lines.append((x1, y2, x2, y2))

    return zone_surf, frontline_lines


def _serialize_unit(u):
    data = {
        'id': u.id,
        'x': u.x, 'y': u.y,
        'team': u.team,
        'type': u.unit_type,
        'hp': u.hp,
        'max_hp': u.max_hp,
        'current_defense': getattr(u, 'current_defense', 0.0),
        'encircled': getattr(u, 'encircled', False),
        'fed_by_city': getattr(u, 'fed_by_city', False),
    }
    if getattr(u, 'can_dig_in', False):
        data['entrenchment'] = u.entrenchment
        data['hold_position'] = u.hold_position
    if getattr(u, 'unit_type', None) == 'engineer':
        data['work_progress'] = getattr(u, 'work_progress', 0.0)
        data['has_task'] = bool(getattr(u, 'engineer_task', None))
    if getattr(u, 'unit_type', None) == 'artillery':
        data['artillery_explosions'] = [list(e) for e in getattr(u, 'artillery_explosions', [])]
        data['artillery_state'] = getattr(u, 'artillery_state', 'idle')
    return data


def serialize_world(world):
    # Units
    units = []
    for u in world.red_units + world.blue_units:
        if u.hp > 0:
            units.append(_serialize_unit(u))

    # Outposts
    outposts = []
    for o in world.outposts_red + world.outposts_blue:
        if o.hp <= 0:
            continue
        outposts.append({
            'id': o.id,
            'x': o.x, 'y': o.y,
            'team': o.team,
            'type': getattr(o, 'unit_type', 'outpost'),
            'hp': o.hp, 'max_hp': o.max_hp,
            'supply_hp': getattr(o, 'supply_hp', 0.0),
            'current_defense': getattr(o, 'current_defense', 0.0),
        })

    # Convoys
    convoys = []
    for c in world.red_convoys + world.blue_convoys:
        if c.hp <= 0:
            continue
        convoys.append({
            'id': c.id,
            'x': c.x, 'y': c.y,
            'team': c.team,
            'hp': c.hp, 'max_hp': c.max_hp,
            'cargo': c.cargo,
            'transferring': c.transferring,
            'transfer_timer': c.transfer_timer,
            'transfer_mode': c.transfer_mode,
        })

    # Bases
    bases = []
    for b in [world.red_base, world.blue_base]:
        if b is None:
            continue
        bases.append({
            'team': b.team,
            'x': b.x, 'y': b.y,
            'hp': b.hp, 'max_hp': b.max_hp,
            'active': b.active,
            'respawn_timer': b.respawn_timer,
        })

    # Cities
    cities = []
    for i, c in enumerate(world.cities):
        cities.append({
            'index': i,
            'owner': c.owner,
            'supply_hp': c.supply_hp,
            'capture_progress': c.capture_progress,
            'capturing_faction': c.capturing_faction,
            'contested': c.contested,
        })

    # Dragon teeth
    teeth = []
    for t in world.dragon_teeth_red + world.dragon_teeth_blue:
        if t.hp <= 0:
            continue
        teeth.append({
            'id': t.id,
            'x': t.x, 'y': t.y,
            'team': t.team,
            'hp': t.hp,
        })

    # Mines
    mines = []
    for m in world.mines_red + world.mines_blue:
        if getattr(m, 'exploded', False):
            continue
        mines.append({
            'id': m.id,
            'x': m.x, 'y': m.y,
            'team': m.team,
            'discovered': dict(getattr(m, 'discovered', {'red': False, 'blue': False})),
        })

    # Bullets
    bullets = []
    for b in world.bullets:
        bullets.append({
            'start': list(b.start),
            'end': list(b.end),
            'life': b.life,
        })

    # Airstrikes
    airstrikes_data = []
    for a in world.airstrikes:
        if getattr(a, 'finished', False):
            continue
        airstrikes_data.append({
            'team': getattr(a, 'team', 'red'),
            'started': getattr(a, 'started', False),
            'finished': getattr(a, 'finished', False),
            'arrived': getattr(a, 'arrived', False),
            'explosion_timer': getattr(a, 'explosion_timer', 0),
            'target': list(getattr(a, 'target', (0, 0))),
            'position': list(a.get_position()),
            'angle': a.get_angle(),
        })

    # Territory
    territory = None
    tg = getattr(world, 'territory_team_grid', None)
    if tg is not None:
        territory = {'team_grid': _encode_team_grid(tg)}

    # Headquarters
    hq_data = {'red': None, 'blue': None}
    for team, hq in [('red', world.red_hq), ('blue', world.blue_hq)]:
        if hq is not None:
            hq_data[team] = {
                'id': hq.id,
                'x': hq.x, 'y': hq.y,
                'hp': hq.hp, 'max_hp': hq.max_hp,
                'active': hq.active,
                'respawn_timer': hq.respawn_timer,
                'current_defense': getattr(hq, 'current_defense', 0.0),
            }

    # Command Points
    command_points = {
        'red': world.command_points.get('red', 0.0),
        'blue': world.command_points.get('blue', 0.0),
    }

    return {
        'units': units,
        'outposts': outposts,
        'convoys': convoys,
        'bases': bases,
        'cities': cities,
        'dragon_teeth': teeth,
        'mines': mines,
        'bullets': bullets,
        'airstrikes': airstrikes_data,
        'territory': territory,
        'hq': hq_data,
        'command_points': command_points,
    }


def apply_snapshot(world, data):
    now = pygame.time.get_ticks()

    # ---- Units ----
    unit_by_id = {}
    for u in world.red_units + world.blue_units:
        unit_by_id[u.id] = u

    new_red, new_blue = [], []
    for u_data in data.get('units', []):
        u = unit_by_id.get(u_data['id'])
        if u is None:
            u = Unit(u_data['x'], u_data['y'], u_data['team'], u_data['type'])
            u.id = u_data['id']
            u.x = u_data['x']
            u.y = u_data['y']
        else:
            u._net_prev_x = u.x
            u._net_prev_y = u.y
            u._net_target_x = u_data['x']
            u._net_target_y = u_data['y']
            u._net_lerp_start = now
            u._net_lerp_dur = SNAPSHOT_INTERVAL_MS
        u.hp = u_data['hp']
        u.max_hp = u_data['max_hp']
        u.current_defense = u_data.get('current_defense', 0.0)
        if 'entrenchment' in u_data:
            u.entrenchment = u_data['entrenchment']
            u.hold_position = u_data.get('hold_position', False)
        u.encircled = u_data.get('encircled', False)
        u.fed_by_city = u_data.get('fed_by_city', False)
        if u.unit_type == 'engineer':
            u.work_progress = u_data.get('work_progress', 0.0)
            if u_data.get('has_task') and u.engineer_task is None:
                u.engineer_task = {'kind': 'build', 'idx': 0,
                                    'positions': [], 'targets': []}
            elif not u_data.get('has_task'):
                u.engineer_task = None
        if u.unit_type == 'artillery':
            u.artillery_explosions = [tuple(e) for e in u_data.get('artillery_explosions', [])]
            u.artillery_state = u_data.get('artillery_state', 'idle')
        if u.team == 'red':
            new_red.append(u)
        else:
            new_blue.append(u)
    world.red_units = new_red
    world.blue_units = new_blue

    # ---- Outposts ----
    op_by_id = {}
    for o in world.outposts_red + world.outposts_blue:
        op_by_id[o.id] = o
    new_r, new_b = [], []
    for o_data in data.get('outposts', []):
        o = op_by_id.get(o_data['id'])
        if o is None:
            if o_data.get('type') == 'warehouse':
                o = Warehouse(o_data['x'], o_data['y'], o_data['team'])
            else:
                o = Outpost(o_data['x'], o_data['y'], o_data['team'])
            o.id = o_data['id']
        o.x = o_data['x']
        o.y = o_data['y']
        o.hp = o_data['hp']
        o.max_hp = o_data['max_hp']
        o.supply_hp = o_data.get('supply_hp', 0.0)
        o.current_defense = o_data.get('current_defense', 0.0)
        (new_r if o.team == 'red' else new_b).append(o)
    world.outposts_red = new_r
    world.outposts_blue = new_b

    # ---- Convoys ----
    cv_by_id = {}
    for c in world.red_convoys + world.blue_convoys:
        cv_by_id[c.id] = c
    new_r, new_b = [], []
    for c_data in data.get('convoys', []):
        c = cv_by_id.get(c_data['id'])
        if c is None:
            c = SupplyConvoy(c_data['x'], c_data['y'], c_data['team'])
            c.id = c_data['id']
            c.x = c_data['x']
            c.y = c_data['y']
        else:
            c._net_prev_x = c.x
            c._net_prev_y = c.y
            c._net_target_x = c_data['x']
            c._net_target_y = c_data['y']
            c._net_lerp_start = now
            c._net_lerp_dur = SNAPSHOT_INTERVAL_MS
        c.hp = c_data['hp']
        c.max_hp = c_data['max_hp']
        c.cargo = c_data.get('cargo', 0)
        c.transferring = c_data.get('transferring', False)
        c.transfer_timer = c_data.get('transfer_timer', 0)
        c.transfer_mode = c_data.get('transfer_mode', None)
        (new_r if c.team == 'red' else new_b).append(c)
    world.red_convoys = new_r
    world.blue_convoys = new_b

    # ---- Bases ----
    for b_data in data.get('bases', []):
        b = world.red_base if b_data['team'] == 'red' else world.blue_base
        if b is None:
            b = SupplyBase(b_data['x'], b_data['y'], b_data['team'])
            if b_data['team'] == 'red':
                world.red_base = b
            else:
                world.blue_base = b
        b.x = b_data['x']
        b.y = b_data['y']
        b.hp = b_data['hp']
        b.max_hp = b_data['max_hp']
        b.active = b_data['active']
        b.respawn_timer = b_data['respawn_timer']

    # ---- Cities ----
    for c_data in data.get('cities', []):
        idx = c_data['index']
        if idx >= len(world.cities):
            continue
        c = world.cities[idx]
        c.owner = c_data['owner']
        c.supply_hp = c_data['supply_hp']
        c.capture_progress = c_data.get('capture_progress', 0.0)
        c.capturing_faction = c_data.get('capturing_faction', None)
        c.contested = c_data.get('contested', False)

    # ---- Dragon teeth ----
    t_by_id = {}
    for t in world.dragon_teeth_red + world.dragon_teeth_blue:
        t_by_id[t.id] = t
    new_r, new_b = [], []
    for t_data in data.get('dragon_teeth', []):
        t = t_by_id.get(t_data['id'])
        if t is None:
            t = DragonTeeth(t_data['x'], t_data['y'], t_data['team'])
            t.id = t_data['id']
        t.x = t_data['x']
        t.y = t_data['y']
        t.hp = t_data['hp']
        (new_r if t.team == 'red' else new_b).append(t)
    world.dragon_teeth_red = new_r
    world.dragon_teeth_blue = new_b

    # ---- Mines ----
    m_by_id = {}
    for m in world.mines_red + world.mines_blue:
        m_by_id[m.id] = m
    new_r, new_b = [], []
    for m_data in data.get('mines', []):
        m = m_by_id.get(m_data['id'])
        if m is None:
            m = Mine(m_data['x'], m_data['y'], m_data['team'])
            m.id = m_data['id']
        m.x = m_data['x']
        m.y = m_data['y']
        m.discovered = dict(m_data.get('discovered', {'red': False, 'blue': False}))
        (new_r if m.team == 'red' else new_b).append(m)
    world.mines_red = new_r
    world.mines_blue = new_b

    # ---- Bullets ----
    world.bullets = []
    for b_data in data.get('bullets', []):
        b = Bullet(0, 0, 0, 0)
        b.start = tuple(b_data['start'])
        b.end = tuple(b_data['end'])
        b.life = b_data['life']
        world.bullets.append(b)

    # ---- Airstrikes ----
    from game import RemoteAirstrike
    world.airstrikes = [RemoteAirstrike(a) for a in data.get('airstrikes', [])]

    # ---- Territory ----
    territory = data.get('territory')
    if territory and 'team_grid' in territory:
        team_grid = _decode_team_grid(territory['team_grid'])
        if team_grid is not None:
            world.territory_team_grid = team_grid
            zone_surf, frontline_lines = _rebuild_territory(team_grid)
            world.territory_zone_surf = zone_surf
            world.territory_frontline_lines = frontline_lines

    # ---- Headquarters ----
    hq_data = data.get('hq', {})
    for team in ('red', 'blue'):
        hq_src = hq_data.get(team)
        hq_cur = world.red_hq if team == 'red' else world.blue_hq
        if hq_src is None:
            if team == 'red':
                world.red_hq = None
            else:
                world.blue_hq = None
            continue
        if hq_cur is None:
            hq_cur = Headquarters(hq_src['x'], hq_src['y'], team)
            hq_cur.id = hq_src['id']
            if team == 'red':
                world.red_hq = hq_cur
            else:
                world.blue_hq = hq_cur
        hq_cur.x = hq_src['x']
        hq_cur.y = hq_src['y']
        hq_cur.hp = hq_src['hp']
        hq_cur.max_hp = hq_src['max_hp']
        hq_cur.active = hq_src.get('active', True)
        hq_cur.respawn_timer = hq_src.get('respawn_timer', 0)
        hq_cur.current_defense = hq_src.get('current_defense', 0.0)

    # ---- Command Points ----
    cp = data.get('command_points', {})
    if cp:
        world.command_points['red'] = cp.get('red', world.command_points.get('red', 0.0))
        world.command_points['blue'] = cp.get('blue', world.command_points.get('blue', 0.0))


def interpolate_world(world):
    now = pygame.time.get_ticks()

    def _lerp_entity(obj):
        if not hasattr(obj, '_net_target_x'):
            return
        dur = getattr(obj, '_net_lerp_dur', SNAPSHOT_INTERVAL_MS)
        if dur <= 0:
            obj.x = obj._net_target_x
            obj.y = obj._net_target_y
            return
        t = (now - obj._net_lerp_start) / dur
        if t >= 1.0:
            obj.x = obj._net_target_x
            obj.y = obj._net_target_y
            return
        if t < 0.0:
            t = 0.0
        obj.x = obj._net_prev_x + (obj._net_target_x - obj._net_prev_x) * t
        obj.y = obj._net_prev_y + (obj._net_target_y - obj._net_prev_y) * t

    for u in world.red_units + world.blue_units:
        _lerp_entity(u)
    for c in world.red_convoys + world.blue_convoys:
        _lerp_entity(c)