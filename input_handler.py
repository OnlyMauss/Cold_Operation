# input_handler.py
import math
import pygame
from config import UNIT_WIDTH, UNIT_HEIGHT, MAX_LINE_LENGTH


class InputHandler:
    def __init__(self):
        self.is_selecting = False
        self.selection_start = None
        self.selection_rect = None
        self.is_pathing = False
        self.current_path = []
        self.show_all_paths = False
        self.show_combat_zones = False
        self.show_logistics = False

        self.mode = 'normal'
        self.blue_units = None

        self.shift_held = False
        self.artillery_points = []

        self.line_start = None
        self.line_end = None
        self.line_drawing = False

        self.commands = {
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

    def reset(self):
        self.is_selecting = False
        self.selection_start = None
        self.selection_rect = None
        self.is_pathing = False
        self.current_path = []
        self.mode = 'normal'
        self.artillery_points = []
        self.line_start = None
        self.line_end = None
        self.line_drawing = False
        pygame.mouse.set_visible(True)

    def process_events(self, events, player_units, enemy_units=None, panel=None, action_panel=None):
        self.blue_units = enemy_units
        self.commands = {key: None for key in self.commands}
        self.commands['build_outpost'] = False
        self.commands['cancel_engineer_task'] = False
        self.commands['toggle_hold'] = False
        self.commands['buy_unit'] = None

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    if panel:
                        panel.toggle()
                if event.key == pygame.K_F3:
                    if self.mode != 'airstrike':
                        self.mode = 'airstrike'
                        pygame.mouse.set_visible(False)
                    else:
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                if event.key == pygame.K_F4:
                    self.show_logistics = not self.show_logistics
                if event.key == pygame.K_b:
                    self.commands['build'] = 'outpost'
                if event.key == pygame.K_s:
                    self.commands['stop_units'] = True
                if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    self.shift_held = True
                if event.key == pygame.K_a:
                    if self.mode == 'normal':
                        if any(getattr(u, 'unit_type', None) == 'artillery'
                               and u.selected for u in player_units):
                            self.mode = 'artillery_aim'
                            pygame.mouse.set_visible(False)
                            self.artillery_points = []
                    elif self.mode == 'artillery_aim':
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                if event.key == pygame.K_ESCAPE:
                    if self.mode in ('build_dragon_teeth', 'build_mines', 'demolish'):
                        self.mode = 'normal'
                        self.line_drawing = False
                        self.line_start = None
                        self.line_end = None
                        pygame.mouse.set_visible(True)

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    self.shift_held = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.mode in ('action_load', 'action_unload'):
                    if event.button == 1:
                        if self.mode == 'action_load':
                            self.commands['convoy_load'] = event.pos
                        else:
                            self.commands['convoy_unload'] = event.pos
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                        continue
                    elif event.button == 3:
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                        continue

                if self.mode in ('build_dragon_teeth', 'build_mines', 'demolish'):
                    if event.button == 1:
                        self.line_drawing = True
                        self.line_start = event.pos
                        self.line_end = event.pos
                    elif event.button == 3:
                        self.mode = 'normal'
                        self.line_drawing = False
                        self.line_start = None
                        self.line_end = None
                        self.commands['cancel_engineer_task'] = True
                        pygame.mouse.set_visible(True)
                    continue

                if event.button == 1:
                    if self.mode == 'airstrike':
                        self.commands['add_airstrike'] = self._get_target(event.pos)
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                        continue
                    elif self.mode == 'artillery_aim':
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                        continue

                    if action_panel and action_panel.visible:
                        cmd = action_panel.handle_click(*event.pos)
                        if cmd is None:
                            pass
                        elif cmd == 'load':
                            self.mode = 'action_load'
                            action_panel.hide()
                            continue
                        elif cmd == 'unload':
                            self.mode = 'action_unload'
                            action_panel.hide()
                            continue
                        elif cmd == 'artillery_fire':
                            self.mode = 'artillery_aim'
                            pygame.mouse.set_visible(False)
                            action_panel.hide()
                            self.artillery_points = []
                            continue
                        elif cmd == 'toggle_hold':
                            self.commands['toggle_hold'] = True
                            action_panel.hide()
                            continue
                        elif cmd == 'build_outpost':
                            self.commands['build'] = 'outpost'
                            action_panel.hide()
                            continue
                        elif cmd == 'build_warehouse':
                            self.commands['build'] = 'warehouse'
                            action_panel.hide()
                            continue
                        elif cmd == 'build_dragon_teeth':
                            self.mode = 'build_dragon_teeth'
                            self.line_drawing = False
                            self.line_start = None
                            self.line_end = None
                            action_panel.hide()
                            continue
                        elif cmd == 'build_mines':
                            self.mode = 'build_mines'
                            self.line_drawing = False
                            self.line_start = None
                            self.line_end = None
                            action_panel.hide()
                            continue
                        elif cmd == 'demolish':
                            self.mode = 'demolish'
                            self.line_drawing = False
                            self.line_start = None
                            self.line_end = None
                            action_panel.hide()
                            continue
                        elif isinstance(cmd, str) and cmd.startswith('buy:'):
                            unit_type = cmd.split(':', 1)[1]
                            self.commands['buy_unit'] = unit_type
                            continue

                        panel_rect = pygame.Rect(action_panel.x, action_panel.y,
                                                 action_panel.width, action_panel.height)
                        if panel_rect.collidepoint(*event.pos):
                            continue

                    mx, my = event.pos
                    clicked_on_unit = False
                    for unit in player_units:
                        rect = pygame.Rect(unit.x, unit.y, UNIT_WIDTH, UNIT_HEIGHT)
                        if rect.collidepoint(mx, my):
                            self.commands['select_units'] = [unit]
                            clicked_on_unit = True
                            break
                    if not clicked_on_unit:
                        self.commands['select_units'] = []
                        self.is_selecting = True
                        self.selection_start = (mx, my)

                elif event.button == 3:
                    if self.mode == 'artillery_aim':
                        self.is_pathing = True
                        self.current_path = [event.pos]
                    elif self.mode == 'airstrike':
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                    else:
                        if any(unit.selected for unit in player_units):
                            self.is_pathing = True
                            self.current_path = [pygame.mouse.get_pos()]

            if event.type == pygame.MOUSEMOTION:
                if self.line_drawing and self.mode in ('build_dragon_teeth',
                                                        'build_mines', 'demolish'):
                    mx, my = pygame.mouse.get_pos()
                    if self.line_start:
                        dx = mx - self.line_start[0]
                        dy = my - self.line_start[1]
                        dist = math.hypot(dx, dy)
                        if dist > MAX_LINE_LENGTH:
                            scale = MAX_LINE_LENGTH / dist
                            mx = self.line_start[0] + dx * scale
                            my = self.line_start[1] + dy * scale
                    self.line_end = (mx, my)

                if self.is_selecting and self.selection_start:
                    current_pos = pygame.mouse.get_pos()
                    x1, y1 = self.selection_start
                    x2, y2 = current_pos
                    sx, sy = min(x1, x2), min(y1, y2)
                    sw, sh = abs(x1 - x2), abs(y1 - y2)
                    self.selection_rect = pygame.Rect(sx, sy, sw, sh)
                if self.is_pathing:
                    mouse_pos = pygame.mouse.get_pos()
                    if self.mode == 'artillery_aim':
                        if not self.current_path or math.hypot(
                                mouse_pos[0] - self.current_path[-1][0],
                                mouse_pos[1] - self.current_path[-1][1]) > 20:
                            self.current_path.append(mouse_pos)
                    else:
                        if self.current_path and math.hypot(
                                mouse_pos[0] - self.current_path[-1][0],
                                mouse_pos[1] - self.current_path[-1][1]) > 15:
                            self.current_path.append(mouse_pos)

            if event.type == pygame.MOUSEBUTTONUP:
                if self.line_drawing and self.mode in ('build_dragon_teeth',
                                                        'build_mines', 'demolish'):
                    if event.button == 1 and self.line_start and self.line_end:
                        d = math.hypot(self.line_end[0] - self.line_start[0],
                                       self.line_end[1] - self.line_start[1])
                        if d >= 10:
                            if self.mode == 'demolish':
                                self.commands['demolish_line'] = {
                                    'start': self.line_start,
                                    'end': self.line_end,
                                }
                            else:
                                btype = 'dragon_teeth' if self.mode == 'build_dragon_teeth' else 'mines'
                                self.commands['draw_build_line'] = {
                                    'type': btype,
                                    'start': self.line_start,
                                    'end': self.line_end,
                                }
                    self.line_drawing = False
                    self.line_start = None
                    self.line_end = None
                    self.mode = 'normal'
                    pygame.mouse.set_visible(True)
                    continue

                if event.button == 1:
                    self.is_selecting = False
                    if self.selection_rect:
                        selected = []
                        for unit in player_units:
                            rect = pygame.Rect(unit.x, unit.y, UNIT_WIDTH, UNIT_HEIGHT)
                            if self.selection_rect.colliderect(rect):
                                selected.append(unit)
                        if selected:
                            self.commands['select_units'] = selected
                        self.selection_rect = None
                    self.selection_start = None

                elif event.button == 3:
                    if self.mode == 'artillery_aim':
                        if self.current_path and len(self.current_path) >= 3:
                            self.commands['artillery_fire'] = self.current_path
                        self.mode = 'normal'
                        pygame.mouse.set_visible(True)
                        self.is_pathing = False
                        self.current_path = []
                    else:
                        if self.is_pathing:
                            self.is_pathing = False
                            if self.current_path:
                                self.commands['move_path'] = self.current_path
                                self.commands['use_road_path'] = self.shift_held
                                self.current_path = []

        return dict(self.commands)

    def _get_target(self, mouse_pos):
        if self.blue_units:
            for unit in self.blue_units:
                rect = pygame.Rect(unit.x, unit.y, UNIT_WIDTH, UNIT_HEIGHT)
                if rect.collidepoint(mouse_pos):
                    return (unit.x + UNIT_WIDTH // 2, unit.y + UNIT_HEIGHT // 2)
        return mouse_pos