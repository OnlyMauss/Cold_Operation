# game.py
import pygame
import sys
import os
import time
from config import *
from world import World
from commands import (CommandProcessor, has_world_commands,
                       serialize_client_commands, deserialize_client_commands)
from helpers import build_info_for
from input_handler import InputHandler
from panel import SettingsPanel
from hud_panel import HudPanel
from menu import MenuScreen
from settings_io import load_settings, save_settings
from network import NetworkServer, NetworkClient
from discovery import ServerDiscoveryBroadcaster
from network_menu import NetworkMenu
from side_select import SideSelectScreen
from bot_ai import BotAI
from serialization import serialize_world, apply_snapshot, interpolate_world
from frontline import compute_influence_grid
from airstrike import Airstrike
import renderer


class RemoteAirstrike:
    def __init__(self, data):
        self.team = data.get('team', 'red')
        self.started = data.get('started', False)
        self.finished = data.get('finished', False)
        self.arrived = data.get('arrived', False)
        self.explosion_timer = data.get('explosion_timer', 0)
        self.target = tuple(data.get('target', [0, 0]))
        self._pos = tuple(data.get('position', [0, 0]))
        self._angle = data.get('angle', 0)

    def get_position(self):
        return self._pos

    def get_angle(self):
        return self._angle


class Game:
    def __init__(self):
        pygame.init()
        self.fullscreen = False
        self.screen = None
        self._create_display()

        self.clock = pygame.time.Clock()
        self.running = True

        self.state = 'menu'
        self.menu_view = 'main'
        self.player_team = 'red'

        self.world = World()
        self.command_processor = CommandProcessor(self.world)

        self._load_textures()
        self._init_ui()
        self._init_menus()

        load_settings(self.settings_panel.items)

        # Меню выбора стороны
        self.side_select = SideSelectScreen()

        # Бот
        self.bot_ai = None
        self.bot_team = None
        self.bot_difficulty = None

        # Сетевое
        self.network_menu = NetworkMenu(self)
        self.net_server = None
        self.discovery_broadcaster = None
        self.net_client = None
        self.net_role = None
        self.net_players = []
        self._snapshot_counter = 0
        self.pending_client_commands = []
        self.pending_server_messages = []
        self.selected_ids = set()

        self.winner = None
        self.paused = False
        self.ping_ms = -1
        self.last_ping_send = 0
        self.disconnect_reason = ""

    # ---------- Окно ----------

    def _create_display(self):
        flags = pygame.SCALED
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("COLD OPERATION")

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._create_display()
        ih = self.input_handler
        cursor_visible = ih.mode not in ('airstrike', 'artillery_aim')
        pygame.mouse.set_visible(cursor_visible)
        ih.is_pathing = False
        ih.current_path = []
        ih.is_selecting = False
        ih.selection_rect = None
        ih.selection_start = None
        ih.line_drawing = False
        ih.line_start = None
        ih.line_end = None

    # ---------- Инициализация ----------

    def _load_textures(self):
        self.textures = {
            'infantry_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'red_soldier.png'), RED),
            'infantry_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'blue_soldier.png'), BLUE),
            'motorized_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'motorized_red.png'), RED),
            'motorized_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'motorized_blue.png'), BLUE),
            'tank_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'tank_red.png'), RED),
            'tank_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'tank_blue.png'), BLUE),
            'engineer_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'engineer_red.png'), RED),
            'engineer_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'engineer_blue.png'), BLUE),
            'artillery_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'artillery_red.png'), RED),
            'artillery_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'artillery_blue.png'), BLUE),
            'outpost_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'outpost_red.png'), RED),
            'outpost_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'outpost_blue.png'), BLUE),
            'warehouse_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'warehouse_red.png'), (150, 100, 50)),
            'warehouse_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'warehouse_blue.png'), (50, 100, 150)),
            'supply_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'supply_red.png'), RED),
            'supply_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'supply_blue.png'), BLUE),
            'convoy_red': renderer.load_texture(os.path.join(TEXTURE_DIR, 'convoy_red.png'), RED),
            'convoy_blue': renderer.load_texture(os.path.join(TEXTURE_DIR, 'convoy_blue.png'), BLUE),
            'shield': renderer.load_texture(os.path.join(TEXTURE_DIR, 'shield.png'), YELLOW),
            'artillery_cursor': renderer.load_texture(os.path.join(TEXTURE_DIR, 'artillery_cursor.png'), YELLOW),
            'headquarters_red': renderer.load_texture_hq(
                os.path.join(TEXTURE_DIR, 'headquarters_red.png'), (180, 30, 30)),
            'headquarters_blue': renderer.load_texture_hq(
                os.path.join(TEXTURE_DIR, 'headquarters_blue.png'), (30, 30, 180)),
        }
        self.flag_textures = {
            'neutral': renderer.load_flag_texture(os.path.join(TEXTURE_DIR, 'flag_neutral.png'), (128, 128, 128)),
            'red': renderer.load_flag_texture(os.path.join(TEXTURE_DIR, 'flag_red.png'), RED),
            'blue': renderer.load_flag_texture(os.path.join(TEXTURE_DIR, 'flag_blue.png'), BLUE),
        }
        try:
            self.plane_tex_red = pygame.image.load(
                os.path.join(TEXTURE_DIR, PLANE_TEXTURE_RED)).convert_alpha()
            self.plane_tex_red = pygame.transform.scale(self.plane_tex_red, (40, 20))
        except Exception:
            self.plane_tex_red = pygame.Surface((40, 20))
            self.plane_tex_red.fill(RED)
        try:
            self.plane_tex_blue = pygame.image.load(
                os.path.join(TEXTURE_DIR, PLANE_TEXTURE_BLUE)).convert_alpha()
            self.plane_tex_blue = pygame.transform.scale(self.plane_tex_blue, (40, 20))
        except Exception:
            self.plane_tex_blue = pygame.Surface((40, 20))
            self.plane_tex_blue.fill(BLUE)
        try:
            self.cursor_tex = pygame.image.load(
                os.path.join(TEXTURE_DIR, CURSOR_TEXTURE)).convert_alpha()
            self.cursor_tex = pygame.transform.scale(self.cursor_tex, (32, 32))
        except Exception:
            self.cursor_tex = pygame.Surface((32, 32))
            self.cursor_tex.fill(WHITE)
        try:
            self.menu_background = pygame.image.load(
                os.path.join(TEXTURE_DIR, 'menu_background.png')).convert()
            self.menu_background = pygame.transform.scale(self.menu_background, (WIDTH, HEIGHT))
        except Exception:
            self.menu_background = None

        self.victory_textures = {'red': None, 'blue': None}
        for team in ('red', 'blue'):
            try:
                img = pygame.image.load(
                    os.path.join(TEXTURE_DIR, f'victory_{team}.png')).convert()
                self.victory_textures[team] = pygame.transform.scale(img, (WIDTH, HEIGHT))
            except Exception:
                self.victory_textures[team] = None

    def _init_ui(self):
        self.settings_panel = SettingsPanel(y=10)
        self.hud_panel = HudPanel(WIDTH - 10, HEIGHT - 10, textures=self.textures)
        self.input_handler = InputHandler()

    def _init_menus(self):
        self.main_menu = MenuScreen("COLD OPERATION", [
            {'label': 'Одиночная игра', 'action': 'play'},
            {'label': 'Сетевая игра', 'action': 'network'},
            {'label': 'Настройки', 'action': 'settings'},
            {'label': 'Выход', 'action': 'quit'},
        ])

    # ---------- Переходы ----------

    def _start_game(self, player_team='red', bot_team=None, difficulty=None):
        self.world = World()
        self.command_processor = CommandProcessor(self.world)
        self.player_team = player_team
        self.bot_team = bot_team
        self.bot_difficulty = difficulty
        self.bot_ai = None
        if bot_team:
            self.bot_ai = BotAI(self.world, bot_team, difficulty)
        self.state = 'playing'
        self.menu_view = 'main'
        self.input_handler.reset()
        self.settings_panel.hide_immediate()
        pygame.mouse.set_visible(True)
        self.net_role = None
        self._snapshot_counter = 0
        self.pending_client_commands = []
        self.pending_server_messages = []
        self.selected_ids = set()
        self.winner = None
        self.paused = False
        self.ping_ms = -1
        self.last_ping_send = 0
        self.disconnect_reason = ""

    def _return_to_menu(self):
        self.world.deselect_all()
        self.input_handler.reset()
        pygame.mouse.set_visible(True)
        self.settings_panel.hide_immediate()
        self._network_close()
        self.bot_ai = None
        self.bot_team = None
        self.bot_difficulty = None
        self.menu_view = 'main'
        self.state = 'menu'
        self.winner = None
        self.paused = False
        self.ping_ms = -1

    # ---------- Меню ----------

    def _update_menu(self):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.menu_view == 'network':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                        continue
                    action = self.network_menu.handle_key(event)
                    if action == 'connect':
                        self._network_connect()
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self.network_menu.handle_click(*event.pos)
                    self._network_handle_action(action)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue
                if event.key == pygame.K_ESCAPE and self.menu_view == 'settings':
                    save_settings(self.settings_panel.items)
                    self.settings_panel.hide_immediate()
                    self.menu_view = 'main'
                    continue

            if self.menu_view == 'main':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = self.main_menu.handle_click(*event.pos)
                    if action == 'play':
                        self.disconnect_reason = ""
                        self.side_select.reset()
                        self.state = 'side_select'
                        return
                    elif action == 'network':
                        self.disconnect_reason = ""
                        self.menu_view = 'network'
                        self.network_menu.back_to_root()
                    elif action == 'settings':
                        self.disconnect_reason = ""
                        self.menu_view = 'settings'
                        self.settings_panel.show_immediate()
                    elif action == 'quit':
                        self.running = False
                        return

            elif self.menu_view == 'settings':
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.settings_panel.handle_click(*event.pos)

        self.draw_menu()

    # ---------- Экран выбора стороны ----------

    def _update_side_select(self):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue
                action = self.side_select.handle_key(event)
                if action == ('back', None):
                    self.side_select.reset()
                    self.state = 'menu'
                    return
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.side_select.handle_click(*event.pos)
                if action is None:
                    continue
                if action[0] == 'select':
                    continue
                if action[0] == 'no_bot':
                    self.side_select.reset()
                    self._start_game(player_team='red', bot_team=None, difficulty=None)
                    return
                if action[0] == 'start':
                    diff = action[1]
                    team = self.side_select.get_pending_team()
                    self.side_select.reset()
                    if team == 'red':
                        self._start_game(player_team='red', bot_team='blue', difficulty=diff)
                    else:
                        self._start_game(player_team='blue', bot_team='red', difficulty=diff)
                    return

        self.side_select.draw(self.screen)
        pygame.display.flip()

    def draw_menu(self):
        if self.menu_view == 'network':
            self.network_menu.draw(self.screen)
            pygame.display.flip()
            return

        if self.menu_background is not None:
            self.screen.blit(self.menu_background, (0, 0))
            dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 120))
            self.screen.blit(dark, (0, 0))
        else:
            self.screen.fill(BG_COLOR)
            for i in range(0, WIDTH, 50):
                pygame.draw.line(self.screen, GRID_COLOR, (i, 0), (i, HEIGHT), 1)
            for i in range(0, HEIGHT, 50):
                pygame.draw.line(screen, GRID_COLOR, (0, i), (WIDTH, i), 1)

        if self.menu_view == 'main':
            self.main_menu.draw(self.screen)
            if self.disconnect_reason:
                font = pygame.font.SysFont("Arial", 18, bold=True)
                txt = font.render(self.disconnect_reason, True, (255, 120, 120))
                bg = pygame.Surface((txt.get_width() + 20, txt.get_height() + 10),
                                    pygame.SRCALPHA)
                bg.fill((0, 0, 0, 180))
                tx = WIDTH // 2 - txt.get_width() // 2
                ty = HEIGHT - 90
                self.screen.blit(bg, (tx - 10, ty - 5))
                self.screen.blit(txt, (tx, ty))

        elif self.menu_view == 'settings':
            title_font = pygame.font.SysFont("Arial", 40, bold=True)
            title_surf = title_font.render("НАСТРОЙКИ", True, (255, 255, 255))
            shadow = title_font.render("НАСТРОЙКИ", True, (0, 0, 0))
            tr = title_surf.get_rect(center=(WIDTH // 2, 130))
            sr = shadow.get_rect(center=(WIDTH // 2 + 2, 132))
            self.screen.blit(shadow, sr)
            self.screen.blit(title_surf, tr)
            self.settings_panel.draw(self.screen)
            hint_font = pygame.font.SysFont("Arial", 16)
            hint = hint_font.render("Esc — назад (настройки сохраняются)", True, YELLOW)
            hr = hint.get_rect(center=(WIDTH // 2, HEIGHT - 40))
            self.screen.blit(hint, hr)

        pygame.display.flip()

    # ---------- Экран победы ----------

    def _update_game_over(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue
                if event.key == pygame.K_ESCAPE:
                    self._return_to_menu()
                    return

        team = self.winner or 'red'
        tex = self.victory_textures.get(team)
        if tex is not None:
            self.screen.blit(tex, (0, 0))
        else:
            if team == 'red':
                self.screen.fill((80, 20, 20))
                color = (255, 200, 200)
                title = "ПОБЕДА КРАСНЫХ"
            else:
                self.screen.fill((20, 20, 80))
                color = (200, 200, 255)
                title = "ПОБЕДА СИНИХ"
            font = pygame.font.SysFont("Arial", 60, bold=True)
            txt = font.render(title, True, color)
            tr = txt.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(txt, tr)

        pygame.display.flip()

    # ---------- Сетевые переходы ----------

    def _network_handle_action(self, action):
        if action is None:
            return
        if action == 'back':
            self._network_close()
            self.menu_view = 'main'
        elif action == 'host':
            self._network_host()
        elif action == 'scan':
            self.network_menu.enter_scan()
        elif action == 'scan_refresh':
            self.network_menu.enter_scan()
        elif isinstance(action, str) and action.startswith('scan_connect:'):
            ip = action.split(':', 1)[1]
            self._network_connect_ip(ip)
        elif action == 'join':
            self.network_menu.enter_join()
        elif action == 'connect':
            self._network_connect()
        elif action == 'start':
            if len(self.net_players) >= 2:
                self._network_start_game()

    def _network_host(self):
        self.net_server = NetworkServer()
        self.net_server.on_client_join = self._on_client_join
        self.net_server.on_client_leave = self._on_client_leave
        self.net_server.on_message = self._on_server_message
        if not self.net_server.start():
            self.net_server = None
            return
        self.discovery_broadcaster = ServerDiscoveryBroadcaster(
            server_name="Cold Operation Server",
            port=self.net_server.port,
        )
        self.discovery_broadcaster.player_count_callback = \
            lambda: self.net_server.player_count() if self.net_server else 0
        self.discovery_broadcaster.start()

        self.net_role = 'host'
        self.net_players = ['Хост']
        self.network_menu.enter_host()
        self.network_menu.set_players(self.net_players)

    def _on_client_join(self, name):
        self.net_players.append(name)
        self.network_menu.set_players(list(self.net_players))

    def _on_client_leave(self, name):
        if name in self.net_players:
            self.net_players.remove(name)
        self.network_menu.set_players(list(self.net_players))

        if self.state == 'playing' and self.net_role == 'host':
            self.disconnect_reason = "Клиент отключился"
            self._return_to_menu()

    def _on_server_message(self, name, msg):
        self.pending_server_messages.append(msg)

    def _network_connect(self):
        ip = self.network_menu.ip_input.strip()
        if not ip:
            self.network_menu.set_status("Введите IP-адрес")
            return
        self._network_connect_ip(ip)

    def _network_connect_ip(self, ip):
        self.net_client = NetworkClient()
        self.net_client.on_message = self._on_network_message
        self.net_client.on_disconnect = self._on_network_disconnect
        if not self.net_client.connect(ip, name='Клиент'):
            self.network_menu.set_status("Не удалось подключиться")
            self.net_client = None
            return
        self.net_role = 'client'
        self.network_menu.enter_lobby(is_host=False)
        self.network_menu.set_players(['Хост', 'Клиент'])

    def _on_network_message(self, msg):
        t = msg.get('type')
        if t == 'player_list':
            self.network_menu.set_players(msg.get('players', []))
        elif t == 'start_game':
            self._start_network_game()
        elif t == 'game_over':
            if self.net_role == 'client' and self.state == 'playing':
                self.winner = msg.get('winner')
                self.state = 'game_over'
        elif t == 'pause':
            if self.state == 'playing':
                self.paused = msg.get('value', False)
        elif t == 'pong':
            sent = msg.get('time', 0)
            self.ping_ms = max(0, int((time.time() * 1000) - sent))
        elif t == 'snapshot':
            if self.net_role == 'client' and self.state == 'playing':
                try:
                    apply_snapshot(self.world, msg['data'])
                except Exception as e:
                    print(f"[Client] Ошибка снапшота: {e}")
        elif t == 'client_command':
            if self.net_role == 'host':
                self.pending_client_commands.append(msg)

    def _on_network_disconnect(self):
        if self.net_role == 'client':
            if self.state == 'playing':
                self.disconnect_reason = "Соединение потеряно"
                self._return_to_menu()
            elif self.menu_view == 'network':
                self.network_menu.set_status("Соединение потеряно")

    def _network_start_game(self):
        if self.net_server:
            try:
                self.net_server.broadcast({'type': 'start_game'})
            except Exception:
                pass
        self._start_network_game()

    def _start_network_game(self):
        self.world = World()
        if self.net_role == 'client':
            self.world.red_units = []
            self.world.blue_units = []
            self.world.outposts_red = []
            self.world.outposts_blue = []
            self.world.red_convoys = []
            self.world.blue_convoys = []
            self.world.dragon_teeth_red = []
            self.world.dragon_teeth_blue = []
            self.world.mines_red = []
            self.world.mines_blue = []
            self.world.bullets = []
            self.world.airstrikes = []
            self.world.red_hq = None
            self.world.blue_hq = None
            self.world.command_points = {'red': 0.0, 'blue': 0.0}

        self.command_processor = CommandProcessor(self.world)
        self.player_team = 'red' if self.net_role == 'host' else 'blue'
        self.bot_ai = None
        self.bot_team = None
        self.bot_difficulty = None
        self.state = 'playing'
        self.menu_view = 'main'
        self.input_handler.reset()
        self.settings_panel.hide_immediate()
        pygame.mouse.set_visible(True)
        self._snapshot_counter = 0
        self.pending_client_commands = []
        self.pending_server_messages = []
        self.selected_ids = set()
        self.winner = None
        self.paused = False
        self.ping_ms = -1
        self.last_ping_send = 0
        self.disconnect_reason = ""

    def _network_close(self):
        if self.discovery_broadcaster:
            self.discovery_broadcaster.stop()
            self.discovery_broadcaster = None
        if self.net_server:
            self.net_server.stop()
            self.net_server = None
        if self.net_client:
            self.net_client.disconnect()
            self.net_client = None
        self.net_role = None
        self.net_players = []
        self.pending_server_messages = []

    # ---------- Пауза ----------

    def _toggle_pause(self):
        self.paused = not self.paused
        msg = {'type': 'pause', 'value': self.paused}
        if self.net_role == 'host' and self.net_server:
            try:
                self.net_server.broadcast(msg)
            except Exception:
                pass
        elif self.net_role == 'client' and self.net_client and self.net_client.connected:
            try:
                self.net_client.send(msg)
            except Exception:
                pass

    def _draw_pause_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont("Arial", 72, bold=True)
        text = font_big.render("ПАУЗА", True, (255, 255, 255))
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        shadow = font_big.render("ПАУЗА", True, (0, 0, 0))
        self.screen.blit(shadow, (rect.x + 3, rect.y + 3))
        self.screen.blit(text, rect)

        font_small = pygame.font.SysFont("Arial", 20)
        hint = font_small.render("P / Pause — продолжить", True, (220, 220, 220))
        hrect = hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.screen.blit(hint, hrect)

    # ---------- Ping ----------

    def _send_ping_if_needed(self):
        if self.net_role != 'client':
            return
        if not self.net_client or not self.net_client.connected:
            return
        now = pygame.time.get_ticks()
        if now - self.last_ping_send >= 1000:
            self.last_ping_send = now
            try:
                self.net_client.send({'type': 'ping', 'time': time.time() * 1000})
            except Exception:
                pass

    def _draw_ping(self):
        if self.ping_ms < 0:
            return
        font = pygame.font.SysFont("Arial", 14)
        if self.ping_ms < 80:
            color = (100, 255, 100)
        elif self.ping_ms < 200:
            color = (255, 220, 100)
        else:
            color = (255, 100, 100)
        txt = font.render(f"Ping: {self.ping_ms} ms", True, color)
        bg = pygame.Surface((txt.get_width() + 10, txt.get_height() + 6),
                            pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        self.screen.blit(bg, (WIDTH - txt.get_width() - 16, 6))
        self.screen.blit(txt, (WIDTH - txt.get_width() - 11, 9))

    # ---------- Проверка победы ----------

    def _check_victory(self):
        red_alive = len(self.world.red_units) > 0
        blue_alive = len(self.world.blue_units) > 0
        if red_alive and not blue_alive:
            return 'red'
        if blue_alive and not red_alive:
            return 'blue'
        return None

    def _trigger_victory(self, winner):
        self.winner = winner
        self.state = 'game_over'
        if self.net_role == 'host' and self.net_server:
            try:
                self.net_server.broadcast({'type': 'game_over', 'winner': winner})
            except Exception:
                pass

    # ---------- Игра: UI ----------

    def _compute_selected(self, refs):
        for obj in refs['units'] + refs['convoys'] + refs['outposts']:
            if obj.selected:
                return obj
        hq = refs.get('hq')
        if hq and hq.active and hq.selected:
            return hq
        return None

    def _setup_hud_panel(self, refs, selected):
        ih = self.input_handler
        if ih.mode in ('action_load', 'action_unload',
                       'build_dragon_teeth', 'build_mines', 'demolish'):
            self.hud_panel.hide()
            return

        if not selected:
            self.hud_panel.hide()
            return

        # Штаб — большое меню вызова юнитов
        if getattr(selected, 'unit_type', None) == 'headquarters':
            team = selected.team
            cp = self.world.command_points.get(team, 0.0)
            territory_pct = self.world._compute_territory_percent(team)
            units = self.world.red_units if team == 'red' else self.world.blue_units
            unit_count = len(units)
            base_r = CP_BASE_RATE
            terr_b = (territory_pct / 100.0) * CP_TERRITORY_BONUS
            pen = min(CP_UNIT_PENALTY_MAX, unit_count * CP_UNIT_PENALTY_PER)
            rate = (base_r + terr_b) * (1.0 - pen)

            labels = {
                'infantry': 'Пехота',
                'engineer': 'Инженер',
                'motorized': 'Мотострелки',
                'tank': 'Танк',
                'artillery': 'Артиллерия',
            }
            unit_list = []
            for utype, cost in UNIT_COSTS.items():
                unit_list.append({
                    'type': utype,
                    'label': labels.get(utype, utype),
                    'cost': cost,
                    'icon': utype,
                    'team': team,
                    'enabled': cp >= cost,
                })

            info = build_info_for(selected)
            info_title = info[0] if info else "Штаб"
            info_rows = info[1] if info else []

            self.hud_panel.show_build_menu(unit_list, cp, rate,
                                           info_title=info_title,
                                           info_rows=info_rows)
            return

        # Обычные кнопки действий
        buttons = []
        if getattr(selected, 'unit_type', None) == 'artillery':
            buttons.append({'label': 'Огонь на подавление',
                            'command': 'artillery_fire', 'icon': 'fire'})
        if hasattr(selected, 'cargo'):
            buttons.append({'label': 'Погрузка',
                            'command': 'load', 'icon': 'load'})
            buttons.append({'label': 'Разгрузка',
                            'command': 'unload', 'icon': 'unload'})
        if getattr(selected, 'can_dig_in', False):
            if getattr(selected, 'hold_position', False):
                buttons.append({'label': 'Отменить удержание',
                                'command': 'toggle_hold', 'icon': 'shield_off'})
            else:
                buttons.append({'label': 'Держать позицию',
                                'command': 'toggle_hold', 'icon': 'hold'})
        if getattr(selected, 'unit_type', None) == 'engineer':
            log = getattr(selected, 'logistics', 0)
            buttons.append({'label': f'Опорник — {COST_OUTPOST}',
                            'command': 'build_outpost', 'icon': 'outpost',
                            'enabled': log >= COST_OUTPOST})
            buttons.append({'label': f'Зубья — {COST_DRAGON_TEETH}',
                            'command': 'build_dragon_teeth', 'icon': 'teeth',
                            'enabled': log >= COST_DRAGON_TEETH})
            buttons.append({'label': f'Мины — {COST_MINES}',
                            'command': 'build_mines', 'icon': 'mines',
                            'enabled': log >= COST_MINES})
            buttons.append({'label': f'Склад — {COST_WAREHOUSE}',
                            'command': 'build_warehouse', 'icon': 'warehouse',
                            'enabled': log >= COST_WAREHOUSE})
            buttons.append({'label': 'Ведро — снос по линии',
                            'command': 'demolish', 'icon': 'bucket'})

        info_title = ""
        info_rows = []
        if self.settings_panel.items[7]["active"]:
            info = build_info_for(selected)
            if info:
                info_title = info[0]
                filtered = []
                for row in info[1]:
                    label, value = row
                    if label in ('HP', 'Урон', 'Логистика', 'Груз',
                                 'Снабжение', 'Защита'):
                        filtered.append((label, value))
                info_rows = filtered[:4]

        if buttons or info_rows:
            self.hud_panel.show(buttons, info_title, info_rows)
        else:
            self.hud_panel.hide()

    # ---------- Игра: события ----------

    def _process_events(self, refs):
        events = pygame.event.get()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.input_handler.mode == 'normal':
                    self._return_to_menu()
                    return None, None, None
                if event.key in (pygame.K_p, pygame.K_PAUSE):
                    self._toggle_pause()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue
                if event.key == pygame.K_F1 and self.player_team != 'blue' and self.net_role is None and self.bot_team is None:
                    self._switch_team('blue')
                    refs = self.world.get_player_refs(self.player_team)
                elif event.key == pygame.K_F2 and self.player_team != 'red' and self.net_role is None and self.bot_team is None:
                    self._switch_team('red')
                    refs = self.world.get_player_refs(self.player_team)

        selectable = (refs['units'] + [refs['base']] + refs['convoys'] + refs['outposts'])
        hq = refs.get('hq')
        if hq is not None and hq.active:
            selectable.append(hq)
        commands = self.input_handler.process_events(
            events, selectable, refs['enemy_units'],
            self.settings_panel, self.hud_panel
        )

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.settings_panel.visible:
                    self.settings_panel.handle_click(*event.pos)

        return commands, selectable, refs

    def _switch_team(self, new_team):
        self.player_team = new_team
        self.world.deselect_all()
        self.input_handler.reset()

    # ---------- Игра: апдейт ----------

    def _collect_selected_ids(self, selectable):
        ids = set()
        for obj in selectable:
            if obj.selected:
                uid = getattr(obj, 'id', None)
                if uid is not None:
                    ids.add(uid)
        return ids

    def _update_playing(self):
        self.settings_panel.update()
        self.hud_panel.update_hover()

        if self.net_role == 'host':
            for msg in self.pending_server_messages:
                t = msg.get('type')
                if t == 'ping':
                    if self.net_server:
                        try:
                            self.net_server.broadcast(
                                {'type': 'pong', 'time': msg.get('time', 0)})
                        except Exception:
                            pass
                elif t == 'pause':
                    self.paused = msg.get('value', False)
            self.pending_server_messages.clear()

        refs = self.world.get_player_refs(self.player_team)
        selected = self._compute_selected(refs)
        self._setup_hud_panel(refs, selected)

        commands, selectable, refs = self._process_events(refs)

        if commands is None:
            return
        if not self.running:
            return

        self._send_ping_if_needed()

        if self.paused:
            if self.net_role == 'client':
                interpolate_world(self.world)
            self._render_paused()
            return

        # === КЛИЕНТ ===
        if self.net_role == 'client':
            if commands['select_units'] is not None:
                for obj in selectable:
                    obj.selected = False
                for obj in commands['select_units']:
                    obj.selected = True

            self.selected_ids = self._collect_selected_ids(selectable)

            if has_world_commands(commands):
                packet = serialize_client_commands(commands, self.selected_ids)
                packet['type'] = 'client_command'
                if self.net_client and self.net_client.connected:
                    self.net_client.send(packet)

            self._render_observer()
            return

        # === ХОСТ / ОДИНОЧНАЯ ИГРА ===
        for packet in self.pending_client_commands:
            self._apply_client_commands(packet)
        self.pending_client_commands.clear()

        self.command_processor.process(commands, selectable, self.player_team)
        render_state = self.world.update(commands)

        # Ход бота
        if self.bot_ai is not None:
            self.bot_ai.update()

        if self.net_role == 'host' and self.net_server:
            self._snapshot_counter += 1
            if self._snapshot_counter >= 3:
                self._snapshot_counter = 0
                try:
                    snapshot = serialize_world(self.world)
                    self.net_server.broadcast({'type': 'snapshot', 'data': snapshot})
                except Exception as e:
                    print(f"[Host] Ошибка снапшота: {e}")

        winner = self._check_victory()
        if winner:
            self._trigger_victory(winner)
            return

        self.draw(render_state)
        pygame.display.flip()

    def _render_paused(self):
        w = self.world
        if w.territory_zone_surf is not None:
            zone_surf = w.territory_zone_surf
            frontline_lines = w.territory_frontline_lines
            influence_grid = None
        else:
            zone_surf, frontline_lines, influence_grid, _ = compute_influence_grid(
                w.red_units, w.blue_units, w.cities, w.red_base, w.blue_base,
                w.outposts_red, w.outposts_blue
            )
        highlight = w._compute_highlight()
        render_state = {
            'zone_surf': zone_surf,
            'frontline_lines': frontline_lines,
            'influence_grid': influence_grid,
            'highlight': highlight,
        }
        self.draw(render_state)
        self._draw_pause_overlay()
        pygame.display.flip()

    def _apply_client_commands(self, packet):
        try:
            cmd = deserialize_client_commands(packet)

            if cmd.get('add_airstrike'):
                target = cmd['add_airstrike']
                self.world.airstrikes.append(Airstrike(target, 'blue'))

            selected_ids = set(packet.get('selected_ids', []))
            selectable = (self.world.blue_units + [self.world.blue_base] +
                          self.world.blue_convoys + self.world.outposts_blue)
            if self.world.blue_hq and self.world.blue_hq.active:
                selectable.append(self.world.blue_hq)
            for obj in selectable:
                obj.selected = (getattr(obj, 'id', None) in selected_ids)

            self.command_processor.process(cmd, selectable, 'blue')
        except Exception as e:
            print(f"[Host] Ошибка клиентской команды: {e}")

    def _render_observer(self):
        w = self.world
        interpolate_world(w)

        if w.territory_zone_surf is not None:
            zone_surf = w.territory_zone_surf
            frontline_lines = w.territory_frontline_lines
            influence_grid = None
        else:
            zone_surf, frontline_lines, influence_grid, _ = compute_influence_grid(
                w.red_units, w.blue_units, w.cities, w.red_base, w.blue_base,
                w.outposts_red, w.outposts_blue
            )

        highlight = w._compute_highlight()
        render_state = {
            'zone_surf': zone_surf,
            'frontline_lines': frontline_lines,
            'influence_grid': influence_grid,
            'highlight': highlight,
        }
        self.draw(render_state)
        self._draw_ping()
        pygame.display.flip()

    # ---------- Игра: рендер ----------

    def draw(self, render_state):
        w = self.world
        renderer.draw(
            self.screen,
            w.red_units, w.blue_units, w.bullets,
            self.input_handler, self.textures, self.flag_textures,
            w.cities, w.airstrikes,
            self.plane_tex_red, self.plane_tex_blue, self.cursor_tex,
            w.roads, w.red_base, w.blue_base, render_state['highlight'],
            w.red_convoys, w.blue_convoys, self.settings_panel,
            w.forests, w.outposts_red, w.outposts_blue,
            self.hud_panel,
            self.textures.get('artillery_cursor'),
            frontline_data=(render_state['zone_surf'],
                            render_state['frontline_lines'],
                            render_state['influence_grid']),
            dragon_teeth_red=w.dragon_teeth_red,
            dragon_teeth_blue=w.dragon_teeth_blue,
            mines_red=w.mines_red,
            mines_blue=w.mines_blue,
            player_team=self.player_team,
            red_hq=w.red_hq,
            blue_hq=w.blue_hq,
            command_points=w.command_points,
        )

    # ---------- Главный цикл ----------

    def run(self):
        while self.running:
            self.clock.tick(FPS)

            if self.state == 'menu':
                self._update_menu()
            elif self.state == 'side_select':
                self._update_side_select()
            elif self.state == 'playing':
                self._update_playing()
            elif self.state == 'game_over':
                self._update_game_over()

        pygame.quit()
        sys.exit()