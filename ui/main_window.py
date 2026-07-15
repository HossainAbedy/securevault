"""
Main vault window.

Features
────────
• Sidebar category filter
• Searchable entry list with detail preview panel
• Copy username / password (auto-clears clipboard after 30 s)
• Right-click context menu
• System-tray icon — closing minimises to tray
• Ctrl+Shift+F global hotkey → desktop autofill
• Lock button zeros vault key and returns to login
"""

import threading
import pyperclip

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QPushButton, QLabel,
    QSystemTrayIcon, QMenu, QStatusBar, QMessageBox, QFrame,
    QToolBar, QSizePolicy, QInputDialog,
)
from PyQt6.QtCore  import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui   import QAction, QFont, QColor, QIcon

import db.database   as db
import auth.session  as session_mgr
from crypto.vault_crypto    import decrypt, encrypt
from autofill.desktop_fill  import register_autofill_hotkey, unregister_autofill_hotkey
from ui.entry_dialog        import EntryDialog
from ui.password_generator  import PasswordGeneratorDialog

CATEGORIES = ["All Entries", "General", "Banking", "Social",
              "Email", "Work", "Shopping", "Other"]


# ── Signal bridge so hotkey thread can talk to Qt main thread ────────────────

class _AutofillSignals(QObject):
    match_found    = pyqtSignal(list, str)   # (entries, window_title)
    no_match       = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureVault")
        self.setMinimumSize(960, 620)

        self._cache: list = []
        self._clip_timer: QTimer | None = None
        self._af_signals = _AutofillSignals()
        self._af_signals.match_found.connect(self._show_autofill_picker)
        self._af_signals.no_match.connect(self._af_no_match)

        self._build_ui()
        self._build_tray()
        self._load_entries()
        self._register_hotkey()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        def _act(label, slot, tip=""):
            a = QAction(label, self)
            a.triggered.connect(slot)
            a.setToolTip(tip)
            tb.addAction(a)
            return a

        _act("＋  Add Entry",        self._add_entry,     "Add a new credential")
        _act("🔑  Generator",         self._open_gen,      "Open password generator")
        tb.addSeparator()
        _act("🔒  Lock Vault",        self._lock,          "Lock and return to login")
        tb.addSeparator()
        _act("⚙  Link Windows Acct", self._link_windows,  "Link current Windows login for auto-unlock")
        tb.addSeparator()
        _act("📥  Import",            self._open_import,   "Import passwords from Chrome, Edge, Firefox or CSV")

        # Spacer + search
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search…")
        self.search.setFixedWidth(220)
        self.search.textChanged.connect(self._on_search)
        tb.addWidget(self.search)

        # ── Central splitter ──────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout(central)
        h.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        h.addWidget(splitter)

        # Left: category tree
        self._cat_tree = QTreeWidget()
        self._cat_tree.setHeaderHidden(True)
        self._cat_tree.setFixedWidth(162)
        for cat in CATEGORIES:
            self._cat_tree.addTopLevelItem(QTreeWidgetItem([cat]))
        self._cat_tree.setCurrentItem(self._cat_tree.topLevelItem(0))
        self._cat_tree.itemClicked.connect(
            lambda item: self._load_entries(category=item.text(0))
        )
        splitter.addWidget(self._cat_tree)

        # Right panel
        right = QWidget()
        rv    = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)

        # Entry list
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Title", "Username", "URL", "Category"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setSortingEnabled(True)
        self._tree.itemClicked.connect(self._on_select)
        self._tree.itemDoubleClicked.connect(
            lambda item, _: self._edit_entry(item.data(0, Qt.ItemDataRole.UserRole))
        )
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._ctx_menu)
        rv.addWidget(self._tree, 1)

        # Detail / action panel
        detail = QFrame()
        detail.setFrameShape(QFrame.Shape.StyledPanel)
        detail.setFixedHeight(130)
        dh = QHBoxLayout(detail)

        info = QVBoxLayout()
        self._d_title = QLabel("Select an entry")
        self._d_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._d_url   = QLabel()
        self._d_url.setObjectName("subtitle")
        self._d_user  = QLabel()
        self._d_user.setObjectName("subtitle")
        for w in (self._d_title, self._d_url, self._d_user):
            info.addWidget(w)
        info.addStretch()
        dh.addLayout(info, 1)

        actions = QVBoxLayout()
        self._btn_copy_user = QPushButton("📋  Copy Username")
        self._btn_copy_pw   = QPushButton("🔑  Copy Password")
        self._btn_edit      = QPushButton("✏️  Edit")
        for b in (self._btn_copy_user, self._btn_copy_pw, self._btn_edit):
            b.setObjectName("secondary")
            actions.addWidget(b)
        self._btn_copy_user.clicked.connect(self._copy_username)
        self._btn_copy_pw.clicked.connect(self._copy_password)
        self._btn_edit.clicked.connect(
            lambda: self._edit_entry(self._selected_id())
        )
        dh.addLayout(actions)
        rv.addWidget(detail)

        splitter.addWidget(right)
        splitter.setSizes([162, 798])

        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        s = session_mgr.get_session()
        tag = " (Windows auto-unlock)" if s.is_windows_user else ""
        sb.showMessage(f"👤  {s.username}{tag}")

    # ── Tray ─────────────────────────────────────────────────────────────────

    def _build_tray(self):
        import sys
        import os

        # Resolve icon path (works in development and PyInstaller)
        if hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "securevault.ico")
        else:
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "securevault.ico"
            )

        icon = QIcon(icon_path)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("SecureVault")

        menu = QMenu()

        menu.addAction("Show Vault").triggered.connect(self._show_window)
        menu.addAction("Lock Vault").triggered.connect(self._lock)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(self._quit)

        self._tray.setContextMenu(menu)

        self._tray.activated.connect(
            lambda reason: self._show_window()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )

        self._tray.show()

    def _show_window(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "SecureVault",
            "Vault is still running. Double-click the tray icon to reopen.",
            QSystemTrayIcon.MessageIcon.Information, 2500,
        )

    # ── Hotkey registration ───────────────────────────────────────────────────

    def _register_hotkey(self):
        try:
            register_autofill_hotkey(self._autofill_trigger)
        except Exception:
            pass   # keyboard module may need elevation; fail silently

    def _autofill_trigger(self, window_info: dict):
        """Called from hotkey thread — find matching entries, emit signal."""
        session = session_mgr.get_session()
        if not session:
            return
        title   = window_info.get("title", "")
        process = window_info.get("process", "").lower()

        # Search by window title words
        words = [w for w in title.replace("–","").replace("-","").split() if len(w) > 3]
        hits  = []
        seen  = set()
        for word in words:
            for e in db.search_entries(session.user_id, word):
                if e["id"] not in seen:
                    hits.append(e)
                    seen.add(e["id"])

        if hits:
            self._af_signals.match_found.emit(list(hits), title)
        else:
            self._af_signals.no_match.emit(title)

    # ── Entry loading ─────────────────────────────────────────────────────────

    def _load_entries(self, *, category: str = None, query: str = None):
        session = session_mgr.get_session()
        if not session:
            return

        if query:
            rows = db.search_entries(session.user_id, query)
        else:
            rows = db.get_entries(session.user_id)

        self._cache = list(rows)
        self._tree.clear()

        active_cat = (
            category
            or (self._cat_tree.currentItem().text(0)
                if self._cat_tree.currentItem() else "All Entries")
        )

        for e in self._cache:
            if active_cat not in ("All Entries", None) and e["category"] != active_cat:
                continue
            item = QTreeWidgetItem([
                e["title"],
                e["entry_username"] or "",
                e["url"] or "",
                e["category"],
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, e["id"])
            self._tree.addTopLevelItem(item)

        for col in range(4):
            self._tree.resizeColumnToContents(col)

        count = self._tree.topLevelItemCount()
        self.statusBar().showMessage(
            f"{count} {'entry' if count == 1 else 'entries'}", 4000
        )

    def _on_search(self, text: str):
        if text.strip():
            self._load_entries(query=text.strip())
        else:
            self._load_entries()

    # ── Selection / detail ────────────────────────────────────────────────────

    def _selected_id(self) -> int | None:
        item = self._tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def _on_select(self, item: QTreeWidgetItem):
        eid     = item.data(0, Qt.ItemDataRole.UserRole)
        session = session_mgr.get_session()
        entry   = db.get_entry(eid, session.user_id)
        if not entry:
            return
        self._d_title.setText(entry["title"])
        self._d_url.setText(entry["url"] or "—")
        self._d_user.setText(f"👤  {entry['entry_username'] or '—'}")

    # ── CRUD actions ──────────────────────────────────────────────────────────

    def _add_entry(self):
        dlg = EntryDialog(self)
        if dlg.exec():
            self._load_entries()

    def _edit_entry(self, entry_id: int | None):
        if not entry_id:
            return
        session = session_mgr.get_session()
        entry   = db.get_entry(entry_id, session.user_id)
        if entry and EntryDialog(self, entry=entry).exec():
            self._load_entries()

    def _delete_entry(self, entry_id: int):
        if QMessageBox.question(
            self, "Delete Entry",
            "Permanently delete this entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            session = session_mgr.get_session()
            db.delete_entry(entry_id, session.user_id)
            self._load_entries()

    # ── Copy helpers ──────────────────────────────────────────────────────────

    def _copy_username(self):
        eid     = self._selected_id()
        session = session_mgr.get_session()
        if not eid or not session:
            return
        entry = db.get_entry(eid, session.user_id)
        if entry and entry["entry_username"]:
            pyperclip.copy(entry["entry_username"])
            self.statusBar().showMessage("Username copied to clipboard.", 3000)

    def _copy_password(self):
        eid     = self._selected_id()
        session = session_mgr.get_session()
        if not eid or not session:
            return
        entry = db.get_entry(eid, session.user_id)
        if not entry:
            return
        try:
            pw = decrypt(bytes(entry["enc_password"]), session.key_bytes).decode()
            pyperclip.copy(pw)
            self.statusBar().showMessage(
                "Password copied. Clipboard clears in 30 s.", 4000
            )
            # Auto-clear
            if self._clip_timer:
                self._clip_timer.stop()
            self._clip_timer = QTimer(singleShot=True)
            self._clip_timer.timeout.connect(lambda: pyperclip.copy(""))
            self._clip_timer.start(30_000)
        except Exception as exc:
            QMessageBox.critical(self, "Decryption Error", str(exc))

    # ── Context menu ──────────────────────────────────────────────────────────

    def _ctx_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        eid  = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("📋  Copy Username").triggered.connect(self._copy_username)
        menu.addAction("🔑  Copy Password").triggered.connect(self._copy_password)
        menu.addSeparator()
        menu.addAction("✏️  Edit").triggered.connect(lambda: self._edit_entry(eid))
        menu.addAction("🗑️  Delete").triggered.connect(lambda: self._delete_entry(eid))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ── Autofill UI (hotkey result on main thread) ────────────────────────────

    def _show_autofill_picker(self, entries: list, window_title: str):
        """Show a small dialog so the user picks which credential to autofill."""
        from autofill.desktop_fill import type_credentials

        labels = [
            f"{e['title']}  —  {e['entry_username'] or '(no username)'}"
            for e in entries
        ]
        choice, ok = QInputDialog.getItem(
            self, "SecureVault Autofill",
            f"Window: {window_title}\n\nChoose credential to fill:",
            labels, 0, False,
        )
        if not ok:
            return

        idx     = labels.index(choice)
        entry   = entries[idx]
        session = session_mgr.get_session()
        try:
            pw = decrypt(bytes(entry["enc_password"]), session.key_bytes).decode()
        except Exception as exc:
            QMessageBox.critical(self, "Decryption Error", str(exc))
            return

        # Return focus to the original window before typing
        self.hide()
        QTimer.singleShot(
            400,
            lambda: threading.Thread(
                target=type_credentials,
                args=(entry["entry_username"] or "", pw),
                daemon=True,
            ).start(),
        )

    def _af_no_match(self, window_title: str):
        self._tray.showMessage(
            "SecureVault",
            f"No saved credentials match:\n{window_title}",
            QSystemTrayIcon.MessageIcon.Information, 2500,
        )

    # ── Windows account link ──────────────────────────────────────────────────

    def _link_windows(self):
        """Let a master-password user add DPAPI auto-unlock retroactively."""
        import auth.windows_auth as win_auth
        session = session_mgr.get_session()
        if session.is_windows_user:
            QMessageBox.information(
                self, "Already linked",
                "This vault is already linked to your Windows account.",
            )
            return
        try:
            sid          = win_auth.get_current_windows_sid()
            user         = db.get_user_by_username(session.username)
            dpapi_blob   = win_auth.dpapi_encrypt(session.key_bytes)
            db.update_user_dpapi(user["id"], dpapi_blob, sid)
            session.is_windows_user = True
            session.windows_sid     = sid
            QMessageBox.information(
                self, "Linked",
                f"Vault is now linked to Windows account '{win_auth.get_current_username()}'.\n"
                "You will be auto-unlocked next time you launch SecureVault.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Link Failed", str(exc))

    # ── Import ────────────────────────────────────────────────────────────────

    def _open_import(self):
        from ui.import_dialog import ImportDialog
        dlg = ImportDialog(self)
        dlg.imported.connect(lambda _: self._load_entries())
        dlg.exec()

    # ── Password generator ────────────────────────────────────────────────────

    def _open_gen(self):
        PasswordGeneratorDialog(self).exec()

    # ── Lock / quit ───────────────────────────────────────────────────────────

    def _lock(self):
        unregister_autofill_hotkey()
        session_mgr.clear_session()
        self.hide()

        from ui.login_dialog import LoginDialog
        dlg = LoginDialog()
        if dlg.exec():
            win = MainWindow()
            win.show()
            self.deleteLater()
        else:
            self._quit()

    def _quit(self):
        unregister_autofill_hotkey()
        session_mgr.clear_session()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
