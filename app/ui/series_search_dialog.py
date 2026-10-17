"""Dialog: search a series online and build a short, spoiler-lean context sheet.

The result is meant to be pasted into the LLM "Extra Context" field. The user
always reviews and can edit the text before it is used.
"""

from PySide6 import QtCore, QtWidgets

from modules.series_context import (
    Candidate,
    SeriesSearchError,
    fetch_info,
    format_sheet,
    search,
)


class _Worker(QtCore.QThread):
    """Runs one blocking network call off the UI thread."""

    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.succeeded.emit(self._fn())
        except SeriesSearchError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # never let a worker crash the app
            self.failed.emit(str(exc))


class SeriesSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, max_chars: int = 1000):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Search a series"))
        self.setMinimumSize(560, 520)
        self._max_chars = max_chars
        self._lang = "fr" if QtCore.QLocale.system().name().startswith("fr") else "en"
        self._candidates: list[Candidate] = []
        self._worker: _Worker | None = None

        layout = QtWidgets.QVBoxLayout(self)

        intro = QtWidgets.QLabel(
            self.tr(
                "Type the title of the manga / manhwa. We fetch a short sheet (premise, genres, "
                "main characters) to help the AI translate with the right tone and names. "
                "Only the beginning of the story is kept, to avoid spoilers."
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        row = QtWidgets.QHBoxLayout()
        self.query_edit = QtWidgets.QLineEdit()
        self.query_edit.setPlaceholderText(self.tr("Series title…"))
        self.search_button = QtWidgets.QPushButton(self.tr("Search"))
        row.addWidget(self.query_edit, 1)
        row.addWidget(self.search_button)
        layout.addLayout(row)

        self.results = QtWidgets.QListWidget()
        self.results.setMaximumHeight(140)
        layout.addWidget(self.results)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setPlaceholderText(self.tr("The sheet will appear here. You can edit it."))
        layout.addWidget(self.preview, 1)

        self.counter = QtWidgets.QLabel("")
        self.counter.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.counter)

        buttons = QtWidgets.QDialogButtonBox()
        self.use_button = buttons.addButton(
            self.tr("Use this sheet"), QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole
        )
        buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.use_button.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.search_button.clicked.connect(self._do_search)
        self.query_edit.returnPressed.connect(self._do_search)
        self.results.currentRowChanged.connect(self._on_pick)
        self.preview.textChanged.connect(self._on_preview_changed)

    # ----------------------------------------------------------------- API
    def sheet_text(self) -> str:
        return self.preview.toPlainText()

    # ------------------------------------------------------------ internals
    def _busy(self, message: str) -> None:
        self.status.setText(message)
        self.search_button.setEnabled(False)
        self.results.setEnabled(False)

    def _idle(self) -> None:
        self.search_button.setEnabled(True)
        self.results.setEnabled(True)

    def _run(self, fn, on_ok) -> None:
        self._worker = _Worker(fn, self)
        self._worker.succeeded.connect(on_ok)
        self._worker.failed.connect(self._on_error)
        self._worker.finished.connect(self._idle)
        self._worker.start()

    def _do_search(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            return
        self.results.clear()
        self.preview.clear()
        self._candidates = []
        self._busy(self.tr("Searching…"))
        self._run(lambda: search(query), self._on_results)

    def _on_results(self, candidates) -> None:
        self._candidates = list(candidates)
        self.results.clear()
        if not self._candidates:
            self.status.setText(self.tr("No result. Try the original or romanized title."))
            return
        for cand in self._candidates:
            self.results.addItem(cand.label())
        self.status.setText(self.tr("Pick the right series."))
        self.results.setCurrentRow(0)

    def _on_pick(self, row: int) -> None:
        if row < 0 or row >= len(self._candidates):
            return
        cand = self._candidates[row]
        self._busy(self.tr("Loading the sheet…"))
        self._run(lambda: fetch_info(cand), self._on_info)

    def _on_info(self, info) -> None:
        self.preview.setPlainText(format_sheet(info, self._lang, self._max_chars))
        if info.spoiler_safe:
            self.status.setText(
                self.tr("Passages marked as spoilers by the source were removed. Still, give it a quick read.")
            )
        else:
            self.status.setText(
                self.tr("This source does not mark spoilers: please read the premise before using it.")
            )

    def _on_error(self, message: str) -> None:
        self.status.setText(self.tr("Search failed: %1").replace("%1", message))

    def _on_preview_changed(self) -> None:
        length = len(self.preview.toPlainText())
        self.counter.setText(f"{length} / {self._max_chars}")
        self.use_button.setEnabled(length > 0)
