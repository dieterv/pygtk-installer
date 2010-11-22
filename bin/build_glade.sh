#!/bin/bash

# Copyright © 2010 pygtk-installer Contributors
#
# This file is part of pygtk-installer.
#
# pygtk-installer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygtk-installer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygtk-installer. If not, see <http://www.gnu.org/licenses/>.

# What is this?
# =============
# build_glade.sh is a script for building glade3 with
# "python widgets support"

# How does it work?
# =================
# Install the deps (gtk+-bundle, ...) MinGW/MSYS with GCC 4.5.0
#   $ mingw-get.exe install gcc
#   $ mingw-get.exe install msys-base
#
# Configure the CHECKOUT, DESTDIR and INTERPRETERS and GTKBUNDLE
# variables in the etc/build_env.conf file
#
# To build glade for each python interpreter, execute
#   $ ./build_glade.sh

#################################################################
# Untill bug 634978 gets fixed you'll need to manually patch    #
# the configure script.                                         #
# https://bugzilla.gnome.org/show_bug.cgi?id=634978             #
#################################################################

# Load "configuration"
source build.conf

MOD=glade3
VER=3.6.7
REV=0
ARCH=win32

DESTDIR=${DESTDIR}/`date +%Y%m%d-%H%M%S`
OLD_CWD=`pwd`
OLD_PATH=${PATH}
OLD_PKG_CONFIG_PATH=${PKG_CONFIG_PATH}

for INTERPRETER in ${INTERPRETERS}; do
    export PATH=${INTERPRETER}:${INTERPRETER}/Scripts:${GTKBUNDLE}/bin:${OLD_PATH}
    export PKG_CONFIG_PATH=${INTERPRETER}/Lib/pkgconfig/:${GTKBUNDLE}/lib/pkgconfig/:${OLD_PKG_CONFIG_PATH}

    len=${#INTERPRETER}
    INTERPRETER_VERSION=$(echo "$INTERPRETER"|cut -c"$((len-1))"-"$len")
    THIS=${MOD}-${VER}-${REV}.${ARCH}-py${INTERPRETER_VERSION}
    ZIP=${MOD}-${VER}-${REV}.${ARCH}-py${INTERPRETER_VERSION}.zip

    PREFIX=${TMPDIR}/${THIS}

    if test -d "${PREFIX}"; then
        rm -rf "${PREFIX}"
    fi

    LOG=${PREFIX}/src/dieterv/${THIS}.log
    mkdir -p ${PREFIX}/src/dieterv/

    (
        set -x

        mkdir -p ${DESTDIR}
        mkdir -p "${PREFIX}"

        cd ${CHECKOUT}/${MOD}-${VER}       

        # Copied from tml@iki.fi's build scripts:
        # Don't do any relinking and don't use any wrappers in libtool. It
        # just causes trouble, IMHO.
        sed -e "s/need_relink=yes/need_relink=no # no way --tml/" \
            -e "s/wrappers_required=yes/wrappers_required=no # no thanks --tml/" \
            <ltmain.sh >ltmain.temp && mv ltmain.temp ltmain.sh

        lt_cv_deplibs_check_method="pass_all" \
        CC="gcc -mthreads" \
        CFLAGS=-O2 \
        PYTHON_INCLUDES="-I${INTERPRETER}/include/" \
        PYTHON_LIBS="-L${INTERPRETER}/libs/ -lpython${INTERPRETER_VERSION}" \
        PYTHON_LIB_LOC="${INTERPRETER}/libs/" \
        ./configure \
        --enable-debug=yes \
        --disable-static \
        --disable-gnome \
        --disable-gtk-doc \
        --enable-python \
        --disable-static \
        --prefix="${PREFIX}" &&

        make -j3 install        
    ) 2>&1 | tee "${LOG}"

    # Write a .exe.manifest file...
    echo "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<assembly xmlns=\"urn:schemas-microsoft-com:asm.v1\" manifestVersion=\"1.0\">
  <assemblyIdentity version=\"1.0.0.0\"
                    name=\"glade-3.exe\"
                    type=\"win32\" />
  <dependency>
    <dependentAssembly>
      <assemblyIdentity
        type=\"win32\"
        name=\"Microsoft.VC90.CRT\"
        version=\"9.0.21022.8\"
        processorArchitecture=\"*\"
        publicKeyToken=\"1fc8b3b9a1e18e3b\" />
    </dependentAssembly>
  </dependency>
</assembly>
" > "${PREFIX}/bin/glade-3.exe.manifest"

    # We don't need these for modules...
    rm -rf ${PREFIX}/lib/glade3/modules/*.dll.a
    rm -rf ${PREFIX}/lib/glade3/modules/*.la
    
    # Put everything in a zip archive...
    cd ${PREFIX}
    zip ${DESTDIR}/${ZIP} -r ./*
done
