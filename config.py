# config.py
import sys
import os

# Определение базовой директории для ресурсов
if getattr(sys, 'frozen', False):
    # Запущено как EXE (PyInstaller)
    BASE_DIR = sys._MEIPASS
else:
    # Запущено как обычный .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEXTURE_DIR = os.path.join(BASE_DIR, "textures")

# ---------- Окно ----------
WIDTH, HEIGHT = 1000, 600
FPS = 60

UNIT_WIDTH = 32
UNIT_HEIGHT = 24

# ---------- Цвета ----------
RED = (200, 0, 0)
BLUE = (0, 0, 200)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
PATH_DOT_COLOR = (255, 255, 255)
BG_COLOR = (55, 85, 55)
GRID_COLOR = (65, 95, 65)

# ---------- Юниты ----------
UNIT_TYPES = {
    'infantry': {
        'hp': 100,
        'speed': 0.5,
        'attack_range': 100,
        'attack_damage': 3,
        'attack_cooldown_max': 30,
        'heal_cost_per_2hp': 1,
    },
    'motorized': {
        'hp': 125,
        'speed': 1.0,
        'attack_range': 120,
        'attack_damage': 2,
        'attack_cooldown_max': 15,
        'heal_cost_per_2hp': 5,
    },
    'tank': {
        'hp': 145,
        'speed': 0.7,
        'attack_range': 140,
        'attack_damage': 5,
        'attack_cooldown_max': 30,
        'heal_cost_per_2hp': 10,
    },
    'engineer': {
        'hp': 70,
        'speed': 0.6,
        'attack_range': 0,
        'attack_damage': 0,
        'attack_cooldown_max': 0,
        'heal_cost_per_2hp': 3,
    },
    'artillery': {
        'hp': 55,
        'speed': 0.3,
        'attack_range': 280,
        'attack_damage': 20,
        'attack_cooldown_max': 0,
        'heal_cost_per_2hp': 4,
        'prepare_time': 120,
        'fire_duration': 180,
        'max_area': 50000,
    },
    'outpost': {
        'hp': 150,
        'speed': 0.0,
        'attack_range': 110,
        'attack_damage': 3,
        'attack_cooldown_max': 30,
        'heal_cost_per_2hp': 4,
        'supply_capacity': 200,
        'self_heal_rate': 2.0 / FPS,
    }
}

# ---------- Города ----------
UNIT_CONTROL_RADIUS = 40
CITY_CAPTURE_POINTS = 200
CAPTURE_SPEED = 0.3
HEAL_PER_FRAME = 3.0 / FPS
CITY_INITIAL_SUPPLY = 50.0

# ---------- Авиаудар ----------
AIRSTRIKE_SPEED = 8
AIRSTRIKE_DAMAGE = 50
AIRSTRIKE_RADIUS = 60
AIRSTRIKE_COOLDOWN = 0
PLANE_TEXTURE_RED = "plane_red.png"
PLANE_TEXTURE_BLUE = "plane_blue.png"
CURSOR_TEXTURE = "attack_cursor.png"
AIRSTRIKE_DELAY = 360

# ---------- Снабжение ----------
SUPPLY_RATE_PER_FRAME = 2.0 / FPS
SUPPLY_BASE_HP = 100
SUPPLY_BASE_RESPAWN_TIME = 3600
SUPPLY_BASE_SPEED = 1.0
SUPPLY_BASE_WIDTH = 32
SUPPLY_BASE_HEIGHT = 32
BORDER_MARGIN = 100
ROAD_COLOR = (255, 153, 0)

# ---------- Конвой ----------
CONVOY_HP = 30
CONVOY_CAPACITY = 100
CONVOY_SPEED = 1.0
CONVOY_TRANSFER_TIME = 180

ROAD_SPEED_BONUS = 0.5

# ---------- Защита местности ----------
# Пехота лучше в городе, мото хуже в городе.
TERRAIN_DEFENSE_BY_TYPE = {
    'infantry':  {'forest': 0.15, 'city': 0.30},
    'motorized': {'forest': 0.15, 'city': 0.10},
    'tank':      {'forest': 0.00, 'city': 0.20},
    'engineer':  {'forest': 0.20, 'city': 0.35},
    'artillery': {'forest': 0.05, 'city': 0.15},
    'outpost':   {'forest': 0.25, 'city': 0.35},
}

TERRAIN_SPEED_MULTIPLIER_BY_TYPE = {
    'infantry':  {'forest': 1.0,  'city': 1.0},
    'motorized': {'forest': 0.65, 'city': 0.75},
    'tank':      {'forest': 0.55, 'city': 0.65},
    'engineer':  {'forest': 1.0,  'city': 1.0},
    'artillery': {'forest': 0.7,  'city': 0.8},
}

