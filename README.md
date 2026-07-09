# 🔐 SecureVault

Personal encrypted password manager for Windows 11.  
Built with Python · PyQt6 · SQLite · AES-256-GCM · Argon2id · Windows DPAPI.

---

## Feature overview

| Feature | Details |
|---|---|
| **Encryption** | AES-256-GCM per entry; vault key never written to disk in plaintext |
| **Key derivation** | Argon2id (64 MB, 3 passes, 4 lanes) |
| **Windows auto-unlock** | Vault key wrapped with DPAPI → no password prompt for the owner account |
| **Other users** | Master password → Argon2id → decrypt vault key |
| **Desktop autofill** | `Ctrl+Shift+F` global hotkey → picker dialog → keyboard injection |
| **Browser autofill** | Chrome/Edge extension + native messaging host (DPAPI auto-auth) |
| **System tray** | Runs minimised; double-click icon to reopen |
| **Password generator** | Configurable length 8-64, character classes, strength meter |
| **Categories** | General, Banking, Social, Email, Work, Shopping, Other |
| **Clipboard safety** | Password auto-clears from clipboard after 30 seconds |
| **DB location** | `%USERPROFILE%\.securevault\vault.db` |

---

## Requirements

- Windows 10 / 11 (DPAPI is Windows-only)
- Python 3.11+

---

## Installation

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

### Step 1 — Register the native messaging host

```powershell
python native_host\install_host.py
```

This creates a `.bat` launcher and writes registry keys for both Chrome and Edge.  
Re-run with `--uninstall` to remove.

### Step 2 — Load the extension (unpacked)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** → select the `browser_extension/` folder.
4. Copy the Extension ID shown on the card.

### Step 3 — Authorise the extension

Open `native_host\com.securevault.nativehost.json` and add your extension ID:

```json
{
  "allowed_origins": [
    "chrome-extension://YOUR_EXTENSION_ID_HERE/"
  ]
}
```

Save the file. Reload the extension. Done.

> The browser extension uses **Windows DPAPI auto-auth** — the vault must be  
> linked to your Windows account (done during registration, or via  
> ⚙ **Link Windows Acct** in the toolbar).

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
├── main.py                      # Entry point
├── requirements.txt
│
├── crypto/
│   └── vault_crypto.py          # AES-256-GCM · Argon2id · password generator
│
├── auth/
│   ├── windows_auth.py          # DPAPI encrypt/decrypt, get SID/username
│   └── session.py               # In-memory session (vault key lives here only)
│
├── db/
│   └── database.py              # SQLite schema + CRUD
│
├── ui/
│   ├── styles.py                # Catppuccin Mocha QSS theme
│   ├── login_dialog.py          # Unlock + register pages
│   ├── main_window.py           # Vault browser, tray, hotkey wiring
│   ├── entry_dialog.py          # Add / edit entry
│   └── password_generator.py   # Generator dialog
│
├── autofill/
│   └── desktop_fill.py          # Hotkey registration + keystroke injection
│
├── native_host/
│   ├── native_host.py           # Standalone Chrome/Edge messaging host
│   └── install_host.py          # One-time registry installer
│
└── browser_extension/
    ├── manifest.json            # MV3
    ├── background.js            # Service worker (bridges popup ↔ native host)
    ├── content.js               # Login-form detection + autofill button/picker
    ├── popup.html               # Extension popup UI
    └── popup.js                 # Popup logic
```

---

## Security notes

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

## Licence

MIT — personal use.
