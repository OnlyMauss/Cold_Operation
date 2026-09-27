# terrain.py
from config import *


class Forest:
    def __init__(self, vertices):
        self.vertices = vertices

    def point_inside(self, x, y):
        n = len(self.vertices)
        inside = False
        p1x, p1y = self.vertices[0]
        for i in range(n + 1):
            p2x, p2y = self.vertices[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside


def get_defense(x, y, unit_type, cities, forests):
    """
    Бонус защиты от местности для данного типа юнита.
    Город приоритетнее леса, если полигоны пересекаются.
    Защита в городе не зависит от владельца — она даёт укрытие всем.
    """
    type_bonus = TERRAIN_DEFENSE_BY_TYPE.get(unit_type, {})
    for city in cities:
        if city.point_in_polygon(x, y):
            return type_bonus.get('city', 0.0)
    for forest in forests:
        if forest.point_inside(x, y):
            return type_bonus.get('forest', 0.0)
    return 0.0


def get_speed_multiplier(x, y, unit_type, cities, forests):
    """
    Множитель скорости для юнита в зависимости от местности.
    Город приоритетнее леса.
    """
    type_mult = TERRAIN_SPEED_MULTIPLIER_BY_TYPE.get(unit_type, {})
    for city in cities:
        if city.point_in_polygon(x, y):
            return type_mult.get('city', 1.0)
    for forest in forests:
        if forest.point_inside(x, y):
            return type_mult.get('forest', 1.0)
    return 1.0