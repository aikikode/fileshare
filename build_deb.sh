#!/bin/bash -
#===============================================================================
#
#          FILE: build_deb.sh
#
#         USAGE: ./build_deb.sh
#
#   DESCRIPTION: Creates deb package
#
#        AUTHOR: Denis Kovalev (aikikode@gmail.com)
#===============================================================================

BUILDDIR="build"
OUTPUTDIR="dist"
APPNAME="indicator-fileshare"
VERSION=$(egrep "^VERSION =" ./${APPNAME} | egrep -o "[0-9\.]+")

mkdir -p ${BUILDDIR} ${OUTPUTDIR}
if [[ -d ${BUILDDIR} ]]
then
    rm -fr ${BUILDDIR}/*
    mkdir -p ${BUILDDIR}/usr/local/bin
    mkdir -p ${BUILDDIR}/usr/local/share/${APPNAME}/media
    mkdir -p ${BUILDDIR}/usr/share/applications
    mkdir -p ${BUILDDIR}/usr/share/doc/${APPNAME}

    cp ${APPNAME}          ${BUILDDIR}/usr/local/bin/
    cp ./icons/*.png       ${BUILDDIR}/usr/local/share/${APPNAME}/media/
    cp ./*.py              ${BUILDDIR}/usr/local/share/${APPNAME}/
    cp ${APPNAME}.desktop  ${BUILDDIR}/usr/share/applications/
    cp ./AUTHORS           ${BUILDDIR}/usr/share/doc/${APPNAME}/
    cp -r ./DEBIAN         ${BUILDDIR}/

    fakeroot dpkg-deb --build ${BUILDDIR} ${OUTPUTDIR}/indicator-fileshare-${VERSION}.deb
    rm -fr ${BUILDDIR}
else
    echo "Error: cannot create directory ${BUILDDIR}"
fi
