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
ACCEL_FILE_NAME = os.path.join(os.path.dirname(__file__), "captain_nemo.accel")
DEBUG = False
SHOW_EXTRA_PANE = False

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

class AccelInfo:
    def __init__(self, current, default):
        self.current = current
        self.default = default

# Map from accel path to info.
ACCELS = {}

# Changes the accelerator associated with a path recording
# the new value in ACCELS.
def change_accel(accel_path, accel_name):
    key, mods = Gtk.accelerator_parse(accel_name)
    info = ACCELS.get(accel_path)
    if info == None:
        known, entry = Gtk.AccelMap.lookup_entry(accel_path)
        name = Gtk.accelerator_name(entry.accel_key, entry.accel_mods)
        info = AccelInfo(name, name)
        ACCELS[accel_path] = info
    if Gtk.AccelMap.change_entry(accel_path, key, mods, True):
        info.current = accel_name
        return True
    return False

# Sets the default accelerators.
def set_default_accels():
    for path, info in ACCELS.items():
        key, mods = Gtk.accelerator_parse(info.default)
        Gtk.AccelMap.change_entry(path, key, mods, True)
    ACCELS.clear()

# Loads accelerators from a file.
def load_accels(filename):
    set_default_accels()
    with open(filename) as f:
        for line in f:
            path, current, default = line.rstrip().split(" ")
            path = urllib.unquote(path)
            key, mods = Gtk.accelerator_parse(current)
            Gtk.AccelMap.change_entry(path, key, mods, True)
            ACCELS[path] = AccelInfo(current, default)

# Saves accelerators to a file.
def save_accels(filename):
    with open(filename, "w") as f:
        for path, info in ACCELS.items():
            f.write("%s %s %s\n" %
                (urllib.quote(path), info.current, info.default))

if DEBUG:
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

def set_orthodox_accels():
    # Change the accelerator for the Open action from Ctrl+O to F3.
    change_accel("<Actions>/ShellActions/Show Hide Extra Pane", "")
    change_accel("<Actions>/DirViewActions/Open", "F3")
    # Remove the accelerator from the 'SplitViewNextPane' action (F6).
    change_accel("<Actions>/ShellActions/SplitViewNextPane", "")
    # Change the accelerator for the New Folder action from Ctrl+Shift+N to F7.
    change_accel("<Actions>/DirViewActions/New Folder", "F7")

