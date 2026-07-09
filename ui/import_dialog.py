"""
Import Passwords dialog.

Tabs: Chrome · Edge · Firefox · CSV
Each importer is loaded lazily inside a try/except — if one browser's
dependencies are missing it just disables that tab, it does not crash.
"""

from __future__ import annotations
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QFileDialog, QMessageBox,
    QComboBox, QGroupBox, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui  import QFont

import db.database  as db
import auth.session as session_mgr
from crypto.vault_crypto    import encrypt
from importers.base         import ImportedCredential


# ── Lazy importer loader ──────────────────────────────────────────────────────

def _load_chrome():
    from importers.chrome_importer import ChromeImporter
    return ChromeImporter()

def _load_edge():
    from importers.edge_importer import EdgeImporter
    return EdgeImporter()

def _load_firefox():
    from importers.firefox_importer import FirefoxImporter
    return FirefoxImporter()

def _load_csv(path=None):
    from importers.csv_importer import CSVImporter
    return CSVImporter(path)


# ── Background import worker ──────────────────────────────────────────────────

class _Worker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(int)

    def __init__(self, creds, user_id, vault_key):
        super().__init__()
        self._creds     = creds
        self._user_id   = user_id
        self._vault_key = vault_key

    def run(self):
        saved = 0
        total = len(self._creds)
        for i, c in enumerate(self._creds):
            try:
                enc = encrypt(c.password.encode(), self._vault_key)
                db.add_entry(
                    user_id      = self._user_id,
                    title        = c.title,
                    url          = c.url,
                    username     = c.username,
                    enc_password = enc,
                    notes        = c.notes,
                    category     = c.category,
                )
                saved += 1
            except Exception:
                pass
            self.progress.emit(i + 1, total)
        self.finished.emit(saved)


# ── Dialog ────────────────────────────────────────────────────────────────────

