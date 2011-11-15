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
# exist commonly used alternative.
#
# In addition this extension defined the following keyboard shortcut:
#   Ctrl+G - open a git client in the current directory
# Also the Compare... item is added to the context menu.

import os, subprocess, urllib, traceback
from gi.repository import Nautilus, GObject, Gtk, Gdk, GConf
import collections

DIFF = 'meld'
GIT_CLIENT = 'gitg'
TERMINAL_KEY = '/desktop/gnome/applications/terminal/exec'
EDITOR = 'gedit'
DEBUG = False

def get_filename(file_info):
    return urllib.unquote(file_info.get_uri()[7:])

def has_file_scheme(f):
    return f.get_uri_scheme() == 'file'

# This class provides depth-first traversal of a widget tree using an iterator.
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

# Widget inspector provides a view of the widget tree.
# It is used in the debug mode (when DEBUG is True).
class WidgetInspector(Gtk.Notebook):
    def __init__(self, window):
        Gtk.Notebook.__init__(self)
        self.window = window
        self.highlight_style_provider = Gtk.CssProvider()
        self.highlight_style_provider.load_from_data(
            '* { background-color: #bcd5eb }')

        # Create popup menu.
        self.menu = Gtk.Menu()
        menuitem = Gtk.MenuItem(label='Refresh')
        menuitem.connect('activate', self.on_refresh)
        self.menu.append(menuitem)
        self.connect('button-press-event', self.on_button_press_event)
        self.connect('popup-menu', self.popup_menu)

        self.append_page(self.create_widget_page(), Gtk.Label('Widgets'))
        self.append_page(self.create_accelmap_page(),
            Gtk.Label('Accelerator Map'))
        self.append_page(self.create_accelgroup_page(),
            Gtk.Label('Accelerator Group'))
        self.show_all()

    def create_widget_page(self):
        self.property_store = Gtk.TreeStore(str, str)
        self.highlighted_widgets = []
        paned = Gtk.Paned()
        paned.pack1(self.create_widget_tree(self.window))
        notebook = Gtk.Notebook()
        self.doc_buffer = Gtk.TextBuffer()
        text_view = Gtk.TextView(buffer=self.doc_buffer)
        win = Gtk.ScrolledWindow()
        win.add(text_view)
        notebook.append_page(win, Gtk.Label('Documentation'))
        notebook.append_page(self.create_property_list(), Gtk.Label('Members'))
        paned.pack2(notebook)
        paned.set_size_request(0, 200)
        paned.set_position(250)
        return paned

    def create_accelmap_page(self):
        accel_store = Gtk.TreeStore(str, str)
        def add_accel(data, accel_path, accel_key, accel_mods, changed):
            label = Gtk.accelerator_get_label(accel_key, accel_mods)
            accel_store.append(None, [label, accel_path])
        Gtk.AccelMap.foreach(None, add_accel)
        tree = Gtk.TreeView(accel_store)
        tree.connect('button-press-event', self.on_button_press_event)
        column = Gtk.TreeViewColumn('Key', Gtk.CellRendererText(), text=0)
        tree.append_column(column)
        column = Gtk.TreeViewColumn('Path', Gtk.CellRendererText(), text=1)
        tree.append_column(column)
        win = Gtk.ScrolledWindow()
        win.add(tree)
        return win

    def create_accelgroup_page(self):
        accel_group = Gtk.accel_groups_from_object(self.window)[0]
        accel_store = Gtk.TreeStore(str, str)
        def add_accel(key, closure, data):
            label = Gtk.accelerator_get_label(key.accel_key, key.accel_mods)
            accel_store.append(None, [label, str(closure)])
        accel_group.find(add_accel, None)
        tree = Gtk.TreeView(accel_store)
        tree.connect('button-press-event', self.on_button_press_event)
        column = Gtk.TreeViewColumn('Key', Gtk.CellRendererText(), text=0)
        tree.append_column(column)
        column = Gtk.TreeViewColumn('Closure', Gtk.CellRendererText(), text=1)
        tree.append_column(column)
        win = Gtk.ScrolledWindow()
        win.add(tree)
        return win

    @staticmethod
    def get_members(cls):
        if cls == None:
            return []
        members = dir(cls)
        if cls.__gtype__.depth != 1:
            parent = cls.__gtype__.parent.pytype
            if parent != None:
                parent_members = frozenset(dir(parent))
                i = len(members) - 1
                while i >= 0:
                    if members[i] in parent_members:
                        del members[i]
                    i -= 1
        return members

    def create_widget_tree(self, window):
        self.widget_tree_store = Gtk.TreeStore(str, Gtk.Widget)
        self.widget_tree = Gtk.TreeView(self.widget_tree_store)
        self.widget_tree.connect('button-press-event', \
            self.on_button_press_event)
        self.widget_tree.set_headers_visible(False)
        column = Gtk.TreeViewColumn('Widget', Gtk.CellRendererText(), text=0)
        self.widget_tree.append_column(column)
        self.on_refresh(None)
        sel = self.widget_tree.get_selection()
        sel.connect('changed', self.on_widget_selection_changed)
        win = Gtk.ScrolledWindow()
        win.set_shadow_type(Gtk.ShadowType.IN)
        win.add(self.widget_tree)
        return win

    def create_property_list(self):
        tree = Gtk.TreeView(self.property_store)
        tree.connect('button-press-event', self.on_button_press_event)
        tree.set_headers_visible(False)
        column = Gtk.TreeViewColumn('Property', Gtk.CellRendererText(), text=0)
        tree.append_column(column)
        column = Gtk.TreeViewColumn('Value', Gtk.CellRendererText(), text=1)
        tree.append_column(column)
        win = Gtk.ScrolledWindow()
        win.add(tree)
        return win

    def unhighlight(self):
        for widget in self.highlighted_widgets:
            widget.get_style_context().remove_provider(self.highlight_style_provider)
        self.highlighted_widgets = []

    def popup_menu(self, widget):
        self.menu.popup(None, None, None, None, 0, 0)
        self.menu.show_all()

    def on_button_press_event(self, widget, event):
        if event.button == 3:
            self.popup_menu(widget)
            return True

    def on_widget_selection_changed(self, selection):
        self.property_store.clear()
        self.doc_buffer.set_text('')
        model, iterator = selection.get_selected()
        if iterator == None:
            return
        widget = model[iterator][1]
        doc = widget.__getattribute__('__doc__')
        gdoc = widget.__getattribute__('__gdoc__')
        if gdoc != doc and doc != None:
            gdoc += '\n' + '-' * 80 + '\n' + doc
        self.doc_buffer.set_text(gdoc)
        members = set(dir(widget))
        gtype = widget.__class__.__gtype__
        def get_value(name):
            try:
                w = widget
                return str(eval('w.' + name))
            except:
                return '<error>'
        while gtype.depth != 0:
            name = gtype.name
            type_members = WidgetInspector.get_members(gtype.pytype)
            gtype = gtype.parent
            if len(type_members) == 0:
                continue
            parent_iter = self.property_store.prepend(None)
            self.property_store.set_value(parent_iter, 0, name)
            if type_members == None:
                continue
            for m in type_members:
                members.discard(m)
                if m == '__doc__' or m == '__gdoc__':
                    value = '<string>'
                else:
                    value = get_value(m)
                self.property_store.append(parent_iter, [m, value])
        for m in members:
            self.property_store.append(None, [m, get_value(m)])
        self.unhighlight()
        walker = walk(widget)
        for w in walker:
            if w == self:
                walker.skip_children()
                continue
            w.get_style_context().add_provider(
                self.highlight_style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.highlighted_widgets.append(w)

    def on_refresh(self, menuitem):
        self.unhighlight()
        self.widget_tree_store.clear()
        parent_iters = [None]
        walker = walk(self.window)
        for w in walker:
            depth = walker.depth()
            name = w.get_name()
            it = self.widget_tree_store.append(parent_iters[depth], [name, w])
            if len(parent_iters) <= depth + 1:
                parent_iters.append(it)
            else:
                parent_iters[depth + 1] = it
        self.widget_tree.expand_to_path(Gtk.TreePath('0:0:0:0'))

class WindowAgent:
    def __init__(self, window):
        self.window = window
        self.loc_entry1 = self.loc_entry2 = None

        # Find the main paned widget and the menubar.
        main_paned = menubar = None
        walker = walk(window, False)
        for w in walker:
            name = w.get_name()
            if name == 'NautilusToolbar':
                p = w.get_parent()
                while not isinstance(p, Gtk.Paned):
                    p = p.get_parent()
                main_paned = p
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

        if main_paned != None:
            # Find location entries.
            self.loc_entry1 = self.find_loc_entry(main_paned.get_child1())
            self.loc_entry2 = self.find_loc_entry(main_paned.get_child2())
        else:
            print 'Main paned not found'

        # Remove the accelerator from the 'Show Hide Extra Pane' action (F3).
        Gtk.AccelMap.change_entry(
            '<Actions>/ShellActions/Show Hide Extra Pane', 0, 0, True)
        # Remove the accelerator from the Open action (Ctrl+O)
        Gtk.AccelMap.change_entry(
            '<Actions>/DirViewActions/Open', 0, 0, True)

        accel_group = Gtk.accel_groups_from_object(window)[0]

        def connect(accel, func):
            key, mods = Gtk.accelerator_parse(accel)
            accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE, func)

        connect('F3', self.on_edit)
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
        if self.show_dialog('Copy',
            'Do you want to copy selected files/directories?'):
            self.copy_menuitem.activate()
        return True

    def on_move(self, accel_group, acceleratable, keyval, modifier):
        if self.show_dialog('Move',
            'Do you want to move selected files/directories?'):
            self.move_menuitem.activate()
        return True

    def on_mkdir(self, accel_group, acceleratable, keyval, modifier):
        self.mkdir_menuitem.activate()
        return True

    def on_delete(self, accel_group, acceleratable, keyval, modifier):
        if self.show_dialog('Delete',
            'Do you want to move selected files/directories to trash?'):
            self.delete_menuitem.activate()
        return True

    def on_edit(self, accel_group, acceleratable, keyval, modifier):
        subprocess.Popen([EDITOR] + self.get_selection())
        return True

    def get_location(self):
        if self.loc_entry1.is_sensitive():
            entry = self.loc_entry1
        else:
            entry = self.loc_entry2
        return entry.get_text()

    def on_terminal(self, accel_group, acceleratable, keyval, modifier):
        terminal = GConf.Client.get_default().get_string(TERMINAL_KEY)
        os.chdir(self.get_location())
        subprocess.Popen([terminal])
        return True

    def on_git(self, accel_group, acceleratable, keyval, modifier):
        os.chdir(self.get_location())
        subprocess.Popen([GIT_CLIENT])
        return True

class WidgetProvider(GObject.GObject, Nautilus.LocationWidgetProvider):
    def __init__(self):
        self.window_agents = {}

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
