#!/usr/bin/env python

from gi.repository import Gtk
from captain_nemo import walk, ACCELS, change_accel, load_accels, save_accels
import unittest

class WalkTest(unittest.TestCase):

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

TEST_ACCEL_PATH = '<Actions>/Test'

class AccelTest(unittest.TestCase):
    def setUp(self):
        self.window = Gtk.Window()
        key, mods = Gtk.accelerator_parse('t')
        Gtk.AccelMap.change_entry(TEST_ACCEL_PATH, key, mods, True)

    def test_0_default_accels_empty(self):
        self.assertEqual({}, ACCELS)

    def test_change_existing_accel(self):
        known, key = Gtk.AccelMap.lookup_entry(TEST_ACCEL_PATH)
        self.assertTrue(known)
        self.assertEqual('t',
            Gtk.accelerator_name(key.accel_key, key.accel_mods))
        change_accel(TEST_ACCEL_PATH, 'q')
        self.assertEqual('q', ACCELS[TEST_ACCEL_PATH].current)
        self.assertEqual('t', ACCELS[TEST_ACCEL_PATH].default)

    def test_change_new_accel(self):
        path = '<Actions>/NewAction'
        known, key = Gtk.AccelMap.lookup_entry(path)
        self.assertFalse(known)
        self.assertEqual('',
            Gtk.accelerator_name(key.accel_key, key.accel_mods))
        change_accel(path, 'n')
        self.assertEqual('n', ACCELS[path].current)
        self.assertEqual('', ACCELS[path].default)

    def test_load_save_accels(self):
        change_accel(TEST_ACCEL_PATH, 'q')
        self.assertEqual('q', ACCELS[TEST_ACCEL_PATH].current)
        save_accels('test.accel')
        change_accel(TEST_ACCEL_PATH, 'p')
        self.assertEqual('p', ACCELS[TEST_ACCEL_PATH].current)
        load_accels('test.accel')
        self.assertEqual('q', ACCELS[TEST_ACCEL_PATH].current)
        self.assertEqual('t', ACCELS[TEST_ACCEL_PATH].default)

    def test_load_save_accel_with_space(self):
        path = '<Actions>/Action With Space'
        change_accel(path, 'a')
        self.assertEqual('a', ACCELS[path].current)
        save_accels('test.accel')
        change_accel(path, 'b')
        self.assertEqual('b', ACCELS[path].current)
        load_accels('test.accel')
        self.assertEqual('a', ACCELS[path].current)

if __name__ == '__main__':
    unittest.main()
