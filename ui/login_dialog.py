"""
Login / Registration dialog.

Page 0 – Unlock: auto-detects Windows user for DPAPI path; falls back to
          username + master password for all others.
Page 1 – Register: creates a new vault, optionally linked to the current
          Windows account.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QWidget, QComboBox,
    QCheckBox, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import db.database as db
import auth.windows_auth as win_auth
import auth.session as session_mgr
from auth.session import Session
from crypto.vault_crypto import (
    generate_vault_key,
    derive_key_from_password,
    hash_password,
    verify_password,
    encrypt,
    decrypt,
)


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SecureVault")
        self.setFixedSize(420, 540)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._setup_ui()

    # ── UI construction ─────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 28, 40, 28)
        root.setSpacing(0)

        # Logo
        title = QLabel("🔐  SecureVault")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel("Windows 11 password vault")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addSpacing(14)
        root.addWidget(line)
        root.addSpacing(14)

        # Pages
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self._build_unlock_page()
        self._build_register_page()

        root.addSpacing(14)
        self.switch_btn = QPushButton("Create new vault  →")
        self.switch_btn.setObjectName("secondary")
        self.switch_btn.clicked.connect(self._switch_page)
        root.addWidget(self.switch_btn)

    # ── Unlock page ──────────────────────────────────────────────────────────

    def _build_unlock_page(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lay.addWidget(self._label("Username"))
        self.ul_combo = QComboBox()
        self._refresh_user_list()
        lay.addWidget(self.ul_combo)

        lay.addSpacing(4)
        lay.addWidget(self._label("Master Password"))
        self.ul_pw = QLineEdit()
        self.ul_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.ul_pw.setPlaceholderText("Enter master password (or leave blank if Windows user)")
        self.ul_pw.returnPressed.connect(self._do_unlock)
        lay.addWidget(self.ul_pw)

        lay.addSpacing(6)
        self.win_status = QLabel()
        self.win_status.setObjectName("subtitle")
        self.win_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.win_status)
        self._check_windows_autounlock()

        lay.addSpacing(10)
        unlock_btn = QPushButton("Unlock Vault")
        unlock_btn.clicked.connect(self._do_unlock)
        lay.addWidget(unlock_btn)

        self.ul_error = QLabel()
        self.ul_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        self.ul_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.ul_error)

        lay.addStretch()
        self.stack.addWidget(page)

    def _check_windows_autounlock(self):
        try:
            sid  = win_auth.get_current_windows_sid()
            user = db.get_user_by_sid(sid)
            if user and user["dpapi_enc_key"]:
                name = win_auth.get_current_username()
                self.win_status.setText(
                    f"✅  Windows auto-unlock ready for '{name}'"
                )
                self.win_status.setStyleSheet("color: #a6e3a1; font-size: 12px;")
                # Pre-select that user in combo
                idx = self.ul_combo.findText(user["username"])
                if idx >= 0:
                    self.ul_combo.setCurrentIndex(idx)
            else:
                self.win_status.setText(
                    "ℹ️  Windows account not linked — enter master password"
                )
        except Exception:
            self.win_status.setText("ℹ️  Windows auth unavailable")

    def _refresh_user_list(self):
        self.ul_combo.clear()
        users = db.get_all_users()
        for u in users:
            self.ul_combo.addItem(u["username"], u["id"])
        if not users:
            self.ul_combo.addItem("(no vaults found)")

    # ── Register page ────────────────────────────────────────────────────────

    def _build_register_page(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lay.addWidget(self._label("Username"))
        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("e.g.  abedy")
        lay.addWidget(self.reg_user)

        lay.addSpacing(4)
        lay.addWidget(self._label("Master Password"))
        self.reg_pw = QLineEdit()
        self.reg_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_pw.setPlaceholderText("Minimum 10 characters")
        lay.addWidget(self.reg_pw)

        lay.addWidget(self._label("Confirm Password"))
        self.reg_pw2 = QLineEdit()
        self.reg_pw2.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_pw2.setPlaceholderText("Re-enter password")
        self.reg_pw2.returnPressed.connect(self._do_register)
        lay.addWidget(self.reg_pw2)

        lay.addSpacing(6)
        self.win_link_cb = QCheckBox(
            "Link to current Windows account (enables auto-unlock)"
        )
        self.win_link_cb.setChecked(True)
        lay.addWidget(self.win_link_cb)

        lay.addSpacing(10)
        reg_btn = QPushButton("Create Vault")
        reg_btn.clicked.connect(self._do_register)
        lay.addWidget(reg_btn)

        self.reg_error = QLabel()
        self.reg_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        self.reg_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reg_error.setWordWrap(True)
        lay.addWidget(self.reg_error)

        lay.addStretch()
        self.stack.addWidget(page)

    # ── Page switching ───────────────────────────────────────────────────────

    def _switch_page(self):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)
            self.switch_btn.setText("←  Back to unlock")
        else:
            self._refresh_user_list()
            self.stack.setCurrentIndex(0)
            self.switch_btn.setText("Create new vault  →")

    # ── Unlock logic ─────────────────────────────────────────────────────────

    def _do_unlock(self):
        self.ul_error.clear()
        username = self.ul_combo.currentText()
        password = self.ul_pw.text()

        if not username or username == "(no vaults found)":
            self.ul_error.setText("No vault found. Please create one first.")
            return

        user = db.get_user_by_username(username)
        if not user:
            self.ul_error.setText("User not found.")
            return

        vault_key    = None
        is_win_user  = False

        # 1️⃣  Try Windows DPAPI auto-unlock
        try:
            sid = win_auth.get_current_windows_sid()
            if user["windows_sid"] == sid and user["dpapi_enc_key"]:
                vault_key   = win_auth.dpapi_decrypt(bytes(user["dpapi_enc_key"]))
                is_win_user = True
        except Exception:
            pass

        # 2️⃣  Fall back to master password
        if vault_key is None:
            if not password:
                self.ul_error.setText(
                    "Windows auto-unlock failed or not configured.\n"
                    "Please enter your master password."
                )
                return
            if not user["mpw_hash"] or not verify_password(user["mpw_hash"], password):
                self.ul_error.setText("Incorrect master password.")
                return
            try:
                derived_key, _ = derive_key_from_password(
                    password, bytes(user["mpw_salt"])
                )
                vault_key = decrypt(bytes(user["mpw_enc_key"]), derived_key)
            except Exception as exc:
                self.ul_error.setText(f"Decryption failed: {exc}")
                return

        session_mgr.set_session(
            Session(
                user_id=user["id"],
                username=username,
                vault_key=bytearray(vault_key),
                is_windows_user=is_win_user,
                windows_sid=user["windows_sid"],
            )
        )
        self.accept()

    # ── Register logic ────────────────────────────────────────────────────────

    def _do_register(self):
        self.reg_error.clear()
        username = self.reg_user.text().strip()
        pw       = self.reg_pw.text()
        pw2      = self.reg_pw2.text()

        if not username:
            self.reg_error.setText("Username cannot be empty.")
            return
        if len(pw) < 10:
            self.reg_error.setText("Password must be at least 10 characters.")
            return
        if pw != pw2:
            self.reg_error.setText("Passwords do not match.")
            return
        if db.get_user_by_username(username):
            self.reg_error.setText("Username already exists.")
            return

        # Generate vault key
        vault_key   = generate_vault_key()

        # Wrap with master password (Argon2id)
        derived_key, salt = derive_key_from_password(pw)
        mpw_enc_key = encrypt(vault_key, derived_key)
        mpw_hash    = hash_password(pw)

        # Optionally wrap with DPAPI too
        win_sid      = None
        dpapi_enc_key = None
        if self.win_link_cb.isChecked():
            try:
                win_sid      = win_auth.get_current_windows_sid()
                dpapi_enc_key = win_auth.dpapi_encrypt(vault_key)
            except Exception as exc:
                self.reg_error.setText(
                    f"Windows account link failed:\n{exc}\n\n"
                    "Vault created with master password only."
                )

        user_id = db.create_user(
            username,
            windows_sid=win_sid,
            dpapi_enc_key=dpapi_enc_key,
            mpw_salt=salt,
            mpw_enc_key=mpw_enc_key,
            mpw_hash=mpw_hash,
        )

        session_mgr.set_session(
            Session(
                user_id=user_id,
                username=username,
                vault_key=bytearray(vault_key),
                is_windows_user=bool(win_sid),
                windows_sid=win_sid,
            )
        )
        self.accept()

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("sectionHead")
        return lbl
