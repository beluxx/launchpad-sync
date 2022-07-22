# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Library access methods to gina."""

import hashlib
import os

from zope.component import getUtility

from lp.services.librarian.interfaces import ILibraryFileAliasSet


def _libType(fname):
    if fname.endswith(".dsc"):
        return "text/x-debian-source-package"
    if fname.endswith(".deb"):
        return "application/x-debian-package"
    if fname.endswith(".udeb"):
        return "application/x-micro-debian-package"
    if fname.endswith(".diff.gz"):
        return "application/gzipped-patch"
    if fname.endswith(".tar.gz"):
        return "application/gzipped-tar"
    return "application/octet-stream"


def getLibraryAlias(root, filename):
    librarian = getUtility(ILibraryFileAliasSet)
    if librarian is None:
        return None
    fname = os.path.join(root, filename)
    fobj = open(fname, "rb")
    size = os.stat(fname).st_size
    alias = librarian.create(
        filename, size, fobj, contentType=_libType(filename)
    )
    fobj.close()
    return alias


def checkLibraryForFile(path, filename):
    fullpath = os.path.join(path, filename)
    assert os.path.exists(fullpath)
    digester = hashlib.sha256()
    openfile = open(fullpath, "rb")
    for chunk in iter(lambda: openfile.read(1024 * 4), b""):
        digester.update(chunk)
    digest = digester.hexdigest()
    openfile.close()
    librarian = getUtility(ILibraryFileAliasSet)
    return not librarian.findBySHA256(digest).is_empty()
