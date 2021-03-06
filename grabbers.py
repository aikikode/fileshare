import cairo
import os
import re
import tempfile
import threading
from gi.repository import GObject, Gdk, GdkPixbuf, Gtk

FILE_GRABBER_SIZE = 50
MAX_PREVIEW_WIDTH = 800
MAX_PREVIEW_HEIGHT = 600


class FileGrabber:
    """ Applet for drag'n'drop files to. The file is automatically uploaded to
        the hosting and the result URL is copied into the clipboard """

    def __init__(self, app_icon, upload_callback):
        self.upload_callback = upload_callback
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_decorated(False)
        self.window.set_opacity(0.5)
        self.window.set_size_request(FILE_GRABBER_SIZE, FILE_GRABBER_SIZE)
        self.window.set_resizable(False)
        self.window.drag_dest_set(0, [], 0)

        self.window.set_gravity(Gdk.Gravity.NORTH_EAST)
        width, height = self.window.get_size()
        self.window.move(Gdk.Screen.width() - width - 20, height)
        self.app_icon = app_icon

        # Add main widget for grabbing files
        self.image = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.app_icon)
        scaled_buf = pixbuf.scale_simple(
            FILE_GRABBER_SIZE, FILE_GRABBER_SIZE,
            GdkPixbuf.InterpType.BILINEAR
        )
        self.image.set_from_pixbuf(scaled_buf)
        self.image.show()
        self.window.add(self.image)
        self.window.connect('drag-motion', self.window_drag_motion)
        self.window.connect('drag-drop', self.window_drag_drop)
        self.window.connect(
            'drag-data-received', self.window_drag_data_received
        )
        self.isShown = False

    def set_upload_callback(self, upload_callback):
        self.upload_callback = upload_callback

    def toggle_window(self):
        if self.isShown:
            self.window.hide()
            self.isShown = False
        else:
            self.window.show()
            # This may not work: it depends on the window manager
            self.window.set_keep_above(True)
            self.isShown = True

    def window_drag_motion(self, wid, context, x, y, time):
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True  # True means "I accept this data"

    def window_drag_drop(self, wid, context, x, y, time):
        wid.drag_get_data(context, context.list_targets()[-1], time)
        return True

    def window_drag_data_received(self, wid, context, x, y, data, info, time):
        text = data.get_text() or data.get_data()
        file_to_upload = text.splitlines()[0].replace('file://', '')
        # Handle Win path
        file_to_upload = re.sub(r'/([^/]+:/)', r'\1/', file_to_upload)
        context.finish(True, False, time)
        GObject.idle_add(self.upload_callback, file_to_upload, False)


