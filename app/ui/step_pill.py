"""Stepper (Import, Translate, Export): numbered links, underline slides to the active step."""

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
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        h = float(self.height())
        w = float(self._item_w)
        accent = QtGui.QColor(dayu_theme.primary_color)

        # Sober style: numbered links with a 2 px underline that slides to the active step.
        font = self.font()
        font.setWeight(QtGui.QFont.Weight.Medium)
        small = QtGui.QFont(font)
        small.setPointSizeF(max(font.pointSizeF() - 2, 6))
        metrics = QtGui.QFontMetricsF(font)
        small_metrics = QtGui.QFontMetricsF(small)

        for i, label in enumerate(self._labels):
            cell = QtCore.QRectF(i * w, 0, w, h - 2)
            under = abs(cell.x() - self._x) < w / 2
            if under:
                text_color = QtGui.QColor(dayu_theme.title_color)
                num_color = accent
            elif i < self._index:
                text_color = QtGui.QColor(dayu_theme.primary_text_color)
                num_color = QtGui.QColor(dayu_theme.secondary_text_color)
            else:
                text_color = QtGui.QColor(dayu_theme.secondary_text_color)
                num_color = QtGui.QColor(dayu_theme.secondary_text_color)

            num = f"{i + 1:02d}"
            gap = 6.0
            total = small_metrics.horizontalAdvance(num) + gap + metrics.horizontalAdvance(label)
            x = cell.x() + (w - total) / 2
            p.setFont(small)
            p.setPen(num_color)
            p.drawText(QtCore.QRectF(x, cell.y(), small_metrics.horizontalAdvance(num) + 1, cell.height()),
                       QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, num)
            p.setFont(font)
            p.setPen(text_color)
            p.drawText(QtCore.QRectF(x + small_metrics.horizontalAdvance(num) + gap, cell.y(),
                                     metrics.horizontalAdvance(label) + 2, cell.height()),
                       QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft, label)

        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(accent)
        p.drawRect(QtCore.QRectF(self._x, h - 2, w, 2))
        p.end()
