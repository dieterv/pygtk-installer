===============
pygtk-installer
===============

The pygtk-installer project provides:

- build_bindings.sh: a tool that builds windows installer packages (both .exe
  and .msi) for pygtk and dependencies.
- build_installer.py: a tool that generates an all-in-one installer bundling
  the separate .msi installers created by build_bindings.sh and the gtk+ runtime
  from ftp.gnome.org/pub/GNOME/binaries/win32/.

=======
WARNING
=======

The all-in-one installer should be considered as a proof of concept.
Please do not use it on productions systems just yet.

If you decide to give it a test anyway:

#. Make absolutely sure the separate pycairo, pygtk, pygobject, etc
   packages are uninstalled. The all-in-one installer does not yet
   check for their presence and will happily overwrite them.
#. You no longer need to fiddle with PATH environment variables.
   The pygtk version that's installed with the all-in-one installer
   should take care of loading the included gtk+ runtime on PATH
   when you import pygtk; pygtk.require('2.0'). As a consequence
   simply importing gtk, gobject, etc might[1] not work without
   the .require() call. The .require() call is typically done only
   once in a startup script somewhere.
#. The all-in-one installer version will stay at 2.22.0.0 until
   there's a stable release. If you want to test newer snapshots
   when they get available, you'll first need to uninstall the
   previous one, either from the "add/remove program" control panel
   applet, or by executing the old versions .msi file and choosing
   the "Remove" option (just to be on the safe side)...
