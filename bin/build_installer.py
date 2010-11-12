#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


import os
import sys
import re

from copy import copy, deepcopy
from datetime import datetime
from hashlib import md5
from optparse import OptionParser
from os.path import abspath, dirname, isdir, isfile, join
from shutil import copyfile, rmtree
from subprocess import Popen, PIPE
from urllib2 import urlopen, URLError
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree, objectify


# Known Python target versions
PYTHON_VERSIONS = ['2.6', '2.7']
# Set to the target version when merging a Product
PYTHON_FULLVERSION = None
PYTHON_VERSION = None

# These paths are used all over the place
ROOTDIR = abspath(join(dirname(__file__), '..'))
ETCDIR = join(ROOTDIR, 'etc')
TMPDIR = join(ROOTDIR, 'tmp')
VARDIR = join(ROOTDIR, 'var')
CACHEDIR = join(VARDIR, 'cache')

# Everything we need to know about WiX and it's tools
WIX_VERSION = '3.5.2305.0'
WIX_NAMESPACE = 'http://schemas.microsoft.com/wix/2006/wi'
WIX_NSMAP = {None : WIX_NAMESPACE}
WIX_DIR = None
WIX_HEAT = None
WIX_DARK = None
WIX_CANDLE = None
WIX_LIGHT = None

# Everything we need to know about xmllint
XML_LINT_VERSION = 20707
XML_LINT = 'xmllint'


def info(message, level=0):
    print '%s* %s' %  ('  ' * level, message)

def error(message, level=0):
    message = '%s! %s' %  ('  ' * level, message)
    raise SystemExit(message)

def generate_uuid():
    return '{%s}' % str(uuid4()).upper()

def xmllint_format(src_file, dest_file, logfile):
    file = open(logfile, 'w')
    process = Popen([XML_LINT,
                     '--nonet',
                     '--format',
                     src_file,
                     '--output',
                     dest_file],
                    stdout=file,
                    stderr=file,
                    universal_newlines=True)
    process.wait()
    file.close()


class Builder(object):
    def __init__(self, arguments=None):
        self.parse_options(arguments)
        self.parse_configuration()
        self.validate_environment()

    def parse_options(self, arguments=None):
        if arguments == None:
            arguments = sys.argv[1:]

        parser = OptionParser(usage='usage: %prog [options] config')
        parser.add_option('-k', '--keep-work',
                  action='store_true', dest='keep_work', default=False,
                  help='keep working directory after build')

        (self.options, self.args) = parser.parse_args(arguments)

        if not len(self.args) == 1:
            error(parser.get_usage())

    def parse_configuration(self):
        version, platform = self.args[0].split('-')

        configfilename = '%s-%s.xml' % (version, platform)
        templatefilename = '%s-%s.template.wxs' % (version, platform)
        configfile = join(ETCDIR, configfilename)
        templatefile = join(ETCDIR, templatefilename)

        if not isfile(configfile):
            error('Unable to load configuration file "%s".' % configfile)

        if not isfile(templatefile):
            error('Unable to load template file "%s".' % templatefile)

        self.config = objectify.parse(configfile).getroot()
        etree.SubElement(self.config, 'version', version=version)
        etree.SubElement(self.config, 'platform', version=platform)
        etree.SubElement(self.config, 'templatefile', path=templatefile)

        info('Loaded configuration "%s" (loaded from "%s").' % (version, configfile))

    def validate_environment(self):
        self.validate_environment_wix()
        self.validate_environment_xmllint()

    def validate_environment_wix(self):
        global WIX_DIR
        global WIX_DARK
        global WIX_HEAT
        global WIX_CANDLE
        global WIX_LIGHT
        global XML_LINT

        # Get WiX path from environment variable
        if not os.environ.has_key('WIX'):
            error('Please verify WiX has been installed and the WIX environment '
                  'variable points to it\'s installation directory.')

        WIX_DIR = join(abspath(os.environ['WIX']), 'bin')

        if not os.path.isdir(WIX_DIR):
            error('WiX bin directory does not seem to exist.')

        WIX_HEAT = join(WIX_DIR, 'heat.exe')
        WIX_DARK = join(WIX_DIR, 'dark.exe')
        WIX_CANDLE = join(WIX_DIR, 'candle.exe')
        WIX_LIGHT = join(WIX_DIR, 'light.exe')

        # Validate WiX version
        output = Popen([WIX_CANDLE,
                        '-?'],
                       stdout=PIPE,
                       stderr=PIPE,
                       universal_newlines=True).communicate()[0]

        wix_version = re.compile(r"(version )(.*?)($)", re.S|re.M).search(output).group(2)

        if not int(WIX_VERSION.replace('.', '')) <= int(wix_version.replace('.', '')):
            error('Your WiX (version %s) is too old. A mininmum of version %s is required.' % (wix_version, WIX_VERSION))


    def validate_environment_xmllint(self):
        try:
            output = Popen([XML_LINT,
                            '--version'],
                           stdout=PIPE,
                           stderr=PIPE,
                           universal_newlines=True).communicate()[1]
        except WindowsError as e:
            error('Please verify xmllint (part of libxml2) has been installed '
                  'and it\'s bin directory is on the PATH environment variable')
        else:
            xml_lint_version = re.compile(r"(version )(.*?)($)", re.S|re.M).search(output).group(2)

            if not XML_LINT_VERSION <= int(xml_lint_version):
                error('Your xmllint (version %s) is too old. A mininmum of version %s is required.' % (xml_lint_version, XML_LINT_VERSION))


    def run(self):
        for child in self.config.interpreters.iterchildren():
            if child.tag == 'interpreter':
                if not child.get('version') in PYTHON_VERSIONS:
                    error('Unknown interpreter version (%s).' % child.get('version'))

                global PYTHON_FULLVERSION
                global PYTHON_VERSION
                PYTHON_FULLVERSION = child.get('version')
                PYTHON_VERSION = child.get('version').replace('.', '')

                product = Product(self.config)
                product.merge()