class ScreenGrabber(threading.Thread):
    def __init__(self, upload_callback, quit_callback, log):
        threading.Thread.__init__(self)
        self.upload_callback = upload_callback
        self.quit_callback = quit_callback
        self.log = log
        self.log.debug('ScreenGrabber: creating')
        self.selected = False
        self.screenWidth = width = Gdk.Screen.width()
        self.screenHeight = height = Gdk.Screen.height()
        self.drawingWindow = drawingWindow = Gtk.Window()
        drawingWindow.set_decorated(False)
        drawingWindow.set_skip_taskbar_hint(True)
        drawingWindow.set_skip_pager_hint(True)
        drawingWindow.set_can_focus(True)
        drawingWindow.set_accept_focus(True)
        drawingWindow.set_keep_above(True)
        drawingWindow.set_default_size(width, height)
        drawingWindow.resize(width, height)
        drawingWindow.move(0, 0)
        drawingWindow.set_app_paintable(True)
        drawingWindow.set_opacity(0.2)
        drawingWindow.fullscreen()
        visual = drawingWindow.get_screen().get_rgba_visual()
        if visual:
            drawingWindow.set_visual(visual)
        drawingWindow.set_app_paintable(True)
        drawingWindow.set_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.KEY_PRESS_MASK
        )
        drawingWindow.show()
        drawingWindow.present()
        drawingWindow.get_window().set_fullscreen_mode(
            Gdk.FullscreenMode.ALL_MONITORS
        )
        cursor = Gdk.Cursor(Gdk.CursorType.CROSSHAIR)
        drawingWindow.get_window().set_cursor(cursor)
        drawingWindow.connect('draw', self.initial_draw)
        drawingWindow.connect(
            'button-press-event', self.select_area_event_handler, self
        )
        drawingWindow.connect(
            'button-release-event', self.select_area_event_handler, self
        )
        drawingWindow.connect(
            'key-press-event', self.select_area_event_handler, self
        )
        drawingWindow.connect(
            'motion-notify-event', self.select_area_event_handler, self
        )

    def initial_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    def select_area_event_handler(self, widget, event, selector):
        if event.type == Gdk.EventType.MOTION_NOTIFY:
            selector.redraw(event.x, event.y)
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            selector.start_selection(event.x, event.y)
        elif event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
            selector.stop_selection(event.x, event.y)
            selector.set_complete_handler(
                self.take_screen_of_area_complete_handler
            )
            selector.__del__()
            del selector
        elif (
            (event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3)
            or (
                event.type == Gdk.EventType.KEY_PRESS
                and event.keyval == Gdk.keyval_from_name('Escape')
            )
        ):
            selector.__del__()
            del selector

    def take_screen_of_area_complete_handler(self, x, y, width, height):
        root = Gdk.get_default_root_window()
        pixbuf = Gdk.pixbuf_get_from_window(root, x, y, width, height)
        self.gtk_screen_image = pixbuf
        # Call preview window
        self.preview_screen_of_area()

    def upload_from_pixmap(self):
        (fp, temp_img_file) = tempfile.mkstemp('.png')
        os.close(fp)
        self.gtk_screen_image.savev(temp_img_file, 'png', [], [])
        GObject.idle_add(self.upload_callback, temp_img_file, True)

    def preview_screen_of_area(self):
        def response(dialog, resp_id):
            if resp_id == Gtk.ResponseType.OK:
                self.upload_from_pixmap()

        image = self.gtk_screen_image
        preview_dialog = Gtk.Dialog(
            title='Preview screenshot',
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                'Upload', Gtk.ResponseType.OK
            )
        )
        preview_dialog.set_default_response(Gtk.ResponseType.OK)
        preview_dialog.set_modal(True)
        preview_dialog.set_decorated(False)
        preview_dialog.set_resizable(False)
        # Scale image for preview
        preview_width = float(image.get_width())
        preview_height = float(image.get_height())
        if preview_width / preview_height > (
            MAX_PREVIEW_WIDTH / MAX_PREVIEW_HEIGHT
        ):
            preview_height = int(
                round((MAX_PREVIEW_WIDTH / preview_width) * preview_height)
            )
            preview_width = MAX_PREVIEW_WIDTH
        else:
            preview_width = int(
                round((MAX_PREVIEW_HEIGHT / preview_height) * preview_width)
            )
            preview_height = MAX_PREVIEW_HEIGHT
        preview_image = image.scale_simple(
            preview_width, preview_height, GdkPixbuf.InterpType.BILINEAR
        )
        widget_image = Gtk.Image.new_from_pixbuf(preview_image)
        widget_image.show()
        preview_dialog.vbox.add(widget_image)
        preview_dialog.connect('response', response)
        preview_dialog.run()
        preview_dialog.destroy()

    def __del__(self):
        if hasattr(self, 'deleted'):
            return True
        ctx = self.drawingWindow.get_window().cairo_create()
        self.clear(ctx)
        # Give cairo some time to clear the screen before the destruction of
        # the window
        GObject.timeout_add(50, self.drawingWindow.destroy)
        if self.selected and hasattr(self, 'complete_handler'):
            x = int(round(min(self.selection_x_start, self.selection_x_end)))
            y = int(round(min(self.selection_y_start, self.selection_y_end)))
            width = int(
                round(abs(self.selection_x_end - self.selection_x_start))
            )
            height = int(
                round(abs(self.selection_y_end - self.selection_y_start))
            )
            # Do not take screen shot if grabbed area is too small
            if width > 10 and height > 10:
                GObject.timeout_add(
                    150, self.complete_handler, x, y, width, height
                )
            else:
                self.log.debug('ScreenGrabber: selected area is too small')
        self.deleted = True

    def start_selection(self, x, y):
        self.selection_x_start = x
        self.selection_y_start = y
        self.selected = True
        self.dark_fill()

    def stop_selection(self, x, y):
        self.selection_x_end = x
        self.selection_y_end = y
        self.drawingWindow.present()

    def redraw(self, x, y):
        def draw_cross(ctx, x, y):
            """
            draw 2 lines crossing at the cursor
            """
            ctx.set_source_rgba(255.0, 255.0, 255.0, 0.3)
            ctx.move_to(x, 0)
            ctx.rel_line_to(0, self.screenHeight)
            ctx.move_to(0, y)
            ctx.rel_line_to(self.screenWidth, 0)
            ctx.stroke()
        ctx = self.drawingWindow.get_window().cairo_create()
        # shade the whole screen
        ctx.rectangle(0, 0, self.screenWidth, self.screenHeight)
        ctx.clip()
        ctx.new_path()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_antialias(cairo.ANTIALIAS_NONE)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        ctx.paint()
        draw_cross(ctx, x, y)
        if not self.selected:
            return False
        draw_cross(ctx, self.selection_x_start, self.selection_y_start)
        # recalculate the selected rectangle
        rLefx = min(self.selection_x_start, x)
        rTopy = min(self.selection_y_start, y)
        rRigx = max(self.selection_x_start, x)
        rBoty = max(self.selection_y_start, y)
        width = rRigx - rLefx
        height = rBoty - rTopy
        # draw border
        ctx.set_source_rgba(255.0, 255.0, 255.0, 0.7)
        ctx.rectangle(rLefx, rTopy, width, height)
        ctx.fill()
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        ctx.rectangle(rLefx + 1, rTopy + 1, width - 2, height - 2)
        ctx.fill()

    def clear(self, ctx):
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.rectangle(0, 0, self.screenWidth, self.screenHeight)
        ctx.fill()
        return ctx

    def dark_fill(self):
        ctx = self.drawingWindow.get_window().cairo_create()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        ctx.paint()

    def set_complete_handler(self, complete_handler):
        self.complete_handler = complete_handler
