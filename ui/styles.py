"""Catppuccin Mocha-inspired dark theme for SecureVault."""

DARK_QSS = """
/* ── Base ─────────────────────────────────────────────────────── */
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #1e1e2e; }

/* ── Inputs ───────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #89b4fa; }
QLineEdit:read-only { background-color: #252536; color: #a6adc8; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #45475a;
}

/* ── Buttons ──────────────────────────────────────────────────── */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    min-width: 76px;
}
QPushButton:hover   { background-color: #b4befe; }
QPushButton:pressed { background-color: #7287fd; }

QPushButton#secondary {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QPushButton#secondary:hover { background-color: #45475a; }

QPushButton#danger {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#danger:hover { background-color: #eba0ac; }

/* ── Tree / List ──────────────────────────────────────────────── */
QTreeWidget, QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    alternate-background-color: #1e1e2e;
    outline: 0;
}
QTreeWidget::item, QListWidget::item { padding: 5px 4px; }
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #252536;
}
QHeaderView::section {
    background-color: #313244;
    color: #a6adc8;
    border: none;
    border-right: 1px solid #45475a;
    padding: 6px 8px;
    font-weight: 600;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #181825; width: 8px; border-radius: 4px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #45475a; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Group box ────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 6px;
    font-weight: 600;
    color: #a6adc8;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }

/* ── Labels ───────────────────────────────────────────────────── */
QLabel#appTitle {
    font-size: 22px;
    font-weight: 700;
    color: #89b4fa;
}
QLabel#subtitle { color: #a6adc8; font-size: 12px; }
QLabel#sectionHead { font-weight: 600; color: #a6adc8; font-size: 11px; }

/* ── Toolbar ──────────────────────────────────────────────────── */
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    spacing: 6px;
    padding: 4px 8px;
}
QToolBar QToolButton {
    background: transparent;
    color: #cdd6f4;
    border-radius: 5px;
    padding: 5px 10px;
}
QToolBar QToolButton:hover { background: #313244; }

/* ── Status bar ───────────────────────────────────────────────── */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
QStatusBar::item { border: none; }

/* ── Menu ─────────────────────────────────────────────────────── */
QMenuBar { background-color: #181825; color: #cdd6f4; }
QMenuBar::item:selected { background-color: #313244; }
QMenu {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 20px; border-radius: 4px; }
QMenu::item:selected { background-color: #45475a; }
QMenu::separator { background: #45475a; height: 1px; margin: 4px 8px; }

/* ── Tabs ─────────────────────────────────────────────────────── */
QTabWidget::pane { border: 1px solid #313244; border-radius: 6px; }
QTabBar::tab {
    background: #181825; color: #a6adc8;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected { background: #313244; color: #89b4fa; }
QTabBar::tab:hover    { background: #252536; }

/* ── Checkboxes ───────────────────────────────────────────────── */
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #45475a; border-radius: 3px;
    background: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa; border-color: #89b4fa;
    image: none;
}

/* ── Slider ───────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background: #313244; height: 6px; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #89b4fa; width: 16px; height: 16px;
    border-radius: 8px; margin: -5px 0;
}
QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 3px; }

/* ── Frame ────────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {  /* HLine / VLine */
    color: #313244;
}

/* ── Tooltip ──────────────────────────────────────────────────── */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
"""
