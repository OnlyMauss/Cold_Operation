# menu.py
import pygame
from config import *


class MenuScreen:
    def __init__(self, title, buttons):
        self.title = title
        self.buttons = buttons  # [{'label': ..., 'action': ..., 'enabled': True, 'hint': ...}]
        self.font_title = pygame.font.SysFont("Arial", 44, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 22)
        self.font_hint = pygame.font.SysFont("Arial", 14)

        self.btn_width = 280
        self.btn_height = 46
        self.btn_spacing = 12

    def _layout(self):
        n = len(self.buttons)
        total_h = n * self.btn_height + (n - 1) * self.btn_spacing
        return HEIGHT // 2 - total_h // 2 + 30

    def _btn_rect(self, i):
        y0 = self._layout()
        x = WIDTH // 2 - self.btn_width // 2
        y = y0 + i * (self.btn_height + self.btn_spacing)
        return pygame.Rect(x, y, self.btn_width, self.btn_height)

    def handle_click(self, mx, my):
        for i, btn in enumerate(self.buttons):
            r = self._btn_rect(i)
            if r.collidepoint(mx, my):
                if btn.get('enabled', True):
                    return btn['action']
        return None

    def draw(self, screen):
        # Заголовок с тенью
        shadow = self.font_title.render(self.title, True, (0, 0, 0))
        title = self.font_title.render(self.title, True, (255, 255, 255))
        title_rect = title.get_rect(center=(WIDTH // 2, 130))
        shadow_rect = shadow.get_rect(center=(WIDTH // 2 + 2, 132))
        screen.blit(shadow, shadow_rect)
        screen.blit(title, title_rect)

        # Кнопки
        for i, btn in enumerate(self.buttons):
            r = self._btn_rect(i)
            enabled = btn.get('enabled', True)
            if enabled:
                pygame.draw.rect(screen, (220, 200, 150), r)
                pygame.draw.rect(screen, (0, 0, 0), r, 2)
                text_color = (0, 0, 0)
            else:
                pygame.draw.rect(screen, (120, 110, 90), r)
                pygame.draw.rect(screen, (0, 0, 0), r, 2)
                text_color = (60, 60, 60)

            label = btn['label']
            if not enabled and btn.get('hint'):
                label = f"{label} ({btn['hint']})"

            text = self.font_btn.render(label, True, text_color)
            text_rect = text.get_rect(center=r.center)
            screen.blit(text, text_rect)

        # Подсказка внизу
        hint = self.font_hint.render("F11 — полный экран", True, (180, 180, 180))
        hint_rect = hint.get_rect(center=(WIDTH // 2, HEIGHT - 20))
        screen.blit(hint, hint_rect)