# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Automatically rebuild the JavaScript bundle when source files change."""

import os
import re

from jsautobuild import YUIBuilder


# Using ionotify we watch our sources of JavaScript in order to know we should
# build when the files change.

def lp_path_builder(changed_path, **builder_props):
    """The custom bit of LP code that determines where files get moved to"""
    # to start out let's assume your CWD is where we're referencing things from
    CWD = os.getcwd()
    JSDIR = os.path.join(CWD, builder_props['build_dir'])
    RENAME = re.compile("^.*lib/lp/(.*)/javascript")

    match = RENAME.search(changed_path)
    js_dir = match.groups()[0]
    return os.path.join(JSDIR, RENAME.sub(js_dir, changed_path))


def main():
    build_dir = 'build/js/lp'
    meta_name = 'LP_MODULES'
    watch_dir = 'lib'

    builder = YUIBuilder(lp_path_builder,
            build_dir,
            watch_dir=watch_dir,
            meta_jsmodule=meta_name)

    builder.run()
