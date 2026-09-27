# firewall.py
import ctypes
import subprocess
import sys
import os


RULE_NAME_TCP = "ColdOperation TCP"
RULE_NAME_UDP = "ColdOperation UDP"
TCP_PORT = 5555
UDP_PORT = 5556
RADMIN_RANGE = "26.0.0.0/8"


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run_hidden(args, timeout=5):
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        return None


def rule_exists(name):
    if sys.platform != 'win32':
        return True
    r = _run_hidden(['netsh', 'advfirewall', 'firewall', 'show', 'rule',
                     f'name={name}'])
    if r is None:
        return False
    return 'No rules match' not in r.stdout and name in r.stdout


def rules_exist():
    return rule_exists(RULE_NAME_TCP) and rule_exists(RULE_NAME_UDP)


def add_rules():
    """Добавляет правила. Требует прав администратора."""
    for name in (RULE_NAME_TCP, RULE_NAME_UDP):
        _run_hidden(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                     f'name={name}'])

    _run_hidden([
        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
        f'name={RULE_NAME_TCP}',
        'dir=in', 'action=allow', 'protocol=TCP',
        f'localport={TCP_PORT}',
        f'remoteip={RADMIN_RANGE}',
        'profile=any', 'enable=yes',
    ])
    _run_hidden([
        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
        f'name={RULE_NAME_UDP}',
        'dir=in', 'action=allow', 'protocol=UDP',
        f'localport={UDP_PORT}',
        f'remoteip={RADMIN_RANGE}',
        'profile=any', 'enable=yes',
    ])


def _build_relaunch_params():
    """Аргументы для перезапуска с админскими правами."""
    if getattr(sys, 'frozen', False):
        # ColdOperation.exe → просто запускаем тот же exe
        return ''
    # python main.py → запускаем python с тем же скриптом
    script = os.path.abspath(sys.argv[0])
    return f'"{script}"'


def _show_message(title, text, warning=False):
    try:
        flags = 0x30 if warning else 0x40
        ctypes.windll.user32.MessageBoxW(0, text, title, flags)
    except Exception:
        print(f"{title}: {text}")


def ensure_firewall():
    """
    Проверяет правила брандмауэра при старте.
    - Если есть → возвращает.
    - Если нет и мы админ → добавляет сразу.
    - Если нет и мы не админ → UAC, перезапуск с админ-правами,
      оригинальный процесс завершается.
    """
    if sys.platform != 'win32':
        return

    # Уже есть
    if rules_exist():
        return

    # У нас уже админские права (например, пользователь запустил exe "от имени админа")
    if is_admin():
        add_rules()
        return

    # Показываем UAC и перезапускаемся
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, _build_relaunch_params(), None, 1
        )
    except Exception as e:
        print(f"[Firewall] Ошибка UAC: {e}")
        return

    if result > 32:
        # UAC показан, elevated-процесс запущен.
        # Оригинал должен завершиться, чтобы не было двух окон.
        sys.exit(0)
    else:
        # UAC отменён (1223 = ERROR_CANCELLED) или другая ошибка
        _show_message(
            "Cold Operation",
            "Без разрешения Windows сетевая игра работать не будет.\n\n"
            "Одиночная игра доступна без ограничений.\n\n"
            "Чтобы включить сетевую игру:\n"
            "1. Перезапустите игру\n"
            "2. В окне запроса нажмите «Да»",
            warning=True
        )
        # Продолжаем работу — одиночная доступна, сетевая нет
        return