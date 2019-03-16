Fileshare Applet
================
Fileshare applet development is inspired mostly by Droplr windows client. Its
purpose is to share images over the Internet using on-line services.  
By now [Imgur](http://imgur.com) and [Droplr](http://droplr.com) services are
supported.

### Fileshare applet features

- drag'n'drop image files to 'File Grabber' to upload
- select screen area to grab, show preview and upload
- link to the result image is automatically stored in the buffer, just paste to share the link
- Imgur and Droplr account support: run 'Log in' menu item to connect application to your account
  (note, that to use Droplr account you'll need to request application keys from the developers,
  see [http://help.droplr.com/customer/portal/articles/1014091-introduction](http://help.droplr.com/customer/portal/articles/1014091-introduction) for more details)

### For Linux users
There're two options for you.
#### Use precompiled package
Download and install latest DEB package from [releases](https://github.com/aikikode/fileshare/releases) page.  
#### Create a package yourself
1. Install Docker and run:  
```bash
./ci/build.sh
```  
this will create deb package  
2. Install it with command:  
```bash
# dpkg -i <deb file>
```

### For Windows users:  
1. Download and run PyGTK all-in-one installer:  
   [http://www.pygtk.org/downloads.html](http://www.pygtk.org/downloads.html)
2. Run fileshare-setup.exe

### Custom keyboard shortcut  
Please, note, that not all systems support hotkeys. To check whether your system supports them, open Python console and type:  
```bash
from gi.repository import Keybinder
```  
If there's no error, shortcuts should work fine.  

By default the keyboard shortcut is "\<Super>P".  
In case it conflicts with your system or you'd like to change it, perform the following:  

1. Start the fileshare application  
2. Quit the app  
3. Edit the file  
```bash
~/.fileshare/settings.cfg
```  
find the section:  
```bash
[KEYMAP]
grabscreen = <Super>P
```  
and change "\<Super>P" to the desired shortcut.  
You may use the following modifiers: \<Alt>, \<Ctrl>, \<Shift>, \<Super>


### Special thanks to:  
- Droplr developers for idea
- Weather Indicator Team for first steps in Unity Python toolbar application development
- VladX, Nanoshot developer for many great PyGTK examples
