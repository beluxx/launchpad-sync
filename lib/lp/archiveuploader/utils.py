# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Archive uploader utilities."""

__all__ = [
    'determine_binary_file_type',
    'determine_source_file_type',
    'DpkgSourceError',
    'extract_dpkg_source',
    'get_source_file_extension',
    'parse_and_merge_file_lists',
    'parse_maintainer_bytes',
    'ParseMaintError',
    'prefix_multi_line_string',
    're_taint_free',
    're_isadeb',
    're_isbuildinfo',
    're_issource',
    're_is_component_orig_tar_ext',
    're_is_component_orig_tar_ext_sig',
    're_no_epoch',
    're_no_revision',
    're_valid_version',
    're_valid_pkg_name',
    're_changes_file_name',
    're_extract_src_version',
    'rfc822_encode_address',
    'UploadError',
    'UploadWarning',
    ]


from collections import defaultdict
import os
import re
import signal
import subprocess

import six

from lp.services.encoding import guess as guess_encoding
from lp.soyuz.enums import BinaryPackageFileType


class UploadError(Exception):
    """All upload errors are returned in this form."""


class UploadWarning(Warning):
    """All upload warnings are returned in this form."""


class DpkgSourceError(Exception):

    _fmt = "Unable to unpack source package (%(result)s): %(output)s"

    def __init__(self, command, output, result):
        super(DpkgSourceError, self).__init__(
            self._fmt % {
                "output": output, "result": result, "command": command})
        self.output = output
        self.result = result
        self.command = command


re_taint_free = re.compile(r"^[-+~/\.\w]+$")

re_isadeb = re.compile(r"(.+?)_(.+?)_(.+)\.(u?d?deb)$")
re_isbuildinfo = re.compile(r"(.+?)_(.+?)_(.+)\.buildinfo$")

source_file_exts = [
    r'orig(?:-.+)?\.tar\.(?:gz|bz2|xz)(?:\.asc)?', 'diff.gz',
    r'(?:debian\.)?tar\.(?:gz|bz2|xz)', 'dsc']
re_issource = re.compile(
    r"([^_]+)_(.+?)\.(%s)" % "|".join(ext for ext in source_file_exts))
re_is_component_orig_tar_ext = re.compile(r"^orig-(.+).tar.(?:gz|bz2|xz)$")
re_is_component_orig_tar_ext_sig = re.compile(
    r"^orig-(.+).tar.(?:gz|bz2|xz)\.asc$")
re_is_orig_tar_ext = re.compile(r"^orig.tar.(?:gz|bz2|xz)$")
re_is_orig_tar_ext_sig = re.compile(r"^orig.tar.(?:gz|bz2|xz)\.asc$")
re_is_debian_tar_ext = re.compile(r"^debian.tar.(?:gz|bz2|xz)$")
re_is_native_tar_ext = re.compile(r"^tar.(?:gz|bz2|xz)$")

re_no_epoch = re.compile(r"^\d+\:")
re_no_revision = re.compile(r"-[^-]+$")

re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+~:]+$")
re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_changes_file_name = re.compile(r"([^_]+)_([^_]+)_([^\.]+).changes")
re_extract_src_version = re.compile(r"(\S+)\s*\((.*)\)")

re_parse_maintainer = re.compile(r"^\s*(\S.*\S)\s*\<([^\>]+)\>")


def get_source_file_extension(filename):
    """Get the extension part of a source file name."""
    match = re_issource.match(filename)
    if match is None:
        return None
    return match.group(3)


