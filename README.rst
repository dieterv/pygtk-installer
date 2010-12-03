=======
WARNING
=======

The all-in-one installer should be considered as a proof of concept.
Please do not use it on production systems just yet!

====================================
Using the PyGTK All-in-one installer
====================================

The PyGTK All-in-one version number
===================================

The all-in-one installers' version number does not map directly to the
pygtk version number. This is a requirement to support windows installer
major upgrades. The version number is constructed as follows::

    PYGTK_MAJOR.PYGTK_MINOR.INSTALLER_REVISION

Stable releases are kept available for download, testing revisions are removed
from the download area once they are superseded by newer versions.

What file should I use?
=======================

All the .msi files are named as follows:

    pygtk-all-in-one-X.X.X.win32-py2.6.msi

Where X.X.X is the PyGTK All-in-one version number and
Y.Y is the Python version number the installer supports.

Migrating from pycairo+pygobject+pygtk packages
===============================================

If you have some or all of the separate pycaior, pygobject, pygtk, pygoocanvas,
pygtksourceview2 or pyrsvg packages, please ensure they are uninstalled before
you begin with the PyGTK All-in-one installer.

The all-in-one installer does not check for their presence and will happily
overwrite files that belong to the separate packages. If you forget to check
for this you risk the following scenario:

       - install Python
       - install pycairo, pygtk and pygobject
       - install pygtk all-in-one
       - uninstall pycairo, pygtk and pygobject
       you now have a *broken* pygtk all-in-one installation

Now would also be a good time to uninstall the gtk+ runtime you've used
with the separate pyg* packages and to clean your PATH environment variable.

Automatic installation
======================

An automatic PyGTK All-in-one installation automatically detects the correct
Python installation directory and if Python was installed for all users or just
yourself. These values are then used by the PyGTK All-in-one installer.

* If you want to generate a log file you can execute the following command from a
  Command Prompt (change X to the correct version numbers)::

    %WINDIR%\system32\msiexec.exe /i pygtk-all-in-one-X.X.X.winX-pyX.X.msi /l*v install.log

  Note that having an installation log is the only way we can provide help should
  something have gone wrong.

* If you do not want to generate an installation log file you can simply double
  click the .msi file that matches the Python version where you want to install PyGTK All-in-one.

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

=======================
Installer build scripts
=======================

The pygtk-installer project provides a set of tools to build the PyGTK
all-in-one installer and it's various dependencies.
There are currently versions of the all-in-one installer supporting Python 2.6
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
