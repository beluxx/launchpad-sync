#!/usr/bin/env python
import apt_pkg, tempfile, os, tempfile, shutil

from classes import SourcePackageRelease, BinaryPackageRelease
from database import Launchpad, Katie

#
package_root = "/srv/archive.ubuntu.com/"
distrorelease = "warty"
components = ["main", "universe", "restricted"]
#components = ["main", "restricted"]
#components = ["restricted"]
arch = "i386"

LPDB = "launchpad_test"
KTDB = "katie"

#
# helpers
#
def get_tagfiles(root, distrorelease, component, arch):
    sources_zipped = os.path.join(root, "dists", distrorelease,
                                  component, "source", "Sources.gz")
    binaries_zipped = os.path.join(root, "dists", distrorelease,
                                   component, "binary-%s" % arch,
                                   "Packages.gz")

    srcfd, sources_tagfile = tempfile.mkstemp()
    os.system("gzip -dc %s > %s" % (sources_zipped, sources_tagfile))
    srcfile = os.fdopen(srcfd)

    binfd, binaries_tagfile = tempfile.mkstemp()
    os.system("gzip -dc %s > %s" % (binaries_zipped, binaries_tagfile))
    binfile = os.fdopen(binfd)

    return srcfile, sources_tagfile, binfile, binaries_tagfile

def do_packages(source_map, bin_map, lp, kdb, keyrings, component):
    try:
        srcfile, src_tags, binfile, bin_tags = \
            get_tagfiles(package_root, distrorelease, component, arch)

        sources = apt_pkg.ParseTagFile(srcfile)
        while sources.Step():
            srcpkg = SourcePackageRelease(component=component, 
                                          **dict(sources.Section))
            source_map[srcpkg.package] = srcpkg

        binaries = apt_pkg.ParseTagFile(binfile)
        while binaries.Step():
            binpkg = BinaryPackageRelease(component=component, 
                                          **dict(binaries.Section))
            name = binpkg.package
            bin_map[name] = binpkg
            # source packages with the same name as binaries get descriptions
            if source_map.has_key(name):
                source_map[name].description = binpkg.description
    finally:
        os.unlink(bin_tags)
        os.unlink(src_tags)

if __name__ == "__main__":
    # get the DB abstractors
    lp = Launchpad(LPDB)
    kdb = Katie(KTDB)

    keyrings = ""
    for keyring in os.listdir("keyrings"):
          keyrings += " --keyring=./keyrings/%s" % keyring
    if not keyrings:
        raise AttributeError, "Keyrings not found in ./keyrings/"

    # Build us dicts of all package releases
    source_map = {}
    bin_map = {}
    for component in components:
        print "@ Loading components for %s" % component
        do_packages(source_map, bin_map, lp, kdb, keyrings, component)

    # Loop through binaries and insert stuff in DB. We do this as a
    # separate loop mainly to ensure that all source packages get
    # preferentially the description relative to a homonymous binary
    # package, and if not, the first description tht pops up.
    bins = bin_map.items()
    bins.sort()
    for name, binpkg in bins:
        print "- Evaluating %s (%s, %s)" % (binpkg.package, 
                                            binpkg.component, 
                                            binpkg.version)
        if not source_map.has_key(binpkg.source):
            # We check if we have a source package or else
            # binpkg.ensure_created() is going to die an ugly death
            print "\t** No source package parsed for %s" % binpkg.package
            continue

        if binpkg.is_created(lp):
            continue

        srcpkg = source_map[binpkg.source]
        if not srcpkg.is_processed:
            if not srcpkg.description:
                # if the source package hasn't had a description
                # set, set one now and hope for the best.
                srcpkg.description = binpkg.description
            # Tricky bit here: even if the source package exists, we
            # need to process it to ensure it has all the data inside it
            # or binary package won't create properly
            srcpkg.process_package(kdb, package_root, keyrings)
            srcpkg.ensure_created(lp)

        # we read the licence from the source package but it is
        # stored in the BinaryPackage table
        binpkg.licence = srcpkg.licence

        binpkg.process_package(kdb, package_root, keyrings)
        binpkg.ensure_created(lp)

    lp.commit()
    lp.close()
    kdb.commit()
    kdb.close()

