"""Motion tokens and helpers shared by the UI.

These mirror the sober design prototype (B, inspired by nakanime): short,
ease-out, no overshoot.

    pill      450 ms  spring 0.8 the step underline slides along the stepper
    disclose  400 ms  spring 1.0 advanced options grow/shrink (no overshoot)
    enter     300 ms  OutCubic   a screen or panel comes in
    pop       200 ms  OutCubic   small floating elements (toasts) appear

A single user setting, ``ui/reduce_motion``, switches every animation off: the
helpers then jump straight to the end state.
"""

from PySide6 import QtCore
from PySide6.QtCore import QSettings

from app.ui.spring import spring_progress

PILL_MS = 450
DISCLOSE_MS = 400
ENTER_MS = 300
POP_MS = 200

CURVE_PILL = QtCore.QEasingCurve.Type.OutCubic
CURVE_STANDARD = QtCore.QEasingCurve.Type.OutCubic
CURVE_POP = QtCore.QEasingCurve.Type.OutCubic

_QWIDGETSIZE_MAX = 16777215


def spring_curve(damping: float = 0.8) -> QtCore.QEasingCurve:
    """A QEasingCurve that follows a damped spring (see app/ui/spring.py)."""
    curve = QtCore.QEasingCurve()
    curve.setCustomType(lambda t, d=damping: spring_progress(t, d))
    return curve


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
    anim.setEasingCurve(spring_curve(1.0))
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
