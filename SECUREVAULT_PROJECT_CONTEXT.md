# SecureVault — Project Context File
> Paste this into any fresh Claude chat to fully restore project context.
> Current as of: July 2026 — v1.0.2

---

## 1. What SecureVault Is

SecureVault is a **self-hosted, offline-first password manager for Windows 11** built entirely from scratch. It stores credentials in an AES-256-GCM encrypted SQLite database on the local machine. No cloud, no subscription, no third-party servers. Passwords never leave the PC.

It consists of:
- A **PyQt6 desktop app** (vault UI, authentication, tray, desktop autofill)
- A **Chrome/Edge browser extension** (MV3, published on Chrome Web Store)
- A **Firefox browser extension** (MV2, signed via Mozilla AMO)
- A **native messaging host** (standalone .exe that bridges browser ↔ vault DB)
- A **Windows installer** (PyInstaller + Inno Setup 6, produces SecureVaultSetup.exe)

---

## 2. Links

| Resource | URL |
|---|---|
| GitHub repo | https://github.com/HossainAbedy/securevault |
| Latest release (v1.0.2) | https://github.com/HossainAbedy/securevault/releases/tag/v1.0.2 |
| Chrome Web Store | https://chromewebstore.google.com/detail/securevault/becngobgachhbpglojolpgioljnfddik |
| Extension ID | `becngobgachhbpglojolpgioljnfddik` |
| Firefox AMO | Submitted unlisted — signed XPI used by installer |
| Privacy policy | https://www.hossainabedy.com/policies/securevault/privacy-policy.html |
| Support page | https://www.hossainabedy.com/policies/securevault/support-policy.html |
| Portfolio | https://hossainabedy.com |
| Developer | Hossain Abedy Supta — abedy.ewu@gmail.com |

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Desktop UI | Python 3.11 + PyQt6 |
| Encryption | AES-256-GCM (cryptography library) |
| Key derivation | Argon2id — 64 MB, 3 passes, 4 lanes (argon2-cffi) |
| Windows binding | Windows DPAPI via pywin32 (win32crypt) |
| Database | SQLite 3 (stdlib) |
| Desktop autofill | keyboard + psutil + pyperclip |
| Browser extension (Chrome/Edge) | Manifest V3, service worker |
| Browser extension (Firefox) | Manifest V2, background page |
| Native messaging | Python subprocess, stdin/stdout, 4-byte LE length prefix |
| Installer build | PyInstaller (onedir for app, onefile for native host) + Inno Setup 6 |
| Firefox install method | Enterprise policy (policies.json force_installed) |
| Code signing | SignPath Foundation (pending approval) |

---

## 4. Security Architecture

### Encryption model
- Every credential is encrypted individually with **AES-256-GCM** before writing to SQLite
- Each encryption uses a fresh **96-bit random nonce** (os.urandom(12))
- Ciphertext format: `nonce[12] || ciphertext || GCM-tag`

### Key lifecycle
1. At vault creation: a random **256-bit vault key** is generated
2. **Windows owner path**: vault key is DPAPI-encrypted and stored in the DB — silent auto-unlock on every launch for the registered Windows account
3. **Master password path**: Argon2id derives a 256-bit wrapping key from password + 16-byte random salt; this wraps the vault key before storage
4. At runtime: vault key lives in a Python `bytearray` in memory only — never written to disk in plaintext
5. On lock: bytearray is zeroed byte-by-byte before discarding
6. Clipboard: auto-cleared 30 seconds after copying a password
7. Native host log: all password fields recursively redacted before logging

### DPAPI
- Windows Data Protection API binds the vault key to the current Windows user account + machine
- DPAPI blobs become invalid if Windows account password is reset by IT
- Master password is always available as a recovery fallback

---

## 5. Database Schema

Location: `%USERPROFILE%\.securevault\vault.db`  
All sensitive columns are encrypted at application layer — the file itself is not file-level encrypted.

