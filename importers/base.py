"""
Base importer interface and shared credential dataclass.
All browser/CSV importers inherit BaseImporter.
"""

from __future__ import annotations
from abc        import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib    import Path


@dataclass
class ImportedCredential:
    title:    str
    url:      str
    username: str
    password: str
    notes:    str = ""
    category: str = "General"

    def __post_init__(self):
        # Derive a clean title from the URL if none provided
        if not self.title and self.url:
            from urllib.parse import urlparse
            self.title = urlparse(self.url).netloc or self.url


class BaseImporter(ABC):

    @property
    @abstractmethod
    def browser_name(self) -> str:
        """Human-readable browser / source name."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the browser/source is installed on this machine."""

    @abstractmethod
    def get_profiles(self) -> list[dict]:
        """
        Return a list of available profiles.
        Each entry: { "name": str, "path": Path }
        """

    @abstractmethod
    def import_from(self, profile_path: Path | None = None, **kwargs) -> list[ImportedCredential]:
        """
        Extract credentials from *profile_path* (or the default profile).
        Must return a list of ImportedCredential instances.
        """
