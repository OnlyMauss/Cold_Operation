# network_menu.py
import pygame
import os
from config import *
from network import SERVER_PORT
from discovery import ServerDiscoveryScanner


class NetworkMenu:
    """Полноэкранное меню сетевой игры."""

    def __init__(self, game):
        self.game = game
        self.view = 'root'  # 'root' | 'host' | 'join' | 'lobby' | 'scan'

        self.root_buttons = [
            {'label': 'Создать сервер', 'action': 'host'},
            {'label': 'Найти серверы', 'action': 'scan'},
            {'label': 'Подключиться по IP', 'action': 'join'},
            {'label': 'Назад', 'action': 'back'},
        ]

        # Поле ввода IP
        self.ip_input = ''
        self.ip_active = False

        # Лобби
        self.lobby_players = []
        self.lobby_status = ''
        self.lobby_is_host = False

        # Сканер серверов
        self.scanner = None
        self.scan_status = 'Нажмите «Обновить», чтобы найти серверы'
        self.scan_started_at = 0

        self.font_title = pygame.font.SysFont("Arial", 44, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 22)
        self.font_small = pygame.font.SysFont("Arial", 16)
        self.font_input = pygame.font.SysFont("Arial", 22)
        self.font_server = pygame.font.SysFont("Arial", 18)

        self.btn_width = 300
        self.btn_height = 46
        self.btn_spacing = 12

        self.background = None
        self._load_background()

    def _load_background(self):
        try:
            path = os.path.join(TEXTURE_DIR, 'network_background.png')
            img = pygame.image.load(path).convert()
            self.background = pygame.transform.scale(img, (WIDTH, HEIGHT))
        except Exception:
            self.background = None

    # ---------- Обработка ----------

    def handle_click(self, mx, my):
        if self.view == 'root':
            y0 = HEIGHT // 2 - 60
            for i, btn in enumerate(self.root_buttons):
                r = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                                y0 + i * (self.btn_height + self.btn_spacing),
                                self.btn_width, self.btn_height)
                if r.collidepoint(mx, my):
                    return btn['action']

        elif self.view == 'host':
            r2 = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                             HEIGHT - 170, self.btn_width, self.btn_height)
            if r2.collidepoint(mx, my):
                return 'start'
            r = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                            HEIGHT - 100, self.btn_width, self.btn_height)
            if r.collidepoint(mx, my):
                return 'back'

        elif self.view == 'scan':
            # Кнопка "Обновить"
            r = pygame.Rect(WIDTH // 2 - self.btn_width // 2, 170,
                            self.btn_width, self.btn_height)
            if r.collidepoint(mx, my):
                return 'scan_refresh'

            # Список серверов
            if self.scanner:
                servers = self.scanner.get_servers()
                y = 240
                for i, srv in enumerate(servers):
                    row = pygame.Rect(WIDTH // 2 - 300, y + i * 60, 600, 50)
                    if row.collidepoint(mx, my):
                        return f'scan_connect:{srv["ip"]}'

            # Кнопка "Назад"
            r2 = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                             HEIGHT - 100, self.btn_width, self.btn_height)
            if r2.collidepoint(mx, my):
                return 'back'

        elif self.view == 'join':
            r = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 60, 300, 44)
            if r.collidepoint(mx, my):
                self.ip_active = True
            else:
                self.ip_active = False

            r2 = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2, 300, self.btn_height)
            if r2.collidepoint(mx, my):
                return 'connect'

            r3 = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 60, 300, self.btn_height)
            if r3.collidepoint(mx, my):
                return 'back'

        elif self.view == 'lobby':
            r = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                            HEIGHT - 100, self.btn_width, self.btn_height)
            if r.collidepoint(mx, my):
                return 'back'

        return None

    def handle_key(self, event):
        if self.view == 'join' and self.ip_active:
            if event.key == pygame.K_BACKSPACE:
                self.ip_input = self.ip_input[:-1]
            elif event.key == pygame.K_RETURN:
                return 'connect'
            elif event.key == pygame.K_ESCAPE:
                self.ip_active = False
                self.ip_input = ''
                self.view = 'root'
            else:
                ch = event.unicode
                if ch and (ch.isdigit() or ch == '.'):
                    if len(self.ip_input) < 15:
                        self.ip_input += ch
        return None

    # ---------- Переходы ----------

    def enter_host(self):
        self.view = 'host'
        self.lobby_is_host = True
        self.lobby_players = []
        self.lobby_status = 'Ожидание подключения...'

    def enter_join(self):
        self.view = 'join'
        self.ip_input = ''
        self.ip_active = False

    def enter_scan(self):
        self.view = 'scan'
        self.scan_status = 'Сканирование...'
        if self.scanner:
            self.scanner.stop()
        self.scanner = ServerDiscoveryScanner()
        self.scanner.start()

    def enter_lobby(self, is_host):
        self.view = 'lobby'
        self.lobby_is_host = is_host
        self.lobby_status = 'Подключено' if not is_host else 'Хост'

    def set_players(self, players):
        self.lobby_players = players

    def set_status(self, status):
        self.lobby_status = status

    def back_to_root(self):
        self.view = 'root'
        self.lobby_players = []
        self.lobby_status = ''
        self.ip_input = ''
        self.ip_active = False
        if self.scanner:
            self.scanner.stop()
            self.scanner = None

    # ---------- Отрисовка ----------

    def draw(self, screen):
        if self.background is not None:
            screen.blit(self.background, (0, 0))
            dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark.fill((0, 0, 0, 100))
            screen.blit(dark, (0, 0))
        else:
            for y in range(HEIGHT):
                t = y / HEIGHT
                r = int(20 + 40 * t)
                g = int(30 + 20 * t)
                b = int(60 + 50 * t)
                pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        title = "СЕТЕВАЯ ИГРА"
        shadow = self.font_title.render(title, True, (0, 0, 0))
        title_surf = self.font_title.render(title, True, (255, 255, 255))
        tr = title_surf.get_rect(center=(WIDTH // 2, 100))
        sr = shadow.get_rect(center=(WIDTH // 2 + 2, 102))
        screen.blit(shadow, sr)
        screen.blit(title_surf, tr)

        if self.view == 'root':
            self._draw_root(screen)
        elif self.view == 'host':
            self._draw_host(screen)
        elif self.view == 'join':
            self._draw_join(screen)
        elif self.view == 'scan':
            self._draw_scan(screen)
        elif self.view == 'lobby':
            self._draw_lobby(screen)

    def _draw_root(self, screen):
        y0 = HEIGHT // 2 - 60
        mouse = pygame.mouse.get_pos()
        for i, btn in enumerate(self.root_buttons):
            r = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                            y0 + i * (self.btn_height + self.btn_spacing),
                            self.btn_width, self.btn_height)
            hover = r.collidepoint(mouse)
            bg = (255, 240, 180) if hover else (220, 200, 150)
            pygame.draw.rect(screen, bg, r)
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
            text = self.font_btn.render(btn['label'], True, (0, 0, 0))
            tr = text.get_rect(center=r.center)
            screen.blit(text, tr)

    def _draw_host(self, screen):
        info1 = self.font_small.render(
            "Сервер запущен. Другие игроки найдут его через «Найти серверы».",
            True, (255, 255, 255))
        screen.blit(info1, info1.get_rect(center=(WIDTH // 2, 170)))

        info2 = self.font_small.render(
            f"Порт: {SERVER_PORT}",
            True, (200, 200, 200))
        screen.blit(info2, info2.get_rect(center=(WIDTH // 2, 195)))

        panel = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 60, 400, 140)
        pygame.draw.rect(screen, (220, 200, 150), panel)
        pygame.draw.rect(screen, (0, 0, 0), panel, 2)

        title = self.font_btn.render("Игроки в лобби:", True, (0, 0, 0))
        screen.blit(title, (panel.x + 10, panel.y + 8))

        y = panel.y + 40
        if not self.lobby_players:
            empty = self.font_small.render("(ожидание...)", True, (100, 100, 100))
            screen.blit(empty, (panel.x + 20, y))
        else:
            for i, name in enumerate(self.lobby_players):
                label = f"{i + 1}. {name}"
                if i == 0:
                    label += " (хост)"
                txt = self.font_small.render(label, True, (0, 0, 0))
                screen.blit(txt, (panel.x + 20, y))
                y += 22

        mouse = pygame.mouse.get_pos()
        # Кнопка "Начать игру" — всегда видна, но активна только при 2+ игроках
        r2 = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                         HEIGHT - 170, self.btn_width, self.btn_height)
        can_start = len(self.lobby_players) >= 2
        hover = r2.collidepoint(mouse) and can_start
        if can_start:
            bg = (150, 255, 150) if hover else (100, 220, 100)
            text_color = (0, 0, 0)
        else:
            bg = (140, 140, 140)
            text_color = (80, 80, 80)
        pygame.draw.rect(screen, bg, r2)
        pygame.draw.rect(screen, (0, 0, 0), r2, 2)
        txt = self.font_btn.render("Начать игру", True, text_color)
        screen.blit(txt, txt.get_rect(center=r2.center))

        r = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                        HEIGHT - 100, self.btn_width, self.btn_height)
        hover = r.collidepoint(mouse)
        bg = (255, 240, 180) if hover else (220, 200, 150)
        pygame.draw.rect(screen, bg, r)
        pygame.draw.rect(screen, (0, 0, 0), r, 2)
        txt = self.font_btn.render("Назад", True, (0, 0, 0))
        screen.blit(txt, txt.get_rect(center=r.center))

    def _draw_join(self, screen):
        label = self.font_small.render("Введите IP-адрес хоста:", True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 90)))

        r = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 60, 300, 44)
        pygame.draw.rect(screen, (255, 255, 255), r)
        border = (0, 150, 255) if self.ip_active else (0, 0, 0)
        pygame.draw.rect(screen, border, r, 2)

        ip_text = self.ip_input if self.ip_input else "например 26.12.34.56"
        color = (0, 0, 0) if self.ip_input else (150, 150, 150)
        txt = self.font_input.render(ip_text, True, color)
        screen.blit(txt, (r.x + 10, r.y + 10))

        mouse = pygame.mouse.get_pos()
        r2 = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2, 300, self.btn_height)
        hover = r2.collidepoint(mouse)
        bg = (255, 240, 180) if hover else (220, 200, 150)
        pygame.draw.rect(screen, bg, r2)
        pygame.draw.rect(screen, (0, 0, 0), r2, 2)
        txt = self.font_btn.render("Подключиться", True, (0, 0, 0))
        screen.blit(txt, txt.get_rect(center=r2.center))

        r3 = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 60, 300, self.btn_height)
        hover = r3.collidepoint(mouse)
        bg = (255, 240, 180) if hover else (220, 200, 150)
        pygame.draw.rect(screen, bg, r3)
        pygame.draw.rect(screen, (0, 0, 0), r3, 2)
        txt = self.font_btn.render("Назад", True, (0, 0, 0))
        screen.blit(txt, txt.get_rect(center=r3.center))

    def _draw_scan(self, screen):
        mouse = pygame.mouse.get_pos()

        # Кнопка "Обновить"
        r = pygame.Rect(WIDTH // 2 - self.btn_width // 2, 170,
                        self.btn_width, self.btn_height)
        hover = r.collidepoint(mouse)
        bg = (255, 240, 180) if hover else (220, 200, 150)
        pygame.draw.rect(screen, bg, r)
        pygame.draw.rect(screen, (0, 0, 0), r, 2)
        txt = self.font_btn.render("Обновить список", True, (0, 0, 0))
        screen.blit(txt, txt.get_rect(center=r.center))

        # Статус
        status = self.font_small.render(self.scan_status, True, (220, 220, 220))
        screen.blit(status, status.get_rect(center=(WIDTH // 2, 230)))

        # Список
        if self.scanner:
            servers = self.scanner.get_servers()
            if not servers and not self.scanner.is_scanning():
                empty = self.font_small.render(
                    "Серверы не найдены. Убедитесь, что все в одной сети Radmin VPN.",
                    True, (200, 200, 200))
                screen.blit(empty, empty.get_rect(center=(WIDTH // 2, 300)))
            else:
                y = 260
                for srv in servers:
                    row = pygame.Rect(WIDTH // 2 - 300, y, 600, 50)
                    hover = row.collidepoint(mouse)
                    bg = (230, 220, 190) if hover else (220, 200, 150)
                    pygame.draw.rect(screen, bg, row)
                    pygame.draw.rect(screen, (0, 0, 0), row, 2)
                    line1 = self.font_server.render(
                        f"{srv['name']}", True, (0, 0, 0))
                    line2 = self.font_small.render(
                        f"{srv['ip']}:{srv['port']}  —  игроков: {srv['players']}",
                        True, (60, 60, 60))
                    screen.blit(line1, (row.x + 12, row.y + 6))
                    screen.blit(line2, (row.x + 12, row.y + 26))
                    y += 60

        # Назад
        r2 = pygame.Rect(WIDTH // 2 - self.btn_width // 2,
                         HEIGHT - 100, self.btn_width, self.btn_height)
        hover = r2.collidepoint(mouse)
        bg = (255, 240, 180) if hover else (220, 200, 150)
        pygame.draw.rect(screen, bg, r2)
        pygame.draw.rect(screen, (0, 0, 0), r2, 2)
        txt = self.font_btn.render("Назад", True, (0, 0, 0))
        screen.blit(txt, txt.get_rect(center=r2.center))

    def _draw_lobby(self, screen):
        info = self.font_btn.render(self.lobby_status, True, (255, 255, 255))
        screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT // 2)))