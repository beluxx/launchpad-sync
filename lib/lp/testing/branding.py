# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = ['set_branding']


import os.path

import canonical.launchpad


def set_branding(browser, icon=True, logo=True, mugshot=True):
    """Set the icon, logo and mugshot fields on the given browser instance.

    Setting any of the image parameters to False will NOT set that
    particular item. This allows us to use the function to test branding on
    IPerson and ISprint which do not allow the setting of custom icons.

    This function expects that the given browser instance contains a set of
    field.icon, field.logo and field.mugshot fields, as generated by an
    ImageChangeWidget.
    """
    # make sure we have relevant-sized files handy
    icon_file = os.path.join(
      os.path.dirname(canonical.launchpad.__file__),
      'images/team.png')
    logo_file = os.path.join(
      os.path.dirname(canonical.launchpad.__file__),
      'images/team-logo.png')
    mugshot_file = os.path.join(
      os.path.dirname(canonical.launchpad.__file__),
      'images/team-mugshot.png')
    # set each of the branding elements in turn, if requested
    if icon:
        browser.getControl(name='field.icon.action').value = ['change']
        browser.getControl(name='field.icon.image').add_file(
          open(icon_file), 'image/png', 'icon.png')
    if logo:
        browser.getControl(name='field.logo.action').value = ['change']
        browser.getControl(name='field.logo.image').add_file(
          open(logo_file), 'image/png', 'logo.png')
    if mugshot:
        browser.getControl(name='field.mugshot.action').value = ['change']
        browser.getControl(name='field.mugshot.image').add_file(
          open(mugshot_file), 'image/png', 'mugshot.png')
