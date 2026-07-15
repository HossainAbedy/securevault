# securevault.spec
# PyInstaller spec for the SecureVault main application.
# Run from the project root:  pyinstaller installer/securevault.spec

from pathlib import Path
import sys

block_cipher = None
ROOT = Path(SPECPATH).parent   # project root (one level above installer/)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include browser extension files so the app can reference them
        (str(ROOT / "securevault.ico"), "."),
        (str(ROOT / "browser_extension"),         "browser_extension"),
        (str(ROOT / "browser_extension_firefox"),  "browser_extension_firefox"),
    ],
    hiddenimports=[
        # pywin32
        "win32api", "win32con", "win32crypt", "win32gui",
        "win32process", "win32security", "win32service",
        "pywintypes", "winerror",
        # cryptography
        "cryptography.hazmat.primitives.ciphers.aead",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.backends.openssl",
        # argon2
        "argon2", "argon2._utils", "argon2.low_level",
        # PyQt6
        "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "PyQt6.sip",
        # app packages
        "auth", "auth.session", "auth.windows_auth",
        "crypto", "crypto.vault_crypto",
        "db", "db.database",
        "ui", "ui.styles", "ui.login_dialog", "ui.main_window",
        "ui.entry_dialog", "ui.password_generator", "ui.import_dialog",
        "autofill", "autofill.desktop_fill",
        "importers", "importers.base", "importers.chrome_importer",
        "importers.edge_importer", "importers.firefox_importer",
        "importers.csv_importer",
        # misc
        "keyboard", "psutil", "pyperclip", "sqlite3",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "PIL", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SecureVault",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,       # windowed — no console window
    disable_windowed_traceback=False,
    icon=str(ROOT / "securevault.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SecureVault",   # output folder: dist/SecureVault/
)
