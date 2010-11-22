===============
pygtk-installer
===============

The pygtk-installer project provides:

- build_glade.sh: a tool that builds glade3 binaries for mswindows with
  "Python Widgets Support".
- build_bindings.sh: a tool that builds windows installer packages (both .exe
  and .msi) for pycairo, pygobject, pygtk, pygoocanvas, pygtksourceview and pyrsvg.
- build_installer.py: a tool that generates an all-in-one installer bundling
  the separate .msi installers created by build_bindings.sh and the gtk+ runtime
  packages from ftp.gnome.org/pub/GNOME/binaries/win32/.

=======
WARNING
=======

The all-in-one installer should be considered as a proof of concept.
Please do not use it on productions systems just yet.

If you decide to give it a test anyway:

#. Make absolutely sure the separate pycairo, pygtk, pygobject, etc
   packages are uninstalled. The all-in-one installer does not yet
   check for their presence and will happily overwrite them.
#. You no longer need to fiddle with the PATH environment variable.
   The pygtk version that's installed with the all-in-one installer
   should take care of loading the included gtk+ runtime on PATH
   when you import pygtk; pygtk.require('2.0'). As a consequence
   simply importing gobject, gtk, etc *might* not work without
   the .require() call. The .require() call is typically done only
   once in a startup script somewhere.
#. Why did you say "*might* not work" above? Ah, good question. If
   you've got another gtk+ runtime on your PATH environment variable - for
   example you installed Dia, MonoDevelop (gtk#), etc. - the PyGtk bindings might
   use one of those runtime libraries. In that case the behavior of the PyGtk
   bindings is unspecified (it might crash, error out, etc.).
#. If it doesn't work, consider executing the following and study the
   output::

       $ python -v
       >>> import pygtk
       >>> pygtk.require('2.0)
