# This module provides various debugging features for Nautilus, such as
# remote access to a Python shell running in Nautilus (manhole) and a
# widget inspector.

import time
from gi.repository import GObject, Gtk
from threading import Thread
from twisted.internet import reactor
from twisted.manhole import telnet
from widget_walk import walk

# A thread running a telnet server for remote access to a Python shell
# in Nautilus.
class TelnetThread(Thread):
    def __init__(self, window_agents):
        Thread.__init__(self)
        # Make sure this thread is a daemon not to prevent program exit.
        self.daemon = True
        factory = telnet.ShellFactory()
        port = reactor.listenTCP(2001, factory)
        factory.username = 'nemo'
        factory.password = 'nemo'
        factory.namespace['agents'] = window_agents
        # Starting the thread is not enough because the Python interpreter
        # is no running all the time and therefore the thread will not run
        # too. Workaround this by using a timer to run the interpreter
        # periodically.
        def timer():
            time.sleep(0.0001) # Yield to other threads.
            return True
        GObject.timeout_add(100, timer)

    def run(self):
        # Installing signal handlers is only allowed from the main thread.
        reactor.run(installSignalHandlers=0)

# Widget inspector provides a view of the widget tree.
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

