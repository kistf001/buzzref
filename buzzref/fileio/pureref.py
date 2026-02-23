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

"""PureRef (.pur) file import support.

Uses the vendored PureRef-format library (MIT License).
"""

import logging
import math

from PyQt6 import QtGui

from buzzref import commands
from buzzref.items import BuzzPixmapItem


logger = logging.getLogger(__name__)


class PureRefIO:
    """Reader for PureRef .pur files."""

    def __init__(self, filename, scene, worker=None):
        self.filename = filename
        self.scene = scene
        self.worker = worker
        self.items = []

    def read(self):
        """Read a PureRef file and add images to the scene."""
        from .vendor.purformat import PurFile

        logger.info(f'Loading PureRef file: {self.filename}')

        pur = PurFile()
        pur.read(self.filename)

        total_items = sum(len(img.transforms) for img in pur.images)
        logger.debug(f'Found {len(pur.images)} images, {total_items} items')

        if self.worker:
            self.worker.begin_processing.emit(total_items)

        item_count = 0
        for image in pur.images:
            if not image.pngBinary:
                continue

            # Load image data
            qimage = QtGui.QImage()
            if not qimage.loadFromData(bytes(image.pngBinary)):
                logger.warning('Failed to load image data')
                continue

            # Create an item for each transform (same image can appear
            # multiple times with different transforms)
            for transform in image.transforms:
                if self.worker and self.worker.canceled:
                    logger.debug('Import canceled')
                    self.worker.finished.emit('', [])
                    return

                item = self._create_item(qimage, transform)
                self.scene.add_item_later(
                    {'item': item, 'type': 'pixmap'}, selected=False)
                self.items.append(item)

                item_count += 1
                if self.worker:
                    self.worker.progress.emit(item_count)
                    self.worker.msleep(5)

        # Add undo command
        if self.items:
            self.scene.undo_stack.push(
                commands.InsertItems(self.scene, self.items,
                                     ignore_first_redo=True))

        logger.info(f'Imported {len(self.items)} items from PureRef file')
        if self.worker:
            self.worker.finished.emit(self.filename, [])

    def _create_item(self, qimage, transform):
        """Create a BuzzPixmapItem from PureRef transform data."""
        item = BuzzPixmapItem(qimage, filename=transform.source)

        # Extract scale, rotation, and flip from 2x2 matrix
        # Matrix format: [m11, m12, m21, m22]
        m11, m12, m21, m22 = transform.matrix

        # Scale is the length of the first column vector
        scale = math.sqrt(m11 * m11 + m21 * m21)

        # Rotation in degrees (atan2 returns radians)
        rotation = math.atan2(m21, m11) * 180.0 / math.pi

        # Determinant < 0 means there's a reflection (flip)
        det = m11 * m22 - m12 * m21
        is_flipped = det < 0

        # Apply transforms
        item.setPos(transform.x, transform.y)
        item.setZValue(transform.zLayer)

        if scale > 0:
            item.setScale(scale)
        if rotation != 0:
            item.setRotation(rotation)
        if is_flipped:
            item.do_flip()

        logger.debug(
            f'Created item: pos=({transform.x:.1f}, {transform.y:.1f}), '
            f'scale={scale:.3f}, rotation={rotation:.1f}, flip={is_flipped}'
        )

        return item
