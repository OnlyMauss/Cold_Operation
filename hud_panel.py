# hud_panel.py
import pygame
from config import *


class HudPanel:
    def __init__(self, right_x, bottom_y, textures=None):
        self.right = right_x
        self.bottom = bottom_y

        self.mode = 'actions'

        # Иконки действий
        self.icon_size = 32
        self.gap = 4
        self.padding = 4
        self.max_icons = 6

        self.actions_width = (self.padding * 2
                              + self.max_icons * self.icon_size
                              + (self.max_icons - 1) * self.gap)
        self.actions_icons_height = self.padding * 2 + self.icon_size

        # Build menu
        self.build_cols = 3
        self.build_rows = 2
        self.build_cell_w = 120
        self.build_cell_h = 58
        self.build_gap = 4
        self.build_header = 48
        self.build_width = (self.padding * 2
                            + self.build_cols * self.build_cell_w
                            + (self.build_cols - 1) * self.build_gap)
        self.build_height = (self.padding * 2
                             + self.build_header
                             + self.build_rows * self.build_cell_h
                             + (self.build_rows - 1) * self.build_gap)

        self.width = self.actions_width
        self.height = self.actions_icons_height
        self.x = right_x - self.width
        self.y = bottom_y - self.height

        self.visible = False
        self.buttons = []
        self.hover_index = -1

        # Инфо-строки (для actions)
        self.info_title = ""
        self.info_rows = []
        self.info_height = 0

        # Build menu
        self.build_units = []
        self.command_points = 0.0
        self.cp_rate = 0.0
        self.build_info_title = ""
        self.build_info_rows = []

        self.textures = textures or {}

        self.font_tooltip = pygame.font.SysFont("Arial", 13)
        self.font_cell = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_cost = pygame.font.SysFont("Arial", 12)
        self.font_header = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_header_info = pygame.font.SysFont("Arial", 12)
        self.font_info = pygame.font.SysFont("Arial", 12)

    def set_textures(self, textures):
        self.textures = textures or {}

    # ---------- Управление ----------

    def show(self, buttons, info_title=None, info_rows=None):
        self.mode = 'actions'
        self.buttons = buttons[:self.max_icons]
        self.info_title = info_title or ""
        self.info_rows = info_rows or []
        self.info_height = self._compute_info_height()

        self.width = self.actions_width
        self.height = self.actions_icons_height + self.info_height
        self.x = self.right - self.width
        self.y = self.bottom - self.height
        self.visible = len(self.buttons) > 0 or bool(self.info_rows)

    def show_build_menu(self, units, cp, cp_rate, info_title="", info_rows=None):
        self.mode = 'build'
        self.width = self.build_width
        self.height = self.build_height
        self.x = self.right - self.width
        self.y = self.bottom - self.height
        self.build_units = units
        self.command_points = cp
        self.cp_rate = cp_rate
        self.build_info_title = info_title
        self.build_info_rows = info_rows or []
        self.visible = True
        self.hover_index = -1

    def hide(self):
        self.visible = False
        self.buttons = []
        self.build_units = []
        self.hover_index = -1
        self.info_title = ""
        self.info_rows = []
        self.info_height = 0

    def _compute_info_height(self):
        if not self.info_title and not self.info_rows:
            return 0
        h = 6
        if self.info_title:
            h += 18
        h += len(self.info_rows) * 16
        h += 6
        return h

    # ---------- Layout ----------

    def _cell_rect(self, index):
        col = index % self.build_cols
        row = index // self.build_cols
        x = self.x + self.padding + col * (self.build_cell_w + self.build_gap)
        y = self.y + self.padding + self.build_header + row * (self.build_cell_h + self.build_gap)
        return pygame.Rect(x, y, self.build_cell_w, self.build_cell_h)

    def _button_rect(self, i):
        # Иконки всегда снизу панели
        bx = self.x + self.padding + i * (self.icon_size + self.gap)
        by = self.y + self.info_height + self.padding
        return pygame.Rect(bx, by, self.icon_size, self.icon_size)

    # ---------- Hover ----------

    def update_hover(self):
        if not self.visible:
            self.hover_index = -1
            return
        mx, my = pygame.mouse.get_pos()
        self.hover_index = -1

        if self.mode == 'build':
            for i in range(len(self.build_units)):
                if self._cell_rect(i).collidepoint(mx, my):
                    self.hover_index = i
                    return
        else:
            for i in range(len(self.buttons)):
                if self._button_rect(i).collidepoint(mx, my):
                    self.hover_index = i
                    return

    # ---------- Клик ----------

    def handle_click(self, mx, my):
        if not self.visible:
            return None

        if self.mode == 'build':
            for i, u in enumerate(self.build_units):
                if self._cell_rect(i).collidepoint(mx, my):
                    if u.get('enabled', True):
                        return f"buy:{u['type']}"
            return None
        else:
            for i, btn in enumerate(self.buttons):
                if self._button_rect(i).collidepoint(mx, my):
                    if btn.get('enabled', True):
                        return btn['command']
            return None

    # ---------- Отрисовка ----------

    def draw(self, screen):
        if not self.visible:
            return
        if self.mode == 'build':
            self._draw_build(screen)
        else:
            self._draw_actions(screen)

    def _draw_actions(self, screen):
        # Основная панель
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, (220, 200, 150), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 2)

        # Инфо-блок сверху
        if self.info_height > 0:
            y = self.y + 6
            if self.info_title:
                title_surf = self.font_header.render(self.info_title, True, (0, 0, 0))
                screen.blit(title_surf, (self.x + 6, y))
                y += 18

            for label, value in self.info_rows:
                label_surf = self.font_info.render(f"{label}:", True, (60, 60, 60))
                value_surf = self.font_info.render(str(value), True, (0, 0, 0))
                screen.blit(label_surf, (self.x + 6, y))
                screen.blit(value_surf, (self.x + 100, y))
                y += 16

        # Иконки снизу
        for i, btn in enumerate(self.buttons):
            r = self._button_rect(i)
            enabled = btn.get('enabled', True)
            hover = (i == self.hover_index)

            if not enabled:
                bg = (170, 170, 170)
                fg = (80, 80, 80)
            elif hover:
                bg = (255, 240, 180)
                fg = (0, 0, 0)
            else:
                bg = (255, 255, 255)
                fg = (0, 0, 0)

            pygame.draw.rect(screen, bg, r)
            pygame.draw.rect(screen, (0, 0, 0), r, 1)

            icon = btn.get('icon')
            if icon:
                self._draw_icon(screen, r.x + 4, r.y + 4, r.width - 8, icon, fg)

        if 0 <= self.hover_index < len(self.buttons):
            self._draw_tooltip(screen, self.hover_index)

    def _draw_build(self, screen):
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, (220, 200, 150), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 2)

        # Шапка
        header_rect = pygame.Rect(self.x + self.padding,
                                  self.y + self.padding,
                                  self.width - self.padding * 2,
                                  self.build_header - 2)
        pygame.draw.rect(screen, (180, 160, 120), header_rect)
        pygame.draw.rect(screen, (0, 0, 0), header_rect, 1)

        line1_left = self.build_info_title or "Штаб"
        line1_right = ""
        for label, value in self.build_info_rows:
            if label == 'HP':
                line1_right = f"HP: {value}"
                break
        t1 = self.font_header.render(line1_left, True, (0, 0, 0))
        screen.blit(t1, (header_rect.x + 6, header_rect.y + 4))
        if line1_right:
            t1r = self.font_header_info.render(line1_right, True, (0, 0, 0))
            screen.blit(t1r, (header_rect.right - t1r.get_width() - 6,
                              header_rect.y + 5))

        cp_text = f"КП: {int(self.command_points)}    +{self.cp_rate * FPS:.1f}/сек"
        t2 = self.font_header_info.render(cp_text, True, (0, 0, 0))
        screen.blit(t2, (header_rect.x + 6, header_rect.y + 24))

        # Ячейки
        for i, u in enumerate(self.build_units):
            r = self._cell_rect(i)
            enabled = u.get('enabled', True)
            hover = (i == self.hover_index) and enabled

            if not enabled:
                bg = (170, 170, 170)
                fg = (80, 80, 80)
            elif hover:
                bg = (255, 240, 180)
                fg = (0, 0, 0)
            else:
                bg = (255, 255, 255)
                fg = (0, 0, 0)

            pygame.draw.rect(screen, bg, r)
            pygame.draw.rect(screen, (0, 0, 0), r, 1)

            icon_name = u.get('icon', 'infantry')
            team = u.get('team', 'red')
            self._draw_unit_icon(screen, r.x + 4, r.y + 4, 28, icon_name, team, fg)

            label = u.get('label', '')
            txt = self.font_cell.render(label, True, fg)
            screen.blit(txt, (r.x + 36, r.y + 8))

            cost_text = f"{u['cost']} КП"
            cost_color = (0, 0, 0) if enabled else (100, 100, 100)
            ct = self.font_cost.render(cost_text, True, cost_color)
            screen.blit(ct, (r.x + 36, r.y + 28))

        if 0 <= self.hover_index < len(self.build_units):
            u = self.build_units[self.hover_index]
            if not u.get('enabled', True):
                self._draw_build_tooltip(
                    screen, self.hover_index,
                    f"Недостаточно КП: нужно {u['cost']}")

    def _draw_build_tooltip(self, screen, index, text):
        txt_surf = self.font_tooltip.render(text, True, (255, 255, 255))
        pad = 6
        tip_w = txt_surf.get_width() + pad * 2
        tip_h = txt_surf.get_height() + pad * 2

        r = self._cell_rect(index)
        tip_x = r.x + r.width // 2 - tip_w // 2
        tip_y = r.y - tip_h - 4
        if tip_x < 4:
            tip_x = 4
        if tip_x + tip_w > WIDTH - 4:
            tip_x = WIDTH - 4 - tip_w
        if tip_y < 4:
            tip_y = r.y + r.height + 4

        tip_rect = pygame.Rect(tip_x, tip_y, tip_w, tip_h)
        pygame.draw.rect(screen, (30, 30, 30), tip_rect)
        pygame.draw.rect(screen, (255, 255, 255), tip_rect, 1)
        screen.blit(txt_surf, (tip_x + pad, tip_y + pad))

    def _draw_tooltip(self, screen, index):
        btn = self.buttons[index]
        label = btn.get('label', '')
        enabled = btn.get('enabled', True)
        text = f"{label}" if enabled else f"{label} — не хватает логистики"

        txt_surf = self.font_tooltip.render(text, True, (255, 255, 255))
        pad = 6
        tip_w = txt_surf.get_width() + pad * 2
        tip_h = txt_surf.get_height() + pad * 2
        r = self._button_rect(index)
        tip_x = r.x + r.width // 2 - tip_w // 2
        tip_y = r.y - tip_h - 4
        if tip_x < 4:
            tip_x = 4
        if tip_x + tip_w > WIDTH - 4:
            tip_x = WIDTH - 4 - tip_w
        if tip_y < 4:
            tip_y = r.y + r.height + 4
        tip_rect = pygame.Rect(tip_x, tip_y, tip_w, tip_h)
        pygame.draw.rect(screen, (30, 30, 30), tip_rect)
        pygame.draw.rect(screen, (255, 255, 255), tip_rect, 1)
        screen.blit(txt_surf, (tip_x + pad, tip_y + pad))

    # ---------- Иконки ----------

    def _draw_unit_icon(self, screen, x, y, size, unit_type, team, color):
        tex = None
        if self.textures:
            tex = self.textures.get(f'{unit_type}_{team}')
        if tex is not None:
            tw, th = tex.get_size()
            scale = size / max(tw, th)
            nw = max(1, int(tw * scale))
            nh = max(1, int(th * scale))
            scaled = pygame.transform.scale(tex, (nw, nh))
            screen.blit(scaled, (x + (size - nw) // 2,
                                 y + (size - nh) // 2))
            return

        # Fallback
        base_color = (200, 60, 60) if team == 'red' else (60, 60, 200)
        if unit_type == 'infantry':
            pygame.draw.circle(screen, base_color, (x + size // 2, y + size // 3), 4)
            pygame.draw.line(screen, base_color,
                             (x + size // 2, y + size // 3 + 4),
                             (x + size // 2, y + size - 2), 3)
        elif unit_type == 'engineer':
            pygame.draw.rect(screen, base_color, (x + 4, y + 4, size - 8, size - 8))
        elif unit_type == 'motorized':
            pygame.draw.rect(screen, base_color, (x + 2, y + 8, size - 4, size - 12))
            pygame.draw.circle(screen, (0, 0, 0), (x + 6, y + size - 4), 3)
            pygame.draw.circle(screen, (0, 0, 0), (x + size - 6, y + size - 4), 3)
        elif unit_type == 'tank':
            pygame.draw.rect(screen, base_color, (x + 2, y + 6, size - 4, size - 10))
            pygame.draw.circle(screen, base_color, (x + size // 2, y + 8), 5)
        elif unit_type == 'artillery':
            pygame.draw.rect(screen, base_color, (x + 2, y + size - 10, size - 4, 6))
            pygame.draw.line(screen, base_color,
                             (x + size // 2, y + size - 10),
                             (x + size // 2 + 4, y + 2), 3)
        else:
            pygame.draw.rect(screen, base_color, (x + 2, y + 2, size - 4, size - 4))

    @staticmethod
    def _draw_icon(screen, x, y, size, name, color):
        if name == 'outpost':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y), (x, y + size // 2), (x + size, y + size // 2)])
            pygame.draw.rect(screen, color, (x + 3, y + size // 2, size - 6, size // 2 - 1))
        elif name == 'teeth':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y), (x, y + size - 1), (x + size, y + size - 1)])
        elif name == 'mines':
            pygame.draw.circle(screen, color, (x + size // 2, y + size // 2), size // 2 - 1)
            pygame.draw.circle(screen, (255, 255, 255),
                               (x + size // 2, y + size // 2), size // 2 - 4)
        elif name == 'warehouse':
            pygame.draw.rect(screen, color, (x + 1, y + 2, size - 2, size - 4), 2)
            pygame.draw.line(screen, color,
                             (x + 1, y + size // 2), (x + size - 1, y + size // 2), 2)
        elif name == 'bucket':
            pygame.draw.rect(screen, color, (x + 1, y + 3, size - 2, size - 6), 2)
            pygame.draw.line(screen, color, (x + 3, y + 1), (x + size - 3, y + 1), 2)
        elif name == 'load':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y + size - 1), (x, y + size // 2), (x + size, y + size // 2)])
            pygame.draw.rect(screen, color, (x + size // 2 - 1, y, 3, size // 2))
        elif name == 'unload':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y), (x, y + size // 2), (x + size, y + size // 2)])
            pygame.draw.rect(screen, color, (x + size // 2 - 1, y + size // 2, 3, size // 2))
        elif name == 'fire':
            pygame.draw.circle(screen, color, (x + size // 2, y + size // 2), size // 2 - 2, 2)
            pygame.draw.line(screen, color, (x + size // 2, y), (x + size // 2, y + size), 1)
            pygame.draw.line(screen, color, (x, y + size // 2), (x + size, y + size // 2), 1)
        elif name == 'hold':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y), (x + size - 1, y + 3),
                (x + size - 1, y + size - 4), (x + size // 2, y + size),
                (x, y + size - 4), (x, y + 3)], 2)
        elif name == 'shield_off':
            pygame.draw.polygon(screen, color, [
                (x + size // 2, y), (x + size - 1, y + 3),
                (x + size - 1, y + size - 4), (x + size // 2, y + size),
                (x, y + size - 4), (x, y + 3)], 2)
            pygame.draw.line(screen, color, (x, y), (x + size, y + size), 2)