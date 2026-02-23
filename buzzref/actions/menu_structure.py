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

from PyQt6.QtCore import QObject

MENU_SEPARATOR = 0


class MenuRegistry(QObject):
    """메뉴 구조를 생성하는 싱글톤 QObject.

    pylupdate6 호환성을 위해 self.tr()을 사용합니다.
    QApplication 생성 이후에 초기화되어야 합니다.
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_menu_structure(self):
        """번역된 메뉴 구조를 생성합니다."""
        return [
            {
                'menu': self.tr('&File'),
                'items': [
                    'new_scene',
                    'open',
                    {
                        'menu': self.tr('Open &Recent'),
                        'items': '_build_recent_files',
                    },
                    MENU_SEPARATOR,
                    'save',
                    'save_as',
                    'export_scene',
                    'export_images',
                    MENU_SEPARATOR,
                    'quit',
                ],
            },
            {
                'menu': self.tr('&Edit'),
                'items': [
                    'undo',
                    'redo',
                    MENU_SEPARATOR,
                    'select_all',
                    'deselect_all',
                    MENU_SEPARATOR,
                    'cut',
                    'copy',
                    'paste',
                    'delete',
                    MENU_SEPARATOR,
                    'raise_to_top',
                    'lower_to_bottom',
                ],
            },
            {
                'menu': self.tr('&View'),
                'items': [
                    'fit_scene',
                    'fit_selection',
                    MENU_SEPARATOR,
                    'fullscreen',
                    'always_on_top',
                    'show_scrollbars',
                    'show_menubar',
                    'show_titlebar',
                    MENU_SEPARATOR,
                    'move_window',
                ],
            },
            {
                'menu': self.tr('&Insert'),
                'items': [
                    'insert_images',
                    'insert_text',
                ],
            },
            {
                'menu': self.tr('&Transform'),
                'items': [
                    'crop',
                    'flip_horizontally',
                    'flip_vertically',
                    MENU_SEPARATOR,
                    'reset_scale',
                    'reset_rotation',
                    'reset_flip',
                    'reset_crop',
                    'reset_transforms',
                ],
            },
            {
                'menu': self.tr('&Normalize'),
                'items': [
                    'normalize_height',
                    'normalize_width',
                    'normalize_size',
                ],
            },
            {
                'menu': self.tr('&Arrange'),
                'items': [
                    'arrange_optimal',
                    'arrange_horizontal',
                    'arrange_vertical',
                    'arrange_square',
                ],
            },
            {
                'menu': self.tr('&Drawing'),
                'items': [
                    'draw_mode',
                    'set_brush_color',
                    'set_brush_size',
                ],
            },
            {
                'menu': self.tr('&Images'),
                'items': [
                    'change_opacity',
                    'grayscale',
                    MENU_SEPARATOR,
                    'show_color_gamut',
                    'show_filename',
                    'sample_color',
                    'capture',
                ],
            },
            {
                'menu': self.tr('&Settings'),
                'items': [
                    'settings',
                    'keyboard_settings',
                    'open_settings_dir',
                ],
            },
            {
                'menu': self.tr('&Help'),
                'items': [
                    'help',
                    'about',
                    'debuglog',
                ],
            },
        ]


# Lazy accessor for backward compatibility
_menu_structure = None


def get_menu_structure():
    """Get the menu structure, creating it if necessary.

    This function should be called after QApplication is created.
    """
    global _menu_structure
    if _menu_structure is None:
        _menu_structure = MenuRegistry.instance().create_menu_structure()
    return _menu_structure


# Backward compatibility alias (deprecated)
# Will be initialized on first access via get_menu_structure()
menu_structure = None
