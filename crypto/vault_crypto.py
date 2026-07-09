"""
SecureVault Cryptography Layer
- AES-256-GCM for all data encryption
- Argon2id for key derivation from master passwords
- Random 256-bit vault key per user
"""

import os
import secrets
import string

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.low_level import hash_secret_raw, Type

NONCE_SIZE    = 12     # 96-bit GCM nonce
KEY_SIZE      = 32     # 256-bit AES key
ARGON2_TIME   = 3
ARGON2_MEMORY = 65536  # 64 MB
ARGON2_LANES  = 4


# ── Key generation ─────────────────────────────────────────────────────────

def generate_vault_key() -> bytes:
    """Generate a cryptographically-random 256-bit vault key."""
    return secrets.token_bytes(KEY_SIZE)


# ── Symmetric encryption ────────────────────────────────────────────────────

def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-256-GCM encrypt.  Returns  nonce ‖ ciphertext ‖ GCM-tag."""
    aesgcm = AESGCM(key)
    nonce  = os.urandom(NONCE_SIZE)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)


def decrypt(data: bytes, key: bytes) -> bytes:
    """AES-256-GCM decrypt.  Raises InvalidTag on tampered data."""
    aesgcm = AESGCM(key)
    nonce, ct = data[:NONCE_SIZE], data[NONCE_SIZE:]
    return aesgcm.decrypt(nonce, ct, None)


# ── Key derivation ──────────────────────────────────────────────────────────

def derive_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """
    Argon2id KDF → 256-bit key.
    Returns (key, salt).  Supply salt on verification; omit to generate fresh.
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME,
        memory_cost=ARGON2_MEMORY,
        parallelism=ARGON2_LANES,
        hash_len=KEY_SIZE,
        type=Type.ID,
    )
    return key, salt


# ── Password hashing (for master-password verification) ────────────────────

def hash_password(password: str) -> str:
    ph = PasswordHasher(
        time_cost=ARGON2_TIME,
        memory_cost=ARGON2_MEMORY,
        parallelism=ARGON2_LANES,
    )
    return ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    ph = PasswordHasher()
    try:
        return ph.verify(stored_hash, password)
    except Exception:
        return False


# ── Password generator ──────────────────────────────────────────────────────

def generate_password(
    length: int = 16,
    upper: bool = True,
    lower: bool = True,
    digits: bool = True,
    symbols: bool = True,
) -> str:
    """Cryptographically-random password using secrets.choice."""
    pool = ""
    required = []

    if upper:
        pool += string.ascii_uppercase
        required.append(secrets.choice(string.ascii_uppercase))
    if lower:
        pool += string.ascii_lowercase
        required.append(secrets.choice(string.ascii_lowercase))
    if digits:
        pool += string.digits
        required.append(secrets.choice(string.digits))
    if symbols:
        sym = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        pool += sym
        required.append(secrets.choice(sym))

    if not pool:
        pool = string.ascii_letters + string.digits

    # Fill remainder, then shuffle so required chars aren't always at front
    remainder = [secrets.choice(pool) for _ in range(length - len(required))]
    chars     = required + remainder
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def password_strength(pw: str) -> tuple[int, str]:
    """Returns (score 0-5, label)."""
    score = 0
    if len(pw) >= 12:  score += 1
    if len(pw) >= 16:  score += 1
    if any(c.isupper()    for c in pw): score += 1
    if any(c.isdigit()    for c in pw): score += 1
    if any(not c.isalnum() for c in pw): score += 1
    labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
    return score, labels[min(score, 5)]
