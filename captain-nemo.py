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

import os, subprocess, urllib
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

# Widget inspector provides a view of the widget tree.
# It is used in the debug mode (when DEBUG is True).
class WidgetInspector(Gtk.Paned):
    def __init__(self, window):
        Gtk.Paned.__init__(self)
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

        # Create panes.
        self.property_store = Gtk.TreeStore(str, str)
        self.highlighted_widgets = []
        self.pack1(self.create_widget_tree(window))
        notebook = Gtk.Notebook()
        self.doc_buffer = Gtk.TextBuffer()
        text_view = Gtk.TextView(buffer=self.doc_buffer)
        win = Gtk.ScrolledWindow()
        win.add(text_view)
        notebook.append_page(win, Gtk.Label('Documentation'))
        notebook.append_page(self.create_property_list(), Gtk.Label('Members'))
        self.pack2(notebook)
        self.set_size_request(0, 200)
        self.set_position(250)
        self.show_all()

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

    def collect_widgets_info(self, widget, iterator):
        if widget == None:
            return
        name = widget.get_name()
        iterator = self.widget_tree_store.append(iterator, [name, widget])
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                self.collect_widgets_info(child, iterator)
        if isinstance(widget, Gtk.MenuItem):
            self.collect_widgets_info(widget.get_submenu(), iterator)

    def highlight(self, widget):
        if widget == self:
            return
        widget.get_style_context().add_provider(self.highlight_style_provider, \
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.highlighted_widgets.append(widget)
        if not isinstance(widget, Gtk.Container):
            return
        for child in widget.get_children():
            self.highlight(child)

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
        self.highlight(widget)

    def on_refresh(self, menuitem):
        self.unhighlight()
        self.widget_tree_store.clear()
        self.collect_widgets_info(self.window, None)
        self.widget_tree.expand_to_path(Gtk.TreePath('0:0:0:0'))

class WindowAgent:
    def __init__(self, window):
        self.window = window
        self.accel_group = Gtk.AccelGroup()
        self.connect('F3', self.on_edit)
        self.connect('F4', self.on_edit)
        self.connect('<Ctrl>O', self.on_terminal)
        self.connect('<Ctrl>G', self.on_git)
        window.add_accel_group(self.accel_group)

        self.find_widgets(window)
        self.show_extra_pane(self.menubar)

        # Remove the accelerator from the 'Show Hide Extra Pane' action.
        Gtk.AccelMap.change_entry(
            '<Actions>/ShellActions/Show Hide Extra Pane', 0, 0, True)

        # Add accelerators to the "Copy/Move to next pane" action.
        accel_map = Gtk.AccelMap.get()
        key, mods = Gtk.accelerator_parse('F5')
        accel_map.add_entry('<Actions>/DirViewActions/Copy to next pane',
            key, mods)
        key, mods = Gtk.accelerator_parse('F6')
        accel_map.add_entry('<Actions>/DirViewActions/Move to next pane',
            key, mods)

        self.loc_entry1 = self.find_loc_entry(self.main_paned.get_child1())
        self.loc_entry2 = self.find_loc_entry(self.main_paned.get_child2())

        if not DEBUG:
            return

        # Add the widget inspector.
        child = window.get_child()
        inspector = WidgetInspector(window)
        window.remove(child)
        paned = Gtk.VPaned()
        paned.pack1(child, True, True)
        paned.pack2(inspector, False, False)
        paned.show()
        window.add(paned)

    # Finds the main paned widget and the menubar.
    def find_widgets(self, widget):
        if widget == None:
            return
        name = widget.get_name()
        if name == 'NautilusToolbar':
            w = widget.get_parent()
            while not isinstance(w, Gtk.Paned):
                w = w.get_parent()
            self.main_paned = w
            return
        if name == 'MenuBar':
            self.menubar = widget
            return
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                self.find_widgets(child)

    def show_extra_pane(self, widget):
        if widget == None:
            return False
        name = widget.get_name()
        if isinstance(widget, Gtk.MenuItem):
            if name == 'Show Hide Extra Pane':
                widget.activate()
                return True
            found = self.show_extra_pane(widget.get_submenu())
            if found:
                return True
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                found = self.show_extra_pane(child)
                if found:
                    return True 
        return False

    def find_loc_entry(self, widget):
        if widget == None:
            return None
        name = widget.get_name()
        if name == 'NautilusLocationEntry':
            return widget
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                result = self.find_loc_entry(child)
                if result != None:
                    return result
        return None

    def connect(self, accel, func):
        key, mods = Gtk.accelerator_parse(accel)
        self.accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE, func)

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
        if uri == 'x-nautilus-desktop:///':
            return None
        agent = self.window_agents.get(window)
        if agent != None:
            return None
        window.connect('destroy', lambda w: self.window_agents.pop(w))
        agent = WindowAgent(window)
        self.window_agents[window] = agent
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
