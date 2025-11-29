# client.py
import socket
import pickle
import threading

from threading import Thread
import sys
import time
import logging
import queue

from config import KDC_HOST, KDC_PORT, SHARED_KEYS, DEFAULT_CLIENT_BASE_PORT
from crypto import encrypt, decrypt, generate_nonce

import os

def save_session_key(local_name: str, peer_name: str, key: bytes):
    """Сохраняет сессионный ключ K_AB в файл keys/{local}_{peer}.key"""
    os.makedirs("keys", exist_ok=True)
    
    first, second = sorted([local_name, peer_name])
    filename = f"keys/{first}_{second}.key"
    with open(filename, 'wb') as f:
        f.write(key)
    print(f"[+] Сессионный ключ сохранён в {filename}")

class NeedhamSchroederClient:
    def __init__(self, name: str, port: int):
        self.name = name.encode()
        self.port = port
        self.key = SHARED_KEYS.get(self.name)
        if self.key is None:
            raise ValueError(f"Клиент {name} не зарегистрирован в SHARED_KEYS")
        self.sessions = {}  # {peer_name: K_AB}

    def start_server(self):
        """Слушает входящие подключения от других клиентов."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("localhost", self.port))
        server_sock.listen(5)
        logging.info(f"Клиент {self.name.decode()} слушает порт {self.port}")

        while True:
            try:
                conn, addr = server_sock.accept()
                threading.Thread(target=self.handle_incoming, args=(conn, addr)).start()
            except Exception as e:
                logging.error(f"Ошибка сервера: {e}")

    def handle_incoming(self, conn, addr):
        try:
            encrypted_ticket = conn.recv(4096)
            logging.info(f"Шаг 3: ← От {addr}: получено зашифрованное сообщение (возможно, билет)")

            ticket = pickle.loads(decrypt(encrypted_ticket, self.key))
            K_AB = ticket['K_AB']
            peer_name = ticket['A']
            peer_str = peer_name.decode()
            logging.info(f"Шаг 3: Расшифрован билет от {peer_str}; установлен K_AB")

            self.sessions[peer_str] = K_AB

            # Шаг 4: отправить N_B
            N_B = generate_nonce()
            logging.info(f"Шаг 4: Сгенерирован N_B = {N_B} для {peer_str}")
            msg = pickle.dumps(N_B)
            conn.sendall(encrypt(msg, K_AB))
            logging.info(f"Шаг 4: → Отправлен N_B клиенту {peer_str}")

            # Шаг 5: получить N_B - 1
            encrypted_resp = conn.recv(4096)
            N_B_minus = pickle.loads(decrypt(encrypted_resp, K_AB))
            if N_B_minus == N_B - 1:
                logging.info(f"✅ Взаимная аутентификация с {peer_str} успешна!")
                save_session_key(self.name.decode(), peer_str, K_AB)
            else:
                logging.warning(f"❌ Неудачная аутентификация с {peer_str}: N_B-1 не совпадает")
        except Exception as e:
            logging.error(f"Ошибка при обработке входящего сообщения: {e}")
        finally:
            conn.close()

    def initiate_session(self, target_name: str, target_port: int):
        """Инициировать протокол с другим клиентом."""
        if target_name == self.name.decode():
            logging.warning("Нельзя инициировать сессию с самим собой")
            return

        logging.info(f"Инициация сессии с клиентом {target_name} (порт {target_port})")

        # Шаг 1: запрос к KDC
        N_A = generate_nonce()
        request = {'A': self.name, 'B': target_name.encode(), 'N_A': N_A}
        logging.info(f"Шаг 1: → Отправка KDC запроса: A={self.name.decode()}, B={target_name}, N_A={N_A}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((KDC_HOST, KDC_PORT))
            s.sendall(pickle.dumps(request))
            encrypted_resp = s.recv(4096)

        resp = pickle.loads(decrypt(encrypted_resp, self.key))
        if resp['N_A'] != N_A:
            logging.error("N_A не совпадает — возможна атака!")
            return

        K_AB = resp['K_AB']
        ticket = resp['Ticket']
        self.sessions[target_name] = K_AB

        logging.info(f"Шаг 2: ← Получен K_AB и ticket от KDC")

        # Шаг 3: отправить билет
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("localhost", target_port))
            s.sendall(ticket)
            logging.info(f"Шаг 3: → Отправлен билет клиенту {target_name}")

            # Шаг 4: получить N_B
            encrypted_N_B = s.recv(4096)
            N_B = pickle.loads(decrypt(encrypted_N_B, K_AB))
            logging.info(f"Шаг 4: ← Получен N_B = {N_B} от {target_name}")

            # Шаг 5: отправить N_B - 1
            reply = pickle.dumps(N_B - 1)
            s.sendall(encrypt(reply, K_AB))
            logging.info(f"Шаг 5: → Отправлен N_B - 1 = {N_B - 1}")

        logging.info(f"✅ Сессия с {target_name} завершена успешно")
        save_session_key(self.name.decode(), target_name, K_AB)

    def interactive_loop(self):
        """Интерактивный ввод в отдельном потоке."""
        cmd_queue = queue.Queue()
        
        def input_reader():
            while True:
                try:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    cmd_queue.put(line.strip())
                except Exception:
                    break

        input_thread = Thread(target=input_reader, daemon=True)
        input_thread.start()

        print(f"\nКлиент {self.name.decode()} готов. Введите команды:")
        print("  connect <имя_клиента>")
        print("  exit")
        print("Пример: connect B\n")

        while True:
            try:
                try:
                    cmd = cmd_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if cmd.lower() == "exit":
                    logging.info("Завершение работы клиента")
                    break
                elif cmd.startswith("connect "):
                    parts = cmd.split()
                    if len(parts) < 2:
                        print("Использование: connect <имя>")
                        continue
                    target = parts[1]
                    if target.encode() not in SHARED_KEYS:
                        print(f"Клиент '{target}' неизвестен. Доступны: {', '.join(k.decode() for k in SHARED_KEYS.keys())}")
                        continue
                    target_port = DEFAULT_CLIENT_BASE_PORT + list(SHARED_KEYS.keys()).index(target.encode())
                    self.initiate_session(target, target_port)
                else:
                    print("Неизвестная команда. Используйте 'connect <имя>' или 'exit'.")
            except KeyboardInterrupt:
                print("\nПрервано пользователем.")
                break
            except Exception as e:
                logging.error(f"Ошибка в интерактивном режиме: {e}")

def start_client(name: str, port: int):
    client = NeedhamSchroederClient(name, port)
    server_thread = threading.Thread(target=client.start_server, daemon=True)
    server_thread.start()
    client.interactive_loop()