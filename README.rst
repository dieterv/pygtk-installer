=======
WARNING
=======

The all-in-one installer should be considered as a proof of concept.
Please do not use it on productions systems just yet!

===============
pygtk-installer
===============

The pygtk-installer project provides a set of tools to build the PyGTK
all-in-one installer and it's various dependencies.
There are currently versions of the all-in-one installer targeting Python 2.6
and Python 2.7.

Included tools:

- build_glade.sh: a tool that builds glade3 binaries for mswindows with
  "Python Widgets Support" for each supported Python version.
- build_bindings.sh: a tool that builds windows installer packages (both .exe
  and .msi) for pycairo, pygobject, pygtk, pygoocanvas, pygtksourceview and
  pyrsvg for each supported Python version.
- build_installer.py: a tool that generates an all-in-one installer bundling
  the separate .msi installers created by build_bindings.sh, the glade binaries
  created by build_glade.sh and various gtk+ runtime packages from
  ftp.gnome.org/pub/GNOME/binaries/win32/.

=============================
Things you might want to know
=============================

#. Make absolutely sure the separate pycairo, pygtk, pygobject, etc packages
   are uninstalled. The all-in-one installer does not check for their presence
   and will happily overwrite files that belong to them. If you forget to check
   for this you risk the following scenario:

       - install Python
       - install pycairo, pygtk and pygobject
       - install pygtk all-in-one
       - uninstall pycairo, pygtk and pygobject
       ... you now have a *broken* pygtk all-in-one installation

#. You no longer need to fiddle with the PATH environment variable. Ever.
   The pygtk version that's installed with the all-in-one installer
   takes care of loading the included gtk+ runtime on the PATH environment
   variable on interpreter startup. As a consequence simply importing gobject,
   gtk, etc works out of the box. As an added advantage there is no possible way
   a different gtk+ runtime can interfere with pygtk all-in-one.

#. I lied. If you have used the separate pygtk, pygobject and pycairo installers
   but decide to migrate to the pygtk all-in-one installer, now is a good time to
   clean your system or user PATH environment variable.

#. If something doesn't work as expected:

       - unsinstall pygtk all-in-one
       - install pygtk all-in-one with the following command (from a "Command Prompt" aka cmd.exe)::

           %WINDIR%\system32\msiexec.exe -i pygtk-all-in-one-2.22.X.win32-py2.X.msi /l*vx install.log

       - then run Python with the following command (from a "Command Prompt" aka cmd.exe)::

           python -v -c "import gtk">import.log 2>&1

       - study both install.log and import.log...

==========
Versioning
==========

The all-in-one installers' version number does not map directly to the
pygtk version number. This is a requirement to support windows installer
major upgrades. The version number is constructed as follows::

    PYGTK_MAJOR.PYGTK_MINOR.INSTALLER_REVISION

Stable releases are kept available for download, testing revisions are removed
from the download area once they are superseeded by newer versions.
