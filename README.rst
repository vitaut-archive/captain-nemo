Captain Nemo
============

Captain Nemo is an extension which converts Nautilus into a two-panel
(orthodox) file manager.

Usage
-----

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

