=======================================
Creating the PyGTK All-in-one installer
=======================================

This document describes how to build the various components included
with the PyGTK All-in-one installer and the installer itself from scratch.


Preparations
============

Unless stated otherwise, everything is this document assumes you'll be working
from an MSYS Bash session running inside a plain old Command Prompt
(aka cmd.exe). MSYS rxvt, Console2 and other console helpers are to be avoided.

MinGW/MSYS developers recommend you to install into C:\MinGW\. Python installs
by default into C:\Python2X. Sometimes installing directly into the C: volume
is not possible. Any other location is just fine as long as you keep in mind
that unless stated otherwise, the installation path for the tools described in
this document should *not* contain spaces. Another little detail to watch out
for is that no paths listed in the PATH environment variable should contain
spaces. Adjust your system and user PATH via the Control Panel as needed.

This document will list the default and recommended installation paths for
everything. You can adjust as needed. For reference, my tools live in
D:\bin\MinGW, D:\bin\Python26, D:\bin\Python27, D:\bin\Windows Installer XML v3.5, etc.

The following list of steps should get you up to speed:

 - Download mingw-get.exe from http://sourceforge.net/projects/mingw/files/ into
   C:\MinGW\bin\ and execute (from a Command Prompt)::

       $ mingw-get.exe install gcc
       $ mingw-get.exe install msys-base

 - Install msys-git

 - Install Python 2.6 into C:\Python26 and Python 2.7 into C:\Python27.

 - Install numpy for both Python 2.6 and 2.7

 - Install lxml for the Python version you'll use to run the build_isntaller.py
   script (Python 2.7 is preferred)

 - As we're building everything from scratch, you'll need to construct a GTK+
   runtime environment by hand. Refer to wix/2.24.0.win32.xml for a list of
   packages you'll need (obviously, you can ignore the Python bindings packages).
   Install these into C:\GTK+-2.24

 - Install WiX 3.5.2519.0 into C:\Windows Installer XML v3.5


Building Python Bindings
========================

The first step in creating the PyGTK All-in-one installer is to build
the Python bindings packages that we'll be including. Follow these steps::

    - Uninstall all versions of pycairo, pygobject, pygtk, etc. for both
      Python 2.6 and Python 2.7. Even older version of the PyGTK All-in-one
      installer have to be removed.
    - Edit bin/build.conf (all paths should be listed in MSYS notation):

        * CHECKOUT    : is the directory where the source code for the bindings
                        packages lives
        * DESTDIR     : is the directory where built distutils .exe and .msi
                        installers will be copied to
        * INTERPRETERS: list of Python 2.6 and 2.7 installation directories
        * GTKBUNDLE   : location of the GTK+ runtime environment you've manually
                        constructed

    - Get the source code for the bindings packages:

        * download and extract pycairo-1.8.10.tar.gz into CHECKOUT and
          apply pycairo-1.8.10_setup.patch TODO:
        * git clone pygobject && git checkout windows origin/windows
        * git clone pygtk && git checkout windows origin/windows
        * git clone pygoocanvas && git checkout windows origin/windows
        * git clone pygtksourceview && git checkout windows origin/windows
        * git clone gnome-python-desktop && git checkout windows origin/windows

    - From an msys bash session, execute "./build_bindings.sh". It will
      automatically build all targets. The script also accepts a list of target
      names as arguments, so when doing maintenance builds you can for example
      execute "./build_bindings.sh pygobject pygtk" to build pygobject and pygtk.

    - During the above "./build_bindings.sh" build procedure, each package's
      newly created installer will be executed. You really need to do this,
      as for example pygtk's build procedure needs pygobject's codegen etc
      (and remember we're building everything from scratch!).

    - Execute Lib/site-packages/gtk-2.0/tests/pygobject and Lib/site-packages/gtk-2.0/tests/pygtk
      with both Python 2.6 and Python 2.7.

    - Execute the included demos for each package and make sure for example
      pyrsvg, pygoocanvas, pygtksourceview, etc work as intended.

If you got here: congratulations, you've just succeeded building Python bindings
on Windows! If you're beginning to feel uneasy, remember nobody said this
was going to be quick or easy. Hang in there, you're almost there!


Building the PyGTK All-in-one installer
=======================================

Now that you've got the installers built for the Python bindings packages we
can continue and build the integrated All-in-one installer. This is done by
a "WiX pre-processor (TODO: invent a better name)" called build_installer.py.

Usage is defined as follows::

    build_installer.py [options] moduleset

    Currently, there's a single option (-p or --pretend) enabling build_installer.py
    to skip WiX compiling and linking steps. This is useful if you want to download
    and check the integrity of the packages that will be included or if you want
    to debug the generated .wxs as .wxi files.

    Moduleset is the name of the file (without .xml) that contains the set of
    modules that need to be included in the aio installer. These moduleset files
    live in the wix directory.

To build the aio installer, follow these steps (replace X with appropriate values)::

    - Edit wix/2.24.X.winXX.xml
    - Run ./build_installer.py 2.24.X.winXX
    - pygtk-all-in-one-2.24.X.winXX.pyX.X.msi and related files are created in
      tmp/winxx-pyX.X/pygtk-all-in-one-2.24.X.winXX.pyX.X/

Enjoy :)
