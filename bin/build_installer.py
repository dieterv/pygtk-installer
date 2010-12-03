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
from distutils.spawn import find_executable
from hashlib import md5
from optparse import OptionParser
from os.path import abspath, basename, dirname, isabs, isdir, isfile, join
from shutil import copyfile, rmtree
from subprocess import Popen, PIPE
from urllib2 import urlopen, URLError
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree, objectify


# These paths are used all over the place
ROOTDIR = abspath(join(dirname(__file__), '..'))
WIXDIR = join(ROOTDIR, 'wix')
TMPDIR = join(ROOTDIR, 'tmp')
CACHEDIR = None

# Everything we need to know about the platform we'll build PyGtk installers
# for. Also maps human readable identifiers to msi speak...
PLATFORMS = {'win32': 'x86', 'win64': 'x64'}
WIN_PLATFORM = None
WIX_PLATFORM = None

# Everything we need to know about the Python interpreter versions we'll
# build PyGtk installers for. If these change, you'll need to update the
# template .wxs file...
PYTHON_VERSIONS = ['2.6', '2.7']
PYTHON_FULLVERSION = None
PYTHON_VERSION = None

# Everything we need to know about  the WiX toolset...
WIX_VERSION = '3.5.2305.0'
WIX_NS = 'http://schemas.microsoft.com/wix/2006/wi'
WIX_NSMAP = {None : WIX_NS}
WIX_HEAT = None
WIX_DARK = None
WIX_CANDLE = None
WIX_LIGHT = None

# Everything we need to know about xmllint...
XML_LINT_VERSION = 20707
XML_LINT = None


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

def copytree(srcdir, dstdir):
    srcnames = os.listdir(srcdir)

    for name in srcnames:
        srcname = join(srcdir, name)
        dstname = join(dstdir, name)

        if isdir(srcname):
            if not isdir(dstname):
                os.mkdir(dstname)

            copytree(srcname, dstname)
        elif isfile(srcname):
            sf = open(srcname, 'rb')
            df = open(dstname, 'wb')
            df.write(sf.read())
            df.close()
            sf.close()

def get_md5(file):
    m = md5()
    f = open(file, 'rb')

    while True:
        t = f.read(1024)
        if len(t) == 0: break # end of file
        m.update(t)

    f.close()

    return m.hexdigest()


