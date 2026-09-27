# main.py
import sys
import os

# Убеждаемся, что корень проекта в sys.path (для случая запуска из другого cwd)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


def main():
    # Проверка / добавление правил брандмауэра при старте.
    # При первом запуске может появиться UAC — игрок нажимает "Да",
    # игра перезапускается с админ-правами, добавляет правила,
    # и запускается дальше без UAC.
    try:
        from firewall import ensure_firewall
        ensure_firewall()
    except Exception as e:
        print(f"[Main] Ошибка при настройке брандмауэра: {e}")

    # Запуск игры
    from game import Game
    Game().run()


if __name__ == "__main__":
    main()