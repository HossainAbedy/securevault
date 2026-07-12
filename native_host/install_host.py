"""
install_host.py  —  Register the SecureVault native messaging host.

Usage
-----
    # Chrome + Edge only
    python install_host.py

    # With extension IDs
    python install_host.py --chrome-ext-id ID --edge-ext-id ID

    # Firefox
    python install_host.py --firefox --firefox-ext-id securevault@abedy

    # All browsers
    python install_host.py --chrome-ext-id ID --edge-ext-id ID --firefox

    # Uninstall
    python install_host.py --uninstall

Chrome/Edge: manifest path stored in Windows registry (HKCU).
Firefox:     manifest written to %APPDATA%\\Mozilla\\NativeMessagingHosts\\
             Uses 'allowed_extensions' instead of 'allowed_origins'.
"""

import sys, json, os, winreg, argparse
from pathlib import Path

HOST_NAME = "com.securevault.nativehost"
HOST_DESC = "SecureVault Password Manager Native Host"


def _make_launcher(host_script: Path) -> Path:
    bat = host_script.with_suffix(".bat")
    bat.write_text(f'@echo off\r\n"{sys.executable}" "{host_script}"\r\n', encoding="ascii")
    return bat


def _reg_write(path: str, value: str):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, value)


# ── Chrome / Edge ─────────────────────────────────────────────────────────────

def install_chrome_edge(chrome_ext_id: str = "", edge_ext_id: str = ""):
    host_script   = (Path(__file__).parent / "native_host.py").resolve()
    bat_file      = _make_launcher(host_script)
    manifest_path = host_script.parent / f"{HOST_NAME}.json"

    origins = []
    if chrome_ext_id:
        origins.append(f"chrome-extension://{chrome_ext_id}/")
    if edge_ext_id:
        origins.append(f"chrome-extension://{edge_ext_id}/")
    if not origins:
        print(f"  ⚠  No extension ID given — edit {manifest_path} to add IDs later.")

    manifest = {
        "name":            HOST_NAME,
        "description":     HOST_DESC,
        "path":            str(bat_file),
        "type":            "stdio",
        "allowed_origins": origins,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Chrome/Edge manifest: {manifest_path}")

    _reg_write(rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}", str(manifest_path))
    print("  ✓ Chrome registry entry created.")
    _reg_write(rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}", str(manifest_path))
    print("  ✓ Edge registry entry created.")


# ── Firefox ───────────────────────────────────────────────────────────────────

def install_firefox(firefox_ext_id: str = "securevault@abedy"):
    host_script  = (Path(__file__).parent / "native_host.py").resolve()
    bat_file     = _make_launcher(host_script)

    # Firefox reads from a folder, not the registry
    ff_dir = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "NativeMessagingHosts"
    ff_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ff_dir / f"{HOST_NAME}.json"

    # Firefox uses 'allowed_extensions', not 'allowed_origins'
    manifest = {
        "name":               HOST_NAME,
        "description":        HOST_DESC,
        "path":               str(bat_file),
        "type":               "stdio",
        "allowed_extensions": [firefox_ext_id],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Firefox manifest:     {manifest_path}")
    print(f"  ✓ Firefox host registered for ID: {firefox_ext_id}")


# ── Uninstall ─────────────────────────────────────────────────────────────────

def uninstall():
    for reg_path in [
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",
    ]:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
            print(f"  Removed: {reg_path}")
        except FileNotFoundError:
            pass

    ff_manifest = (
        Path(os.environ.get("APPDATA", ""))
        / "Mozilla" / "NativeMessagingHosts" / f"{HOST_NAME}.json"
    )
    if ff_manifest.exists():
        ff_manifest.unlink()
        print(f"  Removed Firefox manifest: {ff_manifest}")

    bat = (Path(__file__).parent / "native_host.bat").resolve()
    if bat.exists():
        bat.unlink()

    print("\nUninstall complete.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register SecureVault native host")
    parser.add_argument("--chrome-ext-id",  default="", metavar="ID")
    parser.add_argument("--edge-ext-id",    default="", metavar="ID")
    parser.add_argument("--firefox",        action="store_true",
                        help="Also register for Firefox")
    parser.add_argument("--firefox-ext-id", default="securevault@abedy", metavar="ID",
                        help="Firefox extension ID (default: securevault@abedy)")
    parser.add_argument("--uninstall",      action="store_true")
    args = parser.parse_args()

    if args.uninstall:
        print("Uninstalling…\n")
        uninstall()
    else:
        print("Registering SecureVault native messaging host…\n")
        install_chrome_edge(args.chrome_ext_id, args.edge_ext_id)
        if args.firefox:
            install_firefox(args.firefox_ext_id)
        print("\nDone.")
