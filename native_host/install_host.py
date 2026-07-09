"""
install_host.py  —  Run once to register the native messaging host.

Usage
-----
    python install_host.py [--chrome-ext-id EXT_ID] [--edge-ext-id EXT_ID]

After running, edit the generated .json manifest to add your extension ID(s)
if you didn't supply them on the command line.
"""

import sys
import json
import winreg
import argparse
from pathlib import Path


HOST_NAME = "com.securevault.nativehost"
HOST_DESC = "SecureVault Password Manager Native Host"


def install(chrome_ext_id: str = "", edge_ext_id: str = ""):
    host_script = (Path(__file__).parent / "native_host.py").resolve()
    bat_file    = host_script.with_suffix(".bat")

    # Create a .bat launcher (Chrome/Edge require an executable path, not .py)
    bat_file.write_text(
        f'@echo off\r\n"{sys.executable}" "{host_script}"\r\n',
        encoding="ascii",
    )
    print(f"  Launcher:   {bat_file}")

    # Build allowed_origins list
    origins = []
    if chrome_ext_id:
        origins.append(f"chrome-extension://{chrome_ext_id}/")
    if edge_ext_id:
        origins.append(f"chrome-extension://{edge_ext_id}/")
    if not origins:
        print(
            "\n  ⚠  No extension ID supplied — allowed_origins will be empty.\n"
            "     Edit the manifest JSON later to add your extension ID.\n"
        )

    manifest = {
        "name":            HOST_NAME,
        "description":     HOST_DESC,
        "path":            str(bat_file),
        "type":            "stdio",
        "allowed_origins": origins,
    }

    manifest_path = host_script.parent / f"{HOST_NAME}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  Manifest:   {manifest_path}")

    # Register for Chrome
    _reg_write(
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        str(manifest_path),
    )
    print("  ✓ Chrome registry entry created.")

    # Register for Edge (uses same chrome-extension:// scheme)
    _reg_write(
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",
        str(manifest_path),
    )
    print("  ✓ Edge registry entry created.")

    print(f"\nDone.  Manifest: {manifest_path}")
    if not origins:
        print(
            f"Next step: add your unpacked extension ID to\n"
            f"  {manifest_path}\n"
            f"under the 'allowed_origins' key, then reload the extension."
        )


def _reg_write(path: str, value: str):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, value)


def uninstall():
    for base in [
        rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}",
        rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}",
    ]:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, base)
            print(f"  Removed: {base}")
        except FileNotFoundError:
            pass
    print("Uninstall complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register SecureVault native host")
    parser.add_argument("--chrome-ext-id", default="", metavar="ID")
    parser.add_argument("--edge-ext-id",   default="", metavar="ID")
    parser.add_argument("--uninstall",     action="store_true")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        print("Registering SecureVault native messaging host…\n")
        install(
            chrome_ext_id=args.chrome_ext_id,
            edge_ext_id=args.edge_ext_id,
        )
