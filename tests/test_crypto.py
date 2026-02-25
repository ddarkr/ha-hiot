# pyright: reportMissingImports=false

from __future__ import annotations

import base64

import pytest

from custom_components.hiot.crypto import decrypt, encrypt, evp_bytes_to_key


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "hello hiot integration"

    encrypted = encrypt(plaintext)

    assert isinstance(encrypted, str)
    assert decrypt(encrypted) == plaintext


def test_decrypt_known_cryptojs_compatible_ciphertext() -> None:
    known_ciphertext = "U2FsdGVkX18xMjM0NTY3OLxwDCs+jWSm4Jv1f9w1o6g="

    assert decrypt(known_ciphertext) == "hello hiot"


def test_evp_bytes_to_key_produces_expected_key_iv() -> None:
    key, iv = evp_bytes_to_key(b"hTsEcret", b"12345678")

    assert key.hex() == "3b24b02b50dc3e53a4f1692be409b1e1a2f95c029a3d9c861f3ae8024ecc6c55"
    assert iv.hex() == "2188b854a402d352caa443698e63dc20"


def test_decrypt_raises_for_invalid_payload_header() -> None:
    invalid_payload = base64.b64encode(b"not_salted_payload").decode()

    with pytest.raises(ValueError, match="Invalid salted payload header"):
        decrypt(invalid_payload)


def test_decrypt_raises_for_wrong_passphrase() -> None:
    encrypted = encrypt("secret value", passphrase="correct-pass")

    with pytest.raises(ValueError):
        decrypt(encrypted, passphrase="wrong-pass")
