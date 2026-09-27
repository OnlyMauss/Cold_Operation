# side_select.py
import pygame
import os
import math
from config import *


class SideSelectScreen:
    """Полноэкранный выбор стороны: красные / синие / без бота."""

    def __init__(self):
        self.font_title = pygame.font.SysFont("Arial", 52, bold=True)
        self.font_hint = pygame.font.SysFont("Arial", 18)
        self.font_small = pygame.font.SysFont("Arial", 16)

        # Загрузка флагов
        self.tex_red = None
        self.tex_blue = None
        try:
            img = pygame.image.load(
                os.path.join(TEXTURE_DIR, 'flag_select_red.png')).convert()
            self.tex_red = pygame.transform.scale(img, (WIDTH // 2, HEIGHT))
        except Exception:
            self.tex_red = None
        try:
            img = pygame.image.load(
                os.path.join(TEXTURE_DIR, 'flag_select_blue.png')).convert()
            self.tex_blue = pygame.transform.scale(img, (WIDTH // 2, HEIGHT))
        except Exception:
            self.tex_blue = None

        # Окно выбора сложности
        self.difficulty_visible = False
        self.pending_team = None

    # ---------- Layout ----------

    def _left_rect(self):
        return pygame.Rect(0, 0, WIDTH // 2, HEIGHT)

    def _right_rect(self):
        return pygame.Rect(WIDTH // 2, 0, WIDTH // 2, HEIGHT)

    def _title_rect(self):
        # Область заголовка (можно кликнуть)
        return pygame.Rect(WIDTH // 2 - 220, HEIGHT // 2 - 40, 440, 80)

    def _popup_rect(self):
        w, h = 400, 260
        return pygame.Rect(WIDTH // 2 - w // 2, HEIGHT // 2 - h // 2, w, h)

    def _popup_btn(self, index):
        """0 = Сержант, 1 = Лейтенант, 2 = Назад."""
        p = self._popup_rect()
        bw, bh = 320, 50
        bx = p.x + (p.width - bw) // 2
        by = p.y + 80 + index * 60
        return pygame.Rect(bx, by, bw, bh)

    # ---------- События ----------

    def handle_click(self, mx, my):
        if self.difficulty_visible:
            for i, diff in enumerate(('sergeant', 'lieutenant', 'back')):
                r = self._popup_btn(i)
                if r.collidepoint(mx, my):
                    if diff == 'back':
                        self.difficulty_visible = False
                        self.pending_team = None
                        return None
                    return ('start', diff)
            return None

        # Клик по заголовку = без бота
        if self._title_rect().collidepoint(mx, my):
            return ('no_bot', None)
        # Клик по половинам
        if self._left_rect().collidepoint(mx, my):
            self.difficulty_visible = True
            self.pending_team = 'red'
            return None
        if self._right_rect().collidepoint(mx, my):
            self.difficulty_visible = True
            self.pending_team = 'blue'
            return None
        return None

    def handle_key(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.difficulty_visible:
                self.difficulty_visible = False
                self.pending_team = None
                return None
            return ('back', None)
        return None

    def get_pending_team(self):
        return self.pending_team

    def reset(self):
        self.difficulty_visible = False
        self.pending_team = None

    # ---------- Отрисовка ----------

    def draw(self, screen):
        # Левая половина — красная
        if self.tex_red is not None:
            screen.blit(self.tex_red, (0, 0))
        else:
            self._draw_fallback_red(screen)
        # Правая половина — синяя
        if self.tex_blue is not None:
            screen.blit(self.tex_blue, (WIDTH // 2, 0))
        else:
            self._draw_fallback_blue(screen)

        # Тёмная разделяющая линия
        pygame.draw.line(screen, (0, 0, 0),
                         (WIDTH // 2, 0), (WIDTH // 2, HEIGHT), 4)

        # Небольшое затемнение для читаемости заголовка
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 60))
        screen.blit(overlay, (0, 0))

        # Заголовок (единственный текст на экране)
        text = "КОМУ ДАТЬ ПРИСЯГУ?"
        title_shadow = self.font_title.render(text, True, (0, 0, 0))
        title_main = self.font_title.render(text, True, (255, 255, 255))
        tr = title_main.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(title_shadow, (tr.x + 3, tr.y + 3))
        screen.blit(title_main, tr)

        # Всплывающее окно выбора сложности
        if self.difficulty_visible:
            self._draw_difficulty_popup(screen)

    def _draw_difficulty_popup(self, screen):
        # Затемнение
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 160))
        screen.blit(dark, (0, 0))

        # Панель
        p = self._popup_rect()
        pygame.draw.rect(screen, (220, 200, 150), p)
        pygame.draw.rect(screen, (0, 0, 0), p, 3)

        # Заголовок
        team_name = 'Красных' if self.pending_team == 'red' else 'Синих'
        title = self.font_title.render("Сложность бота", True, (0, 0, 0))
        title_small = self.font_hint.render(
            f"Вы играете за {team_name}",
            True, (60, 60, 60))
        screen.blit(title, title.get_rect(center=(p.centerx, p.y + 32)))
        screen.blit(title_small, title_small.get_rect(center=(p.centerx, p.y + 62)))

        # Кнопки
        labels = [
            ("Сержант", "средний"),
            ("Лейтенант", "высокий"),
            ("Назад", ""),
        ]
        mouse = pygame.mouse.get_pos()
        for i, (label, hint) in enumerate(labels):
            r = self._popup_btn(i)
            hover = r.collidepoint(mouse)
            if i == 2:
                bg = (255, 200, 200) if hover else (220, 170, 170)
            else:
                bg = (255, 240, 180) if hover else (255, 255, 255)
            pygame.draw.rect(screen, bg, r)
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
            txt = self.font_hint.render(label, True, (0, 0, 0))
            screen.blit(txt, txt.get_rect(center=(r.centerx, r.centery - 8)))
            if hint:
                h = self.font_small.render(f"({hint})", True, (90, 90, 90))
                screen.blit(h, h.get_rect(center=(r.centerx, r.centery + 10)))

    # ---------- Fallback ----------

    def _draw_fallback_red(self, screen):
        screen.fill((140, 20, 20), self._left_rect())
        cx, cy = WIDTH // 4, HEIGHT // 2
        pts = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            r = 80 if i % 2 == 0 else 34
            pts.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
        pygame.draw.polygon(screen, (255, 220, 0), pts)

    def _draw_fallback_blue(self, screen):
        screen.fill((20, 30, 90), self._right_rect())
        cx, cy = WIDTH * 3 // 4, HEIGHT // 2
        pygame.draw.circle(screen, (220, 220, 220), (cx, cy), 80, 4)
        for dx, dy in [(0, -50), (0, 50), (-50, 0), (50, 0)]:
            pygame.draw.line(screen, (220, 220, 220),
                             (cx, cy), (cx + dx, cy + dy), 3)