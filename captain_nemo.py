# Captain Nemo is a Nautilus extension which converts Nautilus into
# an orthodox file manager.
#
# This extension requires at least version 1.0-0ubuntu2 of the
# python-nautilus package.
#
# To install copy captain-nemo.py to ~/.local/share/nautilus-python/extensions/
#
# The following keyboard shorcuts are (re)defined to their orthodox meanings.
#
# ------  -----------------------------------  ---------------
#                   Operation
# Key     Orthodox       Nautilus              Alternative Key
# ------  -------------  --------------------  ---------------
# F3      View           Show/Hide Extra Pane
# F4      Edit           Not Used
# F5      Copy           Reload                Ctrl+R
# F6      RenMov         Switch Between Panes  Tab
# F7      Mkdir          Not Used
# F8      Delete         Not Used
# Ctrl+O  Open Terminal  Open File             Enter
#
# As can be seen from the above table for most redefined operations there
# exist commonly used alternatives.
#
# In addition this extension defined the following keyboard shortcut:
#   Ctrl+G - open a git client in the current directory
# Also the Compare... item is added to the context menu when two items are
# selected.

import contextlib
import logging
import os
import subprocess
import sys
import traceback
import urllib
from gi.repository import Nautilus, GObject, Gtk, GConf

DIFF = 'meld'
GIT_CLIENT = 'gitg'
TERMINAL_KEY = '/desktop/gnome/applications/terminal/exec'
EDITOR = 'gedit'
DEBUG = False

# This class allows depth-first traversal of a widget tree using an iterator.
class walk:
    def __init__(self, top, visit_submenu=True):
        self._generator = self._walk(top)
        self._visit_submenu = visit_submenu
        self._skip_children = False
        self._depth = 0

    def __iter__(self):
        return self._generator.__iter__()

    def depth(self):
        return self._depth

    # Skip children of the current widget.
    def skip_children(self):
        self._skip_children = True

    def _walk(self, widget):
        if widget == None: return
        yield widget
        if self._skip_children:
            self._skip_children = False
            return
        self._depth += 1
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                for w in self._walk(child):
                    yield w
        if self._visit_submenu and isinstance(widget, Gtk.MenuItem):
            for w in self._walk(widget.get_submenu()):
                yield w
        self._depth -= 1

if DEBUG:
    # The nautilus_debug package is only imported in DEBUG mode to avoid
    # dependency on twisted for normal use.
    # Also there is a circular dependency between captain_nemo and
    # nautilus_debug which uses the walk function. This is resolved by
    # importing nautilus_debug after walk.
    from nautilus_debug import TelnetThread, WidgetInspector
    logging.basicConfig(
        filename=os.path.join(os.path.dirname(__file__), 'captain_nemo.log'),
        level=logging.DEBUG)

def get_filename(file_info):
    return urllib.unquote(file_info.get_uri()[7:])

def has_file_scheme(f):
    return f.get_uri_scheme() == 'file'

# Catches and logs all exceptions.
@contextlib.contextmanager
def catch_all():
    try:
        yield
    except:
        logging.error(sys.exc_info()[1])

