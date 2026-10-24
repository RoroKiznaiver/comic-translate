"""Profile, level and daily-flame widgets (see app/progress/model.py).

Everything is painted in code (no image assets) and animated with the shared
spring helper; "Reduce animations" turns the motion off.
"""

import math
from datetime import date

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QCoreApplication

from app.progress.model import DAILY_GOALS, level_name, xp_for_level
from app.ui.dayu_widgets import dayu_theme
from app.ui.motion import animations_enabled, spring_animation

FLAME_OUTER = QtGui.QColor("#FFC857")
FLAME_MID = QtGui.QColor("#FF8A5C")
FLAME_INNER = QtGui.QColor("#FFF1C9")


def _tr(text: str) -> str:
    return QCoreApplication.translate("Progress", text)


def paint_flame(p: QtGui.QPainter, rect: QtCore.QRectF, lit: bool, phase: float = 0.0) -> None:
    """A flame in ``rect``. Lit flames flicker a little with ``phase`` (radians)."""
    p.save()
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    sx = 1.0 - 0.025 * abs(math.sin(phase * 1.3)) if lit else 1.0
    sy = 1.0 + 0.04 * math.sin(phase) if lit else 1.0
    p.translate(rect.center().x(), rect.bottom())
    p.scale(sx, sy)
    p.translate(-rect.width() / 2, -rect.height())

    def flame_path() -> QtGui.QPainterPath:
        w, h = rect.width(), rect.height()

        def pt(x: float, y: float) -> QtCore.QPointF:
            return QtCore.QPointF(w * x, h * y)

        path_ = QtGui.QPainterPath()
        path_.moveTo(pt(0.50, 0.02))
        path_.cubicTo(pt(0.62, 0.22), pt(0.86, 0.38), pt(0.86, 0.64))
        path_.cubicTo(pt(0.86, 0.86), pt(0.70, 0.98), pt(0.50, 0.98))
        path_.cubicTo(pt(0.30, 0.98), pt(0.14, 0.86), pt(0.14, 0.64))
        path_.cubicTo(pt(0.14, 0.46), pt(0.28, 0.38), pt(0.34, 0.24))
        path_.cubicTo(pt(0.38, 0.34), pt(0.42, 0.38), pt(0.46, 0.38))
        path_.cubicTo(pt(0.46, 0.24), pt(0.46, 0.12), pt(0.50, 0.02))
        return path_

    p.setPen(QtCore.Qt.PenStyle.NoPen)
    if lit:
        gradient = QtGui.QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0.0, FLAME_OUTER)
        gradient.setColorAt(1.0, FLAME_MID)
        p.setBrush(gradient)
        p.drawPath(flame_path())
        p.setBrush(FLAME_INNER)
        inner = QtGui.QTransform()
        inner.translate(rect.width() * 0.5, rect.height() * 0.98)
        inner.scale(0.5, 0.5)
        inner.translate(-rect.width() * 0.5, -rect.height() * 0.98)
        p.drawPath(inner.map(flame_path()))
    else:
        p.setBrush(QtGui.QColor(dayu_theme.border_color))
        p.drawPath(flame_path())
    p.restore()


class FlameWidget(QtWidgets.QWidget):
    """One flame, flickering when lit."""

    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self._lit = False
        self._phase = 0.0
        self.setFixedSize(size, size)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._tick)

    def set_lit(self, lit: bool) -> None:
        self._lit = bool(lit)
        if self._lit and animations_enabled():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase += 0.35
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QtGui.QPainter(self)
        paint_flame(p, QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1), self._lit, self._phase)
        p.end()