class Builder(object):
    def __init__(self, arguments=None):
        self.parse_options(arguments)
        self.validate_wix()
        self.validate_xmllint()
        self.parse_build_description()

    def parse_options(self, arguments=None):
        if arguments == None:
            arguments = sys.argv[1:]

        #TODO: implement a --keep-tmp option?
        parser = OptionParser(usage='usage: %prog [options] moduleset')
        (self.options, self.args) = parser.parse_args(arguments)

        if not len(self.args) == 1:
            error(parser.get_usage())

    def validate_wix(self):
        # Get WiX installation directory from the WIX environment variable
        if not os.environ.has_key('WIX'):
            error('Please verify WiX has been installed and the WIX environment '
                  'variable points to it\'s installation directory.')

        WIX_DIR = abspath(join(os.environ['WIX'], 'bin'))

        if not os.path.isdir(WIX_DIR):
            error('Please verify WiX has been installed and the WIX environment '
                  'variable points to it\'s installation directory, not it\'s '
                  'bin directory.')

        global WIX_DARK
        global WIX_HEAT
        global WIX_CANDLE
        global WIX_LIGHT
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
            error('Your WiX (version %s) is too old. At least version %s is required.' % (wix_version, WIX_VERSION))

    def validate_xmllint(self):
        global XML_LINT
        XML_LINT = find_executable('xmllint', os.environ['PATH'])

        if not XML_LINT or not os.path.isfile(XML_LINT):
            error('Please verify xmllint has been installed and the PATH environment '
                  'variable points to it\'s installation directory.')

        # Validate xmllint version
        output = Popen([XML_LINT,
                        '--version'],
                       stdout=PIPE,
                       stderr=PIPE,
                       universal_newlines=True).communicate()[1]

        xml_lint_version = re.compile(r"(version )(.*?)($)", re.S|re.M).search(output).group(2)

        if not XML_LINT_VERSION <= int(xml_lint_version):
            error('Your xmllint (version %s) is too old. At least version %s is required.' % (xml_lint_version, XML_LINT_VERSION))

    def parse_build_description(self):
        target = self.args[0].split('.')
        version = '%s.%s.%s' % (target[0], target[1], target[2])
        platform = target[3]

        global CACHEDIR
        CACHEDIR = join(TMPDIR, 'cache', self.args[0])
        buildfile = join(WIXDIR, '%s.xml' % self.args[0])
        schemafile = join(WIXDIR, 'build.xsd')

        if not isdir(CACHEDIR):
            os.makedirs(CACHEDIR)

        if not isfile(buildfile):
            error('Unable to load build description "%s".' % buildfile)

        #schema = etree.XMLSchema(file=schemafile)
        #parser = etree.XMLParser(schema=schema)
        #self.buildfile = objectify.parse(buildfile, parser=parser).getroot()
        self.buildfile = objectify.parse(buildfile).getroot()

        # Store version number
        etree.SubElement(self.buildfile, 'Version', Version=version)

        # Store target platform
        if platform in PLATFORMS.keys():
            global WIN_PLATFORM
            global WIX_PLATFORM
            WIN_PLATFORM = platform
            WIX_PLATFORM = PLATFORMS[platform]
        else:
            error('Unknown platform (%s).' % platform)

        info('Loaded build description "%s" (loaded from "%s").' % (version, buildfile))

    def build(self):
        for child in self.buildfile.Interpreters.iterchildren():
            if child.tag == 'Interpreter':
                if child.get('Version') in PYTHON_VERSIONS:
                    global PYTHON_FULLVERSION
                    global PYTHON_VERSION
                    PYTHON_FULLVERSION = child.get('Version')
                    PYTHON_VERSION = child.get('Version')

                    product = Product(self.buildfile)
                    product.merge()
                else:
                    error('Unknown interpreter version (%s).' % child.get('Version'))


