#!/usr/bin/env python3

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

import logging
import os
import platform
import signal
import sys

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo

from buzzref import constants
from buzzref.translations import TRANSLATIONS_PATH
from buzzref.assets import BuzzAssets
from buzzref.config import CommandlineArgs, BuzzSettings, logfile_name
from buzzref.utils import create_palette_from_dict
from buzzref.view import BuzzGraphicsView

logger = logging.getLogger(__name__)


class BuzzRefApplication(QtWidgets.QApplication):

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.FileOpen:
            for widget in self.topLevelWidgets():
                if isinstance(widget, BuzzRefMainWindow):
                    widget.view.open_from_file(event.file())
                    return True
            return False
        else:
            return super().event(event)


class BuzzRefMainWindow(QtWidgets.QMainWindow):

    def __init__(self, app):
        super().__init__()
        app.setOrganizationName(constants.APPNAME)
        app.setApplicationName(constants.APPNAME)
        self.setWindowIcon(BuzzAssets().logo)
        self.view = BuzzGraphicsView(app, self)
        default_window_size = QtCore.QSize(500, 300)
        geom = self.view.settings.value('MainWindow/geometry')
        if geom is None:
            self.resize(default_window_size)
        else:
            if not self.restoreGeometry(geom):
                self.resize(default_window_size)
        self.setCentralWidget(self.view)
        self.show()

    def closeEvent(self, event):
        geom = self.saveGeometry()
        self.view.settings.setValue('MainWindow/geometry', geom)
        event.accept()

    def __del__(self):
        del self.view


def safe_timer(timeout, func, *args, **kwargs):
    """Create a timer that is safe against garbage collection and
    overlapping calls.
    See: http://ralsina.me/weblog/posts/BB974.html
    """
    def timer_event():
        try:
            func(*args, **kwargs)
        finally:
            QtCore.QTimer.singleShot(timeout, timer_event)
    QtCore.QTimer.singleShot(timeout, timer_event)


def handle_sigint(signum, frame):
    logger.info('Received interrupt. Exiting...')
    QtWidgets.QApplication.quit()


def handle_uncaught_exception(exc_type, exc, traceback):
    logger.critical('Unhandled exception',
                    exc_info=(exc_type, exc, traceback))
    QtWidgets.QApplication.quit()


sys.excepthook = handle_uncaught_exception


def main():
    logger.info(f'Starting {constants.APPNAME} version {constants.VERSION}')
    logger.debug('System: %s', ' '.join(platform.uname()))
    logger.debug('Python: %s', platform.python_version())
    logger.debug('LD_LIBRARY_PATH: %s', os.environ.get('LD_LIBRARY_PATH'))
    settings = BuzzSettings()
    logger.info(f'Using settings: {settings.fileName()}')
    logger.info(f'Logging to: {logfile_name()}')
    settings.on_startup()
    args = CommandlineArgs(with_check=True)  # Force checking
    assert not args.debug_raise_error, args.debug_raise_error

    os.environ["QT_DEBUG_PLUGINS"] = "1"
    app = BuzzRefApplication(sys.argv)

    # Load Qt base translations (standard dialogs, buttons, etc.)
    qt_translator = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(QLocale.system(), 'qtbase', '_', qt_path):
        app.installTranslator(qt_translator)

    # Load BuzzRef translations
    translator = QTranslator(app)
    # Check user preference first, fall back to system locale
    lang_setting = settings.valueOrDefault('General/language')
    if lang_setting and lang_setting != 'system':
        locale = lang_setting
    else:
        locale = QLocale.system().name()  # e.g., ko_KR, ja_JP

    if translator.load(f'buzzref_{locale}', TRANSLATIONS_PATH):
        app.installTranslator(translator)
        logger.info(f'Loaded translation for locale: {locale}')
    else:
        # Try language code only (e.g., 'ko' from 'ko_KR')
        lang = locale.split('_')[0]
        if translator.load(f'buzzref_{lang}', TRANSLATIONS_PATH):
            app.installTranslator(translator)
            logger.info(f'Loaded translation for language: {lang}')

    palette = create_palette_from_dict(constants.COLORS)
    app.setPalette(palette)
    bee = BuzzRefMainWindow(app)  # NOQA:F841

    signal.signal(signal.SIGINT, handle_sigint)
    # Repeatedly run python-noop to give the interpreter time to
    # handle signals
    safe_timer(50, lambda: None)

    app.exec()
    del bee
    del app
    logger.debug('BuzzRef closed')
    QtCore.qInstallMessageHandler(None)


if __name__ == '__main__':
    main()  # pragma: no cover
