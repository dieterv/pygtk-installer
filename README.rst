===============
pygtk-installer
===============

The pygtk-installer project provides:

- build_bindings.sh: a tool that builds windows installer packages (both .exe and .msi) for pygtk and dependencies.
- build_installer.py: a tool that generates an all-in-one installer bundling the separate .msi installers created by build_bindings.sh and the gtk+ runtime from ftp.gnome.org/pub/GNOME/binaries/win32/.

.. WARNING::
    The all-in-one installer should be considered as a proof of concept.
    Please do not use it on productions systems just yet.