# Redefines keyboard shortcuts and adds extra widgets.
class WindowAgent:
    def __init__(self, window):
        self.window = window
        self.loc_entry1 = self.loc_entry2 = None

        # Find the main paned widget and the menubar.
        self.main_paned = menubar = None
        walker = walk(window, False)
        for w in walker:
            name = w.get_name()
            if name == 'NautilusToolbar':
                p = w.get_parent()
                while not isinstance(p, Gtk.Paned):
                    p = p.get_parent()
                self.main_paned = p
                walker.skip_children()
            if name == 'MenuBar':
                menubar = w
                walker.skip_children()

        if menubar != None:
            # Show extra pane.
            for w in walk(menubar):
                name = w.get_name()
                if name == 'Show Hide Extra Pane':
                    w.activate()
                    break
        else:
            print 'Menu bar not found'

        if self.main_paned != None:
            # Find location entries.
            self.loc_entry1 = self.find_loc_entry(self.main_paned.get_child1())
            self.loc_entry2 = self.find_loc_entry(self.main_paned.get_child2())
        else:
            print 'Main paned not found'

        # Remove the accelerator from the 'Show Hide Extra Pane' action (F3).
        Gtk.AccelMap.change_entry(
            '<Actions>/ShellActions/Show Hide Extra Pane', 0, 0, False)
        # Remove the accelerator from the 'SplitViewNextPane' action (F6).
        Gtk.AccelMap.change_entry(
            '<Actions>/ShellActions/SplitViewNextPane', 0, 0, False)
        # Change the accelerator for the Open action from Ctrl+O to F3.
        key, mods = Gtk.accelerator_parse('F3')
        Gtk.AccelMap.change_entry(
            '<Actions>/DirViewActions/Open', key, mods, False)

        accel_group = Gtk.accel_groups_from_object(window)[0]

        def connect(accel, func):
            key, mods = Gtk.accelerator_parse(accel)
            accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE, func)

        connect('F4', self.on_edit)

        if self.loc_entry1 != None and self.loc_entry2 != None:
            connect('<Ctrl>O', self.on_terminal)
            connect('<Ctrl>G', self.on_git)
        else:
            print 'Location entries not found'

        if menubar != None:
            for w in walk(menubar):
                name = w.get_name()
                if name == 'Copy to next pane':
                    connect('F5', self.on_copy)
                    self.copy_menuitem = w
                elif name == 'Move to next pane':
                    connect('F6', self.on_move)
                    self.move_menuitem = w
                elif name == 'New Folder':
                    connect('F7', self.on_mkdir)
                    self.mkdir_menuitem = w
                elif name == 'Trash':
                    connect('F8', self.on_delete)
                    self.delete_menuitem = w

        if DEBUG:
            # Add the widget inspector.
            child = window.get_child()
            inspector = WidgetInspector(window)
            window.remove(child)
            paned = Gtk.VPaned()
            paned.pack1(child, True, True)
            paned.pack2(inspector, False, False)
            paned.show()
            window.add(paned)

    def find_loc_entry(self, widget):
        for w in walk(widget):
            if w.get_name() == 'NautilusLocationEntry':
                return w

    def get_selection(self):
        focus = self.window.get_focus()
        if not isinstance(focus, Gtk.TreeView) and \
           focus.get_parent().get_name() == 'NautilusListView':
            return []
        def collect_uris(treemodel, path, iter, uris):
            uris.append(treemodel[iter][0].get_uri())
        uris = []
        focus.get_selection().selected_foreach(collect_uris, uris)
        return uris

    def show_dialog(self, title, message):
        md = Gtk.MessageDialog(parent=self.window, title=title)
        md.set_property('message-type', Gtk.MessageType.QUESTION)
        md.set_markup(message)
        md.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        md.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        result = md.run()
        md.destroy()
        return result == Gtk.ResponseType.OK

    def on_copy(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            if self.show_dialog('Copy',
                'Do you want to copy selected files/directories?'):
                self.copy_menuitem.activate()
        return True

    def on_move(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            if self.show_dialog('Move',
                'Do you want to move selected files/directories?'):
                self.move_menuitem.activate()
        return True

    def on_mkdir(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            self.mkdir_menuitem.activate()
        return True

    def on_delete(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            if self.show_dialog('Delete',
                'Do you want to move selected files/directories to trash?'):
                self.delete_menuitem.activate()
        return True

    def on_edit(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            selection = self.get_selection()
            logging.debug("on_edit: %s", selection)
            subprocess.Popen([EDITOR] + selection)
        return True

    def get_location(self):
        w = self.window.get_focus()
        while w != None:
            if w == self.main_paned.get_child1():
                entry = self.loc_entry1
                break
            if w == self.main_paned.get_child2():
                entry = self.loc_entry2
                break
            w = w.get_parent()
        return entry.get_text()

    def on_terminal(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            location = self.get_location()
            logging.debug('on_terminal: location=%s', location)
            terminal = GConf.Client.get_default().get_string(TERMINAL_KEY)
            subprocess.Popen([terminal], cwd=location)
        return True

    def on_git(self, accel_group, acceleratable, keyval, modifier):
        with catch_all():
            location = self.get_location()
            logging.debug('on_git: location=%s', location)
            subprocess.Popen([GIT_CLIENT], cwd=location)
        return True

class WidgetProvider(GObject.GObject, Nautilus.LocationWidgetProvider):
    def __init__(self):
        self.window_agents = {}
        self.thread = None
        if DEBUG:
            with catch_all():
                self.thread = TelnetThread(self.window_agents)
                self.thread.start()

    def get_widget(self, uri, window):
        try:
            if uri == 'x-nautilus-desktop:///':
                return None
            agent = self.window_agents.get(window)
            if agent != None:
                return None
            window.connect('destroy', lambda w: self.window_agents.pop(w))
            agent = WindowAgent(window)
            self.window_agents[window] = agent
        except:
            print traceback.print_exc()
        return None

class CompareMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    def on_compare(self, menu, files):
        subprocess.Popen([DIFF, get_filename(files[0]), get_filename(files[1])])
 
    def get_file_items(self, window, files):
        if len(files) != 2: return
        if not has_file_scheme(files[0]) or not has_file_scheme(files[1]):
            return
        item = Nautilus.MenuItem(
            name='SimpleMenuExtension::Compare_Files', label='Compare...',
            tip='Compare...')
        item.connect('activate', self.on_compare, files)
        return [item]