class Product(object):
    def __init__(self, buildfile):
        self.buildfile = buildfile
        self.version = self.buildfile.Version.get('Version')
        self.packageid = 'pygtk-all-in-one-%s.%s-py%s' % (self.version, WIN_PLATFORM, PYTHON_FULLVERSION)

        self.wxsfilename = '%s.wxs' % self.packageid
        self.wixobjfilename = '%s.wixobj' % self.packageid
        self.msifilename = '%s.msi' % self.packageid

        self.builddir = join(TMPDIR, 'build', '%s-py%s' % (WIN_PLATFORM, PYTHON_FULLVERSION), self.packageid)
        self.tmpwxsfile = join(self.builddir, '%s.unformatted' % self.wxsfilename)
        self.wxsfile = join(self.builddir, self.wxsfilename)
        self.wixobjfile = join(self.builddir, self.wixobjfilename)
        self.msifile = join(self.builddir, self.msifilename)

    def merge(self):
        info('Creating .msi installer targeting Python %s' % PYTHON_FULLVERSION)

        self.do_clean()
        self.do_prepare()
        self.do_build()
        self.do_transform()
        self.do_compile()
        self.do_link()
        self.do_post_build()

        info('Success: .msi installer targeting Python %s has been created ("%s")' % (PYTHON_FULLVERSION, self.msifile))

    def do_clean(self):
        info('Cleaning build environment...', 1)

        if isdir(join(self.builddir, '..')):
            rmtree(join(self.builddir, '..'), ignore_errors=False)

    def do_prepare(self):
        info('Preparing build environment...', 1)

        if not isdir(self.builddir):
            os.makedirs(self.builddir)

        copytree(join(WIXDIR, 'template'), self.builddir)
        os.rename(join(self.builddir, 'PyGTK.wxs'), self.wxsfile)

    def do_build(self):
        for child in self.buildfile.Product.Features.iterchildren():
            if child.tag == 'Feature':
                info('Preparing feature "%s"...' % child.get('Id'), 1)
                self.build_feature(child)
            else:
                info('Unknown child element in Features: "%s".' % child.tag, 1)

    def build_feature(self, feature):
        for child in feature.iterchildren():
            if child.tag == 'Feature':
                self.build_feature(child)
            elif child.tag == 'Package':
                info('Preparing source package "%s"' % child.get('Id'), 2)

                sourcepackage = SourcePackage.from_packagetype(self.buildfile, child)
                sourcepackage.merge()

    def do_transform(self):
        # Open our .wxs file
        wxsfile = etree.parse(self.wxsfile).getroot()

        info('Transforming variables...', 1)
        self.transform_variables(wxsfile)

        info('Transforming includes...', 1)
        self.transform_includes(wxsfile)

        info('Transforming features...', 1)
        self.transform_features(wxsfile)

        info('Writing .wxs file...', 1)
        file = open(self.tmpwxsfile, 'w')
        file.write(etree.tostring(wxsfile, pretty_print=True, xml_declaration=True, encoding='utf-8'))
        file.close()

        info('Reformatting .wxs file...', 1)
        self.transform_reformat()

    def transform_variables(self, wxsfile):
        for child in wxsfile:
            #TODO: child.tag seems to be a function for Comment and
            #      ProcessingInstruction elements? Feels dirty :(
            if 'ProcessingInstruction' in str(child.tag):
                if 'SrcImages' in child.text:
                    child.text = child.text.replace('XXX', join(WIXDIR, 'images'))
                elif 'Platform' in child.text:
                    child.text = child.text.replace('XXX', WIX_PLATFORM)
                elif 'PythonVersion' in child.text:
                    child.text = child.text.replace('XXX', PYTHON_FULLVERSION)
                elif 'ProductVersion' in child.text:
                    child.text = child.text.replace('XXX', self.version)

    def transform_includes(self, wxsfile):
        #TODO: there has to be a better way to get at elements than .find + .getnext... XPath???
        product = wxsfile.find('{%s}Product' % WIX_NS)
        package = product.find('{%s}Package' % WIX_NS)

        def transform(element):
            for child in element.iterchildren():
                if child.tag == 'Feature':
                    transform(child)
                elif child.tag == 'Package':
                    pi = etree.ProcessingInstruction('include', child.get('wxifile_%s' % PYTHON_VERSION))
                    package.addnext(pi)

        for child in self.buildfile.Product.Features.iterchildren():
            transform(child)

    def transform_features(self, wxsfile):
        def transform(element, parent):
            if element.tag == 'Feature':
                feature = etree.SubElement(parent,
                                          'Feature',
                                          Id = element.get('Id'),
                                          Title = element.get('Title'),
                                          Description = element.get('Description'),
                                          AllowAdvertise='no',
                                          InstallDefault='local',
                                          TypicalDefault='install')

                if 'Absent' in element.keys():
                    feature.set('Absent', element.get('Absent'))

                if 'Display' in element.keys():
                    feature.set('Display', element.get('Display'))

                if 'InstallDefault' in element.keys():
                    feature.set('InstallDefault', element.get('InstallDefault'))

                if 'Level' in element.keys():
                    feature.set('Level', element.get('Level'))
                elif 'Level' in parent.keys():
                    feature.set('Level', parent.get('Level'))
                else:
                    error('Error computing Level for Feature "%s"' % element.get('Id'), 2)

                if 'Container' in element.keys() and element.get('Container').lower() == 'true':
                    # A Feature should always reference at least one component.
                    # If we do not do this, the SelectionTree widget seems to
                    # ignore the AllowAdvertise, InstallDefault and
                    # TypicalDefault attributes set above. In other words:
                    etree.SubElement(feature, 'ComponentRef', Id='Empty')

                for child in element.iterchildren():
                    transform(child, feature)

            elif element.tag == 'Package':
                def traverse(child, parent):
                    if child.tag == '{%s}Component' % WIX_NS:
                        etree.SubElement(parent, 'ComponentRef', Id=child.get('Id'))
                    else:
                        for x in child:
                            traverse(x, parent)

                wxifile = element.get('wxifile_%s' % PYTHON_VERSION)
                iroot = etree.parse(wxifile).getroot()
                ITARGETDIR = iroot.find('{%s}DirectoryRef' % WIX_NS)
                assert ITARGETDIR.get('Id') == 'TARGETDIR'

                for ichild in ITARGETDIR.iterchildren():
                    traverse(ichild, parent)

        product = wxsfile.find('{%s}Product' % WIX_NS)
        feature = product.find('{%s}Feature' % WIX_NS)

        for child in self.buildfile.Product.Features.iterchildren():
            transform(child, feature)

    def transform_reformat(self):
        xmllint_format(self.tmpwxsfile, self.wxsfile, join(self.builddir, 'xmllint.log'))

    def do_compile(self):
        info('Compiling sources...', 1)

        logfile = join(self.builddir, 'candle.log')
        file = open(logfile, 'w')
        process = Popen([WIX_CANDLE,
                         '-nologo',
                         '-wx',
                         self.wxsfile,
                         '-out',
                         self.wixobjfile],
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            error('WiX "candle" reported error(s). Please review "%s".' % logfile, 1)

        file.close()

    def do_link(self):
        info('Linking objects...', 1)

        logfile = join(self.builddir, 'light.log')
        file = open(logfile, 'w')
        process = Popen([WIX_LIGHT,
                         '-nologo',
                         '-wx',
                         '-ext',
                         'WixUIExtension',
                         '-cultures:en-us',
                         self.wixobjfile,
                         '-out',
                         self.msifile],
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            error('WiX "light" reported error(s). Please review "%s".' % logfile, 1)

        file.close()

    def do_post_build(self):
        # Create .md5 file
        hexdigest = get_md5(self.msifile)
        f = open(join(self.builddir, '%s.md5' % self.msifile), 'w')
        f.write('%s *%s' % (hexdigest, self.msifilename))
        f.close()


class SourcePackage(object):
    @staticmethod
    def from_packagetype(product, package):
        packagetype = package.get('Type')

        for subclass in SourcePackage.__subclasses__():
            if subclass.__name__ == packagetype:
                return subclass(product, package)
        else:
            error('Unknown source package type "%s".' % packagetype)

    def __init__(self, buildfile, package):
        self.buildfile = buildfile
        self.package = package

        if not self.package.get('Url').endswith('/'):
            self.package.set('Url', '%s/' % self.package.get('Url'))

        self.cachefile = join(CACHEDIR, self.filename)
        self.builddir = join(TMPDIR, 'build', '%s-py%s' % (WIN_PLATFORM, PYTHON_FULLVERSION), self.package.get('Id'))
        self.wxsfile = join(self.builddir, '%s.wxs' % self.package.get('Id'))
        self.tmpwxifile = join(self.builddir, '%s.wxi.unformatted' % self.package.get('Id'))
        self.wxifile = join(self.builddir, '%s.wxi' % self.package.get('Id'))

        self.package.set('wxifile_%s' % PYTHON_VERSION, self.wxifile)

    def _check_md5(self, file, digest):
        hexdigest = get_md5(file)

        if digest == hexdigest:
            return True
        else:
            info('md5 digest mismatch: got "%s", expected "%s"...' % (hexdigest, digest), 4)
            return False

    def merge(self):
        self.do_prepare()
        self.do_fetch()
        self.do_unpack()
        self.do_patch()
        self.do_build()
        self.do_transform()
        self.do_save_include()

    def do_prepare(self):
        info('Preparing build environment...', 3)

        if not isdir(self.builddir):
            os.makedirs(self.builddir)

    def do_fetch(self):
        info('Fetching package sources...', 3)

        if not isfile(self.cachefile) or not self._check_md5(self.cachefile, self.digest):
            url = self.package.get('Url') + self.filename

            try:
                info('Downloading package sources...', 4)
                response = urlopen(url)
                cachefile = open(self.cachefile, 'wb')
                cachefile.write(response.read())
                cachefile.close()
            except URLError:
                error('Failed downloading package sources from "%s".' % url)

            if not self._check_md5(self.cachefile, self.digest):
                error('Download md5 mismatch (%s).' % self.cachefile)

    def do_unpack(self):
        raise NotImplementedError

    def do_patch(self):
        info('Patching package sources...', 3)

        filesdir = join(self.builddir, 'File')

        for child in self.package.iterchildren():
            if child.tag == 'RemoveFile':
                if isabs(child.get('Id')):
                    error('Invalid RemoveFile action: Id attribute should not be an absolute path ("%s")' % child.get('Id'), 4)

                f = abspath(join(filesdir, child.get('Id')))

                if isfile(f):
                    os.unlink(f)
                else:
                    error('Invalid RemoveFile action: "%s" does not exist in "%s"' % (child.get('Id'), filesdir), 4)
            elif child.tag == 'CopyFile':
                if isabs(child.get('Src')):
                    error('Invalid CopyFile action: Src attribute should not be an absolute path ("%s")' % child.get('Src'), 4)

                if isabs(child.get('Dest')):
                    error('Invalid CopyFile action: Dest attribute should not be an absolute path ("%s")' % child.get('Dest'), 4)

                src = abspath(join(WIXDIR, child.get('Src'), child.get('Id')))
                dest = abspath(join(filesdir, child.get('Dest'), child.get('Id')))

                if isfile(src):
                    copyfile(src, dest)
                else:
                    error('Invalid CopyFile action: "%s" does not exist in "%s"' % (child.get('Src'), WIXDIR), 4)
            elif child.tag == 'Patch':
                #TODO: implement Patch action
                error('Applying patches is not implemented.', 4)
            elif child.tag != 'comment':
                error('Unknown action "%s"' % child.tag)

    def do_build(self):
        raise NotImplementedError

    def do_transform(self):
        raise NotImplementedError

    def transform_id(self, element, prefix=''):
        '''
        Prepend Id attributes with prefix to ensure unique Id's
        across all merged packages. These changes need to propagate to
        FileId and DestinationDirectory.
        '''

        prefix = '%s_' % self.package.get('Id')

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

    def do_save_include(self):
        # Save the transformed include
        info('Writing .wxi file...', 4)
        file = open(self.tmpwxifile, 'w')
        file.write(etree.tostring(self.include, pretty_print=True, xml_declaration=True, encoding='utf-8'))
        file.close()

        # Reformat saved .wxi file
        info('Reformatting .wxi file...', 4)
        xmllint_format(self.tmpwxifile, self.wxifile, join(self.builddir, 'xmllint.log'))


class MsiSourcePackage(SourcePackage):
    def __init__(self, product, package):
        if PYTHON_FULLVERSION == '2.6':
            self.filename = package.get('Msi_26')
            self.digest = package.get('Digest_26')
        elif PYTHON_FULLVERSION == '2.7':
            self.filename = package.get('Msi_27')
            self.digest = package.get('Digest_27')

        SourcePackage.__init__(self, product, package)

    def do_unpack(self):
        info('Unpacking package sources...', 3)

        logfile = join(self.builddir, 'dark.log')
        file = open(logfile, 'w')
        process = Popen([WIX_DARK,
                         '-nologo',
                         '-x',              # export binaries from cabinets and embedded binaries
                         self.builddir ,     #    to our workdir
                         self.cachefile,    # decompile this .msi file
                         self.wxsfile],     # save to this .wxs file
                        stdout=file,
                        stderr=file,
                        universal_newlines=True)

        if process.wait() != 0:
            info('WiX "dark" reported error(s). Please review "%s".' % logfile, 4)

        file.close()

    def do_build(self):
        info('Creating wix include file...', 3)

        # Get the Wix/Product/Directory node
        root = etree.parse(self.wxsfile).getroot()
        product = root.find('{%s}Product' % WIX_NS)
        include = product.find('{%s}Directory' % WIX_NS)

        # deepcopy the Wix/Product/Directory node into a new tree
        newroot = etree.Element('{%s}Include' % WIX_NS, nsmap=WIX_NSMAP)
        newinclude = etree.SubElement(newroot, '{%s}DirectoryRef' % WIX_NS, Id='TARGETDIR')

        for child in include:
            newinclude.append(deepcopy(child))

        self.include = newroot

    def do_transform(self):
        if PYTHON_FULLVERSION != '2.6':
            info('Removing "TARGETDIR%s" and "TARGETDIRX"' % PYTHON_FULLVERSION, 4)
            self.transform_remove_targetdirs(self.include)

        info('Transforming "Id" attributes...', 4)
        self.transform_id(self.include)

        info('Transforming "ShortName" attributes...', 4)
        self.transform_shortname(self.include)

    def transform_remove_targetdirs(self, element):
        '''
        Remove "TARGETDIR $(var.PythonVersion)" and "TARGETDIRX" elements so
        they can be recreated with "RemoveFile" elements included.
        '''
        tmp = element.find('{%s}DirectoryRef' % WIX_NS)

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
    def __init__(self, product, package):
        if 'archive' in package.keys():
            self.filename = package.get('archive')
            self.digest = package.get('digest')
        else:
            if PYTHON_FULLVERSION == '2.6':
                self.filename = package.get('Archive_26')
                self.digest = package.get('Digest_26')
            elif PYTHON_FULLVERSION == '2.7':
                self.filename = package.get('Archive_27')
                self.digest = package.get('Digest_27')

        SourcePackage.__init__(self, product, package)

    def do_unpack(self):
        info('Unpacking package sources...', 3)

        zipfile = ZipFile(self.cachefile)
        zipfile.extractall(join(self.builddir, 'File'))
        zipfile.close()

    def do_build(self):
        info('Creating wix include file...', 3)

        sourcedir = 'var.%s_sourcedir' % self.package.get('Id')

        logfile = join(self.builddir, 'heat.log')
        file = open(logfile, 'w')

        process = Popen([WIX_HEAT,
                         'dir',                         # harvest a directory
                         join(self.builddir, 'File'),    #     from the directory where we extracted our source package
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
        product = root.find('{%s}Product' % WIX_NS)
        include = product.find('{%s}Directory' % WIX_NS)

        # deepcopy the Wix/Product/Directory node into a new tree
        newroot = etree.Element('{%s}Include' % WIX_NS, nsmap=WIX_NSMAP)
        targetdir = etree.SubElement(newroot,
                                     '{%s}DirectoryRef' % WIX_NS,
                                     Id='TARGETDIR')
        libdir = etree.SubElement(targetdir,
                                  '{%s}Directory' % WIX_NS,
                                  Name='Lib', Id='Lib')
        spdir = etree.SubElement(libdir,
                                 '{%s}Directory' % WIX_NS,
                                 Name='site-packages', Id='site_packages')
        gtkdir = etree.SubElement(spdir,
                                  '{%s}Directory' % WIX_NS,
                                  Name='gtk-2.0', Id='gtk_2.0')
        rtdir = etree.SubElement(gtkdir,
                                 '{%s}Directory' % WIX_NS,
                                  Name='runtime', Id='runtime')

        for child in include:
            rtdir.append(deepcopy(child))

        self.include = newroot

    def do_transform(self):
        info('Transforming "Id" attributes...', 4)
        self.transform_id(self.include)

        info ('Transforming variables...', 4)
        self.transform_variables(self.include)

        info ('Transforming RemoveFile elements for *.py files', 4)
        self.transform_py_files(self.include)

    def transform_variables(self, element):
        pi = etree.ProcessingInstruction('define', '%s_sourcedir = "%s"' % (self.package.get('Id'), join(self.builddir, 'File')))
        element.insert(0, pi)

    def transform_py_files(self, element):
        '''
        Create a RemoveFile element instructing windows installer to remove
        .pyc and .pyo files for each .py file we encounter.
        '''
        def transform(element):
            if element.tag == '{%s}File' % WIX_NS and basename(element.get('Source')).endswith('.py'):
                component = element.getparent()
                directory = component.getparent()

                etree.SubElement(component,
                                  '{%s}RemoveFile' % WIX_NS,
                                  Id='%sc' % element.get('Id'),
                                  Directory=directory.get('Id'),
                                  Name='%sc' % basename(element.get('Source')),
                                  On='uninstall')
                etree.SubElement(component,
                                  '{%s}RemoveFile' % WIX_NS,
                                  Id='%so' % element.get('Id'),
                                  Directory=directory.get('Id'),
                                  Name='%so' % basename(element.get('Source')),
                                  On='uninstall')

            for child in element:
                transform(child)

        transform(element)


def main():
    start = datetime.now()

    builder = Builder()
    builder.build()

    end = datetime.now()
    minutes, seconds = divmod((end - start).seconds, 60)

    info('Builder finished in %s minutes %s seconds' % (minutes, seconds))


if __name__ == '__main__':
    main()