class ProgressChip(QtWidgets.QWidget):
    """Header chip: flame + streak, level, thin XP bar. Click opens the progress window."""

    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._streak = 0
        self._level = 1
        self._bar = 0.0           # animated 0..1
        self._lit = False
        self._phase = 0.0
        self._hover = False
        self._anim = None
        self.setFixedHeight(34)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._tick)
        self.setFixedWidth(self._width_for(0, 1))
        self.setAccessibleName(_tr("Your progress"))

    def _width_for(self, streak: int, level: int) -> int:
        m = QtGui.QFontMetrics(self.font())
        return 10 + 20 + 6 + m.horizontalAdvance(str(streak)) + 12 + m.horizontalAdvance(f"Lv {level}") + 10

    def set_state(self, streak: int, level: int, level_progress: float, lit_today: bool, animate: bool = True) -> None:
        self._streak, self._level, self._lit = int(streak), int(level), bool(lit_today)
        self.setFixedWidth(self._width_for(self._streak, self._level))
        self.setToolTip(_tr("Level {0} · {1}-day streak").format(self._level, self._streak))
        if self._lit and animations_enabled():
            self._timer.start()
        else:
            self._timer.stop()
        target = max(0.0, min(1.0, float(level_progress)))
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if animate and animations_enabled() and self.isVisible():
            start = self._bar
            if target < start:        # level up: fill, then restart from the left
                start = 0.0
            self._anim = spring_animation(
                self, 600, 1.0, lambda p: self._set_bar(start + (target - start) * p), lambda: self._set_bar(target)
            )
            self._anim.start()
        else:
            self._set_bar(target)

    def _set_bar(self, value: float) -> None:
        self._bar = value
        self.update()

    def _tick(self) -> None:
        self._phase += 0.35
        self.update()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        border = QtGui.QColor(dayu_theme.primary_color if self._hover else dayu_theme.border_color)
        p.setPen(QtGui.QPen(border, 1))
        p.setBrush(QtGui.QColor(dayu_theme.background_in_color))
        p.drawRoundedRect(r, 6, 6)

        paint_flame(p, QtCore.QRectF(10, 6, 18, 20), self._lit, self._phase)
        font = self.font()
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        p.setFont(font)
        m = QtGui.QFontMetrics(font)
        x = 10 + 20 + 6
        p.setPen(QtGui.QColor(dayu_theme.title_color if self._lit else dayu_theme.secondary_text_color))
        p.drawText(QtCore.QRectF(x, 0, m.horizontalAdvance(str(self._streak)) + 2, r.height() - 2),
                   QtCore.Qt.AlignmentFlag.AlignVCenter, str(self._streak))
        x += m.horizontalAdvance(str(self._streak)) + 12
        p.setPen(QtGui.QColor(dayu_theme.secondary_text_color))
        p.drawText(QtCore.QRectF(x, 0, m.horizontalAdvance(f"Lv {self._level}") + 2, r.height() - 2),
                   QtCore.Qt.AlignmentFlag.AlignVCenter, f"Lv {self._level}")

        # thin XP bar along the bottom edge
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(dayu_theme.primary_color))
        p.drawRect(QtCore.QRectF(6, r.height() - 2, (r.width() - 12) * self._bar, 2))
        p.end()


class _Bar(QtWidgets.QWidget):
    """Flat progress bar with a spring fill."""

    def __init__(self, height: int = 6, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._anim = None
        self.setFixedHeight(height)

    def set_value(self, value: float, animate: bool = True) -> None:
        target = max(0.0, min(1.0, float(value)))
        if self._anim is not None:
            self._anim.stop()
            self._anim = None
        if animate and animations_enabled() and self.isVisible():
            start = self._value
            self._anim = spring_animation(
                self, 700, 1.0, lambda p: self._set(start + (target - start) * p), lambda: self._set(target)
            )
            self._anim.start()
        else:
            self._set(target)

    def _set(self, v: float) -> None:
        self._value = v
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QtGui.QPainter(self)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(dayu_theme.border_color))
        p.drawRect(self.rect())
        p.setBrush(QtGui.QColor(dayu_theme.primary_color))
        p.drawRect(QtCore.QRectF(0, 0, self.width() * self._value, self.height()))
        p.end()


def _fade_in(widget: QtWidgets.QWidget, duration: int = 350) -> None:
    if not animations_enabled():
        return
    widget.setWindowOpacity(0.0)
    anim = spring_animation(widget, duration, 1.0, lambda p: widget.setWindowOpacity(min(1.0, p)),
                            lambda: widget.setWindowOpacity(1.0))
    widget._fade_anim = anim
    anim.start()