```sql
users (
  id            INTEGER PRIMARY KEY,
  username      TEXT UNIQUE,
  windows_sid   TEXT,           -- Windows account SID for DPAPI binding
  dpapi_enc_key BLOB,           -- vault key wrapped by DPAPI
  mpw_salt      BLOB,           -- Argon2id salt (16 bytes)
  mpw_enc_key   BLOB,           -- vault key encrypted with Argon2id-derived key
  mpw_hash      TEXT            -- Argon2id hash for fast master password verify
)

vault_entries (
  id             INTEGER PRIMARY KEY,
  user_id        INTEGER → users(id) ON DELETE CASCADE,
  title          TEXT,
  url            TEXT,
  entry_username TEXT,
  enc_password   BLOB,          -- AES-256-GCM(vault_key, plaintext_password)
  notes          TEXT,
  category       TEXT,
  created_at     TEXT,
  updated_at     TEXT
)

settings (key TEXT PRIMARY KEY, value TEXT)
```

> All versions of the app share one database. Extracting a new version does not create a new vault.

---

## 6. Complete File Structure

```
securevault/
├── main.py                          Entry point + DPAPI auto-login attempt
├── requirements.txt
├── README.md
├── securevault.ico                  App icon (multi-size, used by PyInstaller + shortcuts)
├── browser_extension.pem            RSA-2048 signing key — GITIGNORED, keep safe
│
├── crypto/
│   ├── __init__.py
│   └── vault_crypto.py              AES-256-GCM encrypt/decrypt, Argon2id KDF,
│                                    password generator, strength meter
├── auth/
│   ├── __init__.py
│   ├── windows_auth.py              DPAPI encrypt/decrypt, get Windows SID/username
│   └── session.py                   In-memory Session dataclass (bytearray vault key)
│
├── db/
│   ├── __init__.py
│   └── database.py                  Full SQLite CRUD — users, vault_entries, settings
│
├── ui/
│   ├── __init__.py
│   ├── styles.py                    Catppuccin Mocha dark theme (QSS)
│   ├── login_dialog.py              Two pages: unlock + register
│   ├── main_window.py               Vault browser, toolbar, tray, hotkey wiring
│   ├── entry_dialog.py              Add/edit entry + inline password generator
│   ├── password_generator.py        Standalone generator dialog
│   └── import_dialog.py             Tabbed import wizard (Chrome/Edge/Firefox/CSV)
│
├── importers/
│   ├── __init__.py
│   ├── base.py                      ImportedCredential dataclass + BaseImporter ABC
│   ├── chrome_importer.py           Chrome: DPAPI decrypt key from Local State,
│                                    AES-256-GCM decrypt Login Data SQLite
│   ├── edge_importer.py             Edge: inherits ChromeImporter, different path
│   ├── firefox_importer.py          Firefox: CSV export (Method A) or
│                                    firefox_decrypt subprocess (Method B)
│   └── csv_importer.py              Generic CSV with auto column detection
│
├── autofill/
│   ├── __init__.py
│   └── desktop_fill.py              Ctrl+Shift+F global hotkey, keystroke injection
│
├── native_host/
│   ├── __init__.py
│   ├── native_host.py               Standalone browser messaging host (no Qt dep)
│   └── install_host.py              Registers native host for Chrome, Edge, Firefox
│
├── browser_extension/               Chrome + Edge (Manifest V3)
│   ├── manifest.json                Includes "key" field for fixed ID in dev
│   ├── background.js                Service worker, routes all messages
│   ├── content.js                   Form detection, autofill, save/update banner,
│                                    multi-page login support (Gmail etc.)
│   ├── popup.html / popup.js        Toolbar popup with credential list + manual save
│   ├── icon16/48/128.png
│   └── SETUP.html                   Post-install browser setup guide
│
├── browser_extension_firefox/       Firefox (Manifest V2)
│   ├── manifest.json                MV2, browser_action, gecko ID, data_collection_permissions
│   ├── background.js                Same as Chrome version
│   ├── content.js                   Same as Chrome version
│   ├── popup.html / popup.js        Same as Chrome version
│   └── icon16/48/128.png
│
└── installer/
    ├── build.bat                    5-step build pipeline (PyInstaller × 2 + manifests + xpi + ISCC)
    ├── build_manifests.py           Generates Chrome/Edge + Firefox native host manifests
    ├── build_xpi.py                 ZIPs browser_extension_firefox/ → securevault_firefox.xpi
    ├── securevault.spec             PyInstaller spec — main app (onedir, windowed)
    ├── native_host.spec             PyInstaller spec — native host (onefile, console=True)
    ├── setup.iss                    Inno Setup 6 script
    ├── assets/
    │   ├── logo.ico
    │   └── banner.bmp
    ├── templates/                   UNUSED — can be deleted
    ├── dist/                        Build output — gitignore
    ├── build/                       PyInstaller temp — gitignore
    └── output/                      SecureVaultSetup.exe — gitignore
```

