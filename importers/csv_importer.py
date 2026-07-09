"""Generic CSV password importer — auto-detects column names."""

from __future__ import annotations
import csv
from pathlib import Path
from urllib.parse import urlparse

try:
    from .base import BaseImporter, ImportedCredential
except ImportError:
    from importers.base import BaseImporter, ImportedCredential

_ALIASES = {
    "url":      ["url","website","site","origin","hostname","web_address"],
    "username": ["username","user","login","email","account","identifier"],
    "password": ["password","pass","pw","passwd","secret"],
    "title":    ["name","title","label","description","site_name"],
}

def _find(headers: dict, group: str):
    for alias in _ALIASES[group]:
        if alias in headers:
            return headers[alias]
    return None

class CSVImporter(BaseImporter):

    def __init__(self, csv_path=None):
        self._path = Path(csv_path) if csv_path else None

    @property
    def browser_name(self): return "CSV file"
    def is_available(self): return True
    def get_profiles(self): return []

    def import_from(self, profile_path=None, csv_path=None, **kwargs):
        target = Path(csv_path) if csv_path else self._path
        if not target:
            raise ValueError("No CSV path provided.")
        if not target.exists():
            raise FileNotFoundError(f"File not found: {target}")

        for enc in ("utf-8-sig","utf-8","cp1252"):
            try:
                return self._parse(target, enc)
            except UnicodeDecodeError:
                continue
        raise RuntimeError(f"Cannot read {target} — try saving as UTF-8.")

    def _parse(self, path: Path, enc: str):
        results = []
        with open(path, newline="", encoding=enc) as f:
            reader  = csv.DictReader(f)
            headers = {h.lower().strip(): h for h in (reader.fieldnames or [])}
            url_col  = _find(headers, "url")
            user_col = _find(headers, "username")
            pw_col   = _find(headers, "password")
            name_col = _find(headers, "title")

            if not pw_col:
                raise ValueError(
                    f"No password column in {path.name}.\n"
                    f"Detected: {', '.join(headers.keys())}"
                )

            for row in reader:
                pw = row.get(pw_col,"").strip()
                if not pw: continue
                url      = row.get(url_col,"").strip()  if url_col  else ""
                username = row.get(user_col,"").strip() if user_col else ""
                name     = row.get(name_col,"").strip() if name_col else ""
                domain   = urlparse(url).netloc or url
                results.append(ImportedCredential(
                    title    = name or domain or "Imported",
                    url      = url,
                    username = username,
                    password = pw,
                    notes    = f"Imported from CSV ({path.name})",
                    category = "General",
                ))
        return results
