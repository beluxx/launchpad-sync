Bug nomination navigation
=========================

Most people don't see the separate page for approving or declining a
release nomination for a bug, because it's handled using an expandable
section on the bug page itself.

But for those people who do see the separate page, the page has the
same navigation as the bug page itself.

    >>> admin_browser.open(
    ...     "http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/+bug/1"
    ...     "/nominations/2/+editstatus"
    ... )
    >>> print_location(admin_browser.contents)
    Hierarchy: Ubuntu > mozilla-firefox package > Bug #1...
    Tabs:
    * Overview - http://launchpad.test/ubuntu/+source/mozilla-firefox
    * Code - http://code.launchpad.test/ubuntu/+source/mozilla-firefox
    * Bugs (selected) -
      http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox
    * Blueprints - not linked
    * Translations -
      http://translations.launchpad.test/ubuntu/+source/mozilla-firefox
    * Answers - http://answers.launchpad.test/ubuntu/+source/mozilla-firefox
    Main heading: Approve or decline nomination for bug #1 in Ubuntu Hoary
