#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012
#
# Authors: Denis Kovalev <aikikode@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of either or both of the following licenses:
#
# 1) the GNU Lesser General Public License version 3, as published by the
# Free Software Foundation; and/or
# 2) the GNU Lesser General Public License version 2.1, as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the applicable version of the GNU Lesser General Public
# License for more details.
#
# You should have received a copy of both the GNU Lesser General Public
# License version 3 and version 2.1 along with this program.  If not, see
# <http://www.gnu.org/licenses>
#

_author__ = 'aikikode'

import gtk
import threading
# to unquote cyrillic file names and spaces
import urllib2
# for delayed actions
import gobject
# for screen area grabber colors
import cairo

FILE_GRABBER_SIZE = 50


class FileGrabber():
    """ Applet for drag'n'drop files to. The file is automatically uploaded to
        the hosting and the result URL is copied into the clipboard """

    def __init__(self, indicator = None):
        self.cb = gtk.Clipboard()
        self.indicator = indicator
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_decorated(False)
        self.window.set_opacity(0.5)
        self.window.set_size_request(FILE_GRABBER_SIZE, FILE_GRABBER_SIZE)
        self.window.set_resizable(False)
        self.window.drag_dest_set(0, [], 0)

        self.window.set_gravity(gtk.gdk.GRAVITY_NORTH_EAST)
        width, height = self.window.get_size()
        self.window.move(gtk.gdk.screen_width() - width - 20, height)
        self.app_icon = self.indicator.app_icon

        # Add main widget for grabbing files
        self.image = gtk.Image()
        pixbuf = gtk.gdk.pixbuf_new_from_file(self.app_icon)
        scaled_buf = pixbuf.scale_simple(FILE_GRABBER_SIZE, FILE_GRABBER_SIZE, gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(scaled_buf)
        self.image.show()
        self.window.add(self.image)
        self.window.connect('drag_motion', self.window_drag_motion)
        self.window.connect('drag_drop', self.window_drag_drop)
        self.window.connect('drag_data_received', self.window_drag_data_received)
        self.isShown = False

    def toggle_window(self):
        if self.isShown:
            self.window.hide()
            self.isShown = False
        else:
            self.window.show()
            self.window.set_keep_above(True)    # This may not work: it depends on the window manager
            self.isShown = True

    def window_drag_motion(self, wid, context, x, y, time):
        context.drag_status(gtk.gdk.ACTION_COPY, time)
        return True      # True means "I accept this data"

    def window_drag_drop(self, wid, context, x, y, time):
        wid.drag_get_data(context, context.targets[-1], time)
        return True

    def window_drag_data_received(self, wid, context, x, y, data, info, time):
        file_to_upload = data.get_text().splitlines()[0].replace("file://", "")
        context.finish(True, False, time)
        self.upload_file(file_to_upload, remove=False)

    def upload_file(self, image, remove=False):
        # convert file name to utf-8
        file_to_upload = image.decode('UTF-8').encode('UTF-8')
        # convert %80%20 and other to cyrillic symbols and spaces
        file_to_upload = urllib2.unquote(file_to_upload)
        gobject.idle_add(self.indicator.service.upload_callback, file_to_upload, remove)

    def show_result(self, url):
        self.cb.set_text(url)
        self.cb.store()
        self.indicator.show_notification(url)
#class FileGrabber()


##############################################################################
class ScreenGrabber(threading.Thread):
    def __init__(self, eventHandler, log):
        threading.Thread.__init__(self)
        self.log = log
        self.log.debug("ScreenGrabber: creating")
        self.selected = False
        root = gtk.gdk.get_default_root_window()
        self.screenWidth, self.screenHeight = root.get_size()
        width, height = self.screenWidth, self.screenHeight
        self.drawingWindow = drawingWindow = gtk.Window(gtk.WINDOW_POPUP)
        drawingWindow.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_SPLASHSCREEN)
        drawingWindow.set_decorated(False)
        drawingWindow.set_has_frame(False)
        drawingWindow.set_skip_taskbar_hint(True)
        drawingWindow.set_skip_pager_hint(True)
        drawingWindow.set_can_focus(True)
        drawingWindow.set_accept_focus(True)
        drawingWindow.set_keep_above(True)
        drawingWindow.set_default_size(width, height)
        drawingWindow.resize(width, height)
        drawingWindow.move(0, 0)
        rgba = drawingWindow.get_screen().get_rgba_colormap()
        drawingWindow.set_app_paintable(True)
        drawingWindow.set_colormap(rgba)
        drawingWindow.set_events(gtk.gdk.POINTER_MOTION_MASK |
                                 gtk.gdk.BUTTON_PRESS_MASK |
                                 gtk.gdk.BUTTON_RELEASE_MASK |
                                 gtk.gdk.KEY_PRESS_MASK)
        drawingWindow.show()
        drawingWindow.present()
        gtk.gdk.keyboard_grab(drawingWindow.window)
        cursor = gtk.gdk.Cursor(gtk.gdk.CROSSHAIR)
        drawingWindow.window.set_cursor(cursor)
        self.cursor = 'crosshair'
        drawingWindow.connect_after('expose-event', self.expose_event)
        drawingWindow.connect('button-press-event', eventHandler, self)
        drawingWindow.connect('button-release-event', eventHandler, self)
        drawingWindow.connect('key-press-event', eventHandler, self)
        drawingWindow.connect('motion-notify-event', eventHandler, self)

    def __del__(self):
        if hasattr(self, 'deleted'):
            return True
        ctx = self.drawingWindow.window.cairo_create()
        self.clear(ctx)
        gtk.gdk.keyboard_ungrab()
        # Give cairo some time to clear the screen before the destruction of the window
        gobject.timeout_add(50, self.drawingWindow.destroy)
        if self.selected and hasattr(self, 'completeHandler'):
            x = int(round(min(self.selection_x_start, self.selection_x_end)))
            y = int(round(min(self.selection_y_start, self.selection_y_end)))
            width = int(round(abs(self.selection_x_end - self.selection_x_start)))
            height = int(round(abs(self.selection_y_end - self.selection_y_start)))
            # Do not take screen shot if grabbed area is too small
            if width > 10 and height > 10:
                gobject.timeout_add(150, self.completeHandler, x, y, width, height)
            else:
                self.log.debug("ScreenGrabber: selected area is too small")
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
        if not self.selected:
            return False
            # recalculate the selected rectangle
        rLefx = min(self.selection_x_start, x)
        rTopy = min(self.selection_y_start, y)
        rRigx = max(self.selection_x_start, x)
        rBoty = max(self.selection_y_start, y)
        width = rRigx - rLefx
        height = rBoty - rTopy
        ctx = self.drawingWindow.window.cairo_create()
        # shade the whole screen
        ctx.rectangle(0, 0, self.screenWidth, self.screenHeight)
        ctx.clip()
        ctx.new_path()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_antialias(cairo.ANTIALIAS_NONE)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        ctx.paint()
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
        ctx = self.drawingWindow.window.cairo_create()
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.5)
        ctx.paint()

    def expose_event(self, widget, event):
        self.dark_fill()
        if self.selected:
            self.redraw(self.selection_x_end, self.selection_y_end)

    def set_complete_handler(self, completeHandler):
        self.completeHandler = completeHandler
#class ScreenGrabber(threading.Thread)
