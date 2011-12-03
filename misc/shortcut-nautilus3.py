# This Nautilus extension adds the following keyboard shortcuts:
#   Ctrl-O - open a terminal in the current directory
#   Ctrl-G - open a git client in the current directory
#
# To install copy the script to ~/.local/share/nautilus-python/extensions/
#
# Requires at least version 1.0-0ubuntu2 of the python-nautilus package.

import os, pipes, urllib
from gi.repository import Nautilus, GObject, Gtk, Gdk, GConf

DIFF = 'meld'
GIT_CLIENT = 'gitg'
TERMINAL_KEY = '/desktop/gnome/applications/terminal/exec'

class ShortcutProvider(GObject.GObject, Nautilus.LocationWidgetProvider):
    def __init__(self):
        self.accel_group = Gtk.AccelGroup()
        self.accel_group.connect(ord('o'), Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE, self.run_terminal)
        self.accel_group.connect(ord('g'), Gdk.ModifierType.CONTROL_MASK,
            Gtk.AccelFlags.VISIBLE, self.run_gitg)
        self.window = None

    def run_terminal(self, accel_group, acceleratable, keyval, modifier):
        filename = urllib.unquote(self.uri[7:])
        terminal = GConf.Client.get_default().get_string(TERMINAL_KEY)
        os.chdir(filename)
        os.system(pipes.quote(terminal) + ' &')
        return True

    def run_gitg(self, accel_group, acceleratable, keyval, modifier):
        filename = urllib.unquote(self.uri[7:])
        os.chdir(filename)
        os.system('gitg &')
        return True

    def get_widget(self, uri, window):
        self.uri = uri
        if self.window:
            self.window.remove_accel_group(self.accel_group)
        window.add_accel_group(self.accel_group)
        self.window = window
        return None

def quote(file_info):
    return pipes.quote(urllib.unquote(file_info.get_uri()[7:])) + " "

def has_file_scheme(f):
    return f.get_uri_scheme() == 'file'

class CompareMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def menu_activate_cb(self, menu, files):
        os.system(DIFF + " " + quote(files[0]) + " " + quote(files[1])  + " &")
    
    def get_file_items(self, window, files):
        if len(files) != 2: return
        if not has_file_scheme(files[0]) or  not has_file_scheme(files[1]):
            return
        item = Nautilus.MenuItem(
            name="SimpleMenuExtension::Compare_Files", label="Compare...",
            tip="Compare...")
        item.connect('activate', self.menu_activate_cb, files)
        return [item]
