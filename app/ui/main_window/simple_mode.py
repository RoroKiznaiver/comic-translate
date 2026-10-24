"""Simple / Advanced interface switch.

The workspace exposes every pipeline step, text-styling control and editing
tool at once. That is great for power users and overwhelming for everyone else.

Simple mode (the default) reduces the screen to the happy path:

    1. import pages  ->  2. Translate  ->  3. export

and shows a step indicator (Import / Translate / Export) whose pill slides to
the current step. "Advanced options" brings back the original, complete
interface. Nothing is removed or rewired: the widgets all still exist and the
controller keeps using them, we only toggle their visibility.
"""

from PySide6 import QtCore
from PySide6.QtCore import QSettings

from app.ui.motion import fade_in, reveal
from app.ui.step_logic import compute_step_index

_SETTINGS_ORG = "ComicLabs"
_SETTINGS_APP = "ComicTranslate"
_SETTINGS_KEY = "ui/advanced_mode"


class SimpleModeMixin:
    # ------------------------------------------------------------------ setup
    def _init_simple_mode(self) -> None:
        """Call once, right after the workspace widgets have been built."""
        self._advanced_mode = self._load_advanced_mode()
        self._batch_finished = False
        self._cancel_clicked = False
        self._stepper_running = False

        # Hidden instantly in simple mode.
        self._advanced_only_widgets = [
            self.hbutton_group,
            self.manual_radio,
            self.automatic_radio,
            self.batch_report_button,
            self.tools_scroll,
        ]
        # Content-sized sections that grow/shrink with an animation.
        self._animated_sections = [self.text_render_widget]

        self.advanced_checkbox.setChecked(self._advanced_mode)
        self.advanced_checkbox.toggled.connect(self.set_advanced_mode)

        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        # The progress bar is visible for the whole duration of a batch.
        self.progress_bar.installEventFilter(self)
        self.central_stack.currentChanged.connect(lambda _i: self._on_stack_changed())

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
        for section in self._animated_sections:
            reveal(section, advanced)

        self.step_pill.setVisible(not advanced)
        self._update_cancel_visibility()
        self._update_stepper()

        # Never trap the user in a hidden manual workflow: simple mode is
        # always the automatic pipeline ("Translate All").
        if not advanced and self.manual_radio.isChecked():
            self.automatic_radio.setChecked(True)
            self.batch_mode_selected()

    def _update_cancel_visibility(self) -> None:
        # "Cancel" is noise until something is actually running.
        if self._advanced_mode:
            self.cancel_button.setVisible(True)
        else:
            self.cancel_button.setVisible(self._stepper_running)

    def _update_stepper(self) -> None:
        has_pages = self.central_stack.currentWidget() is not self.drag_browser
        index = compute_step_index(has_pages, self._stepper_running, self._batch_finished)
        self.step_pill.set_index(index)

    def _on_cancel_clicked(self) -> None:
        self._cancel_clicked = True

    def _on_stack_changed(self) -> None:
        if self.central_stack.currentWidget() is self.drag_browser:
            # Back on the drop zone (new project): start the flow over.
            self._batch_finished = False
        self._update_stepper()
        fade_in(self.central_stack.currentWidget(), 280)

    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is getattr(self, "progress_bar", None):
            kind = event.type()
            if kind == QtCore.QEvent.Type.Show and not self._stepper_running:
                self._stepper_running = True
                self._batch_finished = False
                self._cancel_clicked = False
                self._update_cancel_visibility()
                self._update_stepper()
            elif kind == QtCore.QEvent.Type.Hide and self._stepper_running and obj.isHidden():
                # isHidden() is only true for an explicit hide, not when a parent
                # page is hidden (e.g. the user opens Settings mid-batch).
                self._stepper_running = False
                self._batch_finished = not self._cancel_clicked
                self._update_cancel_visibility()
                self._update_stepper()
        return super().eventFilter(obj, event)
