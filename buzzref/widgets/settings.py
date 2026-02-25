# This file is part of BuzzRef.
#
# BuzzRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BuzzRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BuzzRef.  If not, see <https://www.gnu.org/licenses/>.

from functools import partial
import logging
import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from buzzref import constants
from buzzref.config import BuzzSettings, settings_events
from buzzref.translations import TRANSLATIONS_PATH


logger = logging.getLogger(__name__)


class GroupBase(QtWidgets.QGroupBox):
    TITLE = None
    HELPTEXT = None
    KEY = None

    def __init__(self):
        super().__init__()
        self.settings = BuzzSettings()
        self.update_title()
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        settings_events.restore_defaults.connect(self.on_restore_defaults)

        if self.HELPTEXT:
            helptxt = QtWidgets.QLabel(self.HELPTEXT)
            helptxt.setWordWrap(True)
            self.layout.addWidget(helptxt)

    def update_title(self):
        title = [self.TITLE]
        if self.settings.value_changed(self.KEY):
            title.append(constants.CHANGED_SYMBOL)
        self.setTitle(' '.join(title))

    def on_value_changed(self, value):
        if self.ignore_value_changed:
            return

        value = self.convert_value_from_qt(value)
        if value != self.settings.valueOrDefault(self.KEY):
            logger.debug(f'Setting {self.KEY} changed to: {value}')
            self.settings.setValue(self.KEY, value)
            self.update_title()

    def convert_value_from_qt(self, value):
        return value

    def on_restore_defaults(self):
        new_value = self.settings.valueOrDefault(self.KEY)
        self.ignore_value_changed = True
        self.set_value(new_value)
        self.ignore_value_changed = False
        self.update_title()


class RadioGroup(GroupBase):
    OPTIONS = None

    def __init__(self):
        super().__init__()

        self.ignore_value_changed = True
        self.buttons = {}
        for (value, label, helptext) in self.OPTIONS:
            btn = QtWidgets.QRadioButton(label)
            self.buttons[value] = btn
            btn.setToolTip(helptext)
            btn.toggled.connect(partial(self.on_value_changed, value=value))
            if value == self.settings.valueOrDefault(self.KEY):
                btn.setChecked(True)
            self.layout.addWidget(btn)

        self.ignore_value_changed = False
        self.layout.addStretch(100)

    def set_value(self, value):
        for old_value, btn in self.buttons.items():
            btn.setChecked(old_value == value)


class IntegerGroup(GroupBase):
    MIN = None
    MAX = None

    def __init__(self):
        super().__init__()
        self.input = QtWidgets.QSpinBox()
        self.input.setRange(self.MIN, self.MAX)
        self.set_value(self.settings.valueOrDefault(self.KEY))
        self.input.valueChanged.connect(self.on_value_changed)
        self.layout.addWidget(self.input)
        self.layout.addStretch(100)
        self.ignore_value_changed = False

    def set_value(self, value):
        self.input.setValue(value)


class SingleCheckboxGroup(GroupBase):
    LABEL = None

    def __init__(self):
        super().__init__()
        self.input = QtWidgets.QCheckBox(self.LABEL)
        self.set_value(self.settings.valueOrDefault(self.KEY))
        self.input.checkStateChanged.connect(self.on_value_changed)
        self.layout.addWidget(self.input)
        self.layout.addStretch(100)
        self.ignore_value_changed = False

    def set_value(self, value):
        self.input.setChecked(value)

    def convert_value_from_qt(self, value):
        return value == Qt.CheckState.Checked


class ArrangeDefaultWidget(RadioGroup):
    KEY = 'Items/arrange_default'

    @property
    def TITLE(self):
        return self.tr('Default Arrange Method:')

    @property
    def HELPTEXT(self):
        return self.tr('How images are arranged when inserted in batch')

    @property
    def OPTIONS(self):
        return (
            ('optimal', self.tr('Optimal'), self.tr('Arrange Optimal')),
            ('horizontal', self.tr('Horizontal (by filename)'),
             self.tr('Arrange Horizontal (by filename)')),
            ('vertical', self.tr('Vertical (by filename)'),
             self.tr('Arrange Vertical (by filename)')),
            ('square', self.tr('Square (by filename)'),
             self.tr('Arrange Square (by filename)')))


class ImageStorageFormatWidget(RadioGroup):
    KEY = 'Items/image_storage_format'

    @property
    def TITLE(self):
        return self.tr('Image Storage Format:')

    @property
    def HELPTEXT(self):
        return self.tr('How images are stored inside bee files.'
                       ' Changes will only take effect on newly saved images.')

    @property
    def OPTIONS(self):
        return (
            ('best', self.tr('Best Guess'),
             self.tr('Small images and images with alpha channel '
                     'are stored as png, everything else as jpg')),
            ('png', self.tr('Always PNG'), self.tr(
                'Lossless, but large bee file')),
            ('jpg', self.tr('Always JPG'),
             self.tr('Small bee file, but lossy and no transparency support')))


class ArrangeGapWidget(IntegerGroup):
    KEY = 'Items/arrange_gap'
    MIN = 0
    MAX = 200

    @property
    def TITLE(self):
        return self.tr('Arrange Gap:')

    @property
    def HELPTEXT(self):
        return self.tr('The gap between images when using arrange actions.')


