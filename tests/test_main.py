from unittest.mock import patch, MagicMock

from PyQt6 import QtCore

from buzzref.__main__ import BuzzRefMainWindow, main
from buzzref.assets import BuzzAssets
from buzzref.view import BuzzGraphicsView


@patch('PyQt6.QtWidgets.QWidget.show')
def test_buzzref_mainwindow_init(show_mock, qapp):
    window = BuzzRefMainWindow(qapp)
    assert window.windowTitle() == 'BuzzRef'
    assert BuzzAssets().logo == BuzzAssets().logo
    assert window.windowIcon()
    assert window.contentsMargins() == QtCore.QMargins(0, 0, 0, 0)
    assert isinstance(window.view, BuzzGraphicsView)
    show_mock.assert_called()


@patch('buzzref.view.BuzzGraphicsView.open_from_file')
def test_buzzrefapplication_fileopenevent(open_mock, qapp, main_window):
    event = MagicMock()
    event.type.return_value = QtCore.QEvent.Type.FileOpen
    event.file.return_value = 'test.bee'
    assert qapp.event(event) is True
    open_mock.assert_called_once_with('test.bee')


@patch('buzzref.__main__.BuzzRefApplication')
@patch('buzzref.__main__.CommandlineArgs')
@patch('buzzref.config.BuzzSettings.on_startup')
def test_main(startup_mock, args_mock, app_mock, qapp):
    app_mock.return_value = qapp
    args_mock.return_value.filename = None
    args_mock.return_value.loglevel = 'WARN'
    args_mock.return_value.debug_raise_error = ''

    with patch.object(qapp, 'exec') as exec_mock:
        main()
        exec_mock.assert_called_once_with()

    args_mock.assert_called_once_with(with_check=True)
    startup_mock.assert_called()