---

## 7. Browser Extension Architecture

### Extension ID
- A 2048-bit RSA key (`browser_extension.pem`) was generated via OpenSSL
- The public key is embedded in `browser_extension/manifest.json` as the `key` field
- This makes Chrome derive the same ID (`becngobgachhbpglojolpgioljnfddik`) on every machine
- The `key` field is **removed** before zipping for Chrome Web Store submission
- Firefox ID is fixed via `browser_specific_settings.gecko.id = "securevault@abedy"`

### Native messaging protocol
- 4-byte little-endian length prefix + JSON body over stdin/stdout
- Chrome/Edge/Firefox all launch the native host with `CREATE_NO_WINDOW` — no console flashes
- Native host authenticates via DPAPI (current Windows SID lookup) — no master password in browser
- native_host.exe must be built with `console=True` in PyInstaller — windowed mode kills stdin/stdout

### Supported actions (native host)
| Action | Input | Response |
|---|---|---|
| ping | {} | { status, app } |
| get_credentials | { domain } | { credentials: [{id, title, username, password}] } |
| check_credential | { domain, username, password } | { exists, entry_id, password_changed } |
| save_credential | { url, username, password, title } | { success, entry_id } |
| update_credential | { entry_id, password } | { success } |

### Save/Update flow (critical design)
The save/update banner was broken multiple times before the correct solution was found:

**Root cause 1**: `chrome.storage.session.set()` is async — page navigates away before write completes.  
**Root cause 2**: `beforeunload` throws "Extension context invalidated" — Chrome destroys the JS context before beforeunload fires.  
**Root cause 3**: `return false` in background message handler closes channel before async native host responds.

