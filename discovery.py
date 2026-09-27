# discovery.py
import socket
import threading
import json
import time


DISCOVERY_PORT = 5556
DISCOVERY_MAGIC = "COLD_OP_DISCOVER"
DISCOVERY_RESPONSE = "COLD_OP_SERVER"


class ServerDiscoveryBroadcaster:
    """Слушает UDP broadcast, отвечает клиентам информацией о сервере."""

    def __init__(self, server_name="Cold Operation Server", port=5555):
        self.server_name = server_name
        self.game_port = port
        self.sock = None
        self.running = False
        self.thread = None
        self.player_count_callback = None

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('0.0.0.0', DISCOVERY_PORT))
            self.sock.settimeout(0.5)
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"[Discovery] Не удалось запустить: {e}")
            return False

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _loop(self):
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode('utf-8', errors='ignore').strip()
                if msg == DISCOVERY_MAGIC:
                    players = 0
                    if self.player_count_callback:
                        try:
                            players = self.player_count_callback()
                        except Exception:
                            pass
                    response = {
                        'type': DISCOVERY_RESPONSE,
                        'name': self.server_name,
                        'port': self.game_port,
                        'players': players,
                    }
                    self.sock.sendto(json.dumps(response).encode('utf-8'), addr)
            except socket.timeout:
                continue
            except Exception:
                break


class ServerDiscoveryScanner:
    """Отправляет broadcast и собирает ответы серверов."""

    def __init__(self):
        self.sock = None
        self.servers = {}
        self.running = False
        self.thread = None

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', 0))
            self.sock.settimeout(0.3)
            self.running = True
            self.servers.clear()
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"[Scanner] Ошибка: {e}")
            return False

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def is_scanning(self):
        return self.thread is not None and self.thread.is_alive()

    def _loop(self):
        # Отправляем broadcast на разные адреса
        targets = [
            ('255.255.255.255', DISCOVERY_PORT),
            ('<broadcast>', DISCOVERY_PORT),
        ]
        for t in targets:
            try:
                self.sock.sendto(DISCOVERY_MAGIC.encode('utf-8'), t)
            except Exception:
                pass

        start = time.time()
        while self.running and time.time() - start < 3.0:
            try:
                data, addr = self.sock.recvfrom(1024)
                try:
                    obj = json.loads(data.decode('utf-8', errors='ignore'))
                except Exception:
                    continue
                if obj.get('type') != DISCOVERY_RESPONSE:
                    continue
                ip = addr[0]
                port = obj.get('port', 5555)
                key = (ip, port)
                self.servers[key] = {
                    'ip': ip,
                    'port': port,
                    'name': obj.get('name', 'Server'),
                    'players': obj.get('players', 0),
                }
            except socket.timeout:
                continue
            except Exception:
                break

    def get_servers(self):
        return list(self.servers.values())