# run.py
import argparse
import logging
import sys
from config import SHARED_KEYS, DEFAULT_CLIENT_BASE_PORT
from kdc import start_kdc
from client import start_client

def setup_logging(role: str, name: str = None):
    log_format = f"[%(asctime)s] {role}"
    if name:
        log_format += f"({name})"
    log_format += " %(levelname)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%H:%M:%S"
    )

def main():
    parser = argparse.ArgumentParser(description="Needham-Schroeder Protocol Demo")
    parser.add_argument("--role", choices=["kdc", "client"], required=True, help="Роль: kdc или client")
    parser.add_argument("--name", help="Имя клиента (A, B, C, ...) — только для role=client")
    parser.add_argument("--port", type=int, help="Порт клиента (опционально)")

    args = parser.parse_args()

    if args.role == "kdc":
        setup_logging("KDC")
        start_kdc()
    elif args.role == "client":
        if not args.name:
            sys.exit("Ошибка: для клиента требуется --name (например, A, B, C)")
        if args.name.encode() not in SHARED_KEYS:
            sys.exit(f"Клиент '{args.name}' не зарегистрирован в config.py")
        port = args.port or (DEFAULT_CLIENT_BASE_PORT + list(SHARED_KEYS.keys()).index(args.name.encode()))
        setup_logging("Client", args.name)
        start_client(args.name, port)

if __name__ == "__main__":
    main()