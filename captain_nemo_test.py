#!/usr/bin/env python

from gi.repository import Gtk
from captain_nemo import walk
import unittest

class TestWalk(unittest.TestCase):

    def setUp(self):
        self.window = Gtk.Window()
        box = Gtk.Box()
        paned = Gtk.Paned()
        paned.add(Gtk.Button())
        box.add(paned)
        menubar = Gtk.MenuBar()
        menuitem = Gtk.MenuItem()
        menuitem.set_submenu(Gtk.Menu())
        menubar.add(menuitem)
        box.add(menubar)
        self.window.add(box)

    def test_default(self):
        tree_str = ''
        for w in walk(self.window):
            tree_str += w.get_name() + ' '
        self.assertEqual(tree_str,
            'GtkWindow GtkBox GtkPaned GtkButton ' +
            'GtkMenuBar GtkMenuItem GtkAccelLabel GtkMenu ')

    def test_submenu(self):
        tree_str = ''
        for w in walk(self.window, True):
            tree_str += w.get_name() + ' '
        self.assertEqual(tree_str,
            'GtkWindow GtkBox GtkPaned GtkButton ' +
            'GtkMenuBar GtkMenuItem GtkAccelLabel GtkMenu ')

    def test_no_submenu(self):
        tree_str = ''
        for w in walk(self.window, False):
            tree_str += w.get_name() + ' '
        self.assertEqual(tree_str,
            'GtkWindow GtkBox GtkPaned GtkButton ' +
            'GtkMenuBar GtkMenuItem GtkAccelLabel ')

    def test_break(self):
        tree_str = ''
        for w in walk(self.window):
            tree_str += w.get_name() + ' '
            if w.get_name() == 'GtkButton': break
        self.assertEqual(tree_str, 'GtkWindow GtkBox GtkPaned GtkButton ')

    def test_skip_children(self):
        tree_str = ''
        walker = walk(self.window)
        for w in walker:
            tree_str += w.get_name() + ' '
            if w.get_name() == 'GtkPaned': walker.skip_children()
        self.assertEqual(tree_str,
            'GtkWindow GtkBox GtkPaned ' +
            'GtkMenuBar GtkMenuItem GtkAccelLabel GtkMenu ')

    def test_depth(self):
        tree_str = ''
        walker = walk(self.window)
        for w in walker:
            tree_str += '%s %d ' % (w.get_name(), walker.depth())
        self.assertEqual(tree_str,
            'GtkWindow 0 GtkBox 1 GtkPaned 2 GtkButton 3 ' +
            'GtkMenuBar 2 GtkMenuItem 3 GtkAccelLabel 4 GtkMenu 4 ')

if __name__ == '__main__':
    unittest.main()
