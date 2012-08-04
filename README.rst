Captain Nemo
============

Captain Nemo is an extension which converts Nautilus into a two-panel
(orthodox) file manager.

Features
--------

* Keyboard shortcuts editor with two presets (Default and Orthodox):

.. image:: https://github.com/vitaut/captain-nemo/raw/master/img/keyboard-shortcuts-menu.png

.. image:: https://github.com/vitaut/captain-nemo/raw/master/img/keyboard-shortcuts-dialog.png

* Two-panel view (automatically restored):

.. image:: https://github.com/vitaut/captain-nemo/raw/master/img/two-panel-view.png

* Keyboard shortcuts in Orthodox mode:

======  ==========================================================
Key     Operation
======  ==========================================================
Ctrl+O  Open terminal in the current directory of the active panel
F3      View - currently opens the selected file in Gedit
F4      Edit - currently opens the selected file in Gedit
F5      Copy to another panel
F6      Move to another panel
F7      Create directory
F8      Delete selected files and directories
======  ==========================================================

Installation
------------

1. Install `Python bindings for the Nautilus Extension API
   <http://projects.gnome.org/nautilus-python/>`_ and introspection
   data for GConf using the `python-nautilus <apt://python-nautilus>`_
   and `gir1.2-gconf-2.0 <apt://gir1.2-gconf-2.0>`_ links or the following
   command::

     sudo apt-get install python-nautilus gir1.2-gconf-2.0

   Note that Captain Nemo requires at least version 1.0-0ubuntu2 of the
   ``python-nautilus`` package in Ubuntu.

2. Save `captain_nemo.py
   <https://raw.github.com/vitaut/captain-nemo/master/captain_nemo.py>`_ to
   ``~/.local/share/nautilus-python/extensions/``

3. Restart nautilus::

     nautilus -q
     nautilus &

Authors
-------

Victor Zverovich
~~~~~~~~~~~~~~~~

* https://github.com/vitaut
* http://zverovich.net

License
-------

Copyright 2011 Victor Zverovich

Licensed under the `GNU General Public License, version 2
<http://www.gnu.org/licenses/gpl-2.0.html>`_

