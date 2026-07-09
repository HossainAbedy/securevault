"""Mozilla Firefox password importer."""

from __future__ import annotations
import csv, json, os, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from .base import BaseImporter, ImportedCredential
except ImportError:
    from importers.base import BaseImporter, ImportedCredential


class FirefoxImporter(BaseImporter):

    @property
    def browser_name(self) -> str:
        return "Mozilla Firefox"

    @property
    def _profiles_root(self) -> Path:
        return Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"

    def is_available(self) -> bool:
        return self._profiles_root.exists()

    def get_profiles(self) -> list[dict]:
        if not self.is_available():
            return []
        return [
            {"name": p.name, "path": p}
            for p in sorted(self._profiles_root.iterdir())
            if p.is_dir()
        ]

    def import_from(
        self,
        profile_path: Path | None = None,
        csv_path: str | None = None,
        **kwargs,
    ) -> list[ImportedCredential]:
        if csv_path:
            return self._from_csv(str(csv_path))
        if profile_path:
            result = self._try_auto_decrypt(Path(profile_path))
            if result is not None:
                return result
            raise RuntimeError(
                "Auto-decrypt failed.\n\n"
                "Install firefox_decrypt first:\n"
                "    pip install firefox_decrypt\n\n"
                "Or export from Firefox:\n"
                "    Menu → Passwords → ⋯ → Export Passwords\n"
                "Then use the CSV option."
            )
        raise ValueError("Provide csv_path= or profile_path=.")

    def _from_csv(self, path: str) -> list[ImportedCredential]:
        results = []
        for enc in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                with open(path, newline="", encoding=enc) as f:
                    for row in csv.DictReader(f):
                        pw = row.get("password", "").strip()
                        if not pw:
                            continue
                        url    = row.get("url", "").strip()
                        domain = urlparse(url).netloc or url
                        title  = row.get("name", "").strip() or domain or "Imported"
                        results.append(ImportedCredential(
                            title=title, url=url,
                            username=row.get("username","").strip(),
                            password=pw,
                            notes="Imported from Firefox (CSV)",
                            category="General",
                        ))
                return results
            except UnicodeDecodeError:
                continue
        raise RuntimeError(f"Cannot read file — try saving as UTF-8.")

    def _try_auto_decrypt(self, profile: Path) -> list[ImportedCredential] | None:
        for fmt in (["--format", "json"], []):
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "firefox_decrypt", str(profile)] + fmt,
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0 and r.stdout.strip():
                    if fmt:
                        return self._parse_json(r.stdout)
                    return self._parse_text(r.stdout)
            except Exception:
                pass
        return None

    def _parse_json(self, text: str) -> list[ImportedCredential]:
        results = []
        for item in json.loads(text):
            url = item.get("url") or item.get("hostname") or ""
            results.append(ImportedCredential(
                title    = urlparse(url).netloc or url or "Imported",
                url      = url,
                username = item.get("login") or item.get("username") or "",
                password = item.get("password") or "",
                notes    = "Imported from Firefox (auto-decrypt)",
                category = "General",
            ))
        return results

    def _parse_text(self, text: str) -> list[ImportedCredential]:
        results, block = [], {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if block.get("password"):
                    url = block.get("url","")
                    results.append(ImportedCredential(
                        title    = urlparse(url).netloc or url or "Imported",
                        url      = url,
                        username = block.get("username",""),
                        password = block["password"],
                        notes    = "Imported from Firefox (auto-decrypt)",
                        category = "General",
                    ))
                block = {}
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                v = v.strip().strip("'\"")
                k = k.strip().lower()
                if "website" in k or "url" in k:  block["url"]      = v
                elif "username" in k or "login" in k: block["username"] = v
                elif "password" in k:             block["password"] = v
        return results