**Working solution**:
1. Form submit handler → `sessionStorage.setItem()` synchronously (context still alive)
2. Page navigates (context destroyed — doesn't matter, data is in sessionStorage)
3. Next page loads → new content script → `sessionStorage.getItem()` → finds data
4. Sends `CHECK_CREDENTIAL` to background with callback + `return true` to keep channel open
5. Background calls native host → responds via `sendResponse` (not sendToTab)
6. Content script shows Save or Update banner

**Multi-page login** (Gmail, Microsoft, etc.):
- Page 1 has email field but no password → `captureUsernameOnly()` saves to `sv_partial_username` in sessionStorage
- Page 2 has password field → `capture()` reads partial username from sessionStorage, combines with password
- Domain matching uses root domain (`google.com`) not full subdomain (`accounts.google.com`) to handle cross-subdomain redirects

### Two separate extension folders
Firefox ignores the filename you select in about:debugging — it always loads `manifest.json` from the chosen folder. Chrome MV3 and Firefox MV2 have incompatible manifest keys (`service_worker` vs `scripts`, `action` vs `browser_action`). Solution: two completely separate folders with identical JS files but different manifests.

---

## 8. Installer Architecture

### Build pipeline (build.bat)
```
[1/5] PyInstaller → installer/dist/SecureVault/   (main app, onedir, windowed)
[2/5] PyInstaller → installer/dist/native_host.exe (onefile, console=True)
[3/5] build_manifests.py → generates Chrome/Edge + Firefox manifest JSONs
[4/5] build_xpi.py → packages browser_extension_firefox/ as .xpi
[5/5] ISCC.exe setup.iss → installer/output/SecureVaultSetup.exe
```

### What SecureVaultSetup.exe does on install
- Copies app + native host to `C:\Program Files\SecureVault\`
- Copies Chrome/Edge extension folder (for load-unpacked)
- Copies Firefox .xpi
- Creates native host manifest JSON at `{app}\native_host\com.securevault.nativehost.json`
- Creates Firefox manifest at `%APPDATA%\Mozilla\NativeMessagingHosts\`
- Writes HKCU registry keys for Chrome, Edge, Firefox native messaging
- Writes Firefox enterprise policy to `C:\Program Files\Mozilla Firefox\distribution\policies.json`
  — this auto-installs the extension on next Firefox launch (force_installed)
- Creates desktop shortcut + Start Menu entry
- Registers with Add/Remove Programs for clean uninstall

### build_manifests.py
Generates manifests with hardcoded extension ID. The Chrome Web Store assigned
`becngobgachhbpglojolpgioljnfddik` — this is the permanent ID, same on every machine
because it's derived from `browser_extension.pem`.

```python
CHROME_EXTENSION_IDS = ["becngobgachhbpglojolpgioljnfddik"]
FF_EXT_ID = "securevault@abedy"
```

---

## 9. Key Design Decisions

| Decision | Reason |
|---|---|
| AES-256-GCM per-entry (not file-level) | Granular encryption; file-level encryption adds complexity with no real benefit for this threat model |
| Argon2id 64MB/3pass | Expensive enough to resist GPU brute-force; balances security vs unlock speed |
| DPAPI for Windows owner | Zero-friction experience for the owner; DPAPI is hardware-bound, not just password-bound |
| bytearray vault key, zeroed on lock | Reduces window for in-memory credential extraction |
| SQLite plain file (no SQLCipher) | Avoids native dependency hell; per-field encryption achieves same security goal |
| sessionStorage for save/update | Only synchronous cross-navigation browser storage available to content scripts |
| rootDomain() matching for banners | Handles multi-subdomain flows (accounts.google.com → mail.google.com) |
| Two extension folders | Firefox and Chrome have incompatible manifest formats; shared JS avoids code duplication |
| console=True for native host PyInstaller | Browsers launch native hosts with CREATE_NO_WINDOW; windowed mode kills stdin/stdout |
| Onedir for main app | Faster startup than onefile (no temp extraction); cleaner install |
| Onefile for native host | Browser needs a single executable path in the manifest |
| Firefox enterprise policy | Only way to permanently install unsigned Firefox extension without AMO public listing |

---

## 10. What Is Fully Working (v1.0.2)

- ✅ Vault creation, unlock, lock, DPAPI auto-unlock
- ✅ Multi-user support (separate vault per Windows account)
- ✅ AES-256-GCM per-entry encryption / decryption
- ✅ Add / edit / delete / search / categorise entries
- ✅ Password generator with strength meter
- ✅ System tray — minimise, restore, lock, quit
- ✅ Clipboard auto-clear (30 seconds)
- ✅ Import from Chrome (DPAPI key + AES-GCM Login Data decrypt)
- ✅ Import from Edge (same engine)
- ✅ Import from Firefox (CSV export method)
- ✅ Import from generic CSV (Bitwarden, KeePass, 1Password compatible)
- ✅ Chrome extension — autofill button on login pages
- ✅ Chrome extension — credential picker for multiple matches
- ✅ Chrome extension — Save banner after new login (including Gmail/multi-page)
- ✅ Chrome extension — Update banner when password changes
- ✅ Chrome extension — Manual save button in popup
- ✅ Chrome extension — published on Chrome Web Store
- ✅ Edge — works via Chrome extension (same ID, same manifest)
- ✅ Firefox extension — loads via installer enterprise policy
- ✅ Firefox extension — autofill button works
- ✅ Desktop autofill Ctrl+Shift+F — works when app runs as Administrator
- ✅ Windows installer — full automated deployment
- ✅ Native host — DPAPI auto-auth, all 5 actions working
- ✅ Privacy policy live at hossainabedy.com
- ✅ Support page live at hossainabedy.com
- ✅ App icon on desktop shortcut, taskbar, tray
- ✅ SignPath Foundation application submitted (pending approval)
- ✅ Kaspersky exclusion applied server-side for chrome_importer.py

---

## 11. Known Issues / In Progress

| Issue | Status | Notes |
|---|---|---|
| Firefox save/update banner not showing | 🔴 Bug | Chrome works; Firefox MV2 background page vs service worker may affect sendResponse behaviour |
| Ctrl+Shift+F requires admin | 🟡 Limitation | keyboard module needs elevated permissions; installer shortcut has runasadmin flag |
| chrome_importer.py flagged by Kaspersky | 🟡 Workaround applied | Server-side exclusion added; false-positive report filed with Kaspersky; SignPath signing pending |
| Chrome Web Store review delay | 🟡 In review | v1.0.2 update submitted; first version already approved |
| SignPath code signing | 🟡 Pending | Application submitted; approval takes 1–5 business days |
| templates/ folder in installer | 🟢 Minor | Can be deleted — unused, build_manifests.py does not read from it |

---

## 12. Prioritised TODOs

### High priority
1. **Fix Firefox save/update banner** — debug why `sendResponse` + `return true` pattern works in Chrome MV3 service worker but not Firefox MV2 background page; may need `browser.runtime.sendMessage` Promise API instead of callback
2. **Chrome Web Store v1.0.2 approval** — update submitted, waiting for review
3. **SignPath code signing approval** — follow up if no response in 5 business days

### Medium priority
4. **GitHub Release page** — create proper release notes for v1.0.0, v1.0.1, v1.0.2 with SecureVaultSetup.exe attached; update support page download links
5. **Update Chrome Web Store listing** — add `⚠ Official listing only: URL` warning to description; update screenshots to show save banner
6. **Remove templates/ folder** — `installer/templates/` is unused; delete `chrome_manifest.json` and `firefox_manifest.json` and the folder
7. **Firefox manual save button** — popup.js manual save button exists but needs testing in Firefox
8. **Copyright headers** — add `// SecureVault — Copyright (c) 2026 Hossain Abedy Supta` to all JS files in both extension folders

### Low priority / Future
9. **Auto-update pipeline** — Chrome Web Store handles Chrome; Firefox AMO handles Firefox; installer update mechanism TBD
10. **Password history** — store previous passwords per entry with timestamps
11. **Secure notes** — entries without username/URL, just encrypted text
12. **Export vault** — encrypted JSON or CSV export for backup
13. **Two-factor vault unlock** — TOTP as second factor for master password path
14. **Cross-platform** — Linux/macOS would require replacing DPAPI with platform-equivalent
15. **Chrome extension enterprise deployment** — currently requires load-unpacked; Web Store listing enables force-install via registry

---

## 13. Development Environment

- **OS**: Windows 11
- **Shell**: Git Bash (MINGW64) — use `source .venv/Scripts/activate` not `.venv\Scripts\activate`
- **Python**: 3.11+ in `.venv` virtual environment
- **Key packages**: PyQt6, cryptography, argon2-cffi, pywin32, keyboard, psutil, pyperclip, pyinstaller
- **Build tools**: Inno Setup 6 at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
- **Editor**: VS Code or any editor — no special config required
- **AV**: Kaspersky Endpoint Security managed — `chrome_importer.py` requires folder exclusion

### Quick start
```bash
source .venv/Scripts/activate
python main.py
```

### Build installer
```bash
cmd //c installer/build.bat
# Output: installer/output/SecureVaultSetup.exe
```

### Register native host (dev)
```bash
python native_host/install_host.py --chrome-ext-id becngobgachhbpglojolpgioljnfddik --firefox
```

---

## 14. Vault Database Location Note

The database at `%USERPROFILE%\.securevault\vault.db` is shared across ALL versions of the app. Extracting a new zip or reinstalling does not create a new vault — it always connects to the same existing database. This is intentional and correct behaviour.

---

## 15. Publishing Status

| Channel | Status |
|---|---|
| Chrome Web Store | ✅ Published — v1.0.1 live, v1.0.2 in review |
| Microsoft Edge | ✅ Works via Chrome extension (same ID) |
| Mozilla AMO | ✅ Submitted unlisted — signed XPI used by installer |
| Windows Installer | ✅ v1.0.2 — SecureVaultSetup.exe |
| Privacy Policy | ✅ Live at hossainabedy.com |
| Support Page | ✅ Live at hossainabedy.com |
| Portfolio listing | ✅ Added to hossainabedy.com Projects section |
| LinkedIn announcement | ✅ Posted |
| SignPath code signing | 🟡 Application submitted, pending review |
