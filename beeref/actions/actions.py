# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

from functools import cached_property
import logging

from PyQt6 import QtGui
from PyQt6.QtCore import QObject

from beeref.actions.menu_structure import get_menu_structure
from beeref.config import KeyboardSettings, settings_events
from beeref.utils import ActionList


logger = logging.getLogger(__name__)


class Action:
    SETTINGS_GROUP = 'Actions'

    def __init__(self, id, text, callback=None, shortcuts=None,
                 checkable=False, checked=False, group=None, settings=None,
                 enabled=True, menu_item=None, menu_id=None):
        self.id = id
        self._text = text  # Store source text for translation
        self.callback = callback
        self.shortcuts = shortcuts or []
        self.checkable = checkable
        self.checked = checked
        self.group = group
        self.settings = settings
        self.enabled = enabled
        self.menu_item = menu_item
        self.menu_id = menu_id
        self.qaction = None
        self.kb_settings = KeyboardSettings()
        settings_events.restore_keyboard_defaults.connect(
            self.on_restore_defaults)

    @property
    def text(self):
        """Return translated text (already translated at creation time)."""
        return self._text

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return self.id

    def on_restore_defaults(self):
        if self.qaction:
            self.qaction.setShortcuts(self.get_shortcuts())

    @cached_property
    def menu_path(self):
        path = []

        def _get_path(menu_item):
            if isinstance(menu_item['items'], list):
                # This is a normal menu
                for item in menu_item['items']:
                    if item == self.id:
                        path.append(menu_item['menu'])
                        return True
                    if isinstance(item, dict):
                        # This is a submenu
                        if _get_path(item):
                            path.append(menu_item['menu'])
                            return True
            elif menu_item['items'] == self.menu_id:
                # This is a dynamic submenu (e.g. Recent Files)
                path.append(menu_item['menu'])
                return True

        for menu_item in get_menu_structure():
            _get_path(menu_item)

        return path[::-1]

    def get_shortcuts(self):
        return self.kb_settings.get_list(
            self.SETTINGS_GROUP, self.id, self.shortcuts)

    def set_shortcuts(self, value):
        logger.debug(f'Setting shortcut "{self.id}" to: {value}')
        self.kb_settings.set_list(
            self.SETTINGS_GROUP, self.id, value, self.shortcuts)
        if self.qaction:
            self.qaction.setShortcuts(value)

    def get_qkeysequence(self, index):
        """Current shortcuts as QKeySequence"""
        try:
            return QtGui.QKeySequence(self.get_shortcuts()[index])
        except IndexError:
            return QtGui.QKeySequence()

    def shortcuts_changed(self):
        """Whether shortcuts have changed from their defaults."""
        return self.get_shortcuts() != self.shortcuts

    def get_default_shortcut(self, index):
        try:
            return self.shortcuts[index]
        except IndexError:
            return None


