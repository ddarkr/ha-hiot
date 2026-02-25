"""CryptoJS-compatible AES-256-CBC encryption/decryption helpers.

CryptoJS passphrase mode is OpenSSL-compatible and derives key/IV via
EVP_BytesToKey(MD5) with a random 8-byte salt and "Salted__" header.
This module reproduces that behavior for interoperability.
"""

from __future__ import annotations

import base64
import hashlib

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

from .const import AES_PASSPHRASE


OPENSSL_SALTED_PREFIX = b"Salted__"
KEY_SIZE = 32
IV_SIZE = 16
SALT_SIZE = 8


def evp_bytes_to_key(passphrase: bytes, salt: bytes) -> tuple[bytes, bytes]:
    d1 = hashlib.md5(passphrase + salt).digest()
    d2 = hashlib.md5(d1 + passphrase + salt).digest()
    d3 = hashlib.md5(d2 + passphrase + salt).digest()

    key = d1 + d2
    iv = d3
    return key, iv


def encrypt(plaintext: str, passphrase: str = AES_PASSPHRASE) -> str:
    salt = get_random_bytes(SALT_SIZE)
    key, iv = evp_bytes_to_key(passphrase.encode("utf-8"), salt)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    payload = OPENSSL_SALTED_PREFIX + salt + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt(encrypted_b64: str, passphrase: str = AES_PASSPHRASE) -> str:
    decoded = base64.b64decode(encrypted_b64)

    if len(decoded) < len(OPENSSL_SALTED_PREFIX) + SALT_SIZE:
        raise ValueError("Invalid encrypted payload length")
    if decoded[: len(OPENSSL_SALTED_PREFIX)] != OPENSSL_SALTED_PREFIX:
        raise ValueError("Invalid salted payload header")

    salt = decoded[len(OPENSSL_SALTED_PREFIX) : len(OPENSSL_SALTED_PREFIX) + SALT_SIZE]
    ciphertext = decoded[len(OPENSSL_SALTED_PREFIX) + SALT_SIZE :]
    key, iv = evp_bytes_to_key(passphrase.encode("utf-8"), salt)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode("utf-8")