# ---------- Линия фронта ----------
INFLUENCE_CELL_SIZE = 20
INFLUENCE_RADIUS_CITY = 200
INFLUENCE_RADIUS_BASE = 150
INFLUENCE_UNIT_FACTOR = 1.0
INFLUENCE_UNIT_FACTOR_BY_TYPE = {
    'infantry': 1.0,
    'motorized': 1.0,
    'tank': 1.0,
    'engineer': 0.8,
    'artillery': 0.7,
    'outpost': 1.0,
}
INFLUENCE_THRESHOLD = 0.05
CAPTURE_THRESHOLD = 0.7

# ---------- Инженер ----------
ENGINEER_BUILD_RANGE = 40
ENGINEER_BUILD_TIME = 300
MAX_ROAD_ATTACH_DIST = 100

# ---------- Окружение ----------
ENCIRCLEMENT_DAMAGE_PER_FRAME = 5.0 / FPS

# ---------- Опорник ----------
OUTPOST_SUPPLY_RADIUS = 60
OUTPOST_SUPPLY_RESERVE = 50
OUTPOST_HEAL_PER_FRAME = 1.5 / FPS

# ---------- Территория ----------
NEUTRAL_COLOR = (180, 180, 180, 100)
PERSONAL_CLAIM_RADIUS = 50

# ---------- Блокировка дорог ----------
ROAD_BLOCK_RADIUS = 15
ROAD_ATTACH_DIST = 50

# ---------- Логистика инженера ----------
ENGINEER_MAX_LOGISTICS = 150
ENGINEER_LOGISTICS_RATE = 2.0 / FPS
ENGINEER_REGEN_COST_PER_POINT = 1.0

COST_OUTPOST = 100
COST_DRAGON_TEETH = 75
COST_MINES = 125
COST_WAREHOUSE = 50

# ---------- Склад ----------
WAREHOUSE_HP = 60
WAREHOUSE_SUPPLY_CAPACITY = 100
WAREHOUSE_DEFENSE_RADIUS = 40
WAREHOUSE_DEFENSE_BONUS = 0.20
WAREHOUSE_WIDTH = 24
WAREHOUSE_HEIGHT = 20
WAREHOUSE_INFLUENCE_RADIUS = 60

# ---------- Окапывание ----------
DIG_IN_TIME = 45
DIG_IN_MAX_BONUS = 0.20
DIG_IN_DAMAGE_BONUS = 0.05
DIG_IN_TYPES = ('infantry', 'motorized', 'artillery')
MAX_TOTAL_DEFENSE = 0.60

# ---------- Артиллерия: пробитие укреплений ----------
ARTILLERY_FORTIFICATION_PENETRATION = 0.30

# ---------- Демонтаж и постройка ----------
DEMOLISH_TIME = 120
DEMOLISH_ENEMY_PROXIMITY = 60
MINE_DISCOVERY_RADIUS = 75
ENGINEER_PATH_TIMEOUT = 300
BUILD_OBJECT_TIME = 30
ENGINEER_NEAR_DIST = 25
DEMOLISH_LINE_PICKUP = 20
MINE_PLACE_OFFSET = 80

# ---------- Зубья дракона ----------
DRAGON_TEETH_HP = 200
DRAGON_TEETH_SPACING = 40
DRAGON_TEETH_RADIUS = 6
DRAGON_TEETH_SLOW_TANK = 0.2
DRAGON_TEETH_SLOW_INFANTRY = 0.8

# ---------- Мины ----------
MINE_SPACING = 30
MINE_TRIGGER_RADIUS = 15
MINE_DAMAGE_MIN = 25
MINE_DAMAGE_MAX = 40
MINE_ARM_TIME = 60

# ---------- Линии построек ----------
MAX_LINE_LENGTH = 350

# ---------- Легаси ----------
MAX_CLAIM_DISTANCE = 4

# ---------- Штаб ----------
HQ_HP = 50
HQ_WIDTH = 40
HQ_HEIGHT = 32
HQ_RESPAWN_TIME = 3600
HQ_OFFSET_FROM_BASE_X = 40
HQ_OFFSET_FROM_BASE_Y = -80

# ---------- Очки командования ----------
COMMAND_POINTS_START = 125.0
COMMAND_POINTS_MAX = 1000.0
CP_BASE_RATE = 2.0 / FPS
CP_TERRITORY_BONUS = 4.0 / FPS
CP_UNIT_PENALTY_PER = 0.05
CP_UNIT_PENALTY_MAX = 0.7

UNIT_COSTS = {
    'infantry': 100,
    'engineer': 75,
    'motorized': 170,
    'tank': 250,
    'artillery': 200,
}

SPAWN_RADIUS_MIN = 40
SPAWN_RADIUS_MAX = 80