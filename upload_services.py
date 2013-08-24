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
import webbrowser
import os
import threading
# for uploading
import pycurl
import base64
# for parsing server response
import json
from abc import ABCMeta, abstractmethod


class UploadBase(threading.Thread):
    """ All web image services classes should inherit this class """
    __metaclass__ = ABCMeta   # abstract class
    def __init__(self):
        threading.Thread.__init__(self)
        self.USERNAME = ""
    @abstractmethod
    def login(self):
        pass
    @abstractmethod
    def logout(self):
        pass
    @abstractmethod
    def is_logged_in(self):
        return False
    @abstractmethod
    def upload_callback(self, image, remove):
        return False
    @abstractmethod
    def save_settings(self, config):
        return config


class Imgur(UploadBase):
    def __init__(self, indicator, config, log):
        UploadBase.__init__(self)
        # API v3
        self.CLIENT_ID = "813588ae4b2b41a"
        self.CLIENT_SECRET = "1cc11d1006c90d0e184daa29085a015e24cd6705"
        self.indicator = indicator
        self.log = log
        try:
            self.ACCESS_TOKEN = config.get("AUTH", "access_token")
            self.REFRESH_TOKEN = config.get("AUTH", "refresh_token")
            self.USERNAME = config.get("AUTH", "username")
        except Exception as e:
            self.log.error("Error: %s" % str(e))
            self.ACCESS_TOKEN = ""
            self.REFRESH_TOKEN = ""
            self.USERNAME = ""

    def login(self):
        def auth_response(dialog, resp_id):
            if resp_id == gtk.RESPONSE_OK:
                self.response = ''
                pin = dialog.pin_entry.get_text()
                curl = pycurl.Curl()
                curl.setopt(pycurl.URL, 'https://api.imgur.com/oauth2/token')
                curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 Fileshare')
                curl.setopt(pycurl.POST, 1)
                curl.setopt(pycurl.HTTPPOST,
                            [('client_id', self.CLIENT_ID), ('client_secret', self.CLIENT_SECRET), ('grant_type', 'pin'),
                             ('pin', pin)])
                curl.setopt(pycurl.WRITEFUNCTION, self.write)
                curl.perform()
                resp = json.loads(self.response)
                if "access_token" in resp:
                    self.ACCESS_TOKEN = str(resp["access_token"])
                    self.REFRESH_TOKEN = str(resp["refresh_token"])
                    self.refresh_access_token() # is done to get username
        #def auth_response(dialog, resp_id)
        # Open browser windows and prompt for access to Imgur account
        webbrowser.open(
            "https://api.imgur.com/oauth2/authorize?client_id=" + self.CLIENT_ID + "&response_type=pin&state=APPLICATION_STATE")
        # Window to enter PIN from the site
        pin_dialog = gtk.Dialog(title="Enter PIN",
                                flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                buttons=(
                                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                    gtk.STOCK_OK, gtk.RESPONSE_OK))
        pin_dialog.set_modal(False)
        pin_dialog.set_decorated(True)
        pin_dialog.pin_entry = pin_entry = gtk.Entry()
        pin_entry.show()
        pin_dialog.vbox.add(pin_entry)
        pin_dialog.connect('response', auth_response)
        pin_dialog.run()
        pin_dialog.destroy()

    def write(self, string):
        self.response += string

    def is_logged_in(self):
        return True if self.ACCESS_TOKEN else False

    def save_settings(self, config):
        if not config.has_section("AUTH"):
            config.add_section("AUTH")
        config.set("AUTH", "access_token", self.ACCESS_TOKEN)
        config.set("AUTH", "refresh_token", self.REFRESH_TOKEN)
        config.set("AUTH", "username", self.USERNAME)
        return config

    def refresh_access_token(self):
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, 'https://api.imgur.com/oauth2/token')
        curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 Fileshare')
        curl.setopt(pycurl.POST, 1)
        if self.REFRESH_TOKEN:
            self.response = ""
            curl.setopt(pycurl.HTTPPOST,
                        [('refresh_token', self.REFRESH_TOKEN),
                         ('client_id', self.CLIENT_ID),
                         ('client_secret', self.CLIENT_SECRET),
                         ('grant_type', 'refresh_token')])
            curl.setopt(pycurl.WRITEFUNCTION, self.write)
            curl.perform()
            self.log.debug("Response: " + self.response)
            resp = json.loads(self.response)
            if 'access_token' in resp:
                self.ACCESS_TOKEN = str(resp['access_token'])
                self.REFRESH_TOKEN = str(resp['refresh_token'])
                self.USERNAME = str(resp['account_username'])
                self.indicator.save_settings()
                return True
            else:
                self.logout()
                # Inform the user that we have logged out
                dialog = gtk.MessageDialog(parent=None,
                                           flags=0,
                                           type=gtk.MESSAGE_WARNING,
                                           buttons=gtk.BUTTONS_OK,
                                           message_format=None)
                dialog.set_title("fileshare")
                dialog.set_markup("Authentication failed!")
                dialog.format_secondary_text("Please, log in again. Otherwise your images will be uploaded anonymously.")
                dialog.run()
                dialog.destroy()
        return False

    def upload_callback(self, image, remove):
        def img2base64(image):
            with open(image, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
            return encoded_string

        self.log.debug("Uploading file: " + image)
        self.response = ''
        self.base64String = img2base64(image)
        self.curl = curl = pycurl.Curl()
        curl.setopt(pycurl.URL, 'https://api.imgur.com/3/image')
        curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 Fileshare')
        curl.setopt(pycurl.POST, 1)
        if self.ACCESS_TOKEN:
            curl.setopt(pycurl.HTTPHEADER, ["Authorization: Bearer " + self.ACCESS_TOKEN])
        else:
            # Anonymous upload
            curl.setopt(pycurl.HTTPHEADER, ["Authorization: Client-ID " + self.CLIENT_ID])
        curl.setopt(pycurl.HTTPPOST, [('image', self.base64String)])
        curl.setopt(pycurl.WRITEFUNCTION, self.write)
        self.curl.perform()
        self.log.debug("Response: " + self.response)
        if self.ACCESS_TOKEN and json.loads(self.response)['status'] == 403:
            # Refresh auth token and repeat
            if self.indicator.service.refresh_access_token():
                return self.upload_callback(image, remove)
        else:
            dict = json.loads(self.response)
            try:
                url = dict['data']['link']
                self.indicator.file_grabber.show_result(url)
            except Exception as e:
                self.log.error("Error: %s" % str(e))
        if remove:
            os.remove(image)
        return False  # return False not to be called again as callback

    def logout(self):
        self.ACCESS_TOKEN = ""
        self.REFRESH_TOKEN = ""
        self.USERNAME = ""
#class Imgur()
