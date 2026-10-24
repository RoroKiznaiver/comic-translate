"""Stepper (Import, Translate, Export): Apple-style segmented control, the thumb glides to the active step."""

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.dayu_widgets import dayu_theme
from app.ui.motion import PILL_MS, animations_enabled, spring_animation


class StepPill(QtWidgets.QWidget):
    def __init__(self, labels: list[str], parent=None, item_width: int = 120, height: int = 40):
        super().__init__(parent)
        self._labels = list(labels)
        self._item_w = item_width
        self._index = 0
        self._x = 0.0
        self.setFixedSize(item_width * len(self._labels), height)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(self.tr("Steps"))

        self._anim = None

    # Animated property: x offset of the pill, in pixels.
    def _get_indicator_x(self) -> float:
        return self._x

    def _set_indicator_x(self, value: float) -> None:
        self._x = float(value)
        self.update()

    indicatorX = QtCore.Property(float, _get_indicator_x, _set_indicator_x)

    def index(self) -> int:
        return self._index

    def set_index(self, index: int, animate: bool = True) -> None:
        index = max(0, min(int(index), len(self._labels) - 1))
        if index == self._index:
            return
        self._index = index
        target = float(index * self._item_w)
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if not animate or not animations_enabled() or not self.isVisible():
            self._set_indicator_x(target)
            return
        start = self._x
        self._anim = spring_animation(
            self, PILL_MS, 0.8,
            lambda p: self._set_indicator_x(start + (target - start) * p),
            lambda: self._set_indicator_x(target),
        )
        self._anim.start()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        """Apple-style segmented control: a rounded track and a raised thumb that glides to the active step."""
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        h = float(self.height())
        w = float(self._item_w)
        total_w = w * len(self._labels)
        dark = QtGui.QColor(dayu_theme.background_color).lightness() < 128

        inset = 3.0
        track = QtCore.QRectF(inset, inset, total_w - 2 * inset, h - 2 * inset)
        radius = 10.0
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor("#2C2C2E" if dark else "#E3E3E8"))
        p.drawRoundedRect(track, radius, radius)

        # thumb (with a soft shadow underneath, like the system control)
        thumb = QtCore.QRectF(self._x + inset + 2, inset + 2, w - 2 * inset - 4, h - 2 * inset - 4)
        shadow = QtCore.QRectF(thumb).translated(0, 1.2)
        p.setBrush(QtGui.QColor(0, 0, 0, 70 if dark else 38))
        p.drawRoundedRect(shadow, radius - 2, radius - 2)
        p.setBrush(QtGui.QColor("#636366" if dark else "#FFFFFF"))
        p.drawRoundedRect(thumb, radius - 2, radius - 2)

        font = self.font()
        font.setWeight(QtGui.QFont.Weight.Medium)
        for i, label in enumerate(self._labels):
            cell = QtCore.QRectF(i * w, 0, w, h)
            active = abs(cell.x() - self._x) < w / 2
            if active:
                p.setPen(QtGui.QColor(dayu_theme.title_color if dark else "#1C1C1E"))
            else:
                p.setPen(QtGui.QColor(dayu_theme.secondary_text_color))
            f = QtGui.QFont(font)
            f.setWeight(QtGui.QFont.Weight.DemiBold if active else QtGui.QFont.Weight.Medium)
            p.setFont(f)
            p.drawText(cell, QtCore.Qt.AlignmentFlag.AlignCenter, label)
        p.end()