class ActionsRegistry(QObject):
    """Actions를 생성하고 관리하는 싱글톤 QObject.

    pylupdate6 호환성을 위해 self.tr()을 사용합니다.
    QApplication 생성 이후에 초기화되어야 합니다.
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_actions(self):
        """번역된 텍스트로 모든 Action을 생성합니다."""
        return ActionList([
            Action(
                id='open',
                text=self.tr('&Open'),
                shortcuts=['Ctrl+O'],
                callback='on_action_open',
            ),
            Action(
                id='save',
                text=self.tr('&Save'),
                shortcuts=['Ctrl+S'],
                callback='on_action_save',
                group='active_when_items_in_scene',
            ),
            Action(
                id='save_as',
                text=self.tr('Save &As...'),
                shortcuts=['Ctrl+Shift+S'],
                callback='on_action_save_as',
                group='active_when_items_in_scene',
            ),
            Action(
                id='export_scene',
                text=self.tr('E&xport Scene...'),
                shortcuts=['Ctrl+Shift+E'],
                callback='on_action_export_scene',
                group='active_when_items_in_scene',
            ),
            Action(
                id='export_images',
                text=self.tr('Export &Images...'),
                callback='on_action_export_images',
                group='active_when_items_in_scene',
            ),
            Action(
                id='quit',
                text=self.tr('&Quit'),
                shortcuts=['Ctrl+Q'],
                callback='on_action_quit',
            ),
            Action(
                id='insert_images',
                text=self.tr('&Images...'),
                shortcuts=['Ctrl+I'],
                callback='on_action_insert_images',
            ),
            Action(
                id='insert_text',
                text=self.tr('&Text'),
                shortcuts=['Ctrl+T'],
                callback='on_action_insert_text',
            ),
            Action(
                id='undo',
                text=self.tr('&Undo'),
                shortcuts=['Ctrl+Z'],
                callback='on_action_undo',
                group='active_when_can_undo',
            ),
            Action(
                id='redo',
                text=self.tr('&Redo'),
                shortcuts=['Ctrl+Shift+Z'],
                callback='on_action_redo',
                group='active_when_can_redo',
            ),
            Action(
                id='copy',
                text=self.tr('&Copy'),
                shortcuts=['Ctrl+C'],
                callback='on_action_copy',
                group='active_when_selection',
            ),
            Action(
                id='cut',
                text=self.tr('Cu&t'),
                shortcuts=['Ctrl+X'],
                callback='on_action_cut',
                group='active_when_selection',
            ),
            Action(
                id='paste',
                text=self.tr('&Paste'),
                shortcuts=['Ctrl+V'],
                callback='on_action_paste',
            ),
            Action(
                id='delete',
                text=self.tr('&Delete'),
                shortcuts=['Del'],
                callback='on_action_delete_items',
                group='active_when_selection',
            ),
            Action(
                id='raise_to_top',
                text=self.tr('&Raise to Top'),
                shortcuts=['PgUp'],
                callback='on_action_raise_to_top',
                group='active_when_selection',
            ),
            Action(
                id='lower_to_bottom',
                text=self.tr('Lower to Bottom'),
                shortcuts=['PgDown'],
                callback='on_action_lower_to_bottom',
                group='active_when_selection',
            ),
            Action(
                id='normalize_height',
                text=self.tr('&Height'),
                shortcuts=['Shift+H'],
                callback='on_action_normalize_height',
                group='active_when_selection',
            ),
            Action(
                id='normalize_width',
                text=self.tr('&Width'),
                shortcuts=['Shift+W'],
                callback='on_action_normalize_width',
                group='active_when_selection',
            ),
            Action(
                id='normalize_size',
                text=self.tr('&Size'),
                shortcuts=['Shift+S'],
                callback='on_action_normalize_size',
                group='active_when_selection',
            ),
            Action(
                id='arrange_optimal',
                text=self.tr('&Optimal'),
                shortcuts=['Shift+O'],
                callback='on_action_arrange_optimal',
                group='active_when_selection',
            ),
            Action(
                id='arrange_horizontal',
                text=self.tr('&Horizontal (by filename)'),
                callback='on_action_arrange_horizontal',
                group='active_when_selection',
            ),
            Action(
                id='arrange_vertical',
                text=self.tr('&Vertical (by filename)'),
                callback='on_action_arrange_vertical',
                group='active_when_selection',
            ),
            Action(
                id='arrange_square',
                text=self.tr('&Square (by filename)'),
                callback='on_action_arrange_square',
                group='active_when_selection',
            ),
            Action(
                id='change_opacity',
                text=self.tr('Change &Opacity...'),
                callback='on_action_change_opacity',
                group='active_when_selection',
            ),
            Action(
                id='grayscale',
                text=self.tr('&Grayscale'),
                shortcuts=['G'],
                checkable=True,
                callback='on_action_grayscale',
                group='active_when_selection',
            ),
            Action(
                id='show_color_gamut',
                text=self.tr('Show &Color Gamut'),
                callback='on_action_show_color_gamut',
                group='active_when_single_image',
            ),
            Action(
                id='sample_color',
                text=self.tr('Sample Color'),
                shortcuts=['S'],
                callback='on_action_sample_color',
                group='active_when_items_in_scene',
            ),
            Action(
                id='crop',
                text=self.tr('&Crop'),
                shortcuts=['Shift+C'],
                callback='on_action_crop',
                group='active_when_single_image',
            ),
            Action(
                id='flip_horizontally',
                text=self.tr('Flip &Horizontally'),
                shortcuts=['H'],
                callback='on_action_flip_horizontally',
                group='active_when_selection',
            ),
            Action(
                id='flip_vertically',
                text=self.tr('Flip &Vertically'),
                shortcuts=['V'],
                callback='on_action_flip_vertically',
                group='active_when_selection',
            ),
            Action(
                id='new_scene',
                text=self.tr('&New Scene'),
                shortcuts=['Ctrl+N'],
                callback='on_action_new_scene',
            ),
            Action(
                id='fit_scene',
                text=self.tr('&Fit Scene'),
                shortcuts=['1'],
                callback='on_action_fit_scene',
            ),
            Action(
                id='fit_selection',
                text=self.tr('Fit &Selection'),
                shortcuts=['2'],
                callback='on_action_fit_selection',
                group='active_when_selection',
            ),
            Action(
                id='reset_scale',
                text=self.tr('Reset &Scale'),
                callback='on_action_reset_scale',
                group='active_when_selection',
            ),
            Action(
                id='reset_rotation',
                text=self.tr('Reset &Rotation'),
                callback='on_action_reset_rotation',
                group='active_when_selection',
            ),
            Action(
                id='reset_flip',
                text=self.tr('Reset &Flip'),
                callback='on_action_reset_flip',
                group='active_when_selection',
            ),
            Action(
                id='reset_crop',
                text=self.tr('Reset Cro&p'),
                callback='on_action_reset_crop',
                group='active_when_selection',
            ),
            Action(
                id='reset_transforms',
                text=self.tr('Reset &All'),
                shortcuts=['R'],
                callback='on_action_reset_transforms',
                group='active_when_selection',
            ),
            Action(
                id='select_all',
                text=self.tr('&Select All'),
                shortcuts=['Ctrl+A'],
                callback='on_action_select_all',
            ),
            Action(
                id='deselect_all',
                text=self.tr('Deselect &All'),
                shortcuts=['Ctrl+Shift+A'],
                callback='on_action_deselect_all',
            ),
            Action(
                id='help',
                text=self.tr('&Help'),
                shortcuts=['F1', 'Ctrl+H'],
                callback='on_action_help',
            ),
            Action(
                id='about',
                text=self.tr('&About'),
                callback='on_action_about',
            ),
            Action(
                id='debuglog',
                text=self.tr('Show &Debug Log'),
                callback='on_action_debuglog',
            ),
            Action(
                id='show_scrollbars',
                text=self.tr('Show &Scrollbars'),
                checkable=True,
                settings='View/show_scrollbars',
                callback='on_action_show_scrollbars',
            ),
            Action(
                id='show_menubar',
                text=self.tr('Show &Menu Bar'),
                checkable=True,
                settings='View/show_menubar',
                callback='on_action_show_menubar',
            ),
            Action(
                id='show_titlebar',
                text=self.tr('Show &Title Bar'),
                checkable=True,
                checked=True,
                callback='on_action_show_titlebar',
            ),
            Action(
                id='move_window',
                text=self.tr('Move &Window'),
                shortcuts=['Ctrl+M'],
                callback='on_action_move_window',
            ),
            Action(
                id='fullscreen',
                text=self.tr('&Fullscreen'),
                shortcuts=['F11'],
                checkable=True,
                callback='on_action_fullscreen',
            ),
            Action(
                id='always_on_top',
                text=self.tr('&Always On Top'),
                checkable=True,
                callback='on_action_always_on_top',
            ),
            Action(
                id='settings',
                text=self.tr('&Settings'),
                callback='on_action_settings',
            ),
            Action(
                id='keyboard_settings',
                text=self.tr('&Keyboard && Mouse'),
                callback='on_action_keyboard_settings',
            ),
            Action(
                id='open_settings_dir',
                text=self.tr('&Open Settings Folder'),
                callback='on_action_open_settings_dir',
            ),
            Action(
                id='draw_mode',
                text=self.tr('&Draw'),
                shortcuts=['D'],
                callback='on_action_draw_mode',
            ),
            Action(
                id='set_brush_color',
                text=self.tr('Brush &Color...'),
                callback='on_action_set_brush_color',
            ),
            Action(
                id='set_brush_size',
                text=self.tr('Brush &Size...'),
                callback='on_action_set_brush_size',
            ),
        ])


# Lazy accessor for backward compatibility
_actions = None


def get_actions():
    """Get the actions list, creating it if necessary.

    This function should be called after QApplication is created.
    """
    global _actions
    if _actions is None:
        _actions = ActionsRegistry.instance().create_actions()
    return _actions


# Backward compatibility alias (deprecated)
actions = None  # Will be initialized on first access via get_actions()
