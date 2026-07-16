🔐 SecureVault

Offline password manager for Windows with military-grade encryption, desktop autofill, browser integration, and Windows DPAPI auto-unlock.

Built with Python • PyQt6 • SQLite • AES-256-GCM • Argon2id • Windows DPAPI

SecureVault is designed to keep your passwords local. Your vault never leaves your computer.

---
## Feature

| Feature                    | Description                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------- |
| 🔒 AES-256-GCM Encryption  | Every credential is individually encrypted before being written to SQLite.            |
| 🔑 Argon2id                | Memory-hard password hashing for master password protection.                          |
| 🪟 Windows DPAPI           | Optional passwordless auto-unlock tied to your Windows account.                       |
| 🌐 Browser Integration     | Chrome, Microsoft Edge and Mozilla Firefox support using Native Messaging.            |
| ⚡ Desktop Autofill         | Press **Ctrl+Shift+F** to autofill credentials into desktop applications or browsers. |
| 🔄 Save & Update Detection | Detects login forms and offers to save or update passwords.                           |
| 🔐 Password Generator      | Strong password generator with configurable options and strength meter.               |
| 📋 Clipboard Protection    | Automatically clears copied passwords after 30 seconds.                               |
| 🖥 System Tray             | Runs quietly in the background with quick access.                                     |
| 🗂 Categories              | Banking, Email, Social, Shopping, Work, General and more.                             |


---

## Browser Support
Browser	Status
✅ Google Chrome	Extension available (Chrome Web Store review in progress)
✅ Microsoft Edge	Uses the Chrome-compatible extension
✅ Mozilla Firefox	Signed Mozilla Add-on

## Requirements

- Windows 10 / 11 (DPAPI is Windows-only)
- Python 3.11+

---

## Installation
Download the latest installer from the Releases page.

The installer automatically:

Installs SecureVault
Registers Native Messaging Hosts
Configures Chrome support
Configures Microsoft Edge support
Configures Mozilla Firefox support
Creates optional Desktop and Startup shortcuts

After installation, simply install the browser extension (Chrome/Edge) or restart Firefox if the signed extension has been deployed via enterprise policy.

or for development: 
```powershell
# 1. Clone / extract the project
cd securevault

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate
source .venv/Scripts/activate #bash

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python main.py
```

> **First run**: click "Create new vault", enter a username and master password,  
> and tick "Link to current Windows account" to enable auto-unlock.

---

## Browser extension setup

### Chrome & Microsoft Edge

1. Install SecureVault.
2. Open `chrome://extensions` or `edge://extensions`.
3. Enable **Developer Mode**.
4. Click **Load unpacked**.
5. Select:
6. The extension is ready to use.

### Mozilla Firefox

The installer automatically configures Firefox Native Messaging.

If the signed extension is installed through the enterprise policy, simply restart Firefox.

Otherwise install the signed SecureVault extension from Mozilla Add-ons.

---

## Desktop autofill

Press **Ctrl+Shift+F** while any desktop application or browser is focused.  
SecureVault searches the vault using words from the active window title and  
presents a picker.  After you select a credential it types username → Tab → password.

> The `keyboard` module requires the app (or its terminal) to be **Run as  
> Administrator** if the target window is also elevated (e.g. Task Manager).

---

## Project structure

```
securevault/
│
├── main.py
├── requirements.txt
├── README.md
│
├── crypto/
│   ├── __init__.py
│   └── vault_crypto.py
│
├── auth/
│   ├── __init__.py
│   ├── windows_auth.py
│   └── session.py
│
├── db/
│   ├── __init__.py
│   └── database.py
│
├── ui/
│   ├── __init__.py
│   ├── styles.py
│   ├── login_dialog.py
│   ├── main_window.py
│   ├── entry_dialog.py
│   ├── password_generator.py
│   └── import_dialog.py
│
├── importers/
│   ├── __init__.py
│   ├── base.py
│   ├── chrome_importer.py
│   ├── edge_importer.py
│   ├── firefox_importer.py
│   └── csv_importer.py
│
├── autofill/
│   ├── __init__.py
│   └── desktop_fill.py
│
├── native_host/
│   ├── __init__.py
│   ├── native_host.py
│   └── install_host.py
│
├── browser_extension/              ← Chrome + Edge (MV3)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.js
│   └── SETUP.html
│
├── browser_extension_firefox/      ← Firefox (MV2)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
│
└── installer/
    ├── build.bat                   ← 5-step build pipeline
    ├── build_manifests.py          ← generates native host manifests
    ├── build_xpi.py                ← packages Firefox .xpi
    ├── securevault.spec            ← PyInstaller main app
    ├── native_host.spec            ← PyInstaller native host
    ├── setup.iss                   ← Inno Setup script
    │
    ├── assets/                     ← installer resources
    │   ├── logo.ico                
    │   ├── banner.bmp              
    │   └── setup.html              ← post-install Chrome setup guide
    │
    ├── templates/                  
    │   ├── chrome_manifest.json
    │   └── firefox_manifest.json
    │
    ├── dist/                       ← build output (gitignore this)
    ├── build/                      ← PyInstaller temp (gitignore this)
    └── output/                     ← final SecureVaultSetup.exe
```

---

## Browser Integration

  SecureVault communicates with browsers using the official Native Messaging API.
  
  Supported features include:
  
  Autofill credentials
  Save new passwords
  Update changed passwords
  Browser password import
  Domain matching

No browser data is transmitted over the Internet.

## Security notes

SecureVault follows a local-first security model.

  AES-256-GCM encryption
  Argon2id key derivation
  Windows DPAPI integration
  Offline operation
  No cloud synchronization
  No telemetry
  No analytics
  No advertising
  
  Sensitive data is encrypted before storage. Only encrypted values are written to SQLite.

- The SQLite database is **not** file-encrypted; all sensitive columns are  
  encrypted at the application layer with AES-256-GCM before writing.  
  Add BitLocker full-disk encryption for defence in depth.
- DPAPI blobs are bound to your **Windows user account and machine** by default.  
  Changing your Windows password or migrating to a new PC will invalidate them —  
  always keep your master password as a backup.
- The vault key is stored in a Python `bytearray` in memory and zeroed on lock.
- The `keyboard` module intercepts keystrokes globally — only run from a  
  trusted environment.
- Clipboard auto-clears after 30 seconds; close the app or lock to immediately  
  zero the in-memory key.

---
## Downloads
GitHub Releases (coming soon)
Chrome Web Store (pending review)
Mozilla Add-ons (approved)

## Code Signing

SecureVault is digitally signed using the SignPath Foundation code-signing service.

## Licence

Copyright © Hossain Abedy. All rights reserved. 
