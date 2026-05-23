"""Smoke unit tests for password hashing helpers used by AuthService.register.

Full coverage lives in T15; this file just guards the round-trip contract
that register() relies on (hash -> verify).
"""

from __future__ import annotations

from rest_assured.src.services.auth.passwords import hash_password, verify_password


def test_hash_password_round_trip():
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert verify_password("correct horse battery staple", h) is True


def test_verify_password_rejects_wrong_plaintext():
    h = hash_password("alpha")
    assert verify_password("beta", h) is False


def test_hash_password_uses_random_salt_per_call():
    """T15.c: bcrypt must use a random salt, so two calls on the same plaintext
    must produce distinct hashes."""
    pw = "correct horse battery staple"
    assert hash_password(pw) != hash_password(pw)


def test_hash_password_emits_bcrypt_2b_identifier():
    """T15.d: produced hash must use the modern bcrypt `$2b$` identifier."""
    h = hash_password("pw")
    assert h.startswith("$2b$"), f"expected bcrypt $2b$ prefix, got {h[:4]!r}"
