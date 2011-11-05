Captain Nemo
============

Captain Nemo is an extension which converts Nautilus into a two-panel
(orthodox) file manager.

Usage
-----

1. Install `Python bindings for the Nautilus Extension API
   <http://projects.gnome.org/nautilus-python/>`_::

     sudo apt-get install python-nautilus

   `Click here <apt:python-nautilus>`_ to install ``python-nautilus``.

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
