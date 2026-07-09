"""Password Generator dialog — standalone or embedded in entry editor."""

import pyperclip
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QSlider, QGroupBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from crypto.vault_crypto import generate_password, password_strength


STRENGTH_COLORS = {
    0: "#f38ba8",   # Very Weak  – red
    1: "#f38ba8",   # Weak       – red
    2: "#fab387",   # Fair       – orange
    3: "#f9e2af",   # Good       – yellow
    4: "#a6e3a1",   # Strong     – green
    5: "#89dceb",   # Very Strong– teal
}


class PasswordGeneratorDialog(QDialog):
    """
    Emits `password_selected(str)` when the user clicks "Use This Password".
    Can be used standalone (no signal connection) or embedded in EntryDialog.
    """
    password_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Password Generator")
        self.setFixedSize(400, 370)
        self._setup_ui()
        self._generate()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # ── Generated password ──────────────────────────────────────────────
        pw_row = QHBoxLayout()
        self.pw_display = QLineEdit()
        self.pw_display.setReadOnly(True)
        self.pw_display.setStyleSheet("font-family: 'Consolas', monospace; font-size: 14px;")
        regen_btn = QPushButton("↻")
        regen_btn.setFixedWidth(36)
        regen_btn.setObjectName("secondary")
        regen_btn.setToolTip("Generate new password")
        regen_btn.clicked.connect(self._generate)
        pw_row.addWidget(self.pw_display)
        pw_row.addWidget(regen_btn)
        root.addLayout(pw_row)

        # Strength label
        self.strength_lbl = QLabel()
        self.strength_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.strength_lbl.setStyleSheet("font-weight: bold;")
        root.addWidget(self.strength_lbl)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        # ── Length slider ───────────────────────────────────────────────────
        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Length:"))
        self.len_val = QLabel("16")
        self.len_val.setFixedWidth(28)
        self.len_slider = QSlider(Qt.Orientation.Horizontal)
        self.len_slider.setRange(8, 64)
        self.len_slider.setValue(16)
        self.len_slider.valueChanged.connect(self._on_length)
        len_row.addWidget(self.len_slider)
        len_row.addWidget(self.len_val)
        root.addLayout(len_row)

        # ── Character options ───────────────────────────────────────────────
        group = QGroupBox("Character Types")
        g_lay = QVBoxLayout(group)
        self.cb_upper   = QCheckBox("Uppercase  A–Z")
        self.cb_lower   = QCheckBox("Lowercase  a–z")
        self.cb_digits  = QCheckBox("Digits      0–9")
        self.cb_symbols = QCheckBox("Symbols   !@#$%…")
        for cb in (self.cb_upper, self.cb_lower, self.cb_digits, self.cb_symbols):
            cb.setChecked(True)
            cb.stateChanged.connect(self._generate)
            g_lay.addWidget(cb)
        root.addWidget(group)

        # ── Actions ─────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋  Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(self._copy)

        use_btn  = QPushButton("Use This Password")
        use_btn.clicked.connect(self._use)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.reject)

        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addWidget(use_btn)
        root.addLayout(btn_row)

    def _on_length(self, val: int):
        self.len_val.setText(str(val))
        self._generate()

    def _generate(self):
        pw = generate_password(
            length  = self.len_slider.value(),
            upper   = self.cb_upper.isChecked(),
            lower   = self.cb_lower.isChecked(),
            digits  = self.cb_digits.isChecked(),
            symbols = self.cb_symbols.isChecked(),
        )
        self.pw_display.setText(pw)
        score, label = password_strength(pw)
        color = STRENGTH_COLORS.get(score, "#a6adc8")
        self.strength_lbl.setText(f"Strength: {label}")
        self.strength_lbl.setStyleSheet(f"font-weight: bold; color: {color};")

    def _copy(self):
        pyperclip.copy(self.pw_display.text())

    def _use(self):
        self.password_selected.emit(self.pw_display.text())
        self.accept()