class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, progress, parent=None):
        super().__init__(parent)
        self.progress = progress
        self.setWindowTitle(_tr("Your progress"))
        self.setMinimumWidth(420)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 22, 24, 22)

        top = QtWidgets.QHBoxLayout()
        self.big_flame = FlameWidget(64)
        top.addWidget(self.big_flame)
        texts = QtWidgets.QVBoxLayout()
        self.streak_label = QtWidgets.QLabel()
        font = self.streak_label.font()
        font.setPointSize(font.pointSize() + 6)
        font.setWeight(QtGui.QFont.Weight.Bold)
        self.streak_label.setFont(font)
        self.name_label = QtWidgets.QLabel()
        self.name_label.setStyleSheet(f"color:{dayu_theme.secondary_text_color}")
        texts.addWidget(self.streak_label)
        texts.addWidget(self.name_label)
        top.addLayout(texts, 1)
        layout.addLayout(top)

        self.level_label = QtWidgets.QLabel()
        self.level_bar = _Bar(6)
        self.xp_label = QtWidgets.QLabel()
        self.xp_label.setStyleSheet(f"color:{dayu_theme.secondary_text_color}")
        layout.addWidget(self.level_label)
        layout.addWidget(self.level_bar)
        layout.addWidget(self.xp_label)

        week_title = QtWidgets.QLabel(_tr("This week"))
        week_title.setStyleSheet(f"color:{dayu_theme.secondary_text_color}")
        layout.addWidget(week_title)
        self.week_row = QtWidgets.QHBoxLayout()
        self.week_flames: list[FlameWidget] = []
        self.week_labels: list[QtWidgets.QLabel] = []
        for _ in range(7):
            cell = QtWidgets.QVBoxLayout()
            flame = FlameWidget(30)
            label = QtWidgets.QLabel()
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cell.addWidget(flame, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
            cell.addWidget(label)
            self.week_row.addLayout(cell)
            self.week_flames.append(flame)
            self.week_labels.append(label)
        layout.addLayout(self.week_row)

        self.goal_label = QtWidgets.QLabel()
        self.goal_bar = _Bar(6)
        goal_row = QtWidgets.QHBoxLayout()
        goal_row.addWidget(QtWidgets.QLabel(_tr("Daily goal")))
        self.goal_combo = QtWidgets.QComboBox()
        for goal in DAILY_GOALS:
            self.goal_combo.addItem(_tr("{0} pages").format(goal) if goal > 1 else _tr("1 page"), goal)
        goal_row.addStretch(1)
        goal_row.addWidget(self.goal_combo)
        layout.addLayout(goal_row)
        layout.addWidget(self.goal_bar)
        layout.addWidget(self.goal_label)

        close = QtWidgets.QPushButton(_tr("Close"))
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        self.goal_combo.currentIndexChanged.connect(self._goal_changed)
        self.refresh(animate=False)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        _fade_in(self)
        QtCore.QTimer.singleShot(60, lambda: self.refresh(animate=True))

    def _goal_changed(self, _i: int) -> None:
        self.progress.set_goal(int(self.goal_combo.currentData()))
        self.refresh(animate=True)

    def refresh(self, animate: bool = True) -> None:
        pr = self.progress
        streak = pr.streak()
        self.big_flame.set_lit(streak > 0)
        self.streak_label.setText(_tr("{0}-day streak").format(streak) if streak else _tr("No streak yet"))
        self.name_label.setText(pr.name or "")
        self.level_label.setText(_tr("Level {0} · {1}").format(pr.level, _tr(level_name(pr.level))))
        self.level_bar.set_value(pr.level_progress(), animate)
        self.xp_label.setText(_tr("{0} XP · {1} XP to level {2}").format(
            pr.xp, xp_for_level(pr.level + 1) - pr.xp, pr.level + 1))
        letters = [_tr("M"), _tr("T"), _tr("W"), _tr("T"), _tr("F"), _tr("S"), _tr("S")]
        for cell, flame, label, letter in zip(pr.week(), self.week_flames, self.week_labels, letters):
            flame.set_lit(cell["lit"])
            label.setText(letter)
            bold = "font-weight:700;" if cell["today"] else ""
            label.setStyleSheet(f"color:{dayu_theme.title_color if cell['today'] else dayu_theme.secondary_text_color};{bold}")
        goal = int(pr.data["daily_goal"])
        index = self.goal_combo.findData(goal)
        self.goal_combo.blockSignals(True)
        self.goal_combo.setCurrentIndex(max(index, 0))
        self.goal_combo.blockSignals(False)
        today_pages = pr.pages_on(date.today())
        self.goal_bar.set_value(min(today_pages / goal, 1.0), animate)
        self.goal_label.setText(_tr("Today: {0} / {1} pages").format(today_pages, goal))
        self.goal_label.setStyleSheet(f"color:{dayu_theme.secondary_text_color}")


class ProfileSetupDialog(QtWidgets.QDialog):
    """First launch: a local profile (nothing leaves this computer)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_tr("Welcome to Bulle"))
        self.setMinimumWidth(400)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 22, 24, 22)

        head = QtWidgets.QHBoxLayout()
        flame = FlameWidget(44)
        flame.set_lit(True)
        head.addWidget(flame)
        title = QtWidgets.QLabel(_tr("Create your profile"))
        font = title.font()
        font.setPointSize(font.pointSize() + 5)
        font.setWeight(QtGui.QFont.Weight.Bold)
        title.setFont(font)
        head.addWidget(title, 1)
        layout.addLayout(head)

        note = QtWidgets.QLabel(_tr("Translate pages to earn XP, level up and keep your daily flame alive. "
                                    "Your profile is saved only on this computer."))
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{dayu_theme.secondary_text_color}")
        layout.addWidget(note)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText(_tr("Your name"))
        self.name_edit.setMaxLength(30)
        layout.addWidget(self.name_edit)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(_tr("Daily goal")))
        self.goal_combo = QtWidgets.QComboBox()
        for goal in DAILY_GOALS:
            self.goal_combo.addItem(_tr("{0} pages").format(goal) if goal > 1 else _tr("1 page"), goal)
        self.goal_combo.setCurrentIndex(DAILY_GOALS.index(3))
        row.addStretch(1)
        row.addWidget(self.goal_combo)
        layout.addLayout(row)

        self.start_button = QtWidgets.QPushButton(_tr("Start"))
        self.start_button.setEnabled(False)
        self.start_button.setDefault(True)
        self.start_button.clicked.connect(self.accept)
        self.name_edit.textChanged.connect(lambda t: self.start_button.setEnabled(bool(t.strip())))
        later = QtWidgets.QPushButton(_tr("Later"))
        later.clicked.connect(self.reject)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(later)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        _fade_in(self)

    def values(self) -> tuple[str, int]:
        return self.name_edit.text().strip(), int(self.goal_combo.currentData())


class Celebration(QtWidgets.QFrame):
    """A banner that springs in at the top of the window (level up, streak, goal)."""

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setObjectName("celebration")
        self.setStyleSheet(
            f"#celebration{{background:{dayu_theme.primary_color};border-radius:6px;}}"
            "QLabel{color:#0A0908;font-weight:700;}"
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 16, 8)
        self.flame = FlameWidget(22)
        self.label = QtWidgets.QLabel()
        layout.addWidget(self.flame)
        layout.addWidget(self.label)
        self.hide()
        self._anim = None
        self._queue: list[str] = []
        self._busy = False

    def show_messages(self, messages: list[str]) -> None:
        self._queue.extend(messages)
        if not self._busy:
            self._next()

    def _next(self) -> None:
        if not self._queue:
            self._busy = False
            return
        self._busy = True
        self.label.setText(self._queue.pop(0))
        self.flame.set_lit(True)
        self.adjustSize()
        parent = self.parentWidget()
        x = (parent.width() - self.width()) // 2
        rest_y = 56
        self.show()
        self.raise_()
        if not animations_enabled():
            self.move(x, rest_y)
            QtCore.QTimer.singleShot(2600, self._leave)
            return
        self.move(x, -self.height())
        self._anim = spring_animation(
            self, 450, 0.8,
            lambda p: self.move(x, int(-self.height() + (rest_y + self.height()) * p)),
            lambda: QtCore.QTimer.singleShot(2400, self._leave),
        )
        self._anim.start()

    def _leave(self) -> None:
        if not animations_enabled():
            self.hide()
            self._next()
            return
        x, y = self.x(), self.y()
        self._anim = spring_animation(
            self, 300, 1.0,
            lambda p: self.move(x, int(y + (-self.height() - y) * p)),
            lambda: (self.hide(), self._next()),
        )
        self._anim.start()
