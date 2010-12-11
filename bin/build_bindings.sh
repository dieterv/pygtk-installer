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
# build_bindings.sh is a script for building the
# Py{Cairo, GObject, GTK, GooCanvas, GtkSourceView, Rsvg}
# installers using MinGW/MSYS.
# This script has been tested with MSYS on MS Windows,
# but should work fine via wine on a Linux distribution.

# How does it work?
# =================
# Install the deps (gtk+-bundle, ...) and MinGW/MSYS with GCC 4.5.0
#   $ mingw-get.exe install gcc
#   $ mingw-get.exe install msys-base
#
# Configure the CHECKOUT, DESTDIR and INTERPRETERS and GTKBUNDLE
# variables in the build.conf file
#
# To build all installers, execute
#   $ ./build_bindings.sh
#
# To build specific (but known!) targets, execute
#   $ ./build_bindings.sh pygobject pygtk
# or
#   $ ./build_bindings.sh pygoocanvas
# or ... well, you get the idea


# Load "configuration"
source ../etc/build_env.conf

TARGETS="pycairo-1.8.10 pygobject pygtk pygoocanvas pygtksourceview gnome-python-desktop"
DESTDIR=${DESTDIR}/`date +%Y%m%d-%H%M%S`
OLD_CWD=`pwd`
OLD_PATH=${PATH}
OLD_PKG_CONFIG_PATH=${PKG_CONFIG_PATH}

# check script arguments for specific targets
ARG_TARGETS=""

# create destdir
mkdir -p ${DESTDIR}

if [ $# -gt 0 ]; then
    for ARG in $@; do
        for i in ${TARGETS[@]}; do
            if [[ $i == ${ARG} ]] ; then
                ARG_TARGETS+=${ARG}" "
            fi
        done
    done

    TARGETS=${ARG_TARGETS}
fi

# build each target
for TARGET in ${TARGETS}; do
    TARGETROOT=${CHECKOUT}/${TARGET}

    if [ ! -d "${TARGETROOT}" ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "! Could not build \"${TARGET}\": \"${TARGETROOT}\" does not exist."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        continue
    fi

    if [ ! -f "${TARGETROOT}/setup.py" ]; then
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "! Could not build \"${TARGET}\": \"${TARGETROOT}/setup.py\" does not exist."
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        continue
    fi

    if [ ${TARGET} = "pygtk" ]; then
       # pygtk takes extra arguments
       COMMAND="setup.py build --compiler=mingw32 --enable-threading bdist_wininst --user-access-control=auto bdist_msi"
    else
       COMMAND="setup.py build --compiler=mingw32 bdist_wininst --user-access-control=auto bdist_msi"
    fi

    cd ${TARGETROOT}
    rm -rf ${TARGETROOT}/build/*
    rm -rf ${TARGETROOT}/dist/*

    for INTERPRETER in ${INTERPRETERS}; do
        echo "**********************************************************************"
        echo "* Building \"${TARGET}\" for \"${INTERPRETER}\""
        echo "**********************************************************************"

        export PATH=${INTERPRETER}:${INTERPRETER}/Scripts:${GTKBUNDLE}/bin:${OLD_PATH}
        export PKG_CONFIG_PATH=${INTERPRETER}/Lib/pkgconfig/:${GTKBUNDLE}/lib/pkgconfig/:${OLD_PKG_CONFIG_PATH}

        ${INTERPRETER}/python.exe ${COMMAND}

        INSTALLERS=()
        for i in dist/*.exe; do INSTALLERS+=( ${i%} ); done
        mv dist/* ${DESTDIR}
        if [ ${#INSTALLERS[*]} -gt 0 ]; then
            for INSTALLER in ${INSTALLERS}; do
                result=`${DESTDIR}/$(basename ${INSTALLER})`
            done
        else
            echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            echo "! Building \"${TARGET}\" failed"
            echo "! Press any key to continue..."
            echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            read -p ""
            continue
        fi
    done
done

# cleanup
export PATH=${OLD_PATH}
export PKG_CONFIG_PATH=${OLD_PKG_CONFIG_PATH}
cd ${OLD_CWD}
