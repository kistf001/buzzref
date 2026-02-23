# PureRef-format library (MIT License)
# Source: https://github.com/FyorDev/PureRef-format
# Vendored for BuzzRef PureRef file import support

import os
from typing import List

from .items import PurImage, PurGraphicsTextItem


class PurFile:

    def __init__(self):
        self.canvas = [-10000.0, -10000.0, 10000.0, 10000.0]
        self.zoom = 1.0
        self.xCanvas, self.yCanvas = 0, 0
        self.folderLocation = os.getcwd()
        self.images: List[PurImage] = []
        self.text: List[PurGraphicsTextItem] = []

    def read(self, file: str):
        from .read import read_pur_file
        read_pur_file(self, file)

    def count_image_items(self):
        count = 0
        for image in self.images:
            for transform in image.transforms:
                transform.id = count
                count += 1
        return count

    def count_text_items(self, id_offset: int):
        count = 0

        def count_children(text_item: PurGraphicsTextItem):
            nonlocal count
            text_item.id = count + id_offset
            count += 1
            list(map(count_children, text_item.textChildren))

        list(map(count_children, self.text))
        return len(self.text)
