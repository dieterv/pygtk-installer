#!/bin/bash

CHECKOUT="/d/dev/gnome.org/gnome-windows/checkout"
TMPDIR="/d/dev/gnome.org/pygtk-installer/tmp/build"
DESTDIR="/d/dev/gnome.org/pygtk-installer/dist"
INTERPRETERS="/d/bin/Python26 /d/bin/Python27"
GTKBUNDLE="/d/bin/Python27/Lib/site-packages/gtk-2.0/runtime/"
# Or instead of using the gtk+-bundle included in the pygtk all-in-one
# installer you could use a gtk+-bundle from ftp.gnome.org.
# Both are identical.
# GTKBUNDLE="/d/dev/gnome.org/gtk+-bundle_2.22.0-20101016_win32"

MOD=glade3
VER=3.6.7
REV=1 # Always starts from 1 for each VER
ARCH=win32

DESTDIR=${DESTDIR}/`date +%Y%m%d-%H%M%S`
OLD_CWD=`pwd`
OLD_PATH=${PATH}
OLD_PKG_CONFIG_PATH=${PKG_CONFIG_PATH}

#################################################################
# Build Glade without Python support                            #
#################################################################
export PATH=${GTKBUNDLE}/bin:${OLD_PATH}
export PKG_CONFIG_PATH=${GTKBUNDLE}/lib/pkgconfig/:${OLD_PKG_CONFIG_PATH}

THIS=${MOD}-${VER}-${REV}.${ARCH}
MFT=${MOD}_${VER}-${REV}_${ARCH}.mft
BUILD=${MOD}_${VER}-${REV}_${ARCH}.sh
ZIP=${MOD}-${VER}-${REV}.${ARCH}.zip

PREFIX=${TMPDIR}/${THIS}

if test -d "${PREFIX}"; then
    rm -rf "${PREFIX}"
fi

LOG=${PREFIX}/src/glade3/${THIS}.log
mkdir -p "${PREFIX}/src/glade3/"

(
    set -x
    mkdir -p "${DESTDIR}"
    cd "${CHECKOUT}/${MOD}-${VER}"

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
    --disable-python \
    --disable-static \
    --prefix="${PREFIX}" &&

    make -j3 install &&

    # No thanks
    rm -rf ${PREFIX}/lib/glade3/modules/*.dll.a &&
    rm -rf ${PREFIX}/lib/glade3/modules/*.la &&

    # Create a manifest
    mkdir "${PREFIX}/manifest" &&
    touch "${PREFIX}/manifest/${MFT}" &&

    # Copy build script
    cp "${CHECKOUT}/${MOD}-${VER}/build/mswindows/build_glade.sh" "${PREFIX}/src/glade3/${BUILD}"
) 2>&1 | tee "${LOG}"

# Write manifest and create zip archive...
cd "${PREFIX}" &&
find -type f -print | sed "s/\.\///g" > "${PREFIX}/manifest/${MFT}"
zip "${DESTDIR}/${ZIP}" -q -r ./*

#################################################################
# Build Glade with Python support                               #
#################################################################
for INTERPRETER in ${INTERPRETERS}; do
    export PATH=${INTERPRETER}:${INTERPRETER}/Scripts:${GTKBUNDLE}/bin:${OLD_PATH}
    export PKG_CONFIG_PATH=${INTERPRETER}/Lib/pkgconfig/:${GTKBUNDLE}/lib/pkgconfig/:${OLD_PKG_CONFIG_PATH}

    len=${#INTERPRETER}
    INTERPRETER_VERSION=$(echo "$INTERPRETER"|cut -c"$((len-1))"-"$len")
    THIS=${MOD}-${VER}-${REV}.${ARCH}-py${INTERPRETER_VERSION}
    MFT=${MOD}_${VER}-${REV}_${ARCH}_py${INTERPRETER_VERSION}.mft
    BUILD=${MOD}_${VER}-${REV}_${ARCH}_py${INTERPRETER_VERSION}.sh
    ZIP=${MOD}-${VER}-${REV}.${ARCH}-py${INTERPRETER_VERSION}.zip

    PREFIX=${TMPDIR}/${THIS}

    if test -d "${PREFIX}"; then
        rm -rf "${PREFIX}"
    fi

    LOG=${PREFIX}/src/glade3/${THIS}.log
    mkdir -p "${PREFIX}/src/glade3/"

    (
        set -x
        mkdir -p "${DESTDIR}"
        cd "${CHECKOUT}/${MOD}-${VER}"

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

        make -j3 install &&

        # No thanks
        rm -rf ${PREFIX}/lib/glade3/modules/*.dll.a &&
        rm -rf ${PREFIX}/lib/glade3/modules/*.la &&

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
" > "${PREFIX}/bin/glade-3.exe.manifest" &&

        # Create a manifest
        mkdir "${PREFIX}/manifest" &&
        touch "${PREFIX}/manifest/${MFT}" &&

        # Copy build script
        cp "${CHECKOUT}/${MOD}-${VER}/build/mswindows/build_glade.sh" "${PREFIX}/src/glade3/${BUILD}"
    ) 2>&1 | tee "${LOG}"

    # Write manifest and create zip archive...
    cd "${PREFIX}" &&
    find -type f -print | sed "s/\.\///g" > "${PREFIX}/manifest/${MFT}" &&
    zip "${DESTDIR}/${ZIP}" -q -r ./*

done
