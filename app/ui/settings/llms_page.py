from PySide6 import QtWidgets, QtCore
from ..dayu_widgets.label import MLabel
from ..dayu_widgets.text_edit import MTextEdit
from ..dayu_widgets.check_box import MCheckBox
from ..dayu_widgets.collapse import MCollapse
from ..dayu_widgets.push_button import MPushButton

class LlmsPage(QtWidgets.QWidget):
    DEFAULT_EXTRA_CONTEXT_LIMIT = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extra_context_limit: int | None = self.DEFAULT_EXTRA_CONTEXT_LIMIT

        v = QtWidgets.QVBoxLayout(self)
        main_layout = QtWidgets.QHBoxLayout()

        self.image_checkbox = MCheckBox()
        self.set_image_context_credits(1)
        self.image_checkbox.setChecked(False)

        # Left
        left_layout = QtWidgets.QVBoxLayout()
        prompt_label = MLabel(self.tr("Extra Context:"))
        self.extra_context = MTextEdit()
        self.extra_context.setMinimumHeight(200)

        self.series_search_button = MPushButton(self.tr("Search a series…"))
        self.series_search_button.setToolTip(
            self.tr("Look the series up online and fill this field with a short, spoiler-lean sheet")
        )
        self.series_search_button.clicked.connect(self._open_series_search)

        prompt_row = QtWidgets.QHBoxLayout()
        prompt_row.addWidget(prompt_label)
        prompt_row.addStretch(1)
        prompt_row.addWidget(self.series_search_button)
        left_layout.addLayout(prompt_row)
        left_layout.addWidget(self.extra_context)
        left_layout.addWidget(self.image_checkbox)
        left_layout.addStretch(1)

        # Right
        right_layout = QtWidgets.QVBoxLayout()

        # Advanced settings

        right_layout.addSpacing(10)
        right_layout.addStretch(1)

        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)

        v.addLayout(main_layout)
        v.addStretch(1)

        self.extra_context.textChanged.connect(self._limit_extra_context)

    def _open_series_search(self) -> None:
        from ..series_search_dialog import SeriesSearchDialog

        dialog = SeriesSearchDialog(self, max_chars=self._extra_context_limit or 2000)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        text = dialog.sheet_text().strip()
        if not text:
            return
        if self.extra_context.toPlainText().strip():
            answer = QtWidgets.QMessageBox.question(
                self,
                self.tr("Replace the current context?"),
                self.tr("The Extra Context field already has text. Replace it with the new sheet?"),
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.extra_context.setPlainText(text)

    def set_extra_context_unlimited(self, enabled: bool) -> None:
        self._extra_context_limit = None if enabled else self.DEFAULT_EXTRA_CONTEXT_LIMIT
        self._limit_extra_context()

    def set_image_context_credits(self, credits: int) -> None:
        unit = "Credit" if credits == 1 else "Credits"
        self.image_checkbox.setText(f"{self.tr('Provide Image as Input to AI')} (+{credits} {unit})")

    def _limit_extra_context(self):
        max_length = self._extra_context_limit
        if max_length is None:
            return
        text = self.extra_context.toPlainText()
        if len(text) > max_length:
            # Preserve cursor position
            cursor = self.extra_context.textCursor()
            position = cursor.position()
            
            # Truncate
            self.extra_context.setPlainText(text[:max_length])
            
            # Restore cursor (clamped to end)
            new_position = min(position, max_length)
            cursor.setPosition(new_position)
            self.extra_context.setTextCursor(cursor)

