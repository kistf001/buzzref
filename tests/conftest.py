import os.path
import pytest
import uuid

from unittest.mock import MagicMock, patch

from PyQt6 import QtGui, QtWidgets


def pytest_configure(config):
    # Ignore logging configuration for BuzzRef during test runs. This
    # avoids logging to the regular log file and spamming test output
    # with debug messages.
    #
    # This needs to be done before the application code is even loaded since
    # logging configuration happens on module level
    import logging.config
    logging.config.dictConfig = MagicMock

    # Disable translations during tests by setting locale to C
    # This must be done before QApplication is created
    import os
    os.environ['LANGUAGE'] = 'C'
    os.environ['LC_ALL'] = 'C'
    os.environ['LANG'] = 'C'


@pytest.fixture(autouse=True)
def reset_buzzref_actions():
    from buzzref.actions.actions import get_actions
    for key in list(get_actions().keys()):
        if key.startswith('recent_files_'):
            get_actions().pop(key)


@pytest.fixture(autouse=True)
def commandline_args():
    config_patcher = patch('buzzref.view.commandline_args')
    config_mock = config_patcher.start()
    config_mock.filenames = []
    yield config_mock
    config_patcher.stop()


@pytest.fixture(autouse=True)
def settings(tmpdir):
    from buzzref.config import BuzzSettings
    dir_patcher = patch('buzzref.config.BuzzSettings.get_settings_dir',
                        return_value=tmpdir.dirname)
    dir_patcher.start()
    settings = BuzzSettings()
    yield settings
    settings.clear()
    dir_patcher.stop()


@pytest.fixture(autouse=True)
def kbsettings(tmpdir):
    from buzzref.config import KeyboardSettings
    dir_patcher = patch('buzzref.config.BuzzSettings.get_settings_dir',
                        return_value=tmpdir.dirname)
    dir_patcher.start()
    kbsettings = KeyboardSettings()
    yield kbsettings
    kbsettings.clear()
    dir_patcher.stop()


@pytest.fixture
def main_window(qtbot):
    from buzzref.__main__ import BuzzRefMainWindow
    app = QtWidgets.QApplication.instance()
    main = BuzzRefMainWindow(app)
    qtbot.addWidget(main)
    yield main


@pytest.fixture
def view(main_window):
    yield main_window.view


@pytest.fixture
def imgfilename3x3():
    root = os.path.dirname(__file__)
    yield os.path.join(root, 'assets', 'test3x3.png')


@pytest.fixture
def imgdata3x3(imgfilename3x3):
    with open(imgfilename3x3, 'rb') as f:
        imgdata3x3 = f.read()
    yield imgdata3x3


@pytest.fixture
def tmpfile(tmpdir):
    yield os.path.join(tmpdir, str(uuid.uuid4()))


@pytest.fixture
def item():
    from buzzref.items import BuzzPixmapItem
    img = QtGui.QImage(10, 10, QtGui.QImage.Format.Format_RGB32)
    yield BuzzPixmapItem(img)


@pytest.fixture(scope="session")
def qapp():
    from buzzref.__main__ import BuzzRefApplication
    yield BuzzRefApplication([])
