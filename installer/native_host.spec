# native_host.spec
# PyInstaller spec for the SecureVault native messaging host.
# Built as a single .exe — browsers launch it as a subprocess.
# console=True is REQUIRED so stdin/stdout work for native messaging.
# The console window is hidden by Chrome/Edge/Firefox (CREATE_NO_WINDOW flag).

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH).parent   # project root

a = Analysis(
    [str(ROOT / "native_host" / "native_host.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "win32api", "win32con", "win32crypt",
        "win32security", "pywintypes", "winerror",
        "cryptography.hazmat.primitives.ciphers.aead",
        "cryptography.hazmat.backends.openssl",
        "sqlite3",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="native_host",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,      # MUST be True — native messaging uses stdin/stdout
    icon=None,
)
