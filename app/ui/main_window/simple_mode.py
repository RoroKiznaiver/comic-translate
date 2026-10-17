"""Simple / Advanced interface switch.

The workspace exposes every pipeline step, text-styling control and editing
tool at once. That is great for power users and overwhelming for everyone else.

Simple mode (the default) reduces the screen to the happy path:

    1. import pages  ->  2. pick languages  ->  3. Translate  ->  4. export

"Advanced options" brings back the original, complete interface. Nothing is
removed or rewired: the widgets all still exist and the controller keeps using
them, we only toggle their visibility.
"""

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSettings

_SETTINGS_ORG = "ComicLabs"
_SETTINGS_APP = "ComicTranslate"
_SETTINGS_KEY = "ui/advanced_mode"


class SimpleModeMixin:
    # ------------------------------------------------------------------ setup
    def _init_simple_mode(self) -> None:
        """Call once, right after the workspace widgets have been built."""
        self._advanced_mode = self._load_advanced_mode()

        # Widgets that only make sense for people driving the pipeline by hand.
        self._advanced_only_widgets = [
            self.hbutton_group,
            self.manual_radio,
            self.automatic_radio,
            self.batch_report_button,
            self.text_render_widget,
            self.tools_scroll,
        ]

        self.advanced_checkbox.setChecked(self._advanced_mode)
        self.advanced_checkbox.toggled.connect(self.set_advanced_mode)

        # "Cancel" is noise until something is actually running.
        self.progress_bar.installEventFilter(self)
        # Keep the one-line guide in sync with what the user is looking at.
        self.central_stack.currentChanged.connect(lambda _i: self._update_simple_hint())

        self._apply_mode()

    # -------------------------------------------------------------- settings
    @staticmethod
    def _load_advanced_mode() -> bool:
        try:
            settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
            return settings.value(_SETTINGS_KEY, False, type=bool)
        except Exception:
            return False

    @staticmethod
    def _save_advanced_mode(value: bool) -> None:
        try:
            QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(_SETTINGS_KEY, bool(value))
        except Exception:
            pass

    # ------------------------------------------------------------------- API
    def is_advanced_mode(self) -> bool:
        return bool(getattr(self, "_advanced_mode", False))

    def set_advanced_mode(self, advanced: bool) -> None:
        self._advanced_mode = bool(advanced)
        self._save_advanced_mode(self._advanced_mode)
        self._apply_mode()

    # --------------------------------------------------------------- internals
    def _apply_mode(self) -> None:
        advanced = self._advanced_mode

        for widget in self._advanced_only_widgets:
            widget.setVisible(advanced)

        self.simple_hint.setVisible(not advanced)
        self._update_cancel_visibility()
        self._update_simple_hint()

        # Never trap the user in a hidden manual workflow: simple mode is
        # always the automatic pipeline ("Translate All").
        if not advanced and self.manual_radio.isChecked():
            self.automatic_radio.setChecked(True)
            self.batch_mode_selected()

    def _update_cancel_visibility(self) -> None:
        if self._advanced_mode:
            self.cancel_button.setVisible(True)
        else:
            self.cancel_button.setVisible(self.progress_bar.isVisible())

    def _update_simple_hint(self) -> None:
        if not hasattr(self, "simple_hint"):
            return
        has_pages = self.central_stack.currentWidget() is not self.drag_browser
        if has_pages:
            text = self.tr("Choose the languages on the right, then click “Translate All”.")
        else:
            text = self.tr("Start by dropping your pages (images, PDF, CBZ…) in the box below.")
        self.simple_hint.setText(text)

    def eventFilter(self, obj, event):  # type: ignore[override]
        # The progress bar is shown for the whole duration of a batch, which is
        # exactly when "Cancel" is useful.
        if obj is getattr(self, "progress_bar", None) and event.type() in (
            QtCore.QEvent.Type.Show,
            QtCore.QEvent.Type.Hide,
        ):
            if getattr(self, "_advanced_mode", True) is False:
                self.cancel_button.setVisible(event.type() == QtCore.QEvent.Type.Show)
        return super().eventFilter(obj, event)
