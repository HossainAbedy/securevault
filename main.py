"""
SecureVault — entry point.

Launch order
────────────
1. Initialise SQLite database (idempotent).
2. Attempt Windows DPAPI auto-login for the current user.
3a. If auto-login succeeds → open MainWindow directly.
3b. Otherwise            → show LoginDialog (unlock / register).
4. Run Qt event loop.
"""

import sys, os
from PyQt6.QtGui import QIcon
    
if sys.platform != "win32":
    sys.exit("SecureVault requires Windows 10 / 11.")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import Qt

import db.database          as db
import auth.windows_auth    as win_auth
import auth.session         as session_mgr
from auth.session           import Session
from ui.styles              import DARK_QSS


def _try_windows_autologin() -> bool:
    """
    If the current Windows user has a DPAPI-linked vault, decrypt the vault
    key silently and open a session.  Returns True on success.
    """
    try:
        sid  = win_auth.get_current_windows_sid()
        user = db.get_user_by_sid(sid)
        if user and user["dpapi_enc_key"]:
            vault_key = win_auth.dpapi_decrypt(bytes(user["dpapi_enc_key"]))
            session_mgr.set_session(
                Session(
                    user_id        = user["id"],
                    username       = user["username"],
                    vault_key      = bytearray(vault_key),
                    is_windows_user= True,
                    windows_sid    = sid,
                )
            )
            return True
    except Exception:
        pass
    return False


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    
    if hasattr(sys, "_MEIPASS"):
        _ico = os.path.join(sys._MEIPASS, "securevault.ico")
    else:
        _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "securevault.ico")
    app.setWindowIcon(QIcon(_ico))

    app.setApplicationName("SecureVault")
    app.setOrganizationName("AbedySec")
    app.setQuitOnLastWindowClosed(False)   # keep alive in tray
    app.setStyleSheet(DARK_QSS)

    # Initialise DB (creates tables if first run)
    db.initialize_db()

    # Try silent DPAPI auto-login
    if _try_windows_autologin():
        from ui.main_window import MainWindow
        win = MainWindow()
        win.show()
    else:
        from ui.login_dialog import LoginDialog
        dlg = LoginDialog()
        if dlg.exec():
            from ui.main_window import MainWindow
            win = MainWindow()
            win.show()
        else:
            sys.exit(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
