BuzzRef — A Feature-Enhanced Reference Image Viewer
====================================================

.. raw:: html

   <img align="left" width="100" height="100" src="https://raw.githubusercontent.com/kistf001/buzzref/main/buzzref/assets/logo.png">

**BuzzRef** is an actively maintained fork of `BuzzRef <https://github.com/rbreu/buzzref>`_ by Rebecca Breu, released under GPL-3.0.

This fork focuses on incorporating community contributions, bug fixes, and new features that enhance the creative workflow.

|python-version| |github-ci-flake8| |github-ci-pytest|

.. image:: https://github.com/rbreu/buzzref/blob/main/images/screenshot.png

.. |python-version| image:: https://img.shields.io/badge/python-3.9%2B-blue
   :target: https://www.python.org/

.. |github-ci-flake8| image:: https://github.com/kistf001/buzzref/actions/workflows/flake8.yml/badge.svg
   :target: https://github.com/kistf001/buzzref/actions/workflows/flake8.yml

.. |github-ci-pytest| image:: https://github.com/kistf001/buzzref/actions/workflows/pytest.yml/badge.svg
   :target: https://github.com/kistf001/buzzref/actions/workflows/pytest.yml


What's Different from BuzzRef
----------------------------

**New Features:**

* **Sketching/Drawing Mode** — Press ``D`` to enter draw mode. Supports tablet pressure sensitivity, customizable brush size and color
* **Movable Crop Rectangle** — Drag the crop area to reposition it before applying
* **Show Filename** — Press ``F`` to display the filename of selected image
* **Capture** — Capture scene area or screen with ``Shift+A``
* **PureRef Import** — Open ``.pur`` files directly to migrate from PureRef
* Improved pytest integration (command line flags no longer conflict)

**Compatibility:**

* Python 3.9+ support (including Python 3.13)
* Updated dependency constraints for better compatibility
* Improved web image download (ArtStation, Pinterest) with proper SSL and User-Agent handling


Installation
------------

Stable Release
~~~~~~~~~~~~~~

Get the file for your operating system (Windows, Linux, macOS) from the `latest release <https://github.com/kistf001/buzzref/releases>`_.

**Linux users** need to give the file executable rights before running it.

**MacOS X users**, look at `detailed instructions <https://buzzref.org/macosx-run.html>`_ if you have problems running BuzzRef.


Development Version
~~~~~~~~~~~~~~~~~~~

To get the current development version, you need to have a working Python 3.9+ environment::

  pip install git+https://github.com/kistf001/buzzref.git

Then run ``buzzref`` or ``buzzref filename.bee``.


Features
--------

* Move, scale, rotate, crop and flip images
* **NEW:** Sketch directly on the canvas with pressure-sensitive drawing
* **NEW:** Move crop rectangles before applying
* Mass-scale images to the same width, height or size
* Mass-arrange images vertically, horizontally or for optimal usage of space
* Add text notes
* Enable always-on-top-mode and disable the title bar to let the window unobtrusively float above your art program


Regarding the bee file format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All images are embedded into the bee file as PNG or JPG. The bee file format is a sqlite database inside which the images are stored in an sqlar table—meaning they can be extracted with the `sqlite command line program <https://www.sqlite.org/cli.html>`_::

  sqlite3 myfile.bee -Axv

Options for exporting from inside BuzzRef are planned, but the above always works independently of BuzzRef.


Troubleshooting
---------------

You can access the log output via *Help -> Show Debug Log*. In case BuzzRef doesn't start at all, you can find the log file here:

Windows:

  C:\Documents and Settings\USERNAME\Application Data\BuzzRef\BuzzRef.log

Linux and MacOS:

  /home/USERNAME/.config/BuzzRef/BuzzRef.log


Notes for developers
--------------------

BuzzRef is written in Python and PyQt6. For more info, see `CONTRIBUTING.rst <https://github.com/kistf001/buzzref/blob/main/CONTRIBUTING.rst>`_.


Credits
-------

* Original BuzzRef by `Rebecca Breu <https://github.com/rbreu>`_
* Sketching feature (`PR #150 <https://github.com/rbreu/buzzref/pull/150>`_) by `Cinderflame-Linear <https://github.com/Cinderflame-Linear>`_
* Crop rectangle improvements (`PR #115 <https://github.com/rbreu/buzzref/pull/115>`_) by `DarkDefender <https://github.com/DarkDefender>`_
* Pytest flag fix (`PR #117 <https://github.com/rbreu/buzzref/pull/117>`_) by `DarkDefender <https://github.com/DarkDefender>`_
* Show filename feature, SSL/User-Agent improvements by `g-rix <https://github.com/g-rix>`_
* PureRef file format library by `FyorDev <https://github.com/FyorDev/PureRef-format>`_ (MIT License)


License
-------

This project is licensed under the GPL-3.0 License - see the `LICENSE <LICENSE>`_ file for details.
