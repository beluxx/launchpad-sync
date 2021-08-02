# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create sprites."""

import os
import sys

from lp.services.config import config
from lp.services.spriteutils import SpriteUtil


command_options = ('create-image', 'create-css')


def usage():
    return " Usage: %s %s" % (sys.argv[0], '|'.join(command_options))


def main():
    if len(sys.argv) != 2:
        print("Expected a single argument.", file=sys.stderr)
        print(usage(), file=sys.stderr)
        sys.exit(1)
    else:
        command = sys.argv[1]
        if command not in command_options:
            print("Unknown argument: %s" % command, file=sys.stderr)
            print(usage(), file=sys.stderr)
            sys.exit(2)

    icing = os.path.join(config.root, 'lib/canonical/launchpad/icing')
    sprite_groups = [
        file_name.replace('.css.in', '')
        for file_name in os.listdir(icing) if file_name.endswith('.css.in')]

    for group_name in sprite_groups:
        css_template_file = os.path.join(icing, '%s.css.in' % group_name)
        combined_image_file = os.path.join(icing, '%s.png' % group_name)
        positioning_file = os.path.join(icing, '%s.positioning' % group_name)
        css_file = os.path.join(icing, 'build/%s.css' % group_name)
        if group_name.startswith('block-'):
            # 3 times the size of inline.
            margin = 300
        else:
            # Inline is 2 lines to h1 text + %50 for zooming.
            # 40px + 40px + 20px
            margin = 100

        sprite_util = SpriteUtil(
            css_template_file, 'icon-sprites',
            url_prefix_substitutions={'/@@/': '../images/'},
            margin=margin)

        if command == 'create-image':
            sprite_util.combineImages(icing)
            sprite_util.savePNG(combined_image_file)
            sprite_util.savePositioning(positioning_file)
        elif command == 'create-css':
            sprite_util.loadPositioning(positioning_file)
            # The icing/icon-sprites.png file is relative to the css file
            # in the icing/build/ directory.
            sprite_util.saveConvertedCSS(css_file, '../%s.png' % group_name)
