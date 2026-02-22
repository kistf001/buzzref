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

from functools import partial
import logging
import os
import os.path
import sys
import time

from PyQt6 import QtCore, QtGui, QtWidgets, sip
from PyQt6.QtCore import Qt

from beeref.actions import ActionsMixin, get_actions
from beeref import commands
from beeref.config import CommandlineArgs, BeeSettings, KeyboardSettings
from beeref import constants
from beeref import fileio
from beeref.fileio.errors import IMG_LOADING_ERROR_MSG
from beeref.fileio.export import exporter_registry, ImagesToDirectoryExporter
from beeref import widgets
from beeref.items import BeePixmapItem, BeeTextItem, BeePathItem
from beeref.main_controls import MainControlsMixin
from beeref.scene import BeeGraphicsScene
from beeref.selection import RubberbandItem
from beeref.utils import get_file_extension_from_format, qcolor_to_hex


commandline_args = CommandlineArgs()
logger = logging.getLogger(__name__)


def is_wayland():
    """Check if running on Wayland display server."""
    return os.environ.get('XDG_SESSION_TYPE') == 'wayland'


class BeeGraphicsView(MainControlsMixin,
                      QtWidgets.QGraphicsView,
                      ActionsMixin):

    PAN_MODE = 1
    ZOOM_MODE = 2
    SAMPLE_COLOR_MODE = 3
    DRAW_MODE = 4
    CAPTURE_MODE = 5

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.settings = BeeSettings()
        self.keyboard_settings = KeyboardSettings()
        self.welcome_overlay = widgets.welcome_overlay.WelcomeOverlay(self)

        self.setBackgroundBrush(
            QtGui.QBrush(QtGui.QColor(*constants.COLORS['Scene:Canvas'])))
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self.undo_stack = QtGui.QUndoStack(self)
        self.undo_stack.setUndoLimit(100)
        self.undo_stack.canRedoChanged.connect(self.on_can_redo_changed)
        self.undo_stack.canUndoChanged.connect(self.on_can_undo_changed)
        self.undo_stack.cleanChanged.connect(self.on_undo_clean_changed)

        self.filename = None
        self.previous_transform = None
        self.active_mode = None
        self.draw_item = None
        self.draw_current_stroke = None
        self.draw_brush_size = 20.0
        self.draw_brush_color = [200, 200, 200, 255]
        self._tablet_pressure = 1.0
        self._suppress_context_menu = False
        self.capture_start_pos = None
        self.capture_rubberband = None

        self.scene = BeeGraphicsScene(self.undo_stack)
        self.scene.changed.connect(self.on_scene_changed)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.scene.cursor_changed.connect(self.on_cursor_changed)
        self.scene.cursor_cleared.connect(self.on_cursor_cleared)
        self.setScene(self.scene)

        # Context menu and actions
        self.build_menu_and_actions()
        self.control_target = self
        self.init_main_controls(main_window=parent)

        # Check screen capture availability
        self.update_screen_capture_action_state()

        # Load files given via command line
        if commandline_args.filenames:
            fn = commandline_args.filenames[0]
            if os.path.splitext(fn)[1] == '.bee':
                self.open_from_file(fn)
            else:
                self.do_insert_images(commandline_args.filenames)

        self.update_window_title()

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self.update_window_title()
        if value:
            self.settings.update_recent_files(value)
            self.update_menu_and_actions()

    def cancel_active_modes(self):
        self.scene.cancel_active_modes()
        self.cancel_sample_color_mode()
        self.cancel_capture_mode()
        if self.active_mode == self.DRAW_MODE:
            self.exit_draw_mode(commit=True)
        self.active_mode = None

    def cancel_sample_color_mode(self):
        logger.debug('Cancel sample color mode')
        self.active_mode = None
        self.viewport().unsetCursor()
        if hasattr(self, 'sample_color_widget'):
            self.sample_color_widget.hide()
            del self.sample_color_widget
        if self.scene.has_multi_selection():
            self.scene.multi_select_item.bring_to_front()

    def cancel_capture_mode(self):
        """Cancel capture area mode."""
        if self.active_mode != self.CAPTURE_MODE:
            return
        logger.debug('Cancel capture mode')
        self.active_mode = None
        self.viewport().unsetCursor()
        self.capture_start_pos = None
        if self.capture_rubberband and self.capture_rubberband.scene():
            self.scene.removeItem(self.capture_rubberband)
        self.capture_rubberband = None

    def update_window_title(self):
        clean = self.undo_stack.isClean()
        if clean and not self.filename:
            title = constants.APPNAME
        else:
            name = os.path.basename(self.filename or '[Untitled]')
            clean = '' if clean else '*'
            title = f'{name}{clean} - {constants.APPNAME}'
        self.parent.setWindowTitle(title)

    def on_scene_changed(self, region):
        if sip.isdeleted(self.scene):
            return
        if not self.scene.items():
            logger.debug('No items in scene')
            self.setTransform(QtGui.QTransform())
            self.welcome_overlay.setFocus()
            self.clearFocus()
            self.welcome_overlay.show()
            self.actiongroup_set_enabled('active_when_items_in_scene', False)
        else:
            self.setFocus()
            self.welcome_overlay.clearFocus()
            self.welcome_overlay.hide()
            self.actiongroup_set_enabled('active_when_items_in_scene', True)
        self.recalc_scene_rect()

    def on_can_redo_changed(self, can_redo):
        self.actiongroup_set_enabled('active_when_can_redo', can_redo)

    def on_can_undo_changed(self, can_undo):
        self.actiongroup_set_enabled('active_when_can_undo', can_undo)

    def on_undo_clean_changed(self, clean):
        self.update_window_title()

    def on_context_menu(self, point):
        if self._suppress_context_menu:
            self._suppress_context_menu = False
            return
        self.context_menu.exec(self.mapToGlobal(point))

    def get_supported_image_formats(self, cls):
        formats = []

        for f in cls.supportedImageFormats():
            string = f'*.{f.data().decode()}'
            formats.extend((string, string.upper()))
        return ' '.join(formats)

    def get_view_center(self):
        return QtCore.QPoint(round(self.size().width() / 2),
                             round(self.size().height() / 2))

    def clear_scene(self):
        logging.debug('Clearing scene...')
        self.cancel_active_modes()
        self.scene.clear()
        self.undo_stack.clear()
        self.filename = None
        self.setTransform(QtGui.QTransform())

    def reset_previous_transform(self, toggle_item=None):
        if (self.previous_transform
                and self.previous_transform['toggle_item'] != toggle_item):
            self.previous_transform = None

    def fit_rect(self, rect, toggle_item=None):
        if toggle_item and self.previous_transform:
            logger.debug('Fit view: Reset to previous')
            self.setTransform(self.previous_transform['transform'])
            self.centerOn(self.previous_transform['center'])
            self.previous_transform = None
            return
        if toggle_item:
            self.previous_transform = {
                'toggle_item': toggle_item,
                'transform': QtGui.QTransform(self.transform()),
                'center': self.mapToScene(self.get_view_center()),
            }
        else:
            self.previous_transform = None

        logger.debug(f'Fit view: {rect}')
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.recalc_scene_rect()
        # It seems to be more reliable when we fit a second time
        # Sometimes a changing scene rect can mess up the fitting
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        logger.trace('Fit view done')

    def get_confirmation_unsaved_changes(self, msg):
        confirm = self.settings.valueOrDefault('Save/confirm_close_unsaved')
        if confirm and not self.undo_stack.isClean():
            answer = QtWidgets.QMessageBox.question(
                self,
                self.tr('Discard unsaved changes?'),
                msg,
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.Cancel)
            return answer == QtWidgets.QMessageBox.StandardButton.Yes

        return True

    def on_action_new_scene(self):
        confirm = self.get_confirmation_unsaved_changes(
            self.tr('There are unsaved changes. '
                    'Are you sure you want to open a new scene?'))
        if confirm:
            self.clear_scene()

    def on_action_fit_scene(self):
        self.fit_rect(self.scene.itemsBoundingRect())

    def on_action_fit_selection(self):
        self.fit_rect(self.scene.itemsBoundingRect(selection_only=True))

    def on_action_fullscreen(self, checked):
        if checked:
            self.parent.showFullScreen()
        else:
            self.parent.showNormal()

    def on_action_always_on_top(self, checked):
        self.parent.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, on=checked)
        self.parent.destroy()
        self.parent.create()
        self.parent.show()

    def on_action_show_scrollbars(self, checked):
        if checked:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def on_action_show_menubar(self, checked):
        if checked:
            self.parent.setMenuBar(self.create_menubar())
        else:
            self.parent.setMenuBar(None)

    def on_action_show_titlebar(self, checked):
        self.parent.setWindowFlag(
            Qt.WindowType.FramelessWindowHint, on=not checked)
        self.parent.destroy()
        self.parent.create()
        self.parent.show()

    def on_action_move_window(self):
        if self.welcome_overlay.isHidden():
            self.on_action_movewin_mode()
        else:
            self.welcome_overlay.on_action_movewin_mode()

    def on_action_undo(self):
        logger.debug('Undo: %s' % self.undo_stack.undoText())
        self.cancel_active_modes()
        self.undo_stack.undo()

    def on_action_redo(self):
        logger.debug('Redo: %s' % self.undo_stack.redoText())
        self.cancel_active_modes()
        self.undo_stack.redo()

    def on_action_select_all(self):
        self.scene.select_all_items()

    def on_action_deselect_all(self):
        self.scene.deselect_all_items()

    def on_action_delete_items(self):
        logger.debug('Deleting items...')
        self.cancel_active_modes()
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, self.scene.selectedItems(user_only=True)))

    def on_action_cut(self):
        logger.debug('Cutting items...')
        self.on_action_copy()
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, self.scene.selectedItems(user_only=True)))

    def on_action_raise_to_top(self):
        self.scene.raise_to_top()

    def on_action_lower_to_bottom(self):
        self.scene.lower_to_bottom()

    def on_action_normalize_height(self):
        self.scene.normalize_height()

    def on_action_normalize_width(self):
        self.scene.normalize_width()

    def on_action_normalize_size(self):
        self.scene.normalize_size()

    def on_action_arrange_horizontal(self):
        self.scene.arrange()

    def on_action_arrange_vertical(self):
        self.scene.arrange(vertical=True)

    def on_action_arrange_optimal(self):
        self.scene.arrange_optimal()

    def on_action_arrange_square(self):
        self.scene.arrange_square()

    def on_action_change_opacity(self):
        images = list(filter(
            lambda item: item.is_image,
            self.scene.selectedItems(user_only=True)))
        widgets.ChangeOpacityDialog(self, images, self.undo_stack)

    def on_action_grayscale(self, checked):
        images = list(filter(
            lambda item: item.is_image,
            self.scene.selectedItems(user_only=True)))
        if images:
            self.undo_stack.push(
                commands.ToggleGrayscale(images, checked))

    def on_action_crop(self):
        self.scene.crop_items()

    def on_action_flip_horizontally(self):
        self.scene.flip_items(vertical=False)

    def on_action_flip_vertically(self):
        self.scene.flip_items(vertical=True)

    def on_action_reset_scale(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetScale(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_rotation(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetRotation(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_flip(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetFlip(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_crop(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetCrop(
            self.scene.selectedItems(user_only=True)))

    def on_action_reset_transforms(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetTransforms(
            self.scene.selectedItems(user_only=True)))

    def on_action_show_color_gamut(self):
        widgets.color_gamut.GamutDialog(self, self.scene.selectedItems()[0])

    def on_action_sample_color(self):
        self.cancel_active_modes()
        logger.debug('Entering sample color mode')
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.active_mode = self.SAMPLE_COLOR_MODE

        if self.scene.has_multi_selection():
            # We don't want to sample the multi select item, so
            # temporarily send it to the back:
            self.scene.multi_select_item.lower_behind_selection()

        pos = self.mapFromGlobal(self.cursor().pos())
        self.sample_color_widget = widgets.SampleColorWidget(
            self,
            pos,
            self.scene.sample_color_at(self.mapToScene(pos)))

    def on_action_capture(self):
        """Show capture choice dialog (menu callback)."""
        self.cancel_active_modes()
        self._show_capture_choice_dialog()

    def _show_capture_choice_dialog(self):
        """Show modal dialog to choose capture type."""
        msgbox = QtWidgets.QMessageBox(self)
        msgbox.setWindowTitle(self.tr('Capture'))
        msgbox.setText(self.tr('Select capture type:'))

        scene_btn = msgbox.addButton(
            self.tr('Scene Area'),
            QtWidgets.QMessageBox.ButtonRole.ActionRole)
        screen_btn = msgbox.addButton(
            self.tr('Screen'),
            QtWidgets.QMessageBox.ButtonRole.ActionRole)

        msgbox.exec()

        if msgbox.clickedButton() == scene_btn:
            logger.debug('User chose scene capture')
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            self.active_mode = self.CAPTURE_MODE
        elif msgbox.clickedButton() == screen_btn:
            logger.debug('User chose screen capture')
            self._start_screen_capture()

    def on_action_capture_area(self):
        """Start capture - scene or screen based on mouse position."""
        self.cancel_active_modes()

        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        scene_pos = self.mapToScene(cursor_pos)
        items_rect = self.scene.itemsBoundingRect()

        if items_rect.isEmpty() or not items_rect.contains(scene_pos):
            # Mouse outside scene items → screen capture
            logger.debug('Mouse outside scene area - starting screen capture')
            self._start_screen_capture()
        else:
            # Mouse inside scene items → scene capture
            logger.debug('Mouse inside scene area - starting scene capture')
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            self.active_mode = self.CAPTURE_MODE

    def do_capture_area(self):
        """Capture the selected area and add it as a new image item."""
        if not self.capture_rubberband:
            return

        rect = self.capture_rubberband.sceneBoundingRect()
        if rect.width() < 5 or rect.height() < 5:
            logger.debug('Capture area too small, skipping')
            return

        # Remove rubberband temporarily so it won't be rendered
        self.scene.removeItem(self.capture_rubberband)

        # Deselect items so selection handles won't be rendered
        selected_items = self.scene.selectedItems(user_only=True)
        for item in selected_items:
            item.setSelected(False)

        # Render the scene area to QImage
        size = QtCore.QSize(int(rect.width()), int(rect.height()))
        image = QtGui.QImage(size, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtGui.QColor(0, 0, 0, 0))  # Transparent background

        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        self.scene.render(painter, source=rect)
        painter.end()

        # Create new BeePixmapItem and add to scene
        item = BeePixmapItem(image)
        self.undo_stack.push(commands.InsertItems(self.scene, [item], rect.center()))

        # Restore selection
        for sel_item in selected_items:
            sel_item.setSelected(True)

        logger.debug('Area captured and added as new image')

    def check_screen_capture_available(self):
        """Check if screen capture is available on this platform."""
        if sys.platform == 'linux' and is_wayland():
            # Wayland: Check if Portal is available
            try:
                from PyQt6 import QtDBus
                bus = QtDBus.QDBusConnection.sessionBus()
                reply = bus.interface().isServiceRegistered(
                    'org.freedesktop.portal.Desktop')
                return reply.value() if reply.isValid() else False
            except (ImportError, AttributeError):
                logger.debug('QtDBus not available')
                return False
        else:
            # Windows/macOS/X11: Test grabWindow
            screen = QtWidgets.QApplication.primaryScreen()
            if not screen:
                return False
            pixmap = screen.grabWindow(0, 0, 0, 10, 10)
            return not pixmap.isNull() and pixmap.width() > 0

    def update_screen_capture_action_state(self):
        """Update the screen capture action enabled state."""
        enabled = self.check_screen_capture_available()
        self.actiongroup_set_enabled('screen_capture_available', enabled)
        logger.debug(f'Screen capture available: {enabled}')

    def _start_screen_capture(self):
        """Start screen capture - platform specific."""
        if not self.check_screen_capture_available():
            logger.warning('Screen capture not available')
            return

        logger.debug('Starting screen capture')

        if sys.platform == 'linux' and is_wayland():
            # Wayland: Portal handles UI, no need to hide window
            self._capture_screen_wayland()
        else:
            # Windows/macOS/X11: Hide window, grabWindow, then overlay
            self.parent.hide()
            QtWidgets.QApplication.processEvents()
            QtCore.QTimer.singleShot(100, self._capture_screen_grab)

    def _capture_screen_grab(self):
        """Capture screen using grabWindow (Windows/macOS/X11)."""
        screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            logger.error('No primary screen found')
            self._on_screen_capture_canceled()
            return

        screenshot = screen.grabWindow(0)
        if screenshot.isNull():
            logger.error('Failed to capture screen')
            self._on_screen_capture_canceled()
            return

        logger.debug(f'Screen captured: {screenshot.width()}x{screenshot.height()}')
        self._show_screen_capture_overlay(screenshot)

    def _capture_screen_wayland(self):
        """Capture screen using XDG Desktop Portal (Wayland)."""
        try:
            from PyQt6 import QtDBus
        except ImportError:
            logger.error('QtDBus not available for Wayland screen capture')
            self._on_screen_capture_canceled()
            return

        bus = QtDBus.QDBusConnection.sessionBus()
        if not bus.isConnected():
            logger.error('D-Bus session bus not connected')
            self._on_screen_capture_canceled()
            return

        # Generate unique token
        base = bus.baseService()[1:].replace('.', '_')
        token = f'beeref_{int(time.time())}'
        response_path = f'/org/freedesktop/portal/desktop/request/{base}/{token}'

        # Create runtime handler with proper QDBusMessage slot
        # This must be defined inside the method to use QtDBus.QDBusMessage type
        class _PortalHandler(QtCore.QObject):
            def __init__(self, view):
                super().__init__(view)
                self._view = view

            @QtCore.pyqtSlot(QtDBus.QDBusMessage)
            def on_response(self, message):
                self._view._handle_portal_response(message)

        # Keep handler alive
        self._portal_handler = _PortalHandler(self)

        # Connect to Response signal
        connected = bus.connect(
            'org.freedesktop.portal.Desktop',
            response_path,
            'org.freedesktop.portal.Request',
            'Response',
            self._portal_handler.on_response
        )
        logger.debug(f'Portal Response signal connected: {connected}')

        # Call Screenshot method
        interface = QtDBus.QDBusInterface(
            'org.freedesktop.portal.Desktop',
            '/org/freedesktop/portal/desktop',
            'org.freedesktop.portal.Screenshot',
            bus
        )

        # Options: interactive=True for Portal UI (region selection)
        options = {'handle_token': token, 'interactive': True}
        msg = interface.call('Screenshot', '', options)

        if msg.type() == QtDBus.QDBusMessage.MessageType.ErrorMessage:
            logger.error(f'Portal Screenshot call failed: {msg.errorMessage()}')
            self._on_screen_capture_canceled()

    def _handle_portal_response(self, message):
        """Handle Portal Screenshot response from QDBusMessage.

        Portal Response signature: (ua{sv})
            - u: uint32 - 0 for success, 1 for user cancelled, 2 for error
            - a{sv}: dict - contains 'uri' key with file:// path to screenshot
        """
        args = message.arguments()
        logger.debug(f'Portal response received: {args}')

        if len(args) < 2:
            logger.error(f'Invalid portal response: {args}')
            return

        response = args[0]
        results = args[1]

        if response != 0:
            logger.debug(f'Portal screenshot canceled or failed: {response}')
            return

        uri = results.get('uri', '')
        if not uri:
            logger.error('No URI in portal response')
            return

        # Convert file:// URI to local path
        path = QtCore.QUrl(uri).toLocalFile()
        pixmap = QtGui.QPixmap(path)

        # Delete temporary file
        try:
            os.remove(path)
        except OSError:
            pass

        if pixmap.isNull():
            logger.error('Failed to load screenshot from portal')
            return

        logger.debug(f'Portal screenshot loaded: {pixmap.width()}x{pixmap.height()}')

        # Add directly to scene (Portal handled region selection)
        item = BeePixmapItem(pixmap.toImage())
        pos = self.mapToScene(self.get_view_center())
        self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))

        logger.debug('Screen area captured')

    def _show_screen_capture_overlay(self, pixmap):
        """Show the screen capture overlay for region selection."""
        self.screen_capture_overlay = widgets.screen_capture.ScreenCaptureOverlay(
            pixmap)
        self.screen_capture_overlay.captured.connect(self._on_screen_captured)
        self.screen_capture_overlay.canceled.connect(
            self._on_screen_capture_canceled)
        self.screen_capture_overlay.show()

    def _on_screen_captured(self, pixmap):
        """Handle successful screen capture."""
        # Show main window
        self.parent.show()
        self.parent.activateWindow()

        # Add to scene
        item = BeePixmapItem(pixmap.toImage())
        pos = self.mapToScene(self.get_view_center())
        self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))

        logger.debug('Screen area captured')

    def _on_screen_capture_canceled(self):
        """Handle screen capture cancellation."""
        self.parent.show()
        self.parent.activateWindow()
        logger.debug('Screen capture canceled')

    def on_action_draw_mode(self):
        if self.active_mode == self.DRAW_MODE:
            self.exit_draw_mode(commit=True)
        else:
            self.enter_draw_mode()

    def enter_draw_mode(self):
        self.cancel_active_modes()
        self.scene.deselect_all_items()
        self.active_mode = self.DRAW_MODE
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.welcome_overlay.hide()
        logger.debug('Entered draw mode')

    def exit_draw_mode(self, commit=True):
        logger.debug(f'Exiting draw mode, commit={commit}')
        if self.draw_item:
            if self.draw_current_stroke:
                self.draw_item.add_stroke(self.draw_current_stroke)
                self.draw_item.temp_stroke = None
                self.draw_current_stroke = None
            if commit and self.draw_item.strokes:
                self.scene.removeItem(self.draw_item)
                self.undo_stack.push(
                    commands.InsertItems(
                        self.scene, [self.draw_item]))
            else:
                self.scene.removeItem(self.draw_item)
            self.draw_item = None
        self.active_mode = None
        self.viewport().unsetCursor()

    def on_action_set_brush_color(self):
        current = QtGui.QColor(*self.draw_brush_color)
        color = QtWidgets.QColorDialog.getColor(
            current, self, self.tr('Select Brush Color'),
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.draw_brush_color = [
                color.red(), color.green(), color.blue(), color.alpha()]

    def on_action_set_brush_size(self):
        size, ok = QtWidgets.QInputDialog.getInt(
            self, self.tr('Brush Size'), self.tr('Size (px):'),
            int(self.draw_brush_size), 1, 500)
        if ok:
            self.draw_brush_size = float(size)

    def on_items_loaded(self, value):
        logger.debug('On items loaded: add queued items')
        self.scene.add_queued_items()

    def on_loading_finished(self, filename, errors):
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('Problem loading file'),
                self.tr('<p>Problem loading file %s</p>'
                        '<p>Not accessible or not a proper bee file</p>') % filename)
        else:
            self.filename = filename
            self.scene.add_queued_items()
            self.on_action_fit_scene()

    def on_action_open_recent_file(self, filename):
        confirm = self.get_confirmation_unsaved_changes(
            self.tr('There are unsaved changes. '
                    'Are you sure you want to open a new scene?'))
        if confirm:
            self.open_from_file(filename)

    def open_from_file(self, filename):
        logger.info(f'Opening file {filename}')
        self.clear_scene()
        self.worker = fileio.ThreadedIO(
            fileio.load_bee, filename, self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(self.on_loading_finished)
        self.progress = widgets.BeeProgressDialog(
            self.tr('Loading %s') % filename,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_open(self):
        confirm = self.get_confirmation_unsaved_changes(
            self.tr('There are unsaved changes. '
                    'Are you sure you want to open a new scene?'))
        if not confirm:
            return

        self.cancel_active_modes()
        filename, f = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption=self.tr('Open file'),
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            filename = os.path.normpath(filename)
            self.open_from_file(filename)
            self.filename = filename

    def on_saving_finished(self, filename, errors):
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('Problem saving file'),
                self.tr('<p>Problem saving file %s</p>'
                        '<p>File/directory not accessible</p>') % filename)
        else:
            self.filename = filename
            self.undo_stack.setClean()

    def do_save(self, filename, create_new):
        if not fileio.is_bee_file(filename):
            filename = f'{filename}.bee'
        self.worker = fileio.ThreadedIO(
            fileio.save_bee, filename, self.scene, create_new=create_new)
        self.worker.finished.connect(self.on_saving_finished)
        self.progress = widgets.BeeProgressDialog(
            self.tr('Saving %s') % filename,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_save_as(self):
        self.cancel_active_modes()
        directory = os.path.dirname(self.filename) if self.filename else None
        filename, f = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption=self.tr('Save file'),
            directory=directory,
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            self.do_save(filename, create_new=True)

    def on_action_save(self):
        self.cancel_active_modes()
        if not self.filename:
            self.on_action_save_as()
        else:
            self.do_save(self.filename, create_new=False)

    def on_action_export_scene(self):
        directory = os.path.dirname(self.filename) if self.filename else None
        filename, formatstr = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption=self.tr('Export Scene to Image'),
            directory=directory,
            filter=';;'.join(('Image Files (*.png *.jpg *.jpeg *.svg)',
                              'PNG (*.png)',
                              'JPEG (*.jpg *.jpeg)',
                              'SVG (*.svg)')))

        if not filename:
            return

        name, ext = os.path.splitext(filename)
        if not ext:
            ext = get_file_extension_from_format(formatstr)
            filename = f'{filename}.{ext}'
        logger.debug(f'Got export filename {filename}')

        exporter_cls = exporter_registry[ext]
        exporter = exporter_cls(self.scene)
        if not exporter.get_user_input(self):
            return

        self.worker = fileio.ThreadedIO(exporter.export, filename)
        self.worker.finished.connect(self.on_export_finished)
        self.progress = widgets.BeeProgressDialog(
            self.tr('Exporting %s') % filename,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_export_finished(self, filename, errors):
        if errors:
            err_msg = '</br>'.join(str(errors))
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('Problem writing file'),
                self.tr('<p>Problem writing file %s</p>') % filename
                + f'<p>{err_msg}</p>')

    def on_action_export_images(self):
        directory = os.path.dirname(self.filename) if self.filename else None
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption=self.tr('Export Images'),
            directory=directory)

        if not directory:
            return

        logger.debug(f'Got export directory {directory}')
        self.exporter = ImagesToDirectoryExporter(self.scene, directory)
        self.worker = fileio.ThreadedIO(self.exporter.export)
        self.worker.user_input_required.connect(
            self.on_export_images_file_exists)
        self.worker.finished.connect(self.on_export_finished)
        self.progress = widgets.BeeProgressDialog(
            self.tr('Exporting to %s') % directory,
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_export_images_file_exists(self, filename):
        dlg = widgets.ExportImagesFileExistsDialog(self, filename)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.exporter.handle_existing = dlg.get_answer()
            directory = self.exporter.dirname
            self.progress = widgets.BeeProgressDialog(
                self.tr('Exporting to %s') % directory,
                worker=self.worker,
                parent=self)
            self.worker.start()

    def on_action_quit(self):
        confirm = self.get_confirmation_unsaved_changes(
            self.tr('There are unsaved changes. Are you sure you want to quit?'))
        if confirm:
            logger.info('User quit. Exiting...')
            self.app.quit()

    def on_action_settings(self):
        widgets.settings.SettingsDialog(self)

    def on_action_keyboard_settings(self):
        widgets.controls.ControlsDialog(self)

    def on_action_help(self):
        widgets.HelpDialog(self)

    def on_action_about(self):
        QtWidgets.QMessageBox.about(
            self,
            self.tr('About %s') % constants.APPNAME,
            (f'<h2>{constants.APPNAME} {constants.VERSION}</h2>'
             f'<p>{constants.APPNAME_FULL}</p>'
             f'<p>{constants.COPYRIGHT}</p>'
             f'<p><a href="{constants.WEBSITE}">'
             + self.tr('Visit the %s website') % constants.APPNAME
             + '</a></p>'))

    def on_action_debuglog(self):
        widgets.DebugLogDialog(self)

    def on_insert_images_finished(self, new_scene, filename, errors):
        """Callback for when loading of images is finished.

        :param new_scene: True if the scene was empty before, else False
        :param filename: Not used, for compatibility only
        :param errors: List of filenames that couldn't be loaded
        """

        logger.debug('Insert images finished')
        if errors:
            errornames = [
                f'<li>{fn}</li>' for fn in errors]
            errornames = '<ul>%s</ul>' % '\n'.join(errornames)
            num = len(errors)
            msg = self.tr('%n image(s) could not be opened.', '', num) + '<br/>'
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('Problem loading images'),
                msg + IMG_LOADING_ERROR_MSG + errornames)
        self.scene.add_queued_items()
        self.scene.arrange_default()
        self.undo_stack.endMacro()
        if new_scene:
            self.on_action_fit_scene()

    def do_insert_images(self, filenames, pos=None):
        if not pos:
            pos = self.get_view_center()
        self.scene.deselect_all_items()
        self.undo_stack.beginMacro('Insert Images')
        self.worker = fileio.ThreadedIO(
            fileio.load_images,
            filenames,
            self.mapToScene(pos),
            self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(
            partial(self.on_insert_images_finished,
                    not self.scene.items()))
        self.progress = widgets.BeeProgressDialog(
            self.tr('Loading images'),
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_insert_images(self):
        self.cancel_active_modes()
        formats = self.get_supported_image_formats(QtGui.QImageReader)
        logger.debug(f'Supported image types for reading: {formats}')
        filenames, f = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption=self.tr('Select one or more images to open'),
            filter=f'Images ({formats})')
        self.do_insert_images(filenames)

    def on_action_insert_text(self):
        self.cancel_active_modes()
        item = BeeTextItem()
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))
        item.setScale(1 / self.get_scale())
        self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))

    def on_action_copy(self):
        logger.debug('Copying to clipboard...')
        self.cancel_active_modes()
        clipboard = QtWidgets.QApplication.clipboard()
        items = self.scene.selectedItems(user_only=True)

        # At the moment, we can only copy one image to the global
        # clipboard. (Later, we might create an image of the whole
        # selection for external copying.)
        items[0].copy_to_clipboard(clipboard)

        # However, we can copy all items to the internal clipboard:
        self.scene.copy_selection_to_internal_clipboard()

        # We set a marker for ourselves in the global clipboard so
        # that we know to look up the internal clipboard when pasting:
        clipboard.mimeData().setData(
            'beeref/items', QtCore.QByteArray.number(len(items)))

    def on_action_paste(self):
        self.cancel_active_modes()
        logger.debug('Pasting from clipboard...')
        clipboard = QtWidgets.QApplication.clipboard()
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))

        # See if we need to look up the internal clipboard:
        data = clipboard.mimeData().data('beeref/items')
        logger.debug(f'Custom data in clipboard: {data}')
        if data and self.scene.internal_clipboard:
            # Checking that internal clipboard exists since the user
            # may have opened a new scene since copying.
            self.scene.paste_from_internal_clipboard(pos)
            return

        img = clipboard.image()
        if not img.isNull():
            item = BeePixmapItem(img)
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
            if len(self.scene.items()) == 1:
                # This is the first image in the scene
                self.on_action_fit_scene()
            return
        text = clipboard.text()
        if text:
            item = BeeTextItem(text)
            item.setScale(1 / self.get_scale())
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
            return

        msg = self.tr('No image data or text in clipboard or image too big')
        logger.info(msg)
        widgets.BeeNotification(self, msg)

    def on_action_open_settings_dir(self):
        dirname = os.path.dirname(self.settings.fileName())
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(dirname))

    def on_selection_changed(self):
        if sip.isdeleted(self.scene):
            return
        logger.debug('Currently selected items: %s',
                     len(self.scene.selectedItems(user_only=True)))
        self.actiongroup_set_enabled('active_when_selection',
                                     self.scene.has_selection())
        self.actiongroup_set_enabled('active_when_single_image',
                                     self.scene.has_single_image_selection())

        if self.scene.has_selection():
            item = self.scene.selectedItems(user_only=True)[0]
            grayscale = getattr(item, 'grayscale', False)
            get_actions()['grayscale'].qaction.setChecked(grayscale)
        self.viewport().repaint()

    def on_cursor_changed(self, cursor):
        if self.active_mode is None:
            self.viewport().setCursor(cursor)

    def on_cursor_cleared(self):
        if self.active_mode is None:
            self.viewport().unsetCursor()

    def recalc_scene_rect(self):
        """Resize the scene rectangle so that it is always one view width
        wider than all items' bounding box at each side and one view
        width higher on top and bottom. This gives the impression of
        an infinite canvas."""

        if self.previous_transform:
            return
        logger.trace('Recalculating scene rectangle...')
        try:
            topleft = self.mapFromScene(
                self.scene.itemsBoundingRect().topLeft())
            topleft = self.mapToScene(QtCore.QPoint(
                topleft.x() - self.size().width(),
                topleft.y() - self.size().height()))
            bottomright = self.mapFromScene(
                self.scene.itemsBoundingRect().bottomRight())
            bottomright = self.mapToScene(QtCore.QPoint(
                bottomright.x() + self.size().width(),
                bottomright.y() + self.size().height()))
            self.setSceneRect(QtCore.QRectF(topleft, bottomright))
        except OverflowError:
            logger.info('Maximum scene size reached')
        logger.trace('Done recalculating scene rectangle')

    def get_zoom_size(self, func):
        """Calculates the size of all items' bounding box in the view's
        coordinates.

        This helps ensure that we never zoom out too much (scene
        becomes so tiny that items become invisible) or zoom in too
        much (causing overflow errors).

        :param func: Function which takes the width and height as
            arguments and turns it into a number, for ex. ``min`` or ``max``.
        """

        topleft = self.mapFromScene(
            self.scene.itemsBoundingRect().topLeft())
        bottomright = self.mapFromScene(
            self.scene.itemsBoundingRect().bottomRight())
        return func(bottomright.x() - topleft.x(),
                    bottomright.y() - topleft.y())

    def scale(self, *args, **kwargs):
        super().scale(*args, **kwargs)
        self.scene.on_view_scale_change()
        self.recalc_scene_rect()

    def get_scale(self):
        return self.transform().m11()

    def pan(self, delta):
        if not self.scene.items():
            logger.debug('No items in scene; ignore pan')
            return

        hscroll = self.horizontalScrollBar()
        hscroll.setValue(int(hscroll.value() + delta.x()))
        vscroll = self.verticalScrollBar()
        vscroll.setValue(int(vscroll.value() + delta.y()))

    def zoom(self, delta, anchor):
        if not self.scene.items():
            logger.debug('No items in scene; ignore zoom')
            return

        # We calculate where the anchor is before and after the zoom
        # and then move the view accordingly to keep the anchor fixed
        # We can't use QGraphicsView's AnchorUnderMouse since it
        # uses the current cursor position while we need the initial mouse
        # press position for zooming with Ctrl + Middle Drag
        anchor = QtCore.QPoint(round(anchor.x()),
                               round(anchor.y()))
        ref_point = self.mapToScene(anchor)
        if delta == 0:
            return
        factor = 1 + abs(delta / 1000)
        if delta > 0:
            if self.get_zoom_size(max) < 10000000:
                self.scale(factor, factor)
            else:
                logger.debug('Maximum zoom size reached')
                return
        else:
            if self.get_zoom_size(min) > 50:
                self.scale(1/factor, 1/factor)
            else:
                logger.debug('Minimum zoom size reached')
                return

        self.pan(self.mapFromScene(ref_point) - anchor)
        self.reset_previous_transform()

    def wheelEvent(self, event):
        action, inverted\
            = self.keyboard_settings.mousewheel_action_for_event(event)

        delta = event.angleDelta().y()
        if inverted:
            delta = delta * -1

        if action == 'zoom':
            self.zoom(delta, event.position())
            event.accept()
            return
        if action == 'pan_horizontal':
            self.pan(QtCore.QPointF(0, 0.5 * delta))
            event.accept()
            return
        if action == 'pan_vertical':
            self.pan(QtCore.QPointF(0.5 * delta, 0))
            event.accept()
            return

    def tabletEvent(self, event):
        if self.active_mode == self.DRAW_MODE:
            self._tablet_pressure = event.pressure()
            # Don't accept — let Qt synthesize mouse events for drawing
            event.ignore()
        else:
            super().tabletEvent(event)

    def mousePressEvent(self, event):
        if self.active_mode == self.DRAW_MODE:
            if event.button() == Qt.MouseButton.RightButton:
                self._suppress_context_menu = True
                self.exit_draw_mode(commit=True)
                event.accept()
                return
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                if not self.draw_item:
                    self.draw_item = BeePathItem()
                    self.draw_item.setPos(scene_pos)
                    self.scene.addItem(self.draw_item)
                    self.draw_item.bring_to_front()
                local_pos = self.draw_item.mapFromScene(scene_pos)
                self.draw_current_stroke = {
                    'color': list(self.draw_brush_color),
                    'base_size': self.draw_brush_size,
                    'points': [{
                        'x': round(local_pos.x(), 1),
                        'y': round(local_pos.y(), 1),
                        'pressure': self._tablet_pressure,
                    }],
                }
                self.draw_item.temp_stroke = self.draw_current_stroke
                self.draw_item.update()
                event.accept()
                return
            event.accept()
            return

        if self.mousePressEventMainControls(event):
            return

        if self.active_mode == self.SAMPLE_COLOR_MODE:
            if (event.button() == Qt.MouseButton.LeftButton):
                color = self.scene.sample_color_at(
                    self.mapToScene(event.pos()))
                if color:
                    name = qcolor_to_hex(color)
                    clipboard = QtWidgets.QApplication.clipboard()
                    clipboard.setText(name)
                    self.scene.internal_clipboard = []
                    msg = self.tr('Copied color to clipboard: %s') % name
                    logger.debug(msg)
                    widgets.BeeNotification(self, msg)
                else:
                    logger.debug('No color found')
            self.cancel_sample_color_mode()
            event.accept()
            return

        if self.active_mode == self.CAPTURE_MODE:
            if event.button() == Qt.MouseButton.LeftButton:
                self.capture_start_pos = event.pos()
                self.capture_rubberband = RubberbandItem()
                self.scene.addItem(self.capture_rubberband)
                self.capture_rubberband.bring_to_front()
                scene_pos = self.mapToScene(event.pos())
                self.capture_rubberband.fit(scene_pos, scene_pos)
                event.accept()
                return
            elif event.button() == Qt.MouseButton.RightButton:
                self._suppress_context_menu = True
                self.cancel_capture_mode()
                event.accept()
                return

        action, inverted = self.keyboard_settings.mouse_action_for_event(event)

        if action == 'zoom':
            self.active_mode = self.ZOOM_MODE
            self.event_start = event.position()
            self.event_anchor = event.position()
            self.event_inverted = inverted
            event.accept()
            return

        if action == 'pan':
            logger.trace('Begin pan')
            self.active_mode = self.PAN_MODE
            self.event_start = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            # ClosedHandCursor and OpenHandCursor don't work, but I
            # don't know if that's only on my system or a general
            # problem. It works with other cursors.
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self.active_mode == self.DRAW_MODE
                and self.draw_current_stroke is not None):
            scene_pos = self.mapToScene(event.pos())
            local_pos = self.draw_item.mapFromScene(scene_pos)
            self.draw_current_stroke['points'].append({
                'x': round(local_pos.x(), 1),
                'y': round(local_pos.y(), 1),
                'pressure': self._tablet_pressure,
            })
            self.draw_item.prepareGeometryChange()
            self.draw_item.temp_stroke = self.draw_current_stroke
            self.draw_item.update()
            event.accept()
            return

        if self.active_mode == self.PAN_MODE:
            self.reset_previous_transform()
            pos = event.position()
            self.pan(self.event_start - pos)
            self.event_start = pos
            event.accept()
            return

        if self.active_mode == self.ZOOM_MODE:
            self.reset_previous_transform()
            pos = event.position()
            delta = (self.event_start - pos).y()
            if self.event_inverted:
                delta *= -1
            self.event_start = pos
            self.zoom(delta * 20, self.event_anchor)
            event.accept()
            return

        if self.active_mode == self.SAMPLE_COLOR_MODE:
            self.sample_color_widget.update(
                event.position(),
                self.scene.sample_color_at(self.mapToScene(event.pos())))
            event.accept()
            return

        if self.active_mode == self.CAPTURE_MODE and self.capture_start_pos:
            start_scene = self.mapToScene(self.capture_start_pos)
            current_scene = self.mapToScene(event.pos())
            self.capture_rubberband.fit(start_scene, current_scene)
            event.accept()
            return

        if self.mouseMoveEventMainControls(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (self.active_mode == self.DRAW_MODE
                and self.draw_current_stroke is not None):
            self.draw_item.add_stroke(self.draw_current_stroke)
            self.draw_item.temp_stroke = None
            self.draw_current_stroke = None
            self._tablet_pressure = 1.0
            event.accept()
            return

        if self.active_mode == self.PAN_MODE:
            logger.trace('End pan')
            self.viewport().unsetCursor()
            self.active_mode = None
            event.accept()
            return
        if self.active_mode == self.ZOOM_MODE:
            self.active_mode = None
            event.accept()
            return
        if self.active_mode == self.CAPTURE_MODE:
            if self.capture_start_pos and self.capture_rubberband:
                self.do_capture_area()
            self.cancel_capture_mode()
            event.accept()
            return
        if self.mouseReleaseEventMainControls(event):
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recalc_scene_rect()
        self.welcome_overlay.resize(self.size())

    def keyPressEvent(self, event):
        if self.keyPressEventMainControls(event):
            return
        if self.active_mode == self.DRAW_MODE:
            if event.key() == Qt.Key.Key_Escape:
                self.exit_draw_mode(commit=True)
                event.accept()
                return
        if self.active_mode == self.SAMPLE_COLOR_MODE:
            self.cancel_sample_color_mode()
            event.accept()
            return
        if self.active_mode == self.CAPTURE_MODE:
            if event.key() == Qt.Key.Key_Escape:
                self.cancel_capture_mode()
                event.accept()
                return
        super().keyPressEvent(event)
