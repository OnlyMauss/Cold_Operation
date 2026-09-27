# helpers.py
import math
from config import *


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    nx = x1 + t * dx
    ny = y1 + t * dy
    return math.hypot(px - nx, py - ny)


def build_info_for(obj):
    """Возвращает (title, rows) для инфо-панели, или None."""
    if obj is None:
        return None

    # ---- Штаб ----
    if getattr(obj, 'unit_type', None) == 'headquarters':
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        return (f"Штаб ({team_name})", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Защита", f"{int(obj.current_defense * 100)}%"),
        ])

    # ---- Мина ----
    if getattr(obj, 'unit_type', None) == 'mine':
        return ("Мина", [
            ("Урон", f"{MINE_DAMAGE_MIN}–{MINE_DAMAGE_MAX}"),
            ("Радиус", f"{MINE_TRIGGER_RADIUS} px"),
        ])

    # ---- Зубья ----
    if getattr(obj, 'unit_type', None) == 'dragon_teeth':
        return ("Зубья дракона", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Эффект", "Танки/мото ×0.2"),
        ])

    # ---- Склад ----
    if getattr(obj, 'unit_type', None) == 'warehouse':
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        return (f"Склад ({team_name})", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Снабжение", f"{int(obj.supply_hp)} / {obj.supply_capacity}"),
        ])

    # ---- Опорник ----
    if getattr(obj, 'unit_type', None) == 'outpost':
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        return (f"Опорник ({team_name})", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Снабжение", f"{int(obj.supply_hp)} / {obj.supply_capacity}"),
            ("Радиус атаки", f"{obj.attack_range} px"),
            ("Радиус снабжения", f"{OUTPOST_SUPPLY_RADIUS} px"),
            ("Защита", f"{int(obj.current_defense * 100)}%"),
        ])

    # ---- Конвой ----
    if hasattr(obj, 'cargo'):
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        return (f"Конвой ({team_name})", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Груз", f"{obj.cargo} / {CONVOY_CAPACITY}"),
        ])

    # ---- База снабжения ----
    if hasattr(obj, 'active') and not hasattr(obj, 'unit_type'):
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        return (f"База снабжения ({team_name})", [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Статус", "Активна" if obj.active else "Уничтожена"),
        ])

    # ---- Обычный юнит ----
    if hasattr(obj, 'unit_type'):
        team_name = 'Красный' if obj.team == 'red' else 'Синий'
        type_names = {
            'infantry': 'Пехота',
            'motorized': 'Мотострелки',
            'tank': 'Танк',
            'engineer': 'Инженер',
            'artillery': 'Артиллерия',
        }
        tname = type_names.get(obj.unit_type, obj.unit_type)
        rows = [
            ("HP", f"{int(obj.hp)} / {obj.max_hp}"),
            ("Скорость", f"{obj.speed:.1f}"),
            ("Дальность", f"{obj.attack_range} px"),
            ("Урон", f"{obj.attack_damage}"),
            ("Защита", f"{int(obj.current_defense * 100)}%"),
        ]
        if getattr(obj, 'can_dig_in', False):
            rows.append(("Окоп", f"{int(obj.entrenchment / DIG_IN_MAX_BONUS * 100)}%"))
        if obj.unit_type == 'engineer':
            rows.append(("Логистика", f"{int(obj.logistics)} / {obj.max_logistics}"))
        return (f"{tname} ({team_name})", rows)

    return None