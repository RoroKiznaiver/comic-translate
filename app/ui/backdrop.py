"""Real window materials on Windows 11: Mica and Acrylic (system backdrop).

This gives the sidebar and title bar the genuine frosted look of the OS (the
blurred, tinted desktop behind the window) instead of a flat colour. It needs
Windows 11 22H2 (build 22621) or later; anywhere else ``enable`` returns False
and the interface simply keeps its normal opaque background.
"""

import ctypes
import sys
from ctypes import wintypes

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_KINDS = {"mica": 2, "acrylic": 3, "mica_alt": 4, "off": 1}


class _MARGINS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]


def supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return sys.getwindowsversion().build >= 22621
    except Exception:
        return False


def _set(hwnd: int, attr: int, value: int) -> bool:
    val = ctypes.c_int(value)
    res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd), ctypes.c_uint(attr), ctypes.byref(val), ctypes.sizeof(val)
    )
    return res == 0


def enable(window, dark: bool, kind: str = "mica") -> bool:
    """Apply ``kind`` ("mica", "acrylic", "mica_alt") to the top-level ``window``. True on success."""
    if not supported() or kind not in _KINDS or kind == "off":
        return False
    try:
        hwnd = int(window.winId())
        _set(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)
        margins = _MARGINS(-1, -1, -1, -1)
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd), ctypes.byref(margins))
        return _set(hwnd, _DWMWA_SYSTEMBACKDROP_TYPE, _KINDS[kind])
    except Exception:
        return False


def disable(window) -> None:
    if not supported():
        return
    try:
        hwnd = int(window.winId())
        _set(hwnd, _DWMWA_SYSTEMBACKDROP_TYPE, _KINDS["off"])
    except Exception:
        pass