def determine_source_file_type(filename):
    """Determine the SourcePackageFileType of the given filename."""
    # Avoid circular imports.
    from lp.registry.interfaces.sourcepackage import SourcePackageFileType

    extension = get_source_file_extension(filename)
    if extension is None:
        return None
    elif extension == "dsc":
        return SourcePackageFileType.DSC
    elif extension == "diff.gz":
        return SourcePackageFileType.DIFF
    elif re_is_orig_tar_ext.match(extension):
        return SourcePackageFileType.ORIG_TARBALL
    elif re_is_component_orig_tar_ext.match(extension):
        return SourcePackageFileType.COMPONENT_ORIG_TARBALL
    elif re_is_debian_tar_ext.match(extension):
        return SourcePackageFileType.DEBIAN_TARBALL
    elif re_is_native_tar_ext.match(extension):
        return SourcePackageFileType.NATIVE_TARBALL
    elif re_is_orig_tar_ext_sig.match(extension):
        return SourcePackageFileType.ORIG_TARBALL_SIGNATURE
    elif re_is_component_orig_tar_ext_sig.match(extension):
        return SourcePackageFileType.COMPONENT_ORIG_TARBALL_SIGNATURE
    else:
        return None


def determine_binary_file_type(filename):
    """Determine the BinaryPackageFileType of the given filename."""
    if filename.endswith(".deb"):
        return BinaryPackageFileType.DEB
    elif filename.endswith(".udeb"):
        return BinaryPackageFileType.UDEB
    elif filename.endswith(".ddeb"):
        return BinaryPackageFileType.DDEB
    else:
        return None


def prefix_multi_line_string(str, prefix, include_blank_lines=0):
    """Utility function to split an input string and prefix,

    Each line with a token or tag. Can be used for quoting text etc.
    """
    out = ""
    for line in str.split('\n'):
        line = line.strip()
        if line or include_blank_lines:
            out += "%s%s\n" % (prefix, line)
    # Strip trailing new line
    if out:
        out = out[:-1]
    return out


def extract_component_from_section(section, default_component="main"):
    component = ""
    if section.find("/") != -1:
        component, section = section.split("/")
    else:
        component = default_component

    return (section, component)


class ParseMaintError(Exception):
    """Exception raised for errors in parsing a maintainer field.
    """


def parse_maintainer(maintainer, field_name="Maintainer"):
    """Parses a Maintainer or Changed-By field into the name and address.

    maintainer, name and address are all Unicode.
    """
    maintainer = maintainer.strip()
    if not maintainer:
        return (u'', u'')

    if maintainer.find(u"<") == -1:
        email = maintainer
        name = u""
    elif (maintainer[0] == u"<" and maintainer[-1:] == u">"):
        email = maintainer[1:-1]
        name = u""
    else:
        m = re_parse_maintainer.match(maintainer)
        if not m:
            raise ParseMaintError("%s: doesn't parse as a valid %s field."
                                  % (maintainer, field_name))
        name = m.group(1)
        email = m.group(2)
        # Just in case the maintainer ended up with nested angles; check...
        while email.startswith(u"<"):
            email = email[1:]

    if email.find(u"@") == -1 and email.find(u"buildd_") != 0:
        raise ParseMaintError("%s: no @ found in email address part."
                              % maintainer)

    return (name, email)


def parse_maintainer_bytes(content, fieldname):
    """Wrapper for parse_maintainer to handle both Unicode and bytestrings.

    It verifies the content type and transforms it to text with
    guess().  Then we can safely call parse_maintainer().
    """
    if not isinstance(content, six.text_type):
        content = guess_encoding(content)
    return parse_maintainer(content, fieldname)


def rfc822_encode_address(name, email):
    """Return a Unicode RFC822 encoding of a name and an email address.

    name and email must be Unicode. If they contain non-ASCII
    characters, the result is not RFC822-compliant and you should use
    something like format_address instead.

    This is similar to email.utils.format_addr, except that it handles
    special characters using the 'email (name)' format rather than
    '"name" (email)'.
    """
    # If the maintainer's name contains a full stop then the whole field will
    # not work directly as an email address due to a misfeature in the syntax
    # specified in RFC822; see Debian policy 5.6.2 (Maintainer field syntax)
    # for details.
    if name.find(u',') != -1 or name.find(u'.') != -1:
        return u"%s (%s)" % (email, name)
    else:
        return u"%s <%s>" % (name, email)