class AllocationLimitWidget(IntegerGroup):
    KEY = 'Items/image_allocation_limit'
    MIN = 0
    MAX = 10000

    @property
    def TITLE(self):
        return self.tr('Maximum Image Size:')

    @property
    def HELPTEXT(self):
        return self.tr('The maximum image size that can be loaded '
                       '(in megabytes). Set to 0 for no limitation.')


class ConfirmCloseUnsavedWidget(SingleCheckboxGroup):
    KEY = 'Save/confirm_close_unsaved'

    @property
    def TITLE(self):
        return self.tr('Confirm when closing an unsaved file:')

    @property
    def HELPTEXT(self):
        return self.tr('When about to close an unsaved file, '
                       'should BuzzRef ask for confirmation?')

    @property
    def LABEL(self):
        return self.tr('Confirm when closing')


class LanguageWidget(GroupBase):
    KEY = 'General/language'

    # Language code -> Display name mapping
    # Note: Native names are not translated (they show in their own language)
    LANGUAGES = {
        'system': None,  # Translated at runtime
        'en': 'English',
        'es': 'Español (Spanish)',
        'fr': 'Français (French)',
        'ja': '日本語 (Japanese)',
        'ko': '한국어 (Korean)',
        'zh_CN': '简体中文 (Chinese Simplified)',
        'zh_TW': '繁體中文 (Chinese Traditional)',
    }

    def __init__(self):
        super().__init__()
        self.ignore_value_changed = False

        self.combo = QtWidgets.QComboBox()

        # Detect available translations
        available = self._get_available_languages()

        for code, name in self.LANGUAGES.items():
            if code in available or code in ('system', 'en'):
                # Translate 'System Default' at runtime
                display_name = self.tr(
                    'System Default') if code == 'system' else name
                self.combo.addItem(display_name, code)

        # Set current value
        current = self.settings.valueOrDefault(self.KEY)
        index = self.combo.findData(current)
        if index >= 0:
            self.combo.setCurrentIndex(index)

        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        self.layout.addWidget(self.combo)
        self.layout.addStretch(100)

    @property
    def TITLE(self):
        return self.tr('Language:')

    @property
    def HELPTEXT(self):
        return self.tr(
            'Select the application language. '
            'Restart required for changes to take effect.')

    def _get_available_languages(self):
        """Scan translations directory for available .qm files."""
        available = set()
        if os.path.exists(TRANSLATIONS_PATH):
            for filename in os.listdir(TRANSLATIONS_PATH):
                if filename.startswith(
                        'buzzref_') and filename.endswith('.qm'):
                    # Extract language code from buzzref_ko.qm -> ko
                    lang = filename[8:-3]  # Remove 'buzzref_' and '.qm'
                    # Keep full code for Chinese variants (zh_CN, zh_TW)
                    # but simplify other locale variants (ko_KR -> ko)
                    if lang.startswith('zh_'):
                        available.add(lang)
                    else:
                        available.add(lang.split('_')[0])
        return available

    def _on_combo_changed(self, index):
        if self.ignore_value_changed:
            return
        code = self.combo.itemData(index)
        self.on_value_changed(code)

        # Show restart notification
        QtWidgets.QMessageBox.information(
            self,
            self.tr('Language Changed'),
            self.tr('Please restart BuzzRef for the language change '
                    'to take effect.')
        )

    def set_value(self, value):
        index = self.combo.findData(value)
        if index >= 0:
            self.combo.setCurrentIndex(index)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr('BuzzRef Settings'))
        tabs = QtWidgets.QTabWidget()

        # Miscellaneous
        misc = QtWidgets.QWidget()
        misc_layout = QtWidgets.QGridLayout()
        misc.setLayout(misc_layout)
        misc_layout.addWidget(LanguageWidget(), 0, 0)
        misc_layout.addWidget(ConfirmCloseUnsavedWidget(), 0, 1)
        tabs.addTab(misc, self.tr('&Miscellaneous'))

        # Images & Items
        items = QtWidgets.QWidget()
        items_layout = QtWidgets.QGridLayout()
        items.setLayout(items_layout)
        items_layout.addWidget(ImageStorageFormatWidget(), 0, 0)
        items_layout.addWidget(AllocationLimitWidget(), 0, 1)
        items_layout.addWidget(ArrangeGapWidget(), 1, 0)
        items_layout.addWidget(ArrangeDefaultWidget(), 1, 1)
        tabs.addTab(items, self.tr('&Images && Items'))

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(tabs)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        reset_btn = QtWidgets.QPushButton(self.tr('&Restore Defaults'))
        reset_btn.setAutoDefault(False)
        reset_btn.clicked.connect(self.on_restore_defaults)
        buttons.addButton(reset_btn,
                          QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        layout.addWidget(buttons)
        self.show()

    def on_restore_defaults(self, *args, **kwargs):
        msg = self.tr('Do you want to restore all settings '
                      'to their default values?')
        reply = QtWidgets.QMessageBox.question(
            self,
            self.tr('Restore defaults?'),
            msg)

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            BuzzSettings().restore_defaults()
