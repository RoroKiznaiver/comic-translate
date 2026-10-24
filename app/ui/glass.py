"""Liquid-Glass-style surfaces (iOS 26/27 look) painted with Qt.

A real backdrop blur is not available to plain Qt widgets, so the material is
built from what makes it read as glass: a translucent tinted fill, a brighter
specular line on the top edge, a slightly darker outer edge for separation (the
iOS 27 refinement) and a soft shadow. "Glass transparency" (Settings >
Personalization) goes from ultra clear to fully tinted.
"""

from PySide6 import QtCore, QtGui

from app.ui.dayu_widgets import dayu_theme


def _is_dark() -> bool:
    return QtGui.QColor(dayu_theme.background_color).lightness() < 128


def paint_glass(p: QtGui.QPainter, rect: QtCore.QRectF, radius: float,
                hover: bool = False, raised: bool = False, accent: bool = False) -> None:
    """Paint a glass capsule/rounded panel into ``rect`` (already inset for the shadow)."""
    dark = _is_dark()
    level = max(0.0, min(1.0, getattr(dayu_theme, "glass_level", 55) / 100.0))
    base = QtGui.QColor(255, 255, 255) if dark else QtGui.QColor(255, 255, 255)
    tint = 0.05 + 0.17 * level + (0.05 if hover else 0.0) + (0.10 if raised else 0.0)
    if not dark:
        base = QtGui.QColor(255, 255, 255)
        tint = 0.35 + 0.45 * level + (0.08 if hover else 0.0)

    p.save()
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    # soft shadow
    if raised or not dark:
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, 60 if dark else 28))
        p.drawRoundedRect(rect.translated(0, 1.5), radius, radius)

    fill = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    top = QtGui.QColor(base); top.setAlphaF(min(1.0, tint * 1.25))
    bot = QtGui.QColor(base); bot.setAlphaF(min(1.0, tint * 0.8))
    if accent:
        acc = QtGui.QColor(dayu_theme.primary_color)
        top = QtGui.QColor(acc); top.setAlphaF(0.95)
        bot = QtGui.QColor(acc).darker(112); bot.setAlphaF(0.95)
    fill.setColorAt(0.0, top)
    fill.setColorAt(1.0, bot)
    # darker outer edge
    edge = QtGui.QColor(0, 0, 0, 90 if dark else 34)
    p.setPen(QtGui.QPen(edge, 1))
    p.setBrush(fill)
    p.drawRoundedRect(rect, radius, radius)

    # specular rim: bright line hugging the top, fading down the sides
    rim = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim.setColorAt(0.0, QtGui.QColor(255, 255, 255, 190 if dark else 255))
    rim.setColorAt(0.35, QtGui.QColor(255, 255, 255, 40))
    rim.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
    p.setPen(QtGui.QPen(QtGui.QBrush(rim), 1))
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), max(radius - 1, 1), max(radius - 1, 1))
    p.restore()
