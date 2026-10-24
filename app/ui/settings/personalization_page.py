from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSettings
from .utils import create_title_and_combo, set_combo_box_width

class PersonalizationPage(QtWidgets.QWidget):
    accent_changed = QtCore.Signal(str)
    glass_changed = QtCore.Signal(int)
    material_changed = QtCore.Signal(str)

    def __init__(self, languages: list[str], themes: list[str], parent=None):
        super().__init__(parent)
        self.languages = languages
        self.themes = themes

        layout = QtWidgets.QVBoxLayout(self)

        language_widget, self.lang_combo = create_title_and_combo(self.tr("Language"), self.languages)
        set_combo_box_width(self.lang_combo, self.languages)
        theme_widget, self.theme_combo = create_title_and_combo(self.tr("Theme"), self.themes)
        set_combo_box_width(self.theme_combo, self.themes)

        # Accent colour: the whole interface re-tints live.
        self._accent_keys = ["amber", "blue", "violet", "green", "pink"]
        accent_labels = [self.tr("Amber"), self.tr("Blue"), self.tr("Violet"), self.tr("Green"), self.tr("Pink")]
        accent_widget, self.accent_combo = create_title_and_combo(self.tr("Accent colour"), accent_labels)
        set_combo_box_width(self.accent_combo, accent_labels)
        current = str(QSettings("ComicLabs", "ComicTranslate").value("ui/accent", "amber"))
        if current in self._accent_keys:
            self.accent_combo.setCurrentIndex(self._accent_keys.index(current))
        self.accent_combo.currentIndexChanged.connect(self._on_accent_index)

        # Window material (Windows 11 only): real frosted backdrop behind the sidebar
        self._material_keys = ["mica", "acrylic", "off"]
        material_labels = [self.tr("Mica"), self.tr("Acrylic"), self.tr("Off")]
        material_widget, self.material_combo = create_title_and_combo(self.tr("Window material (Windows 11)"), material_labels)
        set_combo_box_width(self.material_combo, material_labels)
        cur_mat = str(QSettings("ComicLabs", "ComicTranslate").value("ui/material", "mica"))
        if cur_mat in self._material_keys:
            self.material_combo.setCurrentIndex(self._material_keys.index(cur_mat))
        self.material_combo.currentIndexChanged.connect(self._on_material_index)

        # Liquid Glass transparency: ultra clear <-> fully tinted
        glass_row = QtWidgets.QWidget()
        glass_layout = QtWidgets.QVBoxLayout(glass_row)
        glass_layout.setContentsMargins(0, 0, 0, 0)
        glass_layout.addWidget(QtWidgets.QLabel(self.tr("Glass transparency")))
        self.glass_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.glass_slider.setRange(0, 100)
        self.glass_slider.setFixedWidth(260)
        self.glass_slider.setValue(int(QSettings("ComicLabs", "ComicTranslate").value("ui/glass", 55)))
        self.glass_slider.setToolTip(self.tr("Ultra clear  <->  fully tinted"))
        self._glass_timer = QtCore.QTimer(self)
        self._glass_timer.setSingleShot(True)
        self._glass_timer.setInterval(120)
        self._glass_timer.timeout.connect(self._apply_glass)
        self.glass_slider.valueChanged.connect(lambda _v: self._glass_timer.start())
        glass_layout.addWidget(self.glass_slider)

        # Turns every interface animation off (see app/ui/motion.py).
        self.reduce_motion_checkbox = QtWidgets.QCheckBox(self.tr("Reduce animations"))
        self.reduce_motion_checkbox.setChecked(
            QSettings("ComicLabs", "ComicTranslate").value("ui/reduce_motion", False, type=bool)
        )
        self.reduce_motion_checkbox.toggled.connect(
            lambda checked: QSettings("ComicLabs", "ComicTranslate").setValue("ui/reduce_motion", bool(checked))
        )

        # Translation memory (modules/translation/memory.py)
        self.memory_checkbox = QtWidgets.QCheckBox(self.tr("Reuse previous translations (saves tokens)"))
        self.memory_checkbox.setChecked(
            QSettings("ComicLabs", "ComicTranslate").value("memory/enabled", True, type=bool)
        )
        self.memory_checkbox.toggled.connect(
            lambda checked: QSettings("ComicLabs", "ComicTranslate").setValue("memory/enabled", bool(checked))
        )
        self.memory_clear_button = QtWidgets.QPushButton(self.tr("Forget stored translations"))
        self.memory_clear_button.setToolTip(
            self.tr("Next time, every page is sent to the translator again")
        )
        self.memory_clear_button.clicked.connect(self._clear_memory)

        layout.addWidget(language_widget)
        layout.addWidget(theme_widget)
        layout.addWidget(accent_widget)
        layout.addWidget(glass_row)
        layout.addWidget(material_widget)
        layout.addWidget(self.reduce_motion_checkbox)
        layout.addWidget(self.memory_checkbox)
        layout.addWidget(self.memory_clear_button, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

    def _on_material_index(self, index: int) -> None:
        if 0 <= index < len(self._material_keys):
            key = self._material_keys[index]
            QSettings("ComicLabs", "ComicTranslate").setValue("ui/material", key)
            self.material_changed.emit(key)

    def _apply_glass(self) -> None:
        value = int(self.glass_slider.value())
        QSettings("ComicLabs", "ComicTranslate").setValue("ui/glass", value)
        self.glass_changed.emit(value)

    def _on_accent_index(self, index: int) -> None:
        if 0 <= index < len(self._accent_keys):
            key = self._accent_keys[index]
            QSettings("ComicLabs", "ComicTranslate").setValue("ui/accent", key)
            self.accent_changed.emit(key)

    def _clear_memory(self) -> None:
        try:
            from modules.translation.processor import get_translation_memory
            get_translation_memory().clear()
            self.memory_clear_button.setText(self.tr("Stored translations forgotten"))
        except Exception:
            pass
