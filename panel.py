# panel.py
import pygame
from config import WHITE, YELLOW


class SettingsPanel:
    def __init__(self, y=10):
        self.base_x = 0
        self.width = 220
        self.x = -self.width - 4
        self.y = y
        self.visible_height = 280
        self.row_height = 30
        self.padding = 10
        self.visible = False

        self.items = [
            {"label": "Зоны атаки", "active": False},
            {"label": "Все маршруты", "active": False},
            {"label": "Ресурсы городов", "active": False},
            {"label": "Зона баз", "active": False},
            {"label": "Щиты защиты", "active": True},
            {"label": "Линия фронта", "active": True},
            {"label": "HP юнитов (WIP)", "active": False, "enabled": False},
            {"label": "Инфо-панель", "active": True},
        ]
        self.total_content_height = len(self.items) * self.row_height + self.padding * 2
        self.scroll_offset = 0
        self.max_scroll = max(0, self.total_content_height - self.visible_height)

        self.font = pygame.font.SysFont("Arial", 18)

        # Анимация выезда
        self.target_x = -self.width - 4
        self.animation_speed = 30

    def update(self):
        """Вызывается каждый кадр — плавное движение."""
        if self.x < self.target_x:
            self.x = min(self.target_x, self.x + self.animation_speed)
        elif self.x > self.target_x:
            self.x = max(self.target_x, self.x - self.animation_speed)

    def toggle(self):
        self.visible = not self.visible
        self.target_x = self.base_x if self.visible else -self.width - 4

    def show_immediate(self):
        """Мгновенно показать (без анимации)."""
        self.visible = True
        self.target_x = self.base_x
        self.x = self.base_x

    def hide_immediate(self):
        """Мгновенно скрыть (без анимации)."""
        self.visible = False
        self.target_x = -self.width - 4
        self.x = -self.width - 4

    def handle_scroll(self, dy):
        if not self.visible:
            return
        self.scroll_offset += dy * 20
        self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset))

    def handle_click(self, mx, my):
        if not self.visible:
            return
        if self.x < self.base_x - 5:
            return
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.visible_height)
        if not panel_rect.collidepoint(mx, my):
            return
        for i, item in enumerate(self.items):
            if not item.get("enabled", True):
                continue
            btn_rect = pygame.Rect(self.x + 10,
                                   self.y + self.padding + i * self.row_height - self.scroll_offset,
                                   self.width - 20, self.row_height - 4)
            if btn_rect.collidepoint(mx, my):
                item["active"] = not item["active"]
                break

    def draw(self, screen):
        if not self.visible and self.x <= -self.width + 5:
            return

        panel_rect = pygame.Rect(self.x, self.y, self.width, self.visible_height)
        pygame.draw.rect(screen, (220, 200, 150), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 2)

        screen.set_clip(panel_rect)
        for i, item in enumerate(self.items):
            y = self.y + self.padding + i * self.row_height - self.scroll_offset
            if y + self.row_height < self.y or y > self.y + self.visible_height:
                continue
            icon_rect = pygame.Rect(self.x + 10, y, 20, 20)
            if item.get("enabled", True):
                pygame.draw.rect(screen, (0, 0, 200), icon_rect)
                if item["active"]:
                    pygame.draw.line(screen, YELLOW, (icon_rect.x + 4, icon_rect.y + 10),
                                     (icon_rect.x + 8, icon_rect.y + 16), 2)
                    pygame.draw.line(screen, YELLOW, (icon_rect.x + 8, icon_rect.y + 16),
                                     (icon_rect.x + 16, icon_rect.y + 4), 2)
                else:
                    pygame.draw.line(screen, YELLOW, (icon_rect.x + 4, icon_rect.y + 4),
                                     (icon_rect.x + 16, icon_rect.y + 16), 2)
                    pygame.draw.line(screen, YELLOW, (icon_rect.x + 16, icon_rect.y + 4),
                                     (icon_rect.x + 4, icon_rect.y + 16), 2)
            else:
                pygame.draw.rect(screen, (128, 128, 128), icon_rect)
            label = item["label"]
            if not item.get("enabled", True):
                label += " (WIP)"
            text = self.font.render(label, True, (0, 0, 0))
            screen.blit(text, (self.x + 35, y))
        screen.set_clip(None)

        if self.max_scroll > 0:
            bar_height = max(20, self.visible_height * self.visible_height / self.total_content_height)
            bar_y = self.y + (self.scroll_offset / self.max_scroll) * (self.visible_height - bar_height)
            pygame.draw.rect(screen, (100, 100, 100),
                             (self.x + self.width - 8, bar_y, 6, bar_height))