# kdc.py
import socket
import pickle
import threading
import logging
from config import KDC_PORT, KDC_HOST, SHARED_KEYS
from crypto import encrypt, generate_key

def handle_client(conn, addr):
    try:
        data = conn.recv(4096)
        if not data:
            return
        msg = pickle.loads(data)
        A = msg['A']
        B = msg['B']
        N_A = msg['N_A']

        logging.info(f"← От {A.decode()} (адрес {addr}): запрос сессии с {B.decode()}, N_A={N_A}")

        if A not in SHARED_KEYS or B not in SHARED_KEYS:
            logging.error(f"Неизвестный клиент: {A} или {B}")
            return

        K_AB = generate_key()
        logging.info(f"Сгенерирован сессионный ключ K_AB для {A.decode()}–{B.decode()}")

        ticket_for_B = {'K_AB': K_AB, 'A': A}
        encrypted_ticket = encrypt(pickle.dumps(ticket_for_B), SHARED_KEYS[B])

        reply_to_A = {
            'K_AB': K_AB,
            'B': B,
            'N_A': N_A,
            'Ticket': encrypted_ticket
        }
        encrypted_reply = encrypt(pickle.dumps(reply_to_A), SHARED_KEYS[A])

        conn.sendall(encrypted_reply)
        logging.info(f"→ Отправлен ответ {A.decode()}")

    except Exception as e:
        logging.error(f"Ошибка при обработке запроса от {addr}: {e}")
    finally:
        conn.close()

def start_kdc():
    logging.info(f"Запуск KDC на {KDC_HOST}:{KDC_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((KDC_HOST, KDC_PORT))
        s.listen(5)
        logging.info("KDC готов принимать подключения")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()