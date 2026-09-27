# network.py
import socket
import threading
import json
import time


SERVER_PORT = 5555


class NetworkServer:
    """Простой TCP-сервер на сокетах. Обменивается JSON-строками."""

    def __init__(self, port=SERVER_PORT):
        self.port = port
        self.sock = None
        self.clients = []  # [(socket, addr, name)]
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Callbacks (вызываются из сетевого потока)
        self.on_client_join = None
        self.on_client_leave = None
        self.on_message = None

    def start(self):
        if self.running:
            return False
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', self.port))
            self.sock.listen(4)
            self.running = True
            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"[Server] Ошибка запуска: {e}")
            self.running = False
            return False

    def stop(self):
        self.running = False
        with self.lock:
            for c, _, _ in self.clients:
                try:
                    c.close()
                except Exception:
                    pass
            self.clients.clear()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def _accept_loop(self):
        while self.running:
            try:
                self.sock.settimeout(0.5)
                client_sock, addr = self.sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            threading.Thread(target=self._client_loop,
                             args=(client_sock, addr), daemon=True).start()

    def _client_loop(self, client_sock, addr):
        client_sock.settimeout(0.5)
        name = None
        try:
            # Первое сообщение — имя игрока
            data = self._recv_line(client_sock)
            if data is None:
                return
            try:
                msg = json.loads(data)
                name = msg.get('name', f"Player_{addr[1]}")
            except Exception:
                name = f"Player_{addr[1]}"

            with self.lock:
                self.clients.append((client_sock, addr, name))

            self._broadcast({'type': 'player_list',
                             'players': self._player_names()})

            if self.on_client_join:
                try:
                    self.on_client_join(name)
                except Exception:
                    pass

            while self.running:
                data = self._recv_line(client_sock)
                if data is None:
                    break
                try:
                    msg = json.loads(data)
                except Exception:
                    continue
                if self.on_message:
                    try:
                        self.on_message(name, msg)
                    except Exception:
                        pass
        finally:
            with self.lock:
                self.clients = [(c, a, n) for (c, a, n) in self.clients if c != client_sock]
                remaining = self._player_names()
            try:
                client_sock.close()
            except Exception:
                pass
            self._broadcast({'type': 'player_list', 'players': remaining})
            if self.on_client_leave:
                try:
                    self.on_client_leave(name)
                except Exception:
                    pass

    def _recv_line(self, sock):
        """Читает строку байт до \n. Возвращает str или None."""
        buf = b''
        while True:
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                return None
            except Exception:
                return None
            if not chunk:
                return buf.decode('utf-8', errors='ignore') if buf else None
            buf += chunk
            if b'\n' in buf:
                line, _ = buf.split(b'\n', 1)
                return line.decode('utf-8', errors='ignore')

    def _player_names(self):
        return [n for _, _, n in self.clients]

    def _broadcast(self, msg):
        data = (json.dumps(msg) + '\n').encode('utf-8')
        with self.lock:
            for c, _, _ in list(self.clients):
                try:
                    c.sendall(data)
                except Exception:
                    pass

    def broadcast(self, msg):
        self._broadcast(msg)

    def player_count(self):
        with self.lock:
            return len(self.clients)


class NetworkClient:
    """Клиент. Подключается к серверу по IP."""

    def __init__(self):
        self.sock = None
        self.running = False
        self.thread = None
        self.connected = False

        # Callbacks
        self.on_message = None
        self.on_disconnect = None

    def connect(self, host, port=SERVER_PORT, name='Player'):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((host, port))
            self.sock.settimeout(0.5)
        except Exception as e:
            print(f"[Client] Не удалось подключиться: {e}")
            self.sock = None
            return False

        # Отправляем имя
        self.send({'name': name, 'type': 'hello'})
        self.connected = True
        self.running = True
        self.thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.thread.start()
        return True

    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.connected = False

    def _recv_loop(self):
        buf = b''
        while self.running and self.sock:
            try:
                chunk = self.sock.recv(1024)
            except socket.timeout:
                continue
            except Exception:
                break
            if not chunk:
                break
            buf += chunk
            while b'\n' in buf:
                line, buf = buf.split(b'\n', 1)
                try:
                    msg = json.loads(line.decode('utf-8', errors='ignore'))
                except Exception:
                    continue
                if self.on_message:
                    try:
                        self.on_message(msg)
                    except Exception:
                        pass
        self.connected = False
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception:
                pass

    def send(self, msg):
        if not self.sock:
            return
        try:
            data = (json.dumps(msg) + '\n').encode('utf-8')
            self.sock.sendall(data)
        except Exception as e:
            print(f"[Client] Ошибка отправки: {e}")