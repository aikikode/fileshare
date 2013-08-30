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
# For Droplr hashed requests
import hashlib, hmac
import time
import urllib
import mimetypes
# for delayed actions
import gobject


class UploadBase(threading.Thread):
    """ All web image services classes should inherit this class """
    __metaclass__ = ABCMeta   # abstract class
    def __init__(self):
        threading.Thread.__init__(self)
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
    def get_username(self):
        return None
    @abstractmethod
    def get_site_url(self):
        return None
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
        self._client_id = "813588ae4b2b41a"
        self._client_secret = "1cc11d1006c90d0e184daa29085a015e24cd6705"
        self.indicator = indicator
        self.log = log
        self._url = 'https://imgur.com/'
        try:
            self._access_token = config.get("IMGUR", "access_token")
            self._refresh_token = config.get("IMGUR", "refresh_token")
            self._username = config.get("IMGUR", "username")
        except Exception as e:
            self.log.error("Error: %s" % str(e))
            self._access_token = ""
            self._refresh_token = ""
            self._username = ""

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
                            [('client_id', self._client_id), ('client_secret', self._client_secret), ('grant_type', 'pin'),
                             ('pin', pin)])
                curl.setopt(pycurl.WRITEFUNCTION, self.write)
                curl.perform()
                resp = json.loads(self.response)
                if "access_token" in resp:
                    self._access_token = str(resp["access_token"])
                    self._refresh_token = str(resp["refresh_token"])
                    self.refresh_access_token() # is done to get username
        #def auth_response(dialog, resp_id)
        # Open browser windows and prompt for access to Imgur account
        webbrowser.open(
            "https://api.imgur.com/oauth2/authorize?client_id=" + self._client_id + "&response_type=pin&state=APPLICATION_STATE")
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
        return True if self._access_token else False

    def get_username(self):
        return self._username

    def get_site_url(self):
        return self._url

    def save_settings(self, config):
        if not config.has_section("IMGUR"):
            config.add_section("IMGUR")
        config.set("IMGUR", "access_token", self._access_token)
        config.set("IMGUR", "refresh_token", self._refresh_token)
        config.set("IMGUR", "username", self._username)
        return config

    def refresh_access_token(self):
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, 'https://api.imgur.com/oauth2/token')
        curl.setopt(pycurl.USERAGENT, 'Mozilla/5.0 Fileshare')
        curl.setopt(pycurl.POST, 1)
        if self._refresh_token:
            self.response = ""
            curl.setopt(pycurl.HTTPPOST,
                        [('refresh_token', self._refresh_token),
                         ('client_id', self._client_id),
                         ('client_secret', self._client_secret),
                         ('grant_type', 'refresh_token')])
            curl.setopt(pycurl.WRITEFUNCTION, self.write)
            curl.perform()
            self.log.debug("Response: " + self.response)
            resp = json.loads(self.response)
            if 'access_token' in resp:
                self._access_token = str(resp['access_token'])
                self._refresh_token = str(resp['refresh_token'])
                self._username = str(resp['account_username'])
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
        if self._access_token:
            curl.setopt(pycurl.HTTPHEADER, ["Authorization: Bearer " + self._access_token])
        else:
            # Anonymous upload
            curl.setopt(pycurl.HTTPHEADER, ["Authorization: Client-ID " + self._client_id])
        curl.setopt(pycurl.HTTPPOST, [('image', self.base64String)])
        curl.setopt(pycurl.WRITEFUNCTION, self.write)
        self.curl.perform()
        self.log.debug("Response: " + self.response)
        if self._access_token and json.loads(self.response)['status'] == 403:
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
        self._access_token = ""
        self._refresh_token = ""
        self._username = ""
#class Imgur()