class Product(object):
    def __init__(self, config):
        self.config = config
        self.version = self.config.version.get('version')
        self.platform = self.config.platform.get('version')
        self.templatefile = self.config.templatefile.get('path')
        self.packageid = 'pygtk-all-in-one-%s.%s-py%s' % (self.version, self.platform, PYTHON_FULLVERSION)

        self.workdir = join(TMPDIR, PYTHON_FULLVERSION, self.packageid)

        self.wxsfilename = '%s.wxs' % self.packageid
        self.wixobjfilename = '%s.wixobj' % self.packageid
        self.msifilename = '%s.msi' % self.packageid
        self.tmpwxsfile = join(self.workdir, '%s.unformatted' % self.wxsfilename)
        self.wxsfile = join(self.workdir, self.wxsfilename)
        self.wixobjfile = join(self.workdir, self.wixobjfilename)
        self.msifile = join(self.workdir, self.msifilename)

    def merge(self):
        info('Creating .msi installer targeting Python %s' % PYTHON_FULLVERSION)

        self.clean()
        self.prepare()
        self.build()
        self.transform()
        self.compile()
        self.link()

        info('Success: .msi installer targeting Python %s has been created ("%s")' % (PYTHON_FULLVERSION, self.msifile))

    def clean(self):
        allworkdirs = join(TMPDIR, PYTHON_FULLVERSION)

        if isdir(allworkdirs):
            rmtree(allworkdirs)

    def prepare(self):
        if not isdir(self.workdir):
            os.makedirs(self.workdir)

        copyfile(self.templatefile, self.wxsfile)

    def build(self):
        for child in self.config.product.features.iterchildren():
            if child.tag == 'feature':
                self.build_feature(child)
            else:
                info('Unknown child element in Features: "%s".' % child.tag, 1)

    def build_feature(self, feature):
        info('Preparing features for "%s"...' % feature.get('id'), 1)

        for child in feature.iterchildren():
            if child.tag == 'feature':
                self.build_feature(child)
            elif child.tag == 'package':
                info('Preparing source package "%s"' % child.get('id'), 2)

                sourcepackage = SourcePackage.from_packagetype(self.config, child)
                sourcepackage.merge()

    def transform(self):
        # Open our .wxs file
        root = etree.parse(self.wxsfile).getroot()

        info('Transforming variables...', 1)
        self.transform_variables(root)

        info('Transforming includes...', 1)
        self.transform_includes(root)

        info('Transforming features...', 1)
        self.transform_features(root)

        info('Writing .wxs file...', 1)
        file = open(self.tmpwxsfile, 'w')
        file.write(etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8'))
        file.close()

        info('Reformatting .wxs file...', 1)
        self.transform_reformat()

    def transform_variables(self, element):
        for child in element:
            #TODO: child.tag seems to be a function for Comment and
            #      ProcessingInstruction elements? Feels dirty :(
            if 'ProcessingInstruction' in str(child.tag):
                if 'PythonVersion' in child.text:
                    child.text = child.text.replace('XXX', PYTHON_FULLVERSION)
                elif 'ProductName' in child.text:
                    productname = 'Python %s %s' % (PYTHON_FULLVERSION, self.config.product.get('name'))
                    child.text = child.text.replace('XXX', productname)
                elif 'ProductVersion' in child.text:
                    child.text = child.text.replace('XXX', self.version)
                elif 'UpgradeCode' in child.text:
                    upgradecode = self.config.product.get('upgradecode_%s' % PYTHON_VERSION)
                    child.text = child.text.replace('XXX', upgradecode)

    def transform_includes(self, element):
        #TODO: there has to be a better way to get at elements than .find + .getnext... XPath???
        product = element.find('{%s}Product' % WIX_NAMESPACE)
        FEATURE = product.find('{%s}Feature' % WIX_NAMESPACE)

        def transform(element):
            for child in element.iterchildren():
                if child.tag == 'feature':
                    transform(child)
                elif child.tag == 'package':
                    pi = etree.ProcessingInstruction('include', child.get('wxifile_%s' % PYTHON_VERSION))
                    FEATURE.addprevious(pi)

        for child in self.config.product.features.iterchildren():
            transform(child)

    def transform_features(self, element):
        #TODO: there has to be a better way to get at elements than .find + .getnext... XPath???
        product = element.find('{%s}Product' % WIX_NAMESPACE)
        TARGETDIR = product.find('{%s}Directory' % WIX_NAMESPACE)
        FEATURE = product.find('{%s}Feature' % WIX_NAMESPACE)
        FEATUREV = FEATURE.getnext()
        FEATUREX = FEATUREV.getnext()

        def transform(element, PARENT, PARENTV, PARENTX):
            if element.tag == 'feature':
                parent = etree.SubElement(PARENT,
                                          'Feature',
                                          Id = element.get('id'),
                                          Title = element.get('title'),
                                          Description = element.get('description'),
                                          Level = PARENT.get('Level'))
                parentv = etree.SubElement(PARENTV,
                                           'Feature',
                                           Id = '%s%s' % (element.get('id'), PYTHON_FULLVERSION),
                                           Title = element.get('title'),
                                           Description = element.get('description'),
                                           Level = PARENTV.get('Level'))
                parentx = etree.SubElement(PARENTX,
                                           'Feature',
                                           Id = '%sX' % element.get('id'),
                                           Title = element.get('title'),
                                           Description = element.get('description'),
                                           Level = PARENTX.get('Level'))
                for child in element.iterchildren():
                    transform(child, parent, parentv, parentx)

            elif element.tag == 'package':
                wxifile = element.get('wxifile_%s' % PYTHON_VERSION)

                iroot = etree.parse(wxifile).getroot()
                ITARGETDIRV = iroot.find('{%s}DirectoryRef' % WIX_NAMESPACE)
                assert ITARGETDIRV.get('Id') == 'TARGETDIR%s' % PYTHON_FULLVERSION
                ITARGETDIRX = ITARGETDIRV.getnext()
                assert ITARGETDIRX.get('Id') == 'TARGETDIRX'
                ITARGETDIR = ITARGETDIRX.getnext()
                assert ITARGETDIR.get('Id') == 'TARGETDIR'

                def traverse(child, parent):
                    if child.tag == '{%s}Component' % WIX_NAMESPACE:
                        etree.SubElement(parent, 'ComponentRef', Id=child.get('Id'))
                    else:
                        for x in child:
                            traverse(x, parent)

                for vchild in ITARGETDIRV.iterchildren():
                    traverse(vchild, PARENTV)

                for xchild in ITARGETDIRX.iterchildren():
                    traverse(xchild, PARENTX)

                for ichild in ITARGETDIR.iterchildren():
                    traverse(ichild, PARENT)

        for child in self.config.product.features.iterchildren():
            transform(child, FEATURE, FEATUREV, FEATUREX)

    def transform_reformat(self):
        xmllint_format(self.tmpwxsfile, self.wxsfile, join(self.workdir, 'xmllint.log'))

    def compile(self):
        info('Compiling sources...', 3)

        logfile = join(self.workdir, 'candle.log')
        file = open(logfile, 'w')
        process = Popen([WIX_CANDLE,
                         '-nologo',
                         self.wxsfile,
                         '-out',
                         self.wixobjfile],
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            info('WiX "candle" reported error(s). Please review "%s".' % logfile, 4)

        file.close()

    def link(self):
        info('Linking objects...', 3)

        logfile = join(self.workdir, 'light.log')
        file = open(logfile, 'w')
        process = Popen([WIX_LIGHT,
                         '-nologo',
                         self.wixobjfile,
                         '-out',
                         self.msifile],
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            info('WiX "light" reported error(s). Please review "%s".' % logfile, 4)

        file.close()


class SourcePackage(object):
    @staticmethod
    def from_packagetype(config, package):
        packagetype = package.get('type')

        for subclass in SourcePackage.__subclasses__():
            if subclass.__name__ == packagetype:
                return subclass(config, package)
        else:
            error('Unknown source package type "%s".' % packagetype)

    def __init__(self, config, package):
        self.config = config
        self.package = package

        if not self.package.get('url').endswith('/'):
            self.package.set('url', '%s/' % self.package.get('url'))

        self.cachefile = join(CACHEDIR, self.filename)
        self.overlaydir = join(VARDIR, 'overlays', self.config.version.get('version'), self.package.get('id'))
        self.workdir = join(TMPDIR, PYTHON_FULLVERSION, self.package.get('id'))
        self.wxsfile = join(self.workdir, '%s.wxs' % self.package.get('id'))
        self.tmpwxifile = join(self.workdir, '%s.wxi.unformatted' % self.package.get('id'))
        self.wxifile = join(self.workdir, '%s.wxi' % self.package.get('id'))

        self.package.set('wxifile_%s' % PYTHON_VERSION, self.wxifile)

    def _check_md5(self, file, digest):
        m = md5()
        f = open(file, 'rb')

        while True:
            t = f.read(1024)
            if len(t) == 0: break # end of file
            m.update(t)

        hexdigest = m.hexdigest()

        if digest == hexdigest:
            return True
        else:
            info('md5 digest mismatch: got "%s", expected "%s"...' % (hexdigest, digest), 4)
            return False

    def merge(self):
        self.clean()
        self.prepare()
        self.fetch()
        self.unpack()
        self.patch()
        self.build()
        self.transform()
        self.save_include()

    def clean(self):
        info('Cleaning build environment...', 3)

        if isdir(self.workdir):
            rmtree(self.workdir)

    def prepare(self):
        info('Preparing build environment...', 3)

        if not isdir(self.workdir):
            os.makedirs(self.workdir)

        if not isdir(CACHEDIR):
            os.makedirs(CACHEDIR)

    def _fetch_from_cache(self):
        if isfile(self.cachefile):
            if self._check_md5(self.cachefile, self.digest):
                info('Using cached package sources...', 4)
                return True
            else:
                info('Not using chached package sources...', 4)
                os.rename(self.cachefile, '%s.corrupt' % self.cachefile)
                return False
        else:
            return False

    def fetch(self):
        info('Fetching package sources...', 3)

        if not self._fetch_from_cache():
            url = self.package.get('url') + self.filename

            try:
                info('Downloading package sources...', 4)
                response = urlopen(url)
                cachefile = open(self.cachefile, 'wb')
                cachefile.write(response.read())
                cachefile.close()
            except URLError:
                error('Failed downloading package sources from "%s".' % url)

            if not self._check_md5(self.cachefile, self.digest):
                error('md5 mismatch (%s).' % self.cachefile)

    def unpack(self):
        raise NotImplementedError

    def patch(self):
        info('Applying overlay...', 3)

        def copytree(srcdir, dstdir):
            srcnames = os.listdir(srcdir)

            for name in srcnames:
                srcfname = join(srcdir, name)
                dstfname = join(dstdir, name)

                if isdir(srcfname):
                    if not isdir(dstfname):
                        os.mkdir(dstfname)

                    copytree(srcfname, dstfname)
                elif isfile(srcfname):
                    sf = open(srcfname, 'rb')
                    df = open(dstfname, 'wb')
                    df.write(sf.read())
                    df.close()
                    sf.close()

        if isdir(self.overlaydir):
            copytree(self.overlaydir, join(self.workdir, 'File'))

    def build(self):
        raise NotImplementedError

    def transform(self):
        raise NotImplementedError

    def transform_create_targetdirs(self, element):
        '''
        We need to create a new "Directory" "TARGETDIR$(var.PythonVersion)" and a
        new "Directory" "TARGETDIRX", where both mirror all:
            - "Directory" nodes from "TARGETDIR" with an adapted "Id"
            - "Component" nodes from "TARGETDIR" with an adapted "Id" and a newly generated "Guid"
            - "File" nodes from "TARGETDIR" into a "CopyFile" node, with an an adapted "ID"

        This needs to be done for .msi files generated by Python 2.6 distutils
        as they simply don't exist an all other known Python versions' distutils
        because the don't include "RemoveFile" elements...
        '''
        TARGETDIRV = etree.Element('DirectoryRef', Id='TARGETDIR%s' % PYTHON_FULLVERSION)
        TARGETDIRX = etree.Element('DirectoryRef', Id='TARGETDIRX')

        def transform(source, dest, suffix, directory=None):
            for child in source:
                if child.tag == '{%s}DirectoryRef' % WIX_NAMESPACE:
                    transform(child, dest, suffix, child)

                elif child.tag == '{%s}Directory' % WIX_NAMESPACE:
                    newchild = etree.SubElement(dest,
                                                'Directory',
                                                Id = '%s%s' % (child.get('Id'), suffix),
                                                Name = child.get('Name'))

                    transform(child, newchild, suffix, newchild)

                elif child.tag == '{%s}Component' % WIX_NAMESPACE:
                    newchild = etree.SubElement(dest,
                                                'Component',
                                                Id = '%s%s' % (child.get('Id'), suffix),
                                                Guid = generate_uuid())

                    if 'KeyPath' in child.keys():
                        newchild.set('KeyPath', child.get('KeyPath'))
                    else:
                        newchild.set('KeyPath', 'yes')

                    transform(child, newchild, suffix, directory)

                elif child.tag == '{%s}File' % WIX_NAMESPACE:
                    newchild = etree.SubElement(dest,
                                                'CopyFile',
                                                Id = '%s%s' % (child.get('Id'), suffix),
                                                FileId = child.get('Id'),
                                                DestinationDirectory = directory.get('Id'))

                elif child.tag == '{%s}RemoveFile' % WIX_NAMESPACE:
                    newchild = etree.SubElement(dest,
                                                'RemoveFile',
                                                Id = '%s%s' % (child.get('Id'), suffix),
                                                Directory = '%s%s' % (child.get('Directory'), suffix),
                                                Name = child.get('Name'),
                                                On = child.get('On'))

        transform(element, TARGETDIRV, PYTHON_FULLVERSION)
        transform(element, TARGETDIRX, 'X')
        element.insert(0, TARGETDIRV)
        element.insert(1, TARGETDIRX)

    def transform_id(self, element, prefix=''):
        '''
        Prepend Id attributes with prefix to ensure unique Id's
        across all merged packages. These changes need to propagate to
        FileId and DestinationDirectory.
        '''

        prefix = '%s_' % self.package.get('id')

        def transform(element):
            if 'Id' in element.keys():
                if not element.get('Id').startswith('TARGETDIR'):
                    element.set('Id', '%s%s' % (prefix, element.get('Id')))

            if 'FileId' in element.keys():
                element.set('FileId', '%s%s' % (prefix, element.get('FileId')))

            if 'Directory' in element.keys():
                element.set('Directory', '%s%s' % (prefix, element.get('Directory')))

            if 'DestinationDirectory' in element.keys():
                if not element.get('DestinationDirectory').startswith('TARGETDIR'):
                    element.set('DestinationDirectory', '%s%s' % (prefix, element.get('DestinationDirectory')))

            for child in element:
                self.transform_id(child, prefix)

        transform(element)

    def save_include(self):
        # Save the transformed include
        info('Writing .wxi file...', 4)
        file = open(self.tmpwxifile, 'w')
        file.write(etree.tostring(self.include, pretty_print=True, xml_declaration=True, encoding='utf-8'))
        file.close()

        # Reformat saved .wxi file
        info('Reformatting .wxi file...', 4)
        xmllint_format(self.tmpwxifile, self.wxifile, join(self.workdir, 'xmllint.log'))


class MsiSourcePackage(SourcePackage):
    def __init__(self, config, package):
        if PYTHON_FULLVERSION == '2.6':
            self.filename = package.get('msi_26')
            self.digest = package.get('digest_26')
        elif PYTHON_FULLVERSION == '2.7':
            self.filename = package.get('msi_27')
            self.digest = package.get('digest_27')

        SourcePackage.__init__(self, config, package)

    def unpack(self):
        info('Unpacking package sources...', 3)

        logfile = join(self.workdir, 'dark.log')
        file = open(logfile, 'w')
        process = Popen([WIX_DARK,
                         '-nologo',
                         '-x',              # export binaries from cabinets and embedded binaries
                         self.workdir ,     #    to our workdir
                         self.cachefile,    # decompile this .msi file
                         self.wxsfile],     # save to this .wxs file
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            info('WiX "dark" reported error(s). Please review "%s".' % logfile, 4)

        file.close()

    def build(self):
        info('Creating .wxi include file...', 3)

        # Get the Wix/Product/Directory node
        root = etree.parse(self.wxsfile).getroot()
        product = root.find('{%s}Product' % WIX_NAMESPACE)
        include = product.find('{%s}Directory' % WIX_NAMESPACE)

        # deepcopy the Wix/Product/Directory node into a new tree
        newroot = etree.Element('{%s}Include' % WIX_NAMESPACE, nsmap=WIX_NSMAP)
        newinclude = etree.SubElement(newroot, '{%s}DirectoryRef' % WIX_NAMESPACE, Id='TARGETDIR')

        for child in include:
            newinclude.append(deepcopy(child))

        self.include = newroot

    def transform(self):
        if PYTHON_FULLVERSION != '2.6':
            info('Removing "TARGETDIR%s" and "TARGETDIRX"' % PYTHON_FULLVERSION, 4)
            self.transform_remove_targetdirs(self.include)

        info('Creating "TARGETDIR%s" and "TARGETDIRX"' % PYTHON_FULLVERSION, 4)
        self.transform_create_targetdirs(self.include)

        info('Transforming "Id" attributes...', 4)
        self.transform_id(self.include)

        info('Transforming "ShortName" attributes...', 4)
        self.transform_shortname(self.include)

    def transform_remove_targetdirs(self, element):
        '''
        Remove "TARGETDIR $(var.PythonVersion)" and "TARGETDIRX" elements so
        they can be recreated with "RemoveFile" elements included.
        '''
        tmp = element.find('{%s}DirectoryRef' % WIX_NAMESPACE)

        for child in tmp:
            if child.get('Id').startswith('TARGETDIR'):
                tmp.remove(child)

    def transform_shortname(self, element):
        '''
        We want WiX to generate "ShorName" attributes, so we remove them.
        This also fixes illegal "ShortName" attributes on "RemoveFile" elements
        coming from the .msi files generated by Python distutils.
        '''
        def transform(element):
            if 'ShortName' in element.keys():
                del element.attrib['ShortName']

            for child in element:
                transform(child)

        transform(element)


class ArchiveSourcePackage(SourcePackage):
    def __init__(self, config, package):
        self.filename = package.get('archive')
        self.digest = package.get('digest')

        SourcePackage.__init__(self, config, package)

    def unpack(self):
        info('Unpacking package sources...', 3)

        zipfile = ZipFile(self.cachefile)
        zipfile.extractall(join(self.workdir, 'File'))
        zipfile.close()

    def build(self):
        info('Creating .wxi include file...', 3)

        sourcedir = 'var.%s_sourcedir' % self.package.get('id')

        logfile = join(self.workdir, 'heat.log')
        file = open(logfile, 'w')

        process = Popen([WIX_HEAT,
                         'dir',                         # harvest a directory
                         join(self.workdir, 'File'),    #     from the directory where we extracted our source package
                         '-nologo',
                         '-dr',                         # set directory reference to root directories
                         'TARGETDIR',                   #     to TARGETDIR
                         '-gg',                         # generate guids now
                         '-scom',                       # suppress COM elements
                         '-sfrag',                      # suppress fragments
                         '-srd',                        # suppress harvesting the root directory as an element
                         '-sreg',                       # suppress registry harvesting
                         '-svb6',                       # suppress VB6 COM elements
                         '-template',                   # set template to use
                         'product',                     #     to product
                         '-var',                        # substitute File/@Source="SourceDir" with a preprocessor variable
                         sourcedir,                     #     thus SourceDir will become "$(var.xxx_sourcedir)\myfile.txt"
                         '-out',                        # set output file
                         self.wxsfile],                 # to our wxsfile
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)
        file.close()

        if process.wait() != 0:
            info('WiX "heat" reported error(s). Please review "%s".' % logfile, 4)

        root = etree.parse(self.wxsfile).getroot()
        product = root.find('{%s}Product' % WIX_NAMESPACE)
        include = product.find('{%s}Directory' % WIX_NAMESPACE)

        # deepcopy the Wix/Product/Directory node into a new tree
        newroot = etree.Element('{%s}Include' % WIX_NAMESPACE, nsmap=WIX_NSMAP)
        targetdir = etree.SubElement(newroot,
                                     '{%s}DirectoryRef' % WIX_NAMESPACE,
                                     Id='TARGETDIR')
        libdir = etree.SubElement(targetdir,
                                  '{%s}Directory' % WIX_NAMESPACE,
                                  Name='Lib', Id='Lib')
        spdir = etree.SubElement(libdir,
                                 '{%s}Directory' % WIX_NAMESPACE,
                                 Name='site-packages', Id='site_packages')
        gtkdir = etree.SubElement(spdir,
                                  '{%s}Directory' % WIX_NAMESPACE,
                                  Name='gtk-2.0', Id='gtk_2.0')
        rtdir = etree.SubElement(gtkdir,
                                 '{%s}Directory' % WIX_NAMESPACE,
                                  Name='runtime', Id='runtime')

        for child in include:
            rtdir.append(deepcopy(child))

        self.include = newroot

    def transform(self):
        info('Creating "TARGETDIR%s" and "TARGETDIRX"' % PYTHON_FULLVERSION, 4)
        self.transform_create_targetdirs(self.include)

        info('Transforming "Id" attributes...', 4)
        self.transform_id(self.include)

        info ('Transforming variables...', 4)
        self.transform_variables(self.include)

    def transform_variables(self, element):
        pi = etree.ProcessingInstruction('define', '%s_sourcedir = "%s"' % (self.package.get('id'), join(self.workdir, 'File')))
        element.insert(0, pi)


def main():
    start = datetime.now()

    builder = Builder()
    builder.run()

    end = datetime.now()
    minutes, seconds = divmod((end - start).seconds, 60)

    info('Builder finished in %s minutes %s seconds' % (minutes, seconds))


if __name__ == '__main__':
    main()
