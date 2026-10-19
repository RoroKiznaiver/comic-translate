"""Stepper (Import, Translate, Export) with a pill that slides to the active step."""

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.dayu_widgets import dayu_theme
from app.ui.motion import CURVE_PILL, PILL_MS, animations_enabled


def _readable_on(color: QtGui.QColor) -> QtGui.QColor:
    """Dark text on light fills, white text on dark fills."""
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return QtGui.QColor("#15141B") if luminance > 0.55 else QtGui.QColor("#FFFFFF")


class StepPill(QtWidgets.QWidget):
    def __init__(self, labels: list[str], parent=None, item_width: int = 104, height: int = 36):
        super().__init__(parent)
        self._labels = list(labels)
        self._item_w = item_width
        self._index = 0
        self._x = 0.0
        self.setFixedSize(item_width * len(self._labels), height)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(self.tr("Steps"))

        self._anim = QtCore.QPropertyAnimation(self, b"indicatorX", self)

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
        self._anim.stop()
        if not animate or not animations_enabled() or not self.isVisible():
            self._set_indicator_x(target)
            return
        self._anim.setDuration(PILL_MS)
        self._anim.setEasingCurve(CURVE_PILL)
        self._anim.setStartValue(self._x)
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        h = float(self.height())
        w = float(self._item_w)

        track = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QtGui.QPen(QtGui.QColor(dayu_theme.border_color), 1))
        p.setBrush(QtGui.QColor(dayu_theme.background_in_color))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)

        accent = QtGui.QColor(dayu_theme.primary_color)
        pill = QtCore.QRectF(self._x, 0, w, h).adjusted(2, 2, -2, -2)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawRoundedRect(pill, pill.height() / 2, pill.height() / 2)

        font = self.font()
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        p.setFont(font)

        on_accent = _readable_on(accent)
        for i, label in enumerate(self._labels):
            cell = QtCore.QRectF(i * w, 0, w, h)
            under_pill = abs(cell.x() - self._x) < w / 2
            if under_pill:
                color = on_accent
            elif i < self._index:
                color = QtGui.QColor(dayu_theme.title_color)
            else:
                color = QtGui.QColor(dayu_theme.secondary_text_color)
            p.setPen(color)
            p.drawText(cell, QtCore.Qt.AlignmentFlag.AlignCenter, label)
        p.end()
