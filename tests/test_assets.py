from PyQt6 import QtGui

from buzzref.assets import BuzzAssets


def test_singleton(view):
    assert BuzzAssets() is BuzzAssets()
    assert BuzzAssets().logo is BuzzAssets().logo


def test_has_logo(view):
    assert isinstance(BuzzAssets().logo, QtGui.QIcon)
