# crypto.py
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import pickle


def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Шифрует данные с помощью AES-GCM.
    Возвращает: nonce (12 байт) || ciphertext || tag (16 байт)
    """
    if len(key) not in (16, 24, 32):
        raise ValueError("Ключ должен быть 16, 24 или 32 байта")
    
    nonce = os.urandom(12)  # 96 бит
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    return nonce + ciphertext + encryptor.tag

def decrypt(ciphertext_with_nonce_tag: bytes, key: bytes) -> bytes:
    """
    Расшифровывает данные, зашифрованные encrypt().
    """
    if len(key) not in (16, 24, 32):
        raise ValueError("Неверная длина ключа")
    if len(ciphertext_with_nonce_tag) < 12 + 16:
        raise ValueError("Слишком короткое сообщение")
    
    nonce = ciphertext_with_nonce_tag[:12]
    tag = ciphertext_with_nonce_tag[-16:]
    ciphertext = ciphertext_with_nonce_tag[12:-16]
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()

    return decryptor.update(ciphertext) + decryptor.finalize()

def generate_key(length: int = 32) -> bytes:
    """Генерирует криптостойкий ключ (AES-128 по умолчанию)."""
    if length not in (16, 24, 32):
        raise ValueError("Длина ключа должна быть 16, 24 или 32")
    return os.urandom(length)

def generate_nonce() -> int:
    """Генерирует 64-битный nonce для протокола (не путать с AES nonce!)."""
    return int.from_bytes(os.urandom(8), 'big')