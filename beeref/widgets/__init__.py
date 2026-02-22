# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt

from beeref import constants, commands
from beeref.config import logfile_name, BeeSettings
from beeref.widgets import (  # noqa: F401
    controls,
    settings,
    welcome_overlay,
    color_gamut,
)


logger = logging.getLogger(__name__)


class BeeProgressDialog(QtWidgets.QProgressDialog):

    def __init__(self, label, worker, maximum=0, parent=None):
        super().__init__(label, self.tr('Cancel'), 0, maximum, parent=parent)
        logger.debug('Initialised progress bar')
        self.setMinimumDuration(0)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAutoReset(False)
        self.setAutoClose(False)
        worker.begin_processing.connect(self.on_begin_processing)
        worker.progress.connect(self.on_progress)
        worker.finished.connect(self.on_finished)
        worker.user_input_required.connect(self.on_finished)
        self.canceled.connect(worker.on_canceled)

    def on_progress(self, value):
        logger.debug(f'Progress dialog: {value}')
        self.setValue(value)

    def on_begin_processing(self, value):
        logger.debug(f'Beginn progress dialog: {value}')
        self.setMaximum(value)

    def on_finished(self, *args, **kwargs):
        logger.debug('Finished progress dialog')
        self.setValue(self.maximum())
        self.reset()
        self.hide()
        QtCore.QTimer.singleShot(100, self.deleteLater)


class HelpDialog(QtWidgets.QDialog):
    DOCS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'documentation')

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr('%s Help') % constants.APPNAME)

        tabs = QtWidgets.QTabWidget()

        # Controls
        controls_txt = self._load_localized_help('controls.html')
        controls_label = QtWidgets.QLabel(controls_txt)
        controls_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_label)
        tabs.addTab(scroll, self.tr('&Controls'))

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(tabs)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.show()

    def _get_language_code(self):
        """Get the current language code from settings or system locale."""
        settings = BeeSettings()
        lang = settings.valueOrDefault('General/language')
        if lang == 'system':
            locale = QtCore.QLocale.system()
            lang = locale.name().split('_')[0]
        return lang

    def _load_localized_help(self, filename):
        """Load localized help content, falling back to English."""
        lang = self._get_language_code()
        base, ext = os.path.splitext(filename)

        # Try localized version first (e.g., controls_ko.html)
        if lang and lang != 'en':
            localized = os.path.join(self.DOCS_PATH, f'{base}_{lang}{ext}')
            if os.path.exists(localized):
                with open(localized, 'r', encoding='utf-8') as f:
                    return f.read()

        # Fall back to English
        default = os.path.join(self.DOCS_PATH, filename)
        with open(default, 'r', encoding='utf-8') as f:
            return f.read()


class DebugLogDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(self.tr('%s Debug Log') % constants.APPNAME)
        with open(logfile_name()) as f:
            self.log_txt = f.read()

        self.log = QtWidgets.QPlainTextEdit(self.log_txt)
        self.log.setReadOnly(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.copy_button = QtWidgets.QPushButton(self.tr('Co&py To Clipboard'))
        self.copy_button.released.connect(self.copy_to_clipboard)
        buttons.addButton(
            self.copy_button, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        name_widget = QtWidgets.QLabel(logfile_name())
        name_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(name_widget)
        layout.addWidget(self.log)
        layout.addWidget(buttons)
        self.show()

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.log_txt)


class SceneToPixmapExporterDialog(QtWidgets.QDialog):
    MIN_SIZE = 10
    MAX_SIZE = 100000

    def __init__(self, parent, default_size):
        super().__init__(parent)
        self.default_size = default_size
        if (self.default_size.width() > self.MAX_SIZE
                or self.default_size.width() >= self.MAX_SIZE):
            self.default_size.scale(
                self.MAX_SIZE, self.MAX_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio)

        self.ignore_change = False
        self.setWindowTitle(self.tr('Export Scene to Image'))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        width_label = QtWidgets.QLabel(self.tr('Width:'))
        layout.addWidget(width_label, 0, 0)
        self.width_input = QtWidgets.QSpinBox()
        self.width_input.setRange(self.MIN_SIZE, self.MAX_SIZE)
        self.width_input.setValue(default_size.width())
        self.width_input.valueChanged.connect(self.on_width_changed)
        layout.addWidget(self.width_input, 0, 1)

        height_label = QtWidgets.QLabel(self.tr('Height:'))
        layout.addWidget(height_label, 1, 0)
        self.height_input = QtWidgets.QSpinBox()
        self.height_input.setMinimum(10)
        self.height_input.setRange(self.MIN_SIZE, self.MAX_SIZE)
        self.height_input.setValue(default_size.height())
        self.height_input.valueChanged.connect(self.on_height_changed)
        layout.addWidget(self.height_input, 1, 1)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 3, 1)

    def on_width_changed(self, width):
        if not self.ignore_change:
            self.ignore_change = True
            new = self.default_size.scaled(
                width, self.MAX_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
            self.height_input.setValue(new.height())
            self.ignore_change = False

    def on_height_changed(self, height):
        if not self.ignore_change:
            self.ignore_change = True
            new = self.default_size.scaled(
                self.MAX_SIZE, height, Qt.AspectRatioMode.KeepAspectRatio)
            self.width_input.setValue(new.width())
            self.ignore_change = False

    def value(self):
        return QtCore.QSize(self.width_input.value(),
                            self.height_input.value())


class ChangeOpacityDialog(QtWidgets.QDialog):

    def __init__(self, parent, images, undo_stack):
        super().__init__(parent)
        self.undo_stack = undo_stack
        self.images = images
        self.command = commands.ChangeOpacity(images, opacity=1)

        value = int(images[0].opacity() * 100) if images else 100

        self.setWindowTitle(self.tr('Change Opacity:'))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.label = QtWidgets.QLabel(self.tr('Opacity:'))
        layout.addWidget(self.label)

        self.input = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.input.valueChanged.connect(self.on_value_changed)
        self.input.setRange(0, 100)
        self.input.setValue(value)
        layout.addWidget(self.input)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.show()

    def on_value_changed(self, value):
        self.label.setText(self.tr('Opacity: %s%%') % value)
        self.command.opacity = value / 100
        self.command.redo()

    def accept(self):
        if self.images:
            logger.debug(f'Setting opacity to {self.command.opacity}')
            self.command.ignore_first_redo = True
            self.undo_stack.push(self.command)
        return super().accept()

    def reject(self):
        self.command.undo()
        return super().reject()


class BeeNotification(QtWidgets.QWidget):
    def __init__(self, parent, text):
        super().__init__(parent)
        self.label = QtWidgets.QLabel(text)
        self.setObjectName('BeeNotification')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAutoFillBackground(True)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        color = constants.COLORS['Active:Window']
        self.setStyleSheet(
            f'background-color: rgba({color[0]}, {color[1]}, {color[2]}, 0.9);'
            'padding: 0.7em;'
            'border-radius: 5px;')
        self.show()
        # We only get own width after showing it;
        # updateGeometry doesn't work on hidden widgets
        x = (parent.width() - self.width()) / 2
        self.move(int(x), 10)

        QtCore.QTimer.singleShot(1000 * 3, self.deleteLater)


class SampleColorWidget(QtWidgets.QWidget):

    OFFSET = 10  # Offset from mouse pointer
    SIZE = 50
    NONE_COLOR = QtGui.QColor(0, 0, 0, 0)

    def __init__(self, parent, pos, color):
        super().__init__(parent)
        self.color = color
        self.set_pos(pos)
        self.show()

    def set_pos(self, pos):
        self.setGeometry(int(pos.x() + self.OFFSET),
                         int(pos.y() + self.OFFSET),
                         self.SIZE, self.SIZE)

    def paintEvent(self, event):
        color = self.color if self.color else self.NONE_COLOR
        painter = QtGui.QPainter(self)
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.SIZE, self.SIZE)

    def update(self, pos, color):
        self.set_pos(pos)
        self.color = color
        self.repaint()


class ExportImagesFileExistsDialog(QtWidgets.QDialog):

    def __init__(self, parent, filename):
        super().__init__(parent)
        self.setWindowTitle(self.tr('File exists'))

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        label = QtWidgets.QLabel(
            self.tr('File already exists:') + f'\n{filename}')
        layout.addWidget(label)

        choices = (('skip', self.tr('Skip this file')),
                   ('skip_all', self.tr('Skip all existing files')),
                   ('overwrite', self.tr('Overwrite this file')),
                   ('overwrite_all', self.tr('Overwrite all existing files')))

        self.radio_buttons = {}
        for (value, label) in choices:
            btn = QtWidgets.QRadioButton(label)
            self.radio_buttons[value] = btn
            layout.addWidget(btn)
        self.radio_buttons['skip'].setChecked(True)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def get_answer(self):
        for value, btn in self.radio_buttons.items():
            if btn.isChecked():
                return value
