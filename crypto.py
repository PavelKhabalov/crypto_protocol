# crypto.py
import secrets

def xor_bytes(data: bytes, key: bytes) -> bytes:
    """Простое XOR-шифрование (для демонстрации)."""
    return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))

def pad(data: bytes, block_size: int = 16) -> bytes:
    """Добавляет простую padding до кратности block_size."""
    padding_len = block_size - (len(data) % block_size)
    return data + bytes([padding_len] * padding_len)

def unpad(data: bytes) -> bytes:
    """Удаляет padding."""
    pad_len = data[-1]
    return data[:-pad_len]

def encrypt(plaintext: bytes, key: bytes) -> bytes:
    padded = pad(plaintext)
    return xor_bytes(padded, key)

def decrypt(ciphertext: bytes, key: bytes) -> bytes:
    padded = xor_bytes(ciphertext, key)
    return unpad(padded)

def generate_key(length: int = 16) -> bytes:
    return secrets.token_bytes(length)

def generate_nonce() -> int:
    return secrets.randbelow(2**64)