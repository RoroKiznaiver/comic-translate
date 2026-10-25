"""Take screenshots of every main screen of Bulle and gather them in one contact sheet.

Run from the repo folder:   uv run tools/capture_screens.py
Output (folder "bulle_screens" next to the repo): one PNG per screen, contact_sheet.png and report.txt.
Send contact_sheet.png and report.txt back to review the interface.
"""

import os
import sys
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

OUT = os.path.join(ROOT, "bulle_screens")
os.makedirs(OUT, exist_ok=True)
LOG = []
SHOTS = []   # (label, path)


def wait(ms: int) -> None:
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shoot(ct, label: str, delay: int = 900) -> None:
    wait(delay)
    try:
        ct.raise_()
        ct.activateWindow()
        wait(120)
        screen = ct.screen() or QtWidgets.QApplication.primaryScreen()
        pix = screen.grabWindow(int(ct.winId()))
        if pix.isNull():
            pix = ct.grab()
        path = os.path.join(OUT, f"{len(SHOTS) + 1:02d}_{label}.png")
        pix.save(path)
        SHOTS.append((label, path))
    except Exception:
        LOG.append(f"[shoot {label}] {traceback.format_exc()}")


def step(label: str, fn) -> None:
    try:
        fn()
    except Exception:
        LOG.append(f"[step {label}] {traceback.format_exc()}")


def contact_sheet() -> None:
    if not SHOTS:
        return
    cols, tw = 2, 960
    images = []
    for label, path in SHOTS:
        img = QtGui.QImage(path)
        if img.isNull():
            continue
        images.append((label, img.scaledToWidth(tw, QtCore.Qt.TransformationMode.SmoothTransformation)))
    if not images:
        return
    rows = (len(images) + cols - 1) // cols
    row_h = [max(im.height() for _, im in images[r * cols:(r + 1) * cols]) + 36 for r in range(rows)]
    sheet = QtGui.QImage(cols * (tw + 16) + 16, sum(row_h) + 16, QtGui.QImage.Format.Format_RGB32)
    sheet.fill(QtGui.QColor("#111111"))
    p = QtGui.QPainter(sheet)
    p.setPen(QtGui.QColor("#dddddd"))
    for i, (label, im) in enumerate(images):
        r, c = divmod(i, cols)
        x = 16 + c * (tw + 16)
        y = 16 + sum(row_h[:r])
        p.drawText(x, y + 16, f"{i + 1}. {label}")
        p.drawImage(x, y + 24, im)
    p.end()
    sheet.save(os.path.join(OUT, "contact_sheet.png"))


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    from controller import ComicTranslate

    ct = ComicTranslate()
    ct.setWindowIcon(QtGui.QIcon(os.path.join(ROOT, "resources", "icons", "icon.ico")))
    ct.resize(1400, 860)
    ct.move(40, 40)
    ct.show()
    wait(1800)

    shoot(ct, "home_dark")
    step("main", ct.show_main_page)
    shoot(ct, "translate_simple_dark")

    def advanced():
        ct.advanced_checkbox.setChecked(True)
    step("advanced", advanced)
    shoot(ct, "translate_advanced_dark")
    step("advanced off", lambda: ct.advanced_checkbox.setChecked(False))

    def celebrate():
        ct.celebration.show_messages(["Level 2 reached!"])
        ct.confetti.burst(110)
    step("celebrate", celebrate)
    shoot(ct, "celebration_confetti", delay=700)
    wait(3500)

    step("settings", ct.show_settings_page)
    ui = ct.settings_page.ui
    count = ui.stacked_widget.count()
    for i in range(count):
        step(f"settings page {i}", lambda i=i: ui.stacked_widget.setCurrentIndex(i))
        shoot(ct, f"settings_page_{i}", delay=700)

    # Personalization: accent and glass variations on the translate screen
    def set_accent(key, glass=None):
        from PySide6.QtCore import QSettings
        s = QSettings("ComicLabs", "ComicTranslate")
        s.setValue("ui/accent", key)
        if glass is not None:
            s.setValue("ui/glass", glass)
        ct.apply_theme(ct.settings_page.get_theme())

    step("main again", ct.show_main_page)
    for key, glass in (("violet", 55), ("amber", 0), ("amber", 100)):
        step(f"accent {key}", lambda k=key, g=glass: set_accent(k, g))
        shoot(ct, f"translate_{key}_glass{glass}", delay=800)
    step("reset accent", lambda: set_accent("amber", 55))

    # Light theme
    def light():
        ui.theme_combo.setCurrentText(ct.settings_page.ui.tr("Light"))
    step("light", light)
    step("home", ct.show_home_screen)
    shoot(ct, "home_light")
    step("main", ct.show_main_page)
    shoot(ct, "translate_light")
    step("dark back", lambda: ui.theme_combo.setCurrentIndex(0))

    contact_sheet()
    with open(os.path.join(OUT, "report.txt"), "w", encoding="utf-8") as f:
        f.write(f"{len(SHOTS)} screenshots\nErrors: {len(LOG)}\n\n" + "\n".join(LOG))
    print(f"\nDone: {len(SHOTS)} screenshots, {len(LOG)} errors.\nFolder: {OUT}")
    try:
        os.startfile(OUT)  # Windows: open the folder
    except Exception:
        pass
    ct.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
