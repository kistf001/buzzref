import logging
import os.path
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6 import QtCore

from buzzref.logging import (
    BuzzLogger,
    BuzzRotatingFileHandler,
    qt_message_handler,
)


def test_sets_new_loglevel():
    assert logging.getLevelName(5) == 'TRACE'


@patch('buzzref.logging.BuzzLogger.log')
def test_beelogger(log_mock):
    logger = BuzzLogger('mylogger', logging.TRACE)
    logger.trace('blah: %s', 'spam', extra={'foo': 'bar'})
    log_mock.assert_called_once_with(
        logging.TRACE, 'blah: %s', 'spam', extra={'foo': 'bar'})


def test_rotating_file_handler_creates_new_dir(tmpdir):
    logfile = os.path.join(tmpdir, 'foo', 'bar.log')
    handler = BuzzRotatingFileHandler(logfile)
    handler.emit(logging.LogRecord(
        'foo', logging.INFO, 'bar', 66, 'baz', [], None))
    handler.close()
    assert os.path.exists(logfile)


def testrotating_file_handler_uses_existing_dir(tmpdir):
    logfile = os.path.join(tmpdir, 'bar.log')
    handler = BuzzRotatingFileHandler(logfile)
    handler.emit(logging.LogRecord(
        'foo', logging.INFO, 'bar', 66, 'baz', [], None))
    handler.close()
    assert os.path.exists(logfile)


@patch('buzzref.logging.qtlogger.info')
def test_qt_message_handler_without(log_mock, qapp):
    qt_message_handler(QtCore.QtMsgType.QtInfoMsg, None, 'foo')
    log_mock.assert_called_once_with('foo')


@patch('buzzref.logging.qtlogger.warning')
def test_qt_message_handler_with_context(log_mock, qapp):
    ctx = SimpleNamespace(file='bla.txt', line='1', function='myfunc')
    qt_message_handler(QtCore.QtMsgType.QtWarningMsg, ctx, 'foo')
    log_mock.assert_called_once_with('foo: File bla.txt, line 1, in myfunc')
