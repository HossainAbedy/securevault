from __future__ import annotations
import json, os, shutil, sqlite3, base64
from pathlib import Path
from urllib.parse import urlparse

try:
    from .base import BaseImporter, ImportedCredential
except ImportError:
    from importers.base import BaseImporter, ImportedCredential


class ChromeImporter(BaseImporter):

    @property
    def browser_name(self) -> str:
        return "Google Chrome"

    @property
    def _data_root(self) -> Path:
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"

    def is_available(self) -> bool:
        return self._data_root.exists()

    def get_profiles(self) -> list[dict]:
        if not self.is_available():
            return []
        profiles: list[dict] = []

        def _try_add(folder: Path, default_name: str):
            if not (folder / "Login Data").exists():
                return
            try:
                prefs = json.loads(
                    (folder / "Preferences").read_text(encoding="utf-8", errors="ignore")
                )
                name = prefs.get("profile", {}).get("name") or default_name
            except Exception:
                name = default_name
            profiles.append({"name": name, "path": folder})

        _try_add(self._data_root / "Default", "Default")
        for child in sorted(self._data_root.iterdir()):
            if child.is_dir() and child.name.startswith("Profile"):
                _try_add(child, child.name)

        return profiles

    def _load_aes_key(self) -> bytes:
        local_state = self._data_root / "Local State"
        if not local_state.exists():
            raise FileNotFoundError(f"Local State not found: {local_state}")
        data    = json.loads(local_state.read_text(encoding="utf-8", errors="ignore"))
        enc_key = base64.b64decode(data["os_crypt"]["encrypted_key"])
        enc_key = enc_key[5:]  # strip b"DPAPI" prefix
        import win32crypt
        _, key = win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)
        return key

    def _decrypt(self, raw: bytes, aes_key: bytes) -> str:
        if raw[:3] == b"v10":
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            return AESGCM(aes_key).decrypt(raw[3:15], raw[15:], None).decode("utf-8", errors="replace")
        else:
            import win32crypt
            _, pw = win32crypt.CryptUnprotectData(raw, None, None, None, 0)
            return pw.decode("utf-8", errors="replace")

    def import_from(self, profile_path: Path | None = None, **kwargs) -> list[ImportedCredential]:
        if profile_path is None:
            profiles = self.get_profiles()
            if not profiles:
                raise RuntimeError(f"No {self.browser_name} profiles found.")
            profile_path = profiles[0]["path"]

        profile_path = Path(profile_path)
        login_db     = profile_path / "Login Data"
        if not login_db.exists():
            raise FileNotFoundError(f"Login Data not found: {login_db}")

        aes_key = self._load_aes_key()
        tmp = Path(os.environ.get("TEMP", os.environ.get("TMP", "."))) / "sv_browser_tmp.db"

        try:
            shutil.copy2(login_db, tmp)
            conn = sqlite3.connect(str(tmp))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT origin_url, username_value, password_value "
                "FROM logins "
                "WHERE username_value != '' AND length(password_value) > 0 "
                "ORDER BY origin_url"
            ).fetchall()
            conn.close()
        finally:
            try: tmp.unlink()
            except Exception: pass

        results: list[ImportedCredential] = []
        for row in rows:
            try:
                pw     = self._decrypt(bytes(row["password_value"]), aes_key)
                url    = row["origin_url"] or ""
                domain = urlparse(url).netloc or url
                results.append(ImportedCredential(
                    title    = domain,
                    url      = url,
                    username = row["username_value"],
                    password = pw,
                    notes    = "Imported from Google Chrome",
                    category = "General",
                ))
            except Exception:
                pass

        return results