class KeyboardShortcutsDialog(Gtk.Dialog):
    def create_shortcut_list(self):
        self.accel_store = Gtk.TreeStore(str, str, bool)
        self.accel_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        iters = {}
        def add_accel(data, accel_path, key, mods, changed):
            label = Gtk.accelerator_get_label(key, mods)
            split_path = accel_path.split("/")
            parent = None
            for i in range(len(split_path) - 1):
                subpath = "/".join(split_path[:i + 1])
                iter = iters.get(subpath)
                if iter == None:
                    iter = self.accel_store.append(
                        parent, [split_path[i], "", False])
                    iters[subpath] = iter
                parent = iter
            self.accel_store.append(parent, [split_path[-1], label, True])
        Gtk.AccelMap.foreach(None, add_accel)

        self.view = Gtk.TreeView(self.accel_store)
        self.view.set_rules_hint(True)
        self.view.expand_all()

        column = Gtk.TreeViewColumn("Action", Gtk.CellRendererText(), text=0)
        column.set_sort_column_id(0)
        self.view.append_column(column)

        # Unselecting all when the view loses focus solves the following problem:
        # when the user clicks on an accelerator in a selected row the keyboard
        # input is not captured by the view and the accelerator cannot be changed.
        self.view.connect("focus-out-event",
            lambda *args: self.view.get_selection().unselect_all())

        renderer = Gtk.CellRendererAccel()
        renderer.set_property("editable", True)
        renderer.connect("accel-edited", self.accel_edited)
        column = Gtk.TreeViewColumn("Key", renderer, text=1, editable=2)
        column.set_sort_column_id(1)
        self.view.append_column(column)

    # Converts tree iterator to accelerator path.
    def convert_tree_iter_to_accel_path(self, i):
        items = []
        while i != None:
            items.insert(0, self.accel_store.get_value(i, 0))
            i = self.accel_store.iter_parent(i)
        return "/".join(items)

    # Converts tree path to accelerator path.
    def convert_tree_path_to_accel_path(self, path):
        return self.convert_tree_iter_to_accel_path(
            self.accel_store.get_iter(path))

    def do_update_accel_store(self, iter):
        while iter != None:
            if self.accel_store.iter_has_child(iter):
                self.do_update_accel_store(self.accel_store.iter_children(iter))
            else:
                known, key = Gtk.AccelMap.lookup_entry(
                    self.convert_tree_iter_to_accel_path(iter))
                if known:
                    self.accel_store[iter][1] = Gtk.accelerator_get_label(
                        key.accel_key, key.accel_mods)
            iter = self.accel_store.iter_next(iter)

    def update_accel_store(self):
        self.do_update_accel_store(self.accel_store.get_iter_first())
        save_accels(ACCEL_FILE_NAME)

    def accel_edited(self, accel, path, key, mods, keycode):
        with catch_all():
            accel_path = self.convert_tree_path_to_accel_path(path)
            if change_accel(accel_path, Gtk.accelerator_name(key, mods)):
                self.accel_store[path][1] = Gtk.accelerator_get_label(key, mods)
                save_accels(ACCEL_FILE_NAME)

    def use_default(self, widget):
        with catch_all():
            set_default_accels()
            self.update_accel_store()

    def use_orthodox(self, widget):
        with catch_all():
            # Set default accelerators first to discard any changes,
            # then apply orthodox changes on top.
            set_default_accels()
            set_orthodox_accels()
            self.update_accel_store()

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Keyboard Shortcuts", parent,
            Gtk.DialogFlags.DESTROY_WITH_PARENT, border_width=5)

        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(800, 500)

        content = self.get_content_area()
        content.set_spacing(2)

        hbox = Gtk.Box()
        content.pack_start(hbox, True, True, 0)

        window = Gtk.ScrolledWindow(
            border_width=5, shadow_type=Gtk.ShadowType.IN)
        self.create_shortcut_list()
        window.add(self.view)
        hbox.pack_start(window, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
            border_width=5, spacing=10)
        hbox.pack_start(vbox, False, False, 0)

        button = Gtk.Button(label="Use Default")
        button.connect("clicked", self.use_default)
        vbox.pack_start(button, False, False, 0)

        button = Gtk.Button(label="Use Orthodox")
        button.connect("clicked", self.use_orthodox)
        vbox.pack_start(button, False, False, 0)

# Keyboard shortcuts dialog is global because shortcuts apply for a
# whole application, not to a single window.
shortcuts_dialog = None

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
            if SHOW_EXTRA_PANE:
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

        accel_group = Gtk.accel_groups_from_object(window)[0]

        def connect(accel, func):
            key, mods = Gtk.accelerator_parse(accel)
            accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE, func)

        connect('F4', self.on_edit)

        if self.loc_entry1 != None:
            # TODO: look how nautilus-open-terminal work
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
                elif name == 'Trash':
                    connect('F8', self.on_delete)
                    self.delete_menuitem = w
                elif name == 'Edit':
                    item = Gtk.MenuItem(
                        "_Keyboard Shortcuts...", use_underline=True)
                    w.add(item)
                    item.show()
                    item.connect('activate',
                        self.show_keyboard_shortcuts_dialog)

        if DEBUG:
            # Add the widget inspector.
            from nautilus_debug import WidgetInspector
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

    def show_keyboard_shortcuts_dialog(self, widget):
        global shortcuts_dialog
        if shortcuts_dialog:
            shortcuts_dialog.present()
            return
        with catch_all():
            shortcuts_dialog = KeyboardShortcutsDialog(self.window)
            shortcuts_dialog.show_all()
            shortcuts_dialog.run()
            shortcuts_dialog.destroy()
        shortcuts_dialog = None

class WidgetProvider(GObject.GObject, Nautilus.LocationWidgetProvider):
    def __init__(self):
        with catch_all():
            self._loaded_accels = False
            self._window_agents = {}
            if DEBUG:
                # The nautilus_debug package is only imported in DEBUG mode to
                # avoid dependency on twisted for normal use.
                from nautilus_debug import SSHThread
                SSHThread(self._window_agents).start()

    def get_widget(self, uri, window):
        with catch_all():
            if not self._loaded_accels:
                self._loaded_accels = True
                load_accels(ACCEL_FILE_NAME)
            if uri == "x-nautilus-desktop:///":
                return None
            agent = self._window_agents.get(window)
            if agent != None:
                return None
            window.connect("destroy", lambda w: self._window_agents.pop(w))
            agent = WindowAgent(window)
            self._window_agents[window] = agent
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
