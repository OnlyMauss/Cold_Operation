# info_panel.py
import pygame


class InfoPanel:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 240
        self.visible = False
        self.title = ""
        self.rows = []      # список (label, value)
        self.font_title = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_row = pygame.font.SysFont("Arial", 14)

    def show(self, title, rows):
        self.title = title
        self.rows = rows
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self, screen):
        if not self.visible:
            return
        row_h = 20
        padding = 8
        header_h = 24
        height = padding * 2 + header_h + row_h * len(self.rows)
        rect = pygame.Rect(self.x, self.y, self.width, height)
        pygame.draw.rect(screen, (220, 200, 150), rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 2)

        title_surf = self.font_title.render(self.title, True, (0, 0, 0))
        screen.blit(title_surf, (self.x + padding, self.y + padding))

        y = self.y + padding + header_h
        for label, value in self.rows:
            label_surf = self.font_row.render(f"{label}:", True, (0, 0, 0))
            value_surf = self.font_row.render(str(value), True, (0, 0, 0))
            screen.blit(label_surf, (self.x + padding, y))
            screen.blit(value_surf, (self.x + padding + 120, y))
            y += row_h