"""Add / Edit vault entry dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox,
)
from PyQt6.QtCore import Qt

import db.database as db
import auth.session as session_mgr
from crypto.vault_crypto import encrypt, decrypt
from ui.password_generator import PasswordGeneratorDialog

CATEGORIES = ["General", "Banking", "Social", "Email", "Work", "Shopping", "Other"]


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry=None):
        super().__init__(parent)
        self._entry = entry
        self.setWindowTitle("Edit Entry" if entry else "New Entry")
        self.setFixedSize(500, 430)
        self._setup_ui()
        if entry:
            self._populate(entry)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # Title
        self.f_title = QLineEdit()
        self.f_title.setPlaceholderText("e.g.  Gmail, SBAC NetBanking")
        form.addRow("Title *", self.f_title)

        # URL
        self.f_url = QLineEdit()
        self.f_url.setPlaceholderText("https://example.com")
        form.addRow("URL", self.f_url)

        # Username
        self.f_user = QLineEdit()
        self.f_user.setPlaceholderText("username or email")
        form.addRow("Username", self.f_user)

        # Password row (field + toggle + generate)
        pw_row = QHBoxLayout()
        self.f_pw = QLineEdit()
        self.f_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_pw.setPlaceholderText("password")

        self.eye_btn = QPushButton("👁")
        self.eye_btn.setFixedWidth(34)
        self.eye_btn.setObjectName("secondary")
        self.eye_btn.setCheckable(True)
        self.eye_btn.setToolTip("Show / hide password")
        self.eye_btn.toggled.connect(
            lambda on: self.f_pw.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )

        gen_btn = QPushButton("Generate")
        gen_btn.setObjectName("secondary")
        gen_btn.clicked.connect(self._open_generator)

        pw_row.addWidget(self.f_pw)
        pw_row.addWidget(self.eye_btn)
        pw_row.addWidget(gen_btn)
        form.addRow("Password *", pw_row)

        # Category
        self.f_cat = QComboBox()
        self.f_cat.addItems(CATEGORIES)
        form.addRow("Category", self.f_cat)

        # Notes
        self.f_notes = QTextEdit()
        self.f_notes.setFixedHeight(72)
        self.f_notes.setPlaceholderText("Optional notes…")
        form.addRow("Notes", self.f_notes)

        root.addLayout(form)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondary")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)

        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    # ── Populate (edit mode) ──────────────────────────────────────────────────

    def _populate(self, entry):
        self.f_title.setText(entry["title"])
        self.f_url.setText(entry["url"] or "")
        self.f_user.setText(entry["entry_username"] or "")
        self.f_notes.setPlainText(entry["notes"] or "")

        idx = self.f_cat.findText(entry["category"])
        if idx >= 0:
            self.f_cat.setCurrentIndex(idx)

        session = session_mgr.get_session()
        try:
            pw = decrypt(bytes(entry["enc_password"]), session.key_bytes).decode()
            self.f_pw.setText(pw)
        except Exception:
            self.f_pw.setPlaceholderText("⚠ decryption error")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_generator(self):
        dlg = PasswordGeneratorDialog(self)
        dlg.password_selected.connect(self.f_pw.setText)
        dlg.exec()

    def _save(self):
        title    = self.f_title.text().strip()
        password = self.f_pw.text()

        if not title:
            QMessageBox.warning(self, "Validation", "Title is required.")
            return
        if not password:
            QMessageBox.warning(self, "Validation", "Password is required.")
            return

        session     = session_mgr.get_session()
        enc_pw      = encrypt(password.encode(), session.key_bytes)
        url         = self.f_url.text().strip()
        username    = self.f_user.text().strip()
        notes       = self.f_notes.toPlainText().strip()
        category    = self.f_cat.currentText()

        if self._entry:
            db.update_entry(
                self._entry["id"], session.user_id,
                title=title, url=url, username=username,
                enc_password=enc_pw, notes=notes, category=category,
            )
        else:
            db.add_entry(
                user_id=session.user_id,
                title=title, url=url, username=username,
                enc_password=enc_pw, notes=notes, category=category,
            )
        self.accept()
