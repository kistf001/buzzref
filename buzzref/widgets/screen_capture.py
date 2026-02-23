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

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal


logger = logging.getLogger(__name__)


class ScreenCaptureOverlay(QtWidgets.QWidget):
    """Full-screen overlay for selecting a region from a screenshot."""

    captured = pyqtSignal(QtGui.QPixmap)
    canceled = pyqtSignal()

    def __init__(self, screenshot: QtGui.QPixmap):
        super().__init__()
        self.screenshot = screenshot
        self.start_pos = None
        self.current_pos = None

        # Full screen, always on top, frameless
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        logger.debug('ScreenCaptureOverlay initialized')

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        # Draw screenshot as background
        painter.drawPixmap(0, 0, self.screenshot)

        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 100))

        # Draw selection region (show original screenshot in selection)
        if self.start_pos and self.current_pos:
            rect = QtCore.QRect(self.start_pos, self.current_pos).normalized()
            # Draw original screenshot in selection area
            painter.drawPixmap(rect, self.screenshot, rect)
            # Draw white border
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2))
            painter.drawRect(rect)

            # Draw size info
            size_text = f'{rect.width()} x {rect.height()}'
            painter.setPen(QtGui.QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            text_rect = painter.fontMetrics().boundingRect(size_text)
            text_x = rect.x() + (rect.width() - text_rect.width()) // 2
            text_y = rect.bottom() + text_rect.height() + 5
            if text_y > self.height() - 10:
                text_y = rect.top() - 5
            painter.drawText(text_x, text_y, size_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            logger.debug(f'Screen capture started at {self.start_pos}')
        elif event.button() == Qt.MouseButton.RightButton:
            self._cancel()

    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.start_pos and self.current_pos:
                rect = QtCore.QRect(self.start_pos, self.current_pos).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    cropped = self.screenshot.copy(rect)
                    logger.debug(f'Screen captured: {rect.width()}x{rect.height()}')
                    self.captured.emit(cropped)
                else:
                    logger.debug('Selection too small, canceling')
                    self.canceled.emit()
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()

    def _cancel(self):
        logger.debug('Screen capture canceled')
        self.canceled.emit()
        self.close()