class Droplr(UploadBase):
    def __init__(self, indicator, config, log):
        UploadBase.__init__(self)
        self._public_key = ""
        self._private_key = ""
        self.indicator = indicator
        self.log = log
        self._url = 'https://droplr.com/'
        self.api_url = ''
        try:
            self._login = config.get("DROPLR", "email")
            self._password_sha1 = config.get("DROPLR", "password")
            self._authorization_header = base64.b64encode(self._public_key + ":" + self._login)
        except Exception as e:
            self.log.error("Error: %s" % str(e))
            self._login = ""
            self._password_sha1 = ""
            self._authorization_header = ""
        if self.is_logged_in() and not self.are_credentials_ok():
            self.relogin()

    def relogin(self):
        self._login = ""
        self._password_sha1 = ""
        self.indicator.show_notification("Invalid login/password. Please try again")
        self.log.debug("Invalid login/password, trying again")
        gobject.idle_add(self.login)

    def login(self):
        def auth_response(dialog, resp_id):
            if resp_id == gtk.RESPONSE_OK:
                self.response = ''
                email = dialog.email_entry.get_text()
                password = dialog.password_entry.get_text()
                self._login = email
                self._password_sha1 = hashlib.sha1(password).hexdigest()
                del password
                self._authorization_header = base64.b64encode(self._public_key + ":" + self._login)
                if not self.are_credentials_ok():
                    self.relogin()
        #def auth_response(dialog, resp_id)
        # Window to enter email and password
        pin_dialog = gtk.Dialog(title="Droplr Login",
                                flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                buttons=(
                                    "Sign Up", gtk.RESPONSE_OK,
                                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        pin_dialog.set_default_response(gtk.RESPONSE_OK)
        pin_dialog.set_modal(False)
        pin_dialog.set_decorated(True)
        pin_dialog.set_resizable(False)

        pin_dialog.email_entry = email_entry = gtk.Entry()
        email_entry.set_activates_default(gtk.TRUE)
        pin_dialog.email_entry.show()

        pin_dialog.password_entry = password_entry = gtk.Entry()
        password_entry.set_activates_default(gtk.TRUE)

        email_label = gtk.Label("e-mail :")
        password_label = gtk.Label("password :")
        password_entry.set_visibility(False)
        pin_dialog.password_entry.show()

        def forgot_password_callback(self, widget, data = None):
            webbrowser.open('https://www.dropbox.com/forgot')
        forgot_password_button = gtk.Button("Forgot password?")
        forgot_password_button.connect("clicked", forgot_password_callback, None)
        forgot_password_button.props.relief = gtk.RELIEF_NONE
        label =  forgot_password_button.get_children()[0]
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))
        label.modify_fg(gtk.STATE_PRELIGHT, gtk.gdk.color_parse('red'))
        table = gtk.Table(2, 3, True)
        table.attach(email_label, 0, 1, 0, 1)
        table.attach(password_label, 0, 1, 1, 2)
        table.attach(email_entry, 1, 3, 0, 1)
        table.attach(password_entry, 1, 3, 1, 2)
        table.show_all()
        pin_dialog.vbox.add(table)
        pin_dialog.vbox.add(forgot_password_button)
        pin_dialog.show_all()
        pin_dialog.connect('response', auth_response)
        pin_dialog.run()
        pin_dialog.destroy()

    def write(self, string):
        self.response += string

    def is_logged_in(self):
        return True if self._login else False

    def get_username(self):
        return self._login

    def get_site_url(self):
        return self._url

    def save_settings(self, config):
        if not config.has_section("DROPLR"):
            config.add_section("DROPLR")
        config.set("DROPLR", "email", self._login)
        config.set("DROPLR", "password", self._password_sha1)
        return config

    def create_signature(self, string_to_sign):
        return base64.b64encode(hmac.new(self._private_key + ":" + self._password_sha1, string_to_sign, hashlib.sha1).digest())

    def perform_request(self, method, uri, date, content_type, data, params):
        self.response = ''
        curl = pycurl.Curl()
        string_to_sign = "%s /%s.json HTTP/1.1\n%s\n%s" % (method, uri, content_type, date)
        signature = self.create_signature(string_to_sign)

        url = '%s/%s.json' % (self.api_url, uri)
        if params:
            url += "?" + urllib.urlencode(params)
        headers = {}
        headers["Authorization"] = "droplr %s:%s" % (self._authorization_header, signature)
        headers["Date"] = date
        if data:
            headers["Content-Length"] = len(data)
        if content_type:
            headers["Content-Type"] = content_type

        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.USERAGENT, 'Fileshare %s' % self.indicator.get_version())
        curl.setopt(pycurl.HTTPHEADER, [str(x) + ": " + str(headers.get(x)) for x in headers.keys()])
        curl.setopt(pycurl.HEADER, True)
        if data:
            curl.setopt(pycurl.POSTFIELDS, data)
        curl.setopt(pycurl.WRITEFUNCTION, self.write)
        curl.setopt(pycurl.CUSTOMREQUEST, method)
        curl.perform()
        self.log.debug("Response: " + self.response)
        return Droplr.DroplrResponse(self.response)

    def are_credentials_ok(self):
        response = self.perform_request('GET', 'account', str(int(time.time())), None, None, None)
        return not response.is_error()

    def upload_callback(self, image, remove):
        def get_data(image):
            with open(image, "rb") as image_file:
                data = image_file.read()
            return data

        self.log.debug("Uploading file: " + image)
        data = get_data(image)
        params = {'filename': os.path.basename(image)}
        content_type = mimetypes.guess_type(image)[0]
        if content_type is None:
            content_type = 'application/octet-stream'

        date = str(int(time.time()))
        response = self.perform_request("POST", 'files', date, content_type, data, params)
        if not response.is_error():
            dict = response.get_data()
            try:
                url = dict['shortlink']
                self.indicator.file_grabber.show_result(url)
            except Exception as e:
                self.log.error("Error: %s" % str(e))
        if remove:
            os.remove(image)
        return False  # return False not to be called again as callback

    def logout(self):
        self._login = ""
        self._password_sha1 = ""

    class DroplrResponse:
        def __init__(self, response):
            self.error = True
            self.response = response.split("\r\n\r\n")
            if self.response[1]:
                self.error = False
                if self.response[1][:4] == 'HTTP':
                    self.response[1] = self.response[2]
                self.dict = json.loads(self.response[1])
        def is_error(self):
            return self.error
        def get_data(self):
            return self.dict if not self.is_error() else None
#class Droplr()
