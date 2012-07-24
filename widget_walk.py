from gi.repository import Gtk

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