def extract_dpkg_source(dsc_filepath, target, vendor=None):
    """Extract a source package by dsc file path.

    :param dsc_filepath: Path of the DSC file
    :param target: Target directory
    """

    def subprocess_setup():
        # Python installs a SIGPIPE handler by default. This is usually not
        # what non-Python subprocesses expect.
        # http://www.chiark.greenend.org.uk/ucgi/~cjwatson/ \
        #   blosxom/2009-07-02-python-sigpipe.html
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    args = ["dpkg-source", "-sn", "-x", dsc_filepath]
    env = dict(os.environ)
    if vendor is not None:
        env["DEB_VENDOR"] = vendor
    dpkg_source = subprocess.Popen(
        args, stdout=subprocess.PIPE, cwd=target, stderr=subprocess.PIPE,
        preexec_fn=subprocess_setup, env=env)
    output, unused = dpkg_source.communicate()
    result = dpkg_source.wait()
    if result != 0:
        dpkg_output = prefix_multi_line_string(
            output.decode("UTF-8", errors="replace"), "  ")
        raise DpkgSourceError(result=result, output=dpkg_output, command=args)


def parse_file_list(s, field_name, count):
    if s is None:
        return None
    processed = []
    for line in six.ensure_text(s).strip().split('\n'):
        split = line.strip().split()
        if len(split) != count:
            raise UploadError(
                "Wrong number of fields in %s field line." % field_name)
        processed.append(split)
    return processed


def merge_file_lists(files, checksums_sha1, checksums_sha256, changes=True):
    """Merge Files, Checksums-Sha1 and Checksums-Sha256 fields.

    Turns lists of (MD5, size, [extras, ...,] filename),
    (SHA1, size, filename) and (SHA256, size, filename) into a list of
    (filename, {algo: hash}, size, [extras, ...], filename).

    Duplicate filenames, size conflicts, and files with missing hashes
    will cause an UploadError.

    'extras' is (section, priority) if changes=True, otherwise it is omitted.
    """
    # Preprocess the additional hashes, counting each (filename, size)
    # that we see.
    file_hashes = defaultdict(dict)
    hash_files = defaultdict(lambda: defaultdict(int))
    for (algo, checksums) in [
            ('SHA1', checksums_sha1), ('SHA256', checksums_sha256)]:
        if checksums is None:
            continue
        for hash, size, filename in checksums:
            file_hashes[filename][algo] = hash
            hash_files[algo][(filename, size)] += 1

    # Produce a file list containing all of the present hashes, counting
    # each filename and (filename, size) that we see. We'll throw away
    # the complete list later if we discover that there are duplicates
    # or mismatches with the Checksums-* fields.
    complete_files = []
    file_counter = defaultdict(int)
    for attrs in files:
        if changes:
            md5, size, section, priority, filename = attrs
        else:
            md5, size, filename = attrs
        file_hashes[filename]['MD5'] = md5
        file_counter[filename] += 1
        hash_files['MD5'][(filename, size)] += 1
        if changes:
            complete_files.append(
                (filename, file_hashes[filename], size, section, priority))
        else:
            complete_files.append(
                (filename, file_hashes[filename], size))

    # Ensure that each filename was only listed in Files once.
    if set(six.itervalues(file_counter)) - set([1]):
        raise UploadError("Duplicate filenames in Files field.")

    # Ensure that the Checksums-Sha1 and Checksums-Sha256 fields, if
    # present, list the same filenames and sizes as the Files field.
    for field, algo in [
            ('Checksums-Sha1', 'SHA1'), ('Checksums-Sha256', 'SHA256')]:
        if algo in hash_files and hash_files[algo] != hash_files['MD5']:
            raise UploadError("Mismatch between %s and Files fields." % field)
    return complete_files


def parse_and_merge_file_lists(tag_dict, changes=True):
    files_lines = parse_file_list(
        tag_dict['Files'], 'Files', 5 if changes else 3)
    sha1_lines = parse_file_list(
        tag_dict.get('Checksums-Sha1'), 'Checksums-Sha1', 3)
    sha256_lines = parse_file_list(
        tag_dict.get('Checksums-Sha256'), 'Checksums-Sha256', 3)
    return merge_file_lists(
        files_lines, sha1_lines, sha256_lines, changes=changes)