class ImportDialog(QDialog):

    imported = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Passwords")
        self.setMinimumSize(800, 580)
        self._found:    list[ImportedCredential] = []
        self._worker:   _Worker | None           = None
        self._thread:   QThread | None           = None
        self._ff_csv:   str | None               = None
        self._csv_path: str | None               = None
        self._setup_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        head = QLabel("Import Passwords from Browsers or a CSV File")
        head.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        head.setStyleSheet("color: #89b4fa;")
        root.addWidget(head)

        sub = QLabel(
            "Scan your installed browsers to copy saved passwords into SecureVault. "
            "Duplicate entries are not detected automatically — review before importing."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #a6adc8; font-size: 12px;")
        root.addWidget(sub)

        tabs = QTabWidget()
        tabs.addTab(self._browser_tab("Chrome",  _load_chrome),  "🌐  Chrome")
        tabs.addTab(self._browser_tab("Edge",    _load_edge),    "🌀  Edge")
        tabs.addTab(self._firefox_tab(),                          "🦊  Firefox")
        tabs.addTab(self._csv_tab(),                              "📄  CSV")
        root.addWidget(tabs)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        root.addWidget(QLabel("Preview — credentials found:"))
        self._preview = QTreeWidget()
        self._preview.setColumnCount(3)
        self._preview.setHeaderLabels(["Title / Domain", "Username", "URL"])
        self._preview.setAlternatingRowColors(True)
        self._preview.setFixedHeight(160)
        root.addWidget(self._preview)

        self._prog = QProgressBar()
        self._prog.setVisible(False)
        root.addWidget(self._prog)

        btn_row = QHBoxLayout()
        self._status = QLabel()
        self._status.setStyleSheet("color: #a6adc8;")
        btn_row.addWidget(self._status, 1)

        self._import_btn = QPushButton("Import All")
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._do_import)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.reject)

        btn_row.addWidget(close_btn)
        btn_row.addWidget(self._import_btn)
        root.addLayout(btn_row)

    # ── Chrome / Edge tab ─────────────────────────────────────────────────────

    def _browser_tab(self, name: str, loader_fn) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(10)

        # Try loading the importer
        try:
            importer = loader_fn()
        except Exception as exc:
            import traceback
            err = traceback.format_exc()
            lay.addWidget(QLabel(f"⚠  Could not load {name} importer:"))
            details = QLabel(str(exc))
            details.setStyleSheet("color: #f38ba8; font-size: 11px; font-family: Consolas;")
            details.setWordWrap(True)
            details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lay.addWidget(details)
            lay.addStretch()
            return page

        if not importer.is_available():
            lay.addWidget(QLabel(f"⚠  {name} does not appear to be installed on this PC."))
            lay.addStretch()
            return page

        try:
            profiles = importer.get_profiles()
        except Exception as exc:
            lay.addWidget(QLabel(f"⚠  Could not read {name} profiles:\n{exc}"))
            lay.addStretch()
            return page

        if not profiles:
            lay.addWidget(QLabel(f"⚠  No {name} profiles found."))
            lay.addStretch()
            return page

        lay.addWidget(QLabel("Select profile:"))
        combo = QComboBox()
        for p in profiles:
            combo.addItem(p["name"], str(p["path"]))
        lay.addWidget(combo)

        note = QLabel(f"{len(profiles)} profile(s) found. Click Scan to preview.")
        note.setStyleSheet("color: #a6adc8; font-size: 12px;")
        lay.addWidget(note)

        scan_btn = QPushButton(f"🔍  Scan {name}")
        scan_btn.clicked.connect(
            lambda: self._scan_browser(importer, Path(combo.currentData()))
        )
        lay.addWidget(scan_btn)
        lay.addStretch()
        return page

    # ── Firefox tab ───────────────────────────────────────────────────────────

    def _firefox_tab(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(10)

        # Method A — CSV
        g_csv = QGroupBox("Method A  —  Firefox exported CSV  (recommended)")
        gc    = QVBoxLayout(g_csv)
        gc.addWidget(QLabel(
            "In Firefox:  ☰ → Passwords → ⋯ → Export Passwords… → save as .csv\n"
            "Then select the file below."
        ))
        row_a = QHBoxLayout()
        self._ff_csv_label = QLabel("No file selected")
        self._ff_csv_label.setStyleSheet("color: #a6adc8;")
        browse_a = QPushButton("Browse…")
        browse_a.setObjectName("secondary")
        browse_a.clicked.connect(self._browse_ff_csv)
        row_a.addWidget(self._ff_csv_label, 1)
        row_a.addWidget(browse_a)
        gc.addLayout(row_a)
        scan_csv = QPushButton("🔍  Scan CSV")
        scan_csv.clicked.connect(self._scan_ff_csv)
        gc.addWidget(scan_csv)
        lay.addWidget(g_csv)

        # Method B — Auto (optional dep)
        try:
            ff = _load_firefox()
            if ff.is_available():
                g_auto = QGroupBox(
                    "Method B  —  Auto-decrypt  (requires:  pip install firefox_decrypt)"
                )
                ga    = QVBoxLayout(g_auto)
                combo = QComboBox()
                for p in ff.get_profiles():
                    combo.addItem(p["name"], str(p["path"]))
                self._ff_combo = combo
                ga.addWidget(combo)
                auto_btn = QPushButton("🔍  Auto-decrypt Profile")
                auto_btn.clicked.connect(
                    lambda: self._scan_browser(ff, Path(combo.currentData()))
                )
                ga.addWidget(auto_btn)
                lay.addWidget(g_auto)
        except Exception:
            pass

        lay.addStretch()
        return page

    # ── CSV tab ───────────────────────────────────────────────────────────────

    def _csv_tab(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setSpacing(10)
        lay.addWidget(QLabel(
            "Import any CSV with columns: url, username, password\n"
            "Optional: name / title\n"
            "Compatible with Bitwarden, 1Password, KeePass, LastPass exports."
        ))
        row = QHBoxLayout()
        self._csv_label = QLabel("No file selected")
        self._csv_label.setStyleSheet("color: #a6adc8;")
        browse = QPushButton("Browse…")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._browse_csv)
        row.addWidget(self._csv_label, 1)
        row.addWidget(browse)
        lay.addLayout(row)
        scan_btn = QPushButton("🔍  Scan CSV")
        scan_btn.clicked.connect(self._scan_csv)
        lay.addWidget(scan_btn)
        lay.addStretch()
        return page

    # ── Scan actions ──────────────────────────────────────────────────────────

    def _scan_browser(self, importer, profile_path: Path | None = None):
        self._status.setText("Scanning…")
        try:
            creds = importer.import_from(profile_path=profile_path)
            self._show_preview(creds)
        except Exception as exc:
            self._status.setText("")
            QMessageBox.critical(self, "Scan Error", str(exc))

    def _browse_ff_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Firefox exported CSV", "", "CSV files (*.csv)"
        )
        if path:
            self._ff_csv = path
            self._ff_csv_label.setText(Path(path).name)

    def _scan_ff_csv(self):
        if not self._ff_csv:
            QMessageBox.warning(self, "No file", "Please select a CSV file first.")
            return
        try:
            ff    = _load_firefox()
            creds = ff.import_from(csv_path=self._ff_csv)
            self._show_preview(creds)
        except Exception as exc:
            QMessageBox.critical(self, "CSV Error", str(exc))

    def _browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV file", "", "CSV files (*.csv);;All files (*.*)"
        )
        if path:
            self._csv_path = path
            self._csv_label.setText(Path(path).name)

    def _scan_csv(self):
        if not self._csv_path:
            QMessageBox.warning(self, "No file", "Please select a CSV file first.")
            return
        try:
            creds = _load_csv(self._csv_path).import_from()
            self._show_preview(creds)
        except Exception as exc:
            QMessageBox.critical(self, "CSV Error", str(exc))

    def _show_preview(self, creds: list[ImportedCredential]):
        self._found = creds
        self._preview.clear()
        for c in creds:
            self._preview.addTopLevelItem(
                QTreeWidgetItem([c.title, c.username, c.url])
            )
        for col in range(3):
            self._preview.resizeColumnToContents(col)
        n = len(creds)
        self._status.setText(f"Found {n} credential{'s' if n != 1 else ''}.")
        self._import_btn.setEnabled(bool(creds))

    # ── Import ────────────────────────────────────────────────────────────────

    def _do_import(self):
        session = session_mgr.get_session()
        if not session:
            QMessageBox.critical(self, "Error", "No active session — vault is locked.")
            return

        n = len(self._found)
        if QMessageBox.question(
            self, "Confirm Import",
            f"Import {n} credential{'s' if n != 1 else ''} into SecureVault?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        self._import_btn.setEnabled(False)
        self._prog.setRange(0, n)
        self._prog.setValue(0)
        self._prog.setVisible(True)

        self._worker = _Worker(self._found, session.user_id, session.key_bytes)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda d, _: self._prog.setValue(d))
        self._worker.finished.connect(self._on_done)
        self._thread.start()

    def _on_done(self, count: int):
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        self._prog.setVisible(False)
        self._status.setText(f"✅  Imported {count} entries.")
        self.imported.emit(count)
        QMessageBox.information(
            self, "Import Complete",
            f"Successfully imported {count} password entries.\n"
            "The vault list will refresh automatically.",
        )
