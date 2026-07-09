"""Microsoft Edge password importer — same engine as Chrome, different path."""

from __future__ import annotations
import os
from pathlib import Path

try:
    from .chrome_importer import ChromeImporter
except ImportError:
    from importers.chrome_importer import ChromeImporter


class EdgeImporter(ChromeImporter):

    @property
    def browser_name(self) -> str:
        return "Microsoft Edge"

    @property
    def _data_root(self) -> Path:
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data"
