# settings_io.py
import json
import os
import sys

# Файл настроек рядом с .exe (или рядом с main.py, если запуск из исходников)
if getattr(sys, 'frozen', False):
    SETTINGS_DIR = os.path.dirname(sys.executable)
else:
    SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

SETTINGS_KEYS = [
    "attack_zones",
    "all_paths",
    "city_resources",
    "base_zone",
    "shields",
    "frontline",
    "unit_hp",
    "info_panel",
]


def save_settings(items):
    data = {}
    for i, key in enumerate(SETTINGS_KEYS):
        if i < len(items):
            data[key] = bool(items[i].get('active', False))
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Не удалось сохранить настройки: {e}")


def load_settings(items):
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for i, key in enumerate(SETTINGS_KEYS):
            if i < len(items) and key in data:
                items[i]['active'] = bool(data[key])
    except Exception as e:
        print(f"Не удалось загрузить настройки: {e}")