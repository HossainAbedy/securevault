"""
In-memory session.  The decrypted vault key lives here ONLY — it is never
written to disk in plaintext.  Locking zeroes the key bytes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import ctypes


@dataclass
class Session:
    user_id:        int
    username:       str
    vault_key:      bytearray          # mutable so we can zero it
    is_windows_user: bool = False
    windows_sid:    Optional[str] = None

    def __post_init__(self):
        # Store as bytearray so zeroing is possible
        if isinstance(self.vault_key, (bytes, memoryview)):
            self.vault_key = bytearray(self.vault_key)

    def lock(self):
        """Zero the vault key in memory before discarding."""
        for i in range(len(self.vault_key)):
            self.vault_key[i] = 0
        self.vault_key = bytearray()

    @property
    def key_bytes(self) -> bytes:
        """Return vault key as immutable bytes (for crypto calls)."""
        return bytes(self.vault_key)


# ── Global session singleton ────────────────────────────────────────────────

_current: Optional[Session] = None


def get_session() -> Optional[Session]:
    return _current


def set_session(s: Optional[Session]):
    global _current
    _current = s


def clear_session():
    global _current
    if _current is not None:
        _current.lock()
    _current = None


def require_session() -> Session:
    """Raise if no active session (use inside UI actions)."""
    s = _current
    if s is None:
        raise RuntimeError("No active session — vault is locked.")
    return s
