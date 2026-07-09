"""
Windows Authentication helpers.

Uses Windows DPAPI (CryptProtectData / CryptUnprotectData) to bind the vault
key to the current Windows user account — no extra password needed for the
designated owner.  Other users must supply a master password instead.
"""

try:
    import win32api
    import win32security
    import win32crypt
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


def is_available() -> bool:
    return _WIN32_AVAILABLE


def get_current_windows_sid() -> str:
    """Return the SID string of the currently logged-in Windows account."""
    if not _WIN32_AVAILABLE:
        raise RuntimeError("pywin32 not installed.")
    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(),
        win32security.TOKEN_QUERY,
    )
    sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    return win32security.ConvertSidToStringSid(sid)


def get_current_username() -> str:
    if not _WIN32_AVAILABLE:
        import os
        return os.getlogin()
    return win32api.GetUserName()


def dpapi_encrypt(data: bytes, description: str = "SecureVault") -> bytes:
    """
    Encrypt *data* with DPAPI (tied to the current Windows user + machine).
    Returns opaque DPAPI blob.
    """
    if not _WIN32_AVAILABLE:
        raise RuntimeError("pywin32 not installed.")
    return win32crypt.CryptProtectData(
        data, description, None, None, None, 0
    )


def dpapi_decrypt(blob: bytes) -> bytes:
    """
    Decrypt a DPAPI blob.  Only succeeds for the same Windows account that
    produced the blob (and on the same machine by default).
    """
    if not _WIN32_AVAILABLE:
        raise RuntimeError("pywin32 not installed.")
    _, decrypted = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    return decrypted
