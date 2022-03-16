# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Package information classes.

This classes are responsable for fetch and hold the information inside
the sources and binarypackages.
"""

__all__ = [
    'BinaryPackageData',
    'DisplayNameDecodingError',
    'get_dsc_path',
    'InvalidVersionError',
    'MissingRequiredArguments',
    'PoolFileNotFound',
    'prioritymap',
    'SourcePackageData',
    ]

from email.utils import parseaddr
import glob
import os
import re
import shutil
import tempfile

import six

from lp.app.validators.version import valid_debian_version
from lp.archivepublisher.diskpool import poolify
from lp.archiveuploader.changesfile import ChangesFile
from lp.archiveuploader.dscfile import DSCFile
from lp.archiveuploader.nascentuploadfile import BaseBinaryUploadFile
from lp.archiveuploader.utils import (
    DpkgSourceError,
    extract_dpkg_source,
    )
from lp.services import encoding
from lp.services.database.constants import UTC_NOW
from lp.services.scripts import log
from lp.soyuz.enums import PackagePublishingPriority
from lp.soyuz.scripts.gina import (
    call,
    ExecutionError,
    )
from lp.soyuz.scripts.gina.changelog import parse_changelog


#
# Data setup
#

prioritymap = {
    "required": PackagePublishingPriority.REQUIRED,
    "important": PackagePublishingPriority.IMPORTANT,
    "standard": PackagePublishingPriority.STANDARD,
    "optional": PackagePublishingPriority.OPTIONAL,
    "extra": PackagePublishingPriority.EXTRA,
    # Some binarypackages ended up with priority source, apparently
    # because of a bug in dak.
    "source": PackagePublishingPriority.EXTRA,
}


#
# Helper functions
#

def stripseq(seq):
    return [s.strip() for s in seq]


epoch_re = re.compile(r"^\d+:")


def get_dsc_path(name, version, component, archive_root):
    pool_root = os.path.join(archive_root, "pool")
    version = epoch_re.sub("", version)
    filename = "%s_%s.dsc" % (name, version)

    # We do a first attempt using the obvious directory name, composed
    # with the component. However, this may fail if a binary is being
    # published in another component.
    pool_dir = poolify(name, component)
    fullpath = os.path.join(pool_root, pool_dir, filename)
    if os.path.exists(fullpath):
        return filename, fullpath, component

    # Do a second pass, scrubbing through all components in the pool.
    for alt_component_entry in os.scandir(pool_root):
        if not alt_component_entry.is_dir():
            continue
        pool_dir = poolify(name, alt_component_entry.name)
        fullpath = os.path.join(pool_root, pool_dir, filename)
        if os.path.exists(fullpath):
            return filename, fullpath, alt_component_entry.name

    # Couldn't find the file anywhere -- too bad.
    raise PoolFileNotFound("File %s not in archive" % filename)


def unpack_dsc(package, version, component, distro_name, archive_root):
    dsc_name, dsc_path, component = get_dsc_path(package, version,
                                                 component, archive_root)
    version = re.sub(r"^\d+:", "", version)
    version = re.sub(r"-[^-]+$", "", version)
    source_dir = "%s-%s" % (package, version)
    try:
        extract_dpkg_source(dsc_path, ".", vendor=distro_name)
    except DpkgSourceError as e:
        if os.path.isdir(source_dir):
            shutil.rmtree(source_dir)
        raise ExecutionError("Error %d unpacking source" % e.result)

    return source_dir, dsc_path


def read_dsc(package, version, component, distro_name, archive_root):
    source_dir, dsc_path = unpack_dsc(package, version, component,
                                      distro_name, archive_root)

    try:
        with open(dsc_path, "rb") as f:
            dsc = f.read().strip()

        fullpath = os.path.join(source_dir, "debian", "changelog")
        changelog = None
        if os.path.exists(fullpath):
            with open(fullpath, "rb") as f:
                changelog = f.read().strip()
        else:
            log.warning(
                "No changelog file found for %s in %s" % (package, source_dir))
            changelog = None

        copyright = None
        globpath = os.path.join(source_dir, "debian", "*copyright")
        for fullpath in glob.glob(globpath):
            if not os.path.exists(fullpath):
                continue
            with open(fullpath, "rb") as f:
                copyright = f.read().strip()

        if copyright is None:
            log.warning(
                "No copyright file found for %s in %s" % (package, source_dir))
            copyright = b''
    finally:
        shutil.rmtree(source_dir)

    return dsc, changelog, copyright


def parse_person(val):
    """Parse a full email address into human-readable name and address."""
    # Some addresses have commas in them, as in: "Adam C. Powell, IV
    # <hazelsct@debian.example.com>". email.utils.parseaddr seems not to
    # handle this properly, so we munge them here.
    val = val.replace(',', '')
    return parseaddr(val)


def parse_section(v):
    if "/" in v:
        # When a "/" is found in the section, it indicates
        # component/section. We don't want to override the
        # component, since it is correctly indicated by the
        # packages/sources files.
        return v.split("/", 1)[1]
    else:
        return v


#
# Exception classes
#

class MissingRequiredArguments(Exception):
    """Missing Required Arguments Exception.

    Raised if we attempted to construct a SourcePackageData based on an
    invalid Sources.gz entry -- IOW, without all the required arguments.
    This is because we are stuck (for now) passing arguments using
    **args as some of the argument names are not valid Python identifiers
    """


class PoolFileNotFound(Exception):
    """The specified file was not found in the archive pool"""


class InvalidVersionError(Exception):
    """An invalid package version was found"""


class InvalidSourceVersionError(InvalidVersionError):
    """
    An invalid source package version was found when processing a binary
    package.
    """


class DisplayNameDecodingError(Exception):
    """Invalid unicode encountered in displayname"""


#
# Implementation classes
#

class AbstractPackageData:
    # This class represents information on a single package that was
    # obtained through the archive. This information comes from either a
    # Sources or Packages file, and is complemented by data scrubbed
    # from the corresponding pool files (the dsc, deb and tar.gz)
    archive_root = None
    package = None
    _required = None
    _user_defined = None
    version = None

    # Component is something of a special case. It is set up in
    # archive.py:PackagesMap and always supplied to the constructor (and
    # only overwritten after in special cases, which I'm not sure are
    # really correct). We check it as part of _required in the
    # subclasses only as a sanity check.
    component = None

    def __init__(self):
        if self.version is None or not valid_debian_version(self.version):
            raise InvalidVersionError("%s has an invalid version: %s" %
                                      (self.package, self.version))

        absent = object()
        missing = []
        for attr in self._required:
            if isinstance(attr, tuple):
                if all(getattr(self, oneattr, absent) is absent
                       for oneattr in attr):
                    missing.append(attr)
            elif getattr(self, attr, absent) is absent:
                missing.append(attr)
        if missing:
            raise MissingRequiredArguments(missing)

    def process_package(self, distro_name, archive_root):
        """Process the package using the files located in the archive.

        Raises PoolFileNotFound if a file is not found in the pool.
        """
        self.archive_root = archive_root

        tempdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(tempdir)
        try:
            self.do_package(distro_name, archive_root)
        finally:
            os.chdir(cwd)
            shutil.rmtree(tempdir)

        self.date_uploaded = UTC_NOW
        return True

    def is_field_known(self, lowfield):
        """Is this field a known one?"""
        # _known_fields contains the fields that archiveuploader recognises
        # from a raw .dsc or .*deb; _required contains a few extra fields
        # that are added to Sources and Packages index files.  If a field is
        # in neither, it counts as user-defined.
        if lowfield in self._known_fields:
            return True
        for required in self._required:
            if isinstance(required, tuple):
                if lowfield in required:
                    return True
            elif lowfield == required:
                return True
        return False

    def set_field(self, key, value):
        """Record an arbitrary control field."""
        lowkey = key.lower()
        if self.is_field_known(lowkey):
            setattr(self, lowkey.replace("-", "_"), value)
        else:
            if self._user_defined is None:
                self._user_defined = []
            self._user_defined.append([key, value])

    def do_package(self, distro_name, archive_root):
        """To be provided by derived class."""
        raise NotImplementedError


class SourcePackageData(AbstractPackageData):
    """Important data relating to a given `SourcePackageRelease`."""

    # Defaults, overwritten by __init__
    directory = None

    # Defaults, potentially overwritten by __init__
    build_depends = ""
    build_depends_indep = ""
    build_conflicts = ""
    build_conflicts_indep = ""
    standards_version = ""
    section = None
    format = None

    # These arguments /must/ have been set in the Sources file and
    # supplied to __init__ as keyword arguments. If any are not, a
    # MissingRequiredArguments exception is raised.
    _required = [
        'package',
        'binaries',
        'version',
        'maintainer',
        'section',
        'architecture',
        'directory',
        ('files', 'checksums-sha1', 'checksums-sha256', 'checksums-sha512'),
        'component',
        ]

    _known_fields = {k.lower() for k in DSCFile.known_fields}

    def __init__(self, **args):
        for k, v in args.items():
            if k == 'Binary':
                self.binaries = stripseq(six.ensure_text(v).split(","))
            elif k == 'Section':
                self.section = parse_section(six.ensure_text(v))
            elif k == 'Urgency':
                urgency = six.ensure_text(v)
                # This is to handle cases like:
                #   - debget: 'high (actually works)
                #   - lxtools: 'low, closes=90239'
                if " " in urgency:
                    urgency = urgency.split()[0]
                if "," in urgency:
                    urgency = urgency.split(",")[0]
                self.urgency = urgency
            elif k == 'Maintainer':
                try:
                    maintainer = encoding.guess(v)
                except UnicodeDecodeError:
                    raise DisplayNameDecodingError(
                        "Could not decode Maintainer field %r" % v)
                self.maintainer = parse_person(maintainer)
            elif k == 'Files' or k.startswith('Checksums-'):
                if not hasattr(self, 'files'):
                    self.files = []
                    files = six.ensure_text(v).split("\n")
                    for f in files:
                        self.files.append(stripseq(f.split(" "))[-1])
            else:
                self.set_field(k, encoding.guess(v))

        if self.section is None:
            self.section = 'misc'
            log.warning(
                "Source package %s lacks section, assumed %r",
                self.package, self.section)

        if '/' in self.section:
            # this apparently happens with packages in universe.
            # 3dchess, for instance, uses "universe/games"
            self.section = self.section.split("/", 1)[1]

        AbstractPackageData.__init__(self)

    def do_package(self, distro_name, archive_root):
        """Get the Changelog and urgency from the package on archive.

        If successful processing of the package occurs, this method
        sets the changelog and urgency attributes.
        """
        dsc, changelog, copyright = read_dsc(
            self.package, self.version, self.component, distro_name,
            archive_root)

        self.dsc = encoding.guess(dsc)
        self.copyright = encoding.guess(copyright)
        parsed_changelog = None
        if changelog:
            parsed_changelog = parse_changelog(changelog.split(b'\n'))

        self.urgency = None
        self.changelog = None
        self.changelog_entry = None
        if parsed_changelog and parsed_changelog[0]:
            cldata = parsed_changelog[0]
            if 'changes' in cldata:
                cldata_package = six.ensure_text(cldata["package"])
                cldata_version = six.ensure_text(cldata["version"])
                if cldata_package != self.package:
                    log.warning(
                        "Changelog package %s differs from %s" %
                        (cldata_package, self.package))
                if cldata_version != self.version:
                    log.warning(
                        "Changelog version %s differs from %s" %
                        (cldata_version, self.version))
                self.changelog_entry = encoding.guess(cldata["changes"])
                self.changelog = changelog
                self.urgency = cldata["urgency"]
                if self.urgency is not None:
                    self.urgency = six.ensure_text(self.urgency)
            else:
                log.warning(
                    "Changelog empty for source %s (%s)" %
                    (self.package, self.version))

    def ensure_complete(self):
        if self.format is None:
            # XXX kiko 2005-11-05: this is very funny. We care so much about
            # it here, but we don't do anything about this in handlers.py!
            self.format = "1.0"
            log.warning(
                "Invalid format in %s, assumed %r", self.package, self.format)

        if self.urgency not in ChangesFile.urgency_map:
            log.warning(
                "Invalid urgency in %s, %r, assumed %r",
                self.package, self.urgency, "low")
            self.urgency = "low"


class BinaryPackageData(AbstractPackageData):
    """This Class holds important data to a given binarypackage."""

    # These attributes must have been set by the end of the __init__ method.
    # They are passed in as keyword arguments. If any are not set, a
    # MissingRequiredArguments exception is raised.
    _required = [
        'package',
        'installed_size',
        'maintainer',
        'section',
        'architecture',
        'version',
        'filename',
        'component',
        'size',
        ('md5sum', 'sha1', 'sha256', 'sha512'),
        'description',
        'summary',
        'priority',
        ]

    _known_fields = {k.lower() for k in BaseBinaryUploadFile.known_fields}

    # Set in __init__
    source = None
    source_version = None
    version = None
    architecture = None
    filename = None
    section = None
    priority = None

    # Defaults, optionally overwritten in __init__
    depends = ""
    suggests = ""
    recommends = ""
    conflicts = ""
    replaces = ""
    provides = ""
    pre_depends = ""
    enhances = ""
    breaks = ""
    built_using = ""
    essential = False

    # Overwritten in do_package, optionally
    shlibs = None

    source_version_re = re.compile(r'([^ ]+) +\(([^\)]+)\)')

    def __init__(self, **args):
        for k, v in args.items():
            if k == "Maintainer":
                self.maintainer = parse_person(encoding.guess(v))
            elif k == "Essential":
                self.essential = (v == b"yes")
            elif k == 'Section':
                self.section = parse_section(six.ensure_text(v))
            elif k == "Description":
                self.description = encoding.guess(v)
                summary = self.description.split("\n")[0].strip()
                if not summary.endswith('.'):
                    summary = summary + '.'
                self.summary = summary
            elif k == "Installed-Size":
                installed_size = six.ensure_text(v)
                try:
                    self.installed_size = int(installed_size)
                except ValueError:
                    raise MissingRequiredArguments("Installed-Size is "
                        "not a valid integer: %r" % installed_size)
            elif k == "Built-Using":
                self.built_using = six.ensure_text(v)
                # Preserve the original form of Built-Using to avoid
                # possible unfortunate apt behaviour.  This is most easily
                # done by adding it to _user_defined as well.
                if self._user_defined is None:
                    self._user_defined = []
                self._user_defined.append([k, self.built_using])
            else:
                self.set_field(k, encoding.guess(v))

        if self.source:
            # We need to handle cases like "Source: myspell
            # (1:3.0+pre3.1-6)". apt-pkg kindly splits this for us
            # already, but sometimes fails.
            # XXX: dsilvers 2005-09-22: Work out why this happens and
            # file an upstream bug against python-apt once we've worked
            # it out.
            if self.source_version is None:
                match = self.source_version_re.match(self.source)
                if match:
                    self.source = match.group(1)
                    self.source_version = match.group(2)
                else:
                    # XXX kiko 2005-10-18:
                    # This is probably a best-guess and might fail.
                    self.source_version = self.version
        else:
            # Some packages have Source, some don't -- the ones that
            # don't have the same package name.
            self.source = self.package
            self.source_version = self.version

        if (self.source_version is None or
            self.source_version != self.version and
            not valid_debian_version(self.source_version)):
            raise InvalidSourceVersionError(
                "Binary package %s (%s) refers to source package %s "
                "with invalid version: %s" %
                (self.package, self.version, self.source,
                 self.source_version))

        if self.section is None:
            self.section = 'misc'
            log.warning(
                "Binary package %s lacks a section, assumed %r",
                self.package, self.section)

        if self.priority is None:
            self.priority = 'extra'
            log.warning(
                "Binary package %s lacks valid priority, assumed %r",
                self.package, self.priority)

        AbstractPackageData.__init__(self)

    def do_package(self, distro_name, archive_root):
        """Grab shared library info from .deb."""
        fullpath = os.path.join(archive_root, self.filename)
        if not os.path.exists(fullpath):
            raise PoolFileNotFound('%s not found' % fullpath)

        call("dpkg -e %s" % fullpath)
        shlibfile = os.path.join("DEBIAN", "shlibs")
        if os.path.exists(shlibfile):
            with open(shlibfile) as f:
                self.shlibs = f.read().strip()
            log.debug("Grabbing shared library info from %s" % shlibfile)
