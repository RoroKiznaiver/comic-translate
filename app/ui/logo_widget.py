"""The Bulle logo as a live widget: a glossy bubble with a light glint that sweeps across it."""

import os

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.motion import animations_enabled, spring_animation

_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources", "icons", "logo.png")


class BulleLogo(QtWidgets.QWidget):
    """Draws logo.png. The glint plays on hover and shortly after the window appears;
    a click makes the bubble squash and spring back."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self._pix = QtGui.QPixmap(_LOGO)
        self._glint = -1.0     # -1 = idle, 0..1 = band position
        self._scale = 1.0
        self._glint_anim = None
        self._scale_anim = None
        self.setFixedSize(size, size)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAccessibleName("Bulle")
        QtCore.QTimer.singleShot(700, self.play_glint)

    # -- animation ---------------------------------------------------------
    def play_glint(self) -> None:
        if not animations_enabled() or not self.isVisible():
            return
        if self._glint_anim is not None:
            self._glint_anim.stop()

        def apply(p: float) -> None:
            self._glint = p
            self.update()

        def done() -> None:
            self._glint = -1.0
            self._glint_anim = None
            self.update()

        self._glint_anim = spring_animation(self, 900, 1.0, apply, done)
        self._glint_anim.start()

    def _bounce(self) -> None:
        if not animations_enabled():
            return
        if self._scale_anim is not None:
            self._scale_anim.stop()

        def apply(p: float) -> None:
            self._scale = 0.86 + 0.14 * p
            self.update()

        def done() -> None:
            self._scale = 1.0
            self._scale_anim = None
            self.update()

        self._scale_anim = spring_animation(self, 520, 0.45, apply, done)
        self._scale_anim.start()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.play_glint()
        super().enterEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._bounce()
        self.play_glint()
        super().mousePressEvent(event)

    # -- painting ----------------------------------------------------------
    def paintEvent(self, event) -> None:  # type: ignore[override]
        if self._pix.isNull():
            return
        dpr = self.devicePixelRatioF()
        side = int(self._size * dpr)
        base = self._pix.scaled(side, side, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                QtCore.Qt.TransformationMode.SmoothTransformation)

        if self._glint >= 0.0:
            layer = QtGui.QPixmap(base)
            g = QtGui.QPainter(layer)
            g.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            g.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceAtop)
            # diagonal band travelling from top-left to bottom-right, fading at both ends
            pos = -0.35 + 1.7 * self._glint
            grad = QtGui.QLinearGradient(side * pos, side * (pos - 0.3), side * (pos + 0.25), side * (pos + 0.05))
            strength = max(0.0, 1.0 - abs(self._glint - 0.5) * 1.6)
            grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 0))
            grad.setColorAt(0.5, QtGui.QColor(255, 255, 255, int(190 * strength)))
            grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
            g.fillRect(layer.rect(), grad)
            g.end()
            base = layer

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(self._scale, self._scale)
        p.translate(-self.width() / 2, -self.height() / 2)
        target = QtCore.QRectF(0, 0, self._size, self._size)
        p.drawPixmap(target, base, QtCore.QRectF(base.rect()))
        p.end()
