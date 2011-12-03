# Nautilus extension that adds a keyboard shortcut Ctrl-O that opens a terminal
# in the current directory. Copy it to the extensions install path, e.g.
# ~/.nautilus/python-extensions/

import gconf, gtk, nautilus, os, pipes, urllib

TERMINAL_KEY = '/desktop/gnome/applications/terminal/exec'

class ShortcutProvider(nautilus.LocationWidgetProvider):
    def __init__(self):
        self.client = gconf.client_get_default()
        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_group(
           ord('o'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE, self.run_terminal)
        self.accel_group.connect_group(
           ord('g'), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE, self.run_gitg)
        self.window = None

    def run_terminal(self, accel_group, acceleratable, keyval, modifier):
        filename = urllib.unquote(self.uri[7:])
        terminal = self.client.get_string(TERMINAL_KEY)
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
    return pipes.quote(file_info.get_location().get_path()) + " "

class CompareMenuProvider(nautilus.MenuProvider):
    def __init__(self):
        pass
    
    def menu_activate_cb(self, menu, files):
        os.system("meld " + quote(files[0]) + " " + quote(files[1])  + " &")
    
    def get_file_items(self, window, files):
        if len(files) != 2: return
        item = nautilus.MenuItem(
            "SimpleMenuExtension::Compare_Files", "Compare...", "Compare...")
        item.connect('activate', self.menu_activate_cb, files)
        return [item]
