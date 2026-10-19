"""Motion tokens and helpers shared by the UI.

These mirror the design prototype ("Langage de mouvement"):

    pill      450 ms  OutQuart   active step slides along the stepper
    disclose  300 ms  OutCubic   advanced options grow/shrink
    enter     500 ms  OutCubic   a screen or panel comes in
    pop       400 ms  OutBack    floating elements (toasts) appear with a little overshoot

A single user setting, ``ui/reduce_motion``, switches every animation off: the
helpers then jump straight to the end state.
"""

from PySide6 import QtCore
from PySide6.QtCore import QSettings

PILL_MS = 450
DISCLOSE_MS = 300
ENTER_MS = 500
POP_MS = 400

CURVE_PILL = QtCore.QEasingCurve.Type.OutQuart
CURVE_STANDARD = QtCore.QEasingCurve.Type.OutCubic
CURVE_POP = QtCore.QEasingCurve.Type.OutBack

_QWIDGETSIZE_MAX = 16777215


def animations_enabled() -> bool:
    """False when the user turned on "Reduce animations"."""
    try:
        return not QSettings("ComicLabs", "ComicTranslate").value("ui/reduce_motion", False, type=bool)
    except Exception:
        return True


def reveal(widget, show: bool, duration: int = DISCLOSE_MS) -> None:
    """Show or hide ``widget`` by animating its height.

    Falls back to a plain ``setVisible`` when animations are disabled or the
    window is not on screen yet (first layout), so initial state never animates.
    """
    previous = getattr(widget, "_reveal_anim", None)
    if previous is not None:
        previous.stop()
        widget._reveal_anim = None
        widget.setMaximumHeight(_QWIDGETSIZE_MAX)

    already_shown = not widget.isHidden()
    if show == already_shown:
        return

    if not animations_enabled() or not widget.window().isVisible():
        widget.setVisible(show)
        return

    if show:
        widget.setMaximumHeight(0)
        widget.setVisible(True)
        start, end = 0, max(widget.sizeHint().height(), 1)
    else:
        start, end = widget.height(), 0

    anim = QtCore.QPropertyAnimation(widget, b"maximumHeight", widget)
    anim.setDuration(duration)
    anim.setEasingCurve(CURVE_STANDARD)
    anim.setStartValue(start)
    anim.setEndValue(end)

    def _done() -> None:
        widget.setMaximumHeight(_QWIDGETSIZE_MAX)
        if not show:
            widget.setVisible(False)
        widget._reveal_anim = None

    anim.finished.connect(_done)
    widget._reveal_anim = anim
    anim.start()
