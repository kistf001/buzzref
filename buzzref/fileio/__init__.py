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

from PyQt6 import QtCore

from buzzref import commands
from buzzref.fileio.errors import BuzzFileIOError
from buzzref.fileio.image import load_image
from buzzref.fileio.pureref import PureRefIO
from buzzref.fileio.sql import SQLiteIO, is_bee_file
from buzzref.items import BuzzPixmapItem


__all__ = [
    'is_bee_file',
    'load_bee',
    'load_pur',
    'save_bee',
    'load_images',
    'ThreadedLoader',
    'BuzzFileIOError',
]

logger = logging.getLogger(__name__)


def load_bee(filename, scene, worker=None):
    """Load BuzzRef native file."""
    logger.info(f'Loading from file {filename}...')
    io = SQLiteIO(filename, scene, readonly=True, worker=worker)
    return io.read()


def load_pur(filename, scene, worker=None):
    """Load PureRef file."""
    logger.info(f'Loading PureRef file {filename}...')
    io = PureRefIO(filename, scene, worker=worker)
    return io.read()


def save_bee(filename, scene, create_new=False, worker=None):
    """Save BuzzRef native file."""
    logger.info(f'Saving to file {filename}...')
    logger.debug(f'Create new: {create_new}')
    io = SQLiteIO(filename, scene, create_new, worker=worker)
    io.write()
    logger.info('End save')


def load_images(filenames, pos, scene, worker):
    """Add images to existing scene."""

    errors = []
    items = []
    worker.begin_processing.emit(len(filenames))
    for i, filename in enumerate(filenames):
        logger.info(f'Loading image from file {filename}')
        img, filename = load_image(filename)
        worker.progress.emit(i)
        if img.isNull():
            logger.info(f'Could not load file {filename}')
            errors.append(filename)
            continue

        item = BuzzPixmapItem(img, filename)
        item.set_pos_center(pos)
        scene.add_item_later({'item': item, 'type': 'pixmap'}, selected=True)
        items.append(item)
        if worker.canceled:
            break
        # Give main thread time to process items:
        worker.msleep(10)

    scene.undo_stack.push(
        commands.InsertItems(scene, items, ignore_first_redo=True))
    worker.finished.emit('', errors)


class ThreadedIO(QtCore.QThread):
    """Dedicated thread for loading and saving."""

    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(str, list)
    begin_processing = QtCore.pyqtSignal(int)
    user_input_required = QtCore.pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.kwargs['worker'] = self
        self.canceled = False

    def run(self):
        self.func(*self.args, **self.kwargs)

    def on_canceled(self):
        self.canceled = True
