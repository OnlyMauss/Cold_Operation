# action_panel.py
import pygame
from config import WHITE, YELLOW


class ActionPanel:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 180
        self.height = 80
        self.visible = False
        self.actions = []
        self.font = pygame.font.SysFont("Arial", 14)

    def set_actions(self, actions):
        self.actions = actions
        self.visible = len(actions) > 0

    def hide(self):
        self.visible = False

    def handle_click(self, mx, my):
        if not self.visible:
            return None
        for i, action in enumerate(self.actions):
            btn_rect = pygame.Rect(self.x + 5, self.y + 5 + i * 28, self.width - 10, 24)
            if btn_rect.collidepoint(mx, my):
                if not action.get('enabled', True):
                    return None
                return action['command']
        return None

    def draw(self, screen):
        if not self.visible:
            return
        height = 10 + len(self.actions) * 28
        panel_rect = pygame.Rect(self.x, self.y, self.width, height)
        pygame.draw.rect(screen, (220, 200, 150), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 2)

        for i, action in enumerate(self.actions):
            y = self.y + 5 + i * 28
            btn_rect = pygame.Rect(self.x + 5, y, self.width - 10, 24)
            enabled = action.get('enabled', True)
            if enabled:
                pygame.draw.rect(screen, (255, 255, 255), btn_rect)
                text_color = (0, 0, 0)
            else:
                pygame.draw.rect(screen, (160, 160, 160), btn_rect)
                text_color = (90, 90, 90)
            pygame.draw.rect(screen, (0, 0, 0), btn_rect, 1)
            text = self.font.render(action['label'], True, text_color)
            text_rect = text.get_rect(center=btn_rect.center)
            screen.blit(text, text_rect)