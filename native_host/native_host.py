"""
SecureVault Native Messaging Host  (enhanced)
──────────────────────────────────────────────
Chrome / Edge communicate with this script via stdin/stdout using the
Native Messaging protocol (4-byte little-endian length-prefixed JSON).

Supported actions
─────────────────
  ping                                    → { status, app }
  get_credentials   { domain }           → { credentials: [...] }
  check_credential  { domain, username } → { exists, entry_id }
  save_credential   { url, username, password, title? } → { success, entry_id }
  update_credential { entry_id, password }              → { success }

All credential actions authenticate automatically via Windows DPAPI —
no master password prompt in the browser.
"""

import sys
import json
import struct
import sqlite3
import logging
import os
from pathlib import Path

# ── Logging ───────────────────────────────────────────────────────────────────
_LOG = Path.home() / ".securevault" / "native_host.log"
_LOG.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_LOG),
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)

# ── DB helpers (no Qt dependency) ─────────────────────────────────────────────
DB_PATH = Path.home() / ".securevault" / "vault.db"

def _db() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

# ── Crypto helpers ────────────────────────────────────────────────────────────

def _current_sid() -> str:
    import win32api, win32security
    tok = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
    sid = win32security.GetTokenInformation(tok, win32security.TokenUser)[0]
    return win32security.ConvertSidToStringSid(sid)

def _dpapi_decrypt(blob: bytes) -> bytes:
    import win32crypt
    _, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    return data

def _dpapi_encrypt(data: bytes) -> bytes:
    import win32crypt
    return win32crypt.CryptProtectData(data, "SecureVault", None, None, None, 0)

def _aes_decrypt(data: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key).decrypt(data[:12], data[12:], None)

def _aes_encrypt(plaintext: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import secrets
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, None)

def _auth() -> tuple[dict, bytes]:
    """Return (user_row, vault_key) using DPAPI for current Windows user."""
    sid = _current_sid()
    with _db() as c:
        user = c.execute("SELECT * FROM users WHERE windows_sid = ?", (sid,)).fetchone()
    if not user:
        raise RuntimeError(
            "No vault linked to this Windows account. "
            "Open SecureVault → ⚙ Link Windows Acct."
        )
    if not user["dpapi_enc_key"]:
        raise RuntimeError("Vault key not linked to Windows account.")
    return dict(user), _dpapi_decrypt(bytes(user["dpapi_enc_key"]))

# ── Native Messaging protocol ──────────────────────────────────────────────────

def _read() -> dict | None:
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        return None
    length = struct.unpack("<I", raw)[0]
    body   = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))

def _send(obj: dict):
    body = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(body)))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()

# ── Handlers ───────────────────────────────────────────────────────────────────

def _handle_ping(_msg):
    return {"status": "ok", "app": "SecureVault"}


def _handle_get_credentials(msg):
    domain = msg.get("domain", "").strip()
    if not domain:
        return {"error": "No domain provided."}

    user, vault_key = _auth()

    with _db() as c:
        rows = c.execute(
            "SELECT id, title, entry_username, enc_password "
            "FROM vault_entries WHERE user_id = ? AND url LIKE ? ORDER BY title",
            (user["id"], f"%{domain}%"),
        ).fetchall()

    results = []
    for row in rows:
        try:
            pw = _aes_decrypt(bytes(row["enc_password"]), vault_key).decode()
            results.append({
                "id":       row["id"],
                "title":    row["title"],
                "username": row["entry_username"] or "",
                "password": pw,
            })
        except Exception as e:
            logging.warning(f"Skip entry {row['id']}: {e}")

    return {"credentials": results}


def _handle_check_credential(msg):
    """
    Check whether a credential for (domain, username) already exists.
    Returns { exists: bool, entry_id: int|null, stored_password_matches: bool }
    """
    domain   = msg.get("domain", "")
    username = msg.get("username", "")
    password = msg.get("password", "")   # optional — used to detect password change

    user, vault_key = _auth()

    with _db() as c:
        rows = c.execute(
            "SELECT id, enc_password FROM vault_entries "
            "WHERE user_id = ? AND url LIKE ? AND entry_username = ?",
            (user["id"], f"%{domain}%", username),
        ).fetchall()

    if not rows:
        return {"exists": False, "entry_id": None, "password_changed": False}

    row = rows[0]
    pw_matches = False
    if password:
        try:
            stored = _aes_decrypt(bytes(row["enc_password"]), vault_key).decode()
            pw_matches = (stored == password)
        except Exception:
            pass

    return {
        "exists":           True,
        "entry_id":         row["id"],
        "password_changed": bool(password) and not pw_matches,
    }


def _handle_save_credential(msg):
    """Save a brand-new credential from the browser."""
    url      = msg.get("url", "")
    username = msg.get("username", "")
    password = msg.get("password", "")
    title    = msg.get("title") or ""

    if not password:
        return {"error": "No password provided."}

    from urllib.parse import urlparse
    domain = urlparse(url).netloc or url
    if not title:
        title = domain or "Saved from browser"

    user, vault_key = _auth()
    enc_pw = _aes_encrypt(password.encode(), vault_key)

    with _db() as c:
        r = c.execute(
            "INSERT INTO vault_entries "
            "(user_id, title, url, entry_username, enc_password, notes, category) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], title, url, username, enc_pw,
             "Saved from browser", "General"),
        )
        entry_id = r.lastrowid

    logging.info(f"Saved new credential: {title} ({username}) @ {domain}")
    return {"success": True, "entry_id": entry_id}


def _handle_update_credential(msg):
    """Update the password of an existing vault entry."""
    entry_id = msg.get("entry_id")
    password = msg.get("password", "")

    if not entry_id or not password:
        return {"error": "entry_id and password are required."}

    user, vault_key = _auth()
    enc_pw = _aes_encrypt(password.encode(), vault_key)

    with _db() as c:
        c.execute(
            "UPDATE vault_entries SET enc_password = ?, updated_at = datetime('now') "
            "WHERE id = ? AND user_id = ?",
            (enc_pw, entry_id, user["id"]),
        )

    logging.info(f"Updated password for entry {entry_id}")
    return {"success": True}


# ── Dispatch table ────────────────────────────────────────────────────────────

_HANDLERS = {
    "ping":              _handle_ping,
    "get_credentials":   _handle_get_credentials,
    "check_credential":  _handle_check_credential,
    "save_credential":   _handle_save_credential,
    "update_credential": _handle_update_credential,
}

def _redact(obj) -> dict:
    """Recursively strip password values before logging."""
    if isinstance(obj, dict):
        return {
            k: ("***" if k == "password" else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(i) for i in obj]
    return obj


def _dispatch(msg: dict) -> dict:
    action = msg.get("action", "")
    handler = _HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action!r}"}
    try:
        return handler(msg)
    except Exception as exc:
        logging.exception(f"Handler '{action}' raised")
        return {"error": str(exc)}

# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    logging.info("Native host started (pid %d)", os.getpid())
    while True:
        try:
            msg = _read()
            if msg is None:
                logging.info("stdin closed — exiting.")
                break
            logging.debug("→  %s", _redact(msg))
            resp = _dispatch(msg)
            logging.debug("←  %s", _redact(resp))
            _send(resp)
        except Exception as exc:
            logging.exception("Main loop error")
            try:
                _send({"error": str(exc)})
            except Exception:
                break

if __name__ == "__main__":
    main()
