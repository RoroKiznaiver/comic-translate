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


def spring_animation(owner, duration: int, damping: float, apply, on_finished=None):
    """Drive ``apply(progress)`` with a damped spring over ``duration`` ms.

    Only public Qt API is used (a linear QVariantAnimation 0 -> 1 whose value is
    mapped through the spring), so there is no custom easing callback for Qt to
    call back into. Returns the animation; the caller starts and keeps it.
    """
    anim = QtCore.QVariantAnimation(owner)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(duration)
    anim.setEasingCurve(QtCore.QEasingCurve.Type.Linear)
    anim.valueChanged.connect(lambda v: apply(spring_progress(float(v), damping)))
    if on_finished is not None:
        anim.finished.connect(on_finished)
    return anim


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

    def _apply(progress: float) -> None:
        widget.setMaximumHeight(max(0, int(round(start + (end - start) * progress))))

    def _done() -> None:
        widget.setMaximumHeight(_QWIDGETSIZE_MAX)
        if not show:
            widget.setVisible(False)
        widget._reveal_anim = None

    anim = spring_animation(widget, duration, 1.0, _apply, _done)
    widget._reveal_anim = anim
    anim.start()
