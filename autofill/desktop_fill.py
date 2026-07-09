"""
Desktop autofill module.

Strategy
────────
1.  Ctrl+Shift+F  global hotkey → captures the currently active window info.
2.  MainWindow searches the vault and shows a picker (on the Qt main thread).
3.  After the user picks, `type_credentials()` sends keystrokes to the
    previously-focused window (username → Tab → password).

We use the `keyboard` library for both the hotkey and the keystroke injection.
`pyperclip` is used as a clipboard-paste fallback for long passwords that the
`keyboard.write()` method might mis-encode on non-ASCII keyboards.

Requires:   pip install keyboard psutil pyperclip pywin32
Admin note: `keyboard` needs to run elevated (Run as Administrator) on Windows
            if the target window is also elevated.
"""

import time
import threading
from typing import Callable

try:
    import keyboard
    _KB_AVAILABLE = True
except ImportError:
    _KB_AVAILABLE = False

try:
    import win32gui
    import win32process
    import psutil
    _WIN_AVAILABLE = True
except ImportError:
    _WIN_AVAILABLE = False

import pyperclip

_HOTKEY         = "ctrl+shift+f"
_hotkey_handler = None          # current registered handler


# ── Window info ──────────────────────────────────────────────────────────────

def get_active_window_info() -> dict:
    """Return title, process name, and exe path of the foreground window."""
    info = {"title": "", "process": "", "exe": "", "hwnd": 0}
    if not _WIN_AVAILABLE:
        return info
    try:
        hwnd           = win32gui.GetForegroundWindow()
        info["hwnd"]   = hwnd
        info["title"]  = win32gui.GetWindowText(hwnd)
        _, pid         = win32process.GetWindowThreadProcessId(hwnd)
        proc           = psutil.Process(pid)
        info["process"] = proc.name()
        info["exe"]    = proc.exe()
    except Exception:
        pass
    return info


# ── Hotkey registration ───────────────────────────────────────────────────────

def register_autofill_hotkey(callback: Callable[[dict], None]):
    """
    Register Ctrl+Shift+F.  When triggered, calls *callback* with a dict
    containing active-window info.  The callback is invoked on a daemon
    thread so it must not touch Qt widgets directly (use signals).
    """
    global _hotkey_handler

    if not _KB_AVAILABLE:
        raise RuntimeError(
            "The `keyboard` package is not installed.  "
            "Run:  pip install keyboard"
        )

    unregister_autofill_hotkey()   # clean up previous registration

    def _handler():
        info = get_active_window_info()
        t = threading.Thread(target=callback, args=(info,), daemon=True)
        t.start()

    keyboard.add_hotkey(_HOTKEY, _handler, suppress=False)
    _hotkey_handler = _handler


def unregister_autofill_hotkey():
    global _hotkey_handler
    if not _KB_AVAILABLE:
        return
    try:
        keyboard.remove_hotkey(_HOTKEY)
    except Exception:
        pass
    _hotkey_handler = None


# ── Credential injection ──────────────────────────────────────────────────────

def type_credentials(username: str, password: str, use_clipboard: bool = False):
    """
    Inject *username* and *password* into the currently focused window.

    Parameters
    ----------
    username      : leave empty string "" to skip the username field.
    password      : the plaintext password to inject.
    use_clipboard : if True, paste via Ctrl+V instead of character-by-character
                    typing (faster for long passwords; clears clipboard after).
    """
    if not _KB_AVAILABLE:
        # Clipboard fallback when keyboard module unavailable
        if username:
            pyperclip.copy(username)
        return

    time.sleep(0.3)   # let the target window regain focus

    if use_clipboard:
        _paste_via_clipboard(username, password)
    else:
        _type_direct(username, password)


def _type_direct(username: str, password: str):
    """Send each character individually — works on most apps."""
    if username:
        keyboard.write(username, delay=0.03)
        keyboard.press_and_release("tab")
        time.sleep(0.15)
    keyboard.write(password, delay=0.03)


def _paste_via_clipboard(username: str, password: str):
    """Paste via clipboard — faster, but briefly exposes data in clipboard."""
    original = ""
    try:
        original = pyperclip.paste()
    except Exception:
        pass

    try:
        if username:
            pyperclip.copy(username)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.15)
            keyboard.press_and_release("tab")
            time.sleep(0.15)

        pyperclip.copy(password)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.15)
    finally:
        # Restore original clipboard content (or clear)
        try:
            pyperclip.copy(original)
        except Exception:
            pass
