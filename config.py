# config.py
import os

# Порт KDC (фиксированный)
KDC_PORT = 8888
KDC_HOST = "localhost"

# Заранее разделяемые ключи (в реальности — из защищённого хранилища)
# Для демонстрации: клиенты A, B, C...
SHARED_KEYS = {
    b"A": b"secret_key_A123",
    b"B": b"secret_key_B456",
    b"C": b"secret_key_C789",
}

# Порт по умолчанию для клиента (можно переопределить)
DEFAULT_CLIENT_BASE_PORT = 9000  # client A → 9000, B → 9001 и т.д.