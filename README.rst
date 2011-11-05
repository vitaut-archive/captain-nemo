Captain Nemo
============

Captain Nemo is an extension which converts Nautilus into a two-panel
(orthodox) file manager.

Usage
-----

1. Install `Python bindings for the Nautilus Extension API
   <http://projects.gnome.org/nautilus-python/>`_ using 
   `this link <apt:python-nautilus>`_ or the following command::

     sudo apt-get install python-nautilus

   Note that Captain Nemo requires at least version 1.0-0ubuntu2 of the
   ``python-nautilus`` package in Ubuntu.

2. Copy `captain-nemo.py
   <https://raw.github.com/vitaut/captain-nemo/master/captain-nemo.py>`_ to
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

