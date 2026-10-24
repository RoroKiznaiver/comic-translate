"""Small moments of delight, each tied to something that just happened.

    Confetti        level up, daily goal, new streak day
    float_text      "+30 XP" rises from the progress chip after pages are translated
    PressFeedback   buttons dip when pressed and spring back on release

Everything respects the "Reduce animations" setting and never blocks the UI.
"""

import math
import random

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.dayu_widgets import dayu_theme
from app.ui.motion import animations_enabled, spring_animation


class Confetti(QtWidgets.QWidget):
    """A short burst of confetti over the whole window. Mouse events pass through."""

    DURATION_MS = 1900

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._parts: list[dict] = []
        self._t = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._step)
        self.hide()

    def burst(self, strength: int = 70, origin: QtCore.QPointF | None = None) -> None:
        parent = self.parentWidget()
        if parent is None or not animations_enabled() or not parent.isVisible():
            return
        self.setGeometry(parent.rect())
        self.raise_()
        self.show()
        w, h = self.width(), self.height()
        ox, oy = (origin.x(), origin.y()) if origin is not None else (w / 2, h * 0.28)
        colors = [dayu_theme.primary_color, "#FFD60A", "#FF9F0A", "#FFFFFF", "#FF375F", "#64D2FF"]
        for _ in range(int(strength)):
            ang = random.uniform(-math.pi * 0.95, -math.pi * 0.05)   # upward fan
            speed = random.uniform(5.0, 15.0)
            self._parts.append({
                "x": ox, "y": oy,
                "vx": math.cos(ang) * speed, "vy": math.sin(ang) * speed,
                "rot": random.uniform(0, 360), "vr": random.uniform(-14, 14),
                "w": random.uniform(5, 10), "h": random.uniform(3, 7),
                "c": QtGui.QColor(random.choice(colors)),
                "round": random.random() < 0.3,
            })
        self._t = 0
        self._timer.start()

    def _step(self) -> None:
        self._t += 16
        for p in self._parts:
            p["vy"] += 0.42          # gravity
            p["vx"] *= 0.985
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["rot"] += p["vr"]
        if self._t >= self.DURATION_MS:
            self._timer.stop()
            self._parts.clear()
            self.hide()
            return
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._parts:
            return
        fade = 1.0 if self._t < self.DURATION_MS * 0.6 else max(0.0, (self.DURATION_MS - self._t) / (self.DURATION_MS * 0.4))
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        for q in self._parts:
            c = QtGui.QColor(q["c"])
            c.setAlphaF(fade)
            p.setBrush(c)
            p.save()
            p.translate(q["x"], q["y"])
            p.rotate(q["rot"])
            if q["round"]:
                p.drawEllipse(QtCore.QRectF(-q["w"] / 3, -q["w"] / 3, q["w"] * 0.66, q["w"] * 0.66))
            else:
                p.drawRoundedRect(QtCore.QRectF(-q["w"] / 2, -q["h"] / 2, q["w"], q["h"]), 1.5, 1.5)
            p.restore()
        p.end()


def float_text(anchor: QtWidgets.QWidget, text: str, rise: int = 34) -> None:
    """Show ``text`` just under ``anchor``; it drifts up and dissolves."""
    window = anchor.window()
    if window is None or not animations_enabled() or not anchor.isVisible():
        return
    label = QtWidgets.QLabel(text, window)
    label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    label.setStyleSheet(
        f"background:transparent;color:{dayu_theme.primary_color};font-weight:700;font-size:13pt;"
    )
    label.adjustSize()
    pos = anchor.mapTo(window, QtCore.QPoint(0, anchor.height()))
    x = pos.x() + (anchor.width() - label.width()) // 2
    y0 = pos.y() + 2
    label.move(x, y0)
    effect = QtWidgets.QGraphicsOpacityEffect(label)
    label.setGraphicsEffect(effect)
    label.show()
    label.raise_()

    def _apply(p: float) -> None:
        label.move(x, y0 + int(rise * p))
        effect.setOpacity(1.0 if p < 0.55 else max(0.0, 1.0 - (p - 0.55) / 0.45))

    anim = spring_animation(label, 1300, 1.0, _apply, label.deleteLater)
    anim.start()


class PressFeedback(QtCore.QObject):
    """Application-wide: a button dims a little while pressed and eases back on release."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pressed: dict[int, QtWidgets.QAbstractButton] = {}

    def eventFilter(self, obj, event):  # type: ignore[override]
        try:
            kind = event.type()
            if isinstance(obj, QtWidgets.QAbstractButton):
                if kind == QtCore.QEvent.Type.MouseButtonPress and obj.isEnabled() and animations_enabled():
                    if obj.graphicsEffect() is None:
                        effect = QtWidgets.QGraphicsOpacityEffect(obj)
                        effect.setOpacity(0.72)
                        obj.setGraphicsEffect(effect)
                        obj._press_effect = effect
                elif kind == QtCore.QEvent.Type.MouseButtonRelease:
                    effect = getattr(obj, "_press_effect", None)
                    if effect is not None and obj.graphicsEffect() is effect:
                        self._release(obj, effect)
        except Exception:
            pass
        return False

    @staticmethod
    def _release(button, effect) -> None:
        start = effect.opacity()

        def _apply(p: float) -> None:
            effect.setOpacity(min(1.0, start + (1.0 - start) * p))

        def _done() -> None:
            if button.graphicsEffect() is effect:
                button.setGraphicsEffect(None)
            button._press_effect = None

        spring_animation(button, 320, 0.6, _apply, _done).start()
