"""
build_manifests.py

Generate Native Messaging manifest files for
Chrome, Edge and Firefox.

Outputs:
    installer/dist/com.securevault.nativehost.json
    installer/dist/com.securevault.nativehost.firefox.json
"""

import json
from pathlib import Path


HOST_NAME = "com.securevault.nativehost"

CHROME_EXTENSION_IDS = [
    "becngobgachhbpglojolpgioljnfddik",
]
FF_EXT_ID = "securevault@abedy"


def main():

    root = Path(__file__).parent.parent
    dist = root / "installer" / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    # This path is where Inno Setup installs the native host.
    native_host_path = (
        r"C:\Program Files\SecureVault\native_host\native_host.exe"
    )

    chrome_manifest = {
        "name": HOST_NAME,
        "description": "SecureVault Native Messaging Host",
        "path": native_host_path,
        "type": "stdio",
        "allowed_origins": [
            *(f"chrome-extension://{ext_id}/" for ext_id in CHROME_EXTENSION_IDS),
            *(f"chrome-extension://{ext_id}/" for ext_id in CHROME_EXTENSION_IDS),
        ]
    }

    firefox_manifest = {
        "name": HOST_NAME,
        "description": "SecureVault Native Messaging Host",
        "path": native_host_path,
        "type": "stdio",
        "allowed_extensions": [
            FF_EXT_ID
        ]
    }

    chrome_file = dist / "com.securevault.nativehost.json"
    firefox_file = dist / "com.securevault.nativehost.firefox.json"

    with chrome_file.open("w", encoding="utf-8") as f:
        json.dump(chrome_manifest, f, indent=4)

    with firefox_file.open("w", encoding="utf-8") as f:
        json.dump(firefox_manifest, f, indent=4)

    print(f"✓ Created {chrome_file.name}")
    print(f"✓ Created {firefox_file.name}")


if __name__ == "__main__":
    main()