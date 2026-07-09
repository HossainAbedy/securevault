# Lazy package — submodules imported on demand inside import_dialog.py
# to avoid cascading ModuleNotFoundError at startup.
from .base import ImportedCredential

__all__ = ["ImportedCredential"]
