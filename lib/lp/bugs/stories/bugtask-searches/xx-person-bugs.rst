Bugs a given user is involved with
==================================

When visiting the 'Bugs' facet of a person, the report that is displayed
lists the bugs related to that person.

    >>> anon_browser.open('http://launchpad.test/~name12')
    >>> anon_browser.getLink('Bugs').click()
    >>> print(anon_browser.title)
    Bugs : Sample Person

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/~name12

Note that we may see each bug more than once in case it's reported
against more than one target (https://launchpad.net/bugs/1357).

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> print_bugtasks(anon_browser.contents)
    3 Bug Title Test
        mozilla-firefox (Debian) Unknown New
    5 Firefox install instructions should be complete
        Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
        Mozilla Firefox Medium New
    5 Firefox install instructions should be complete
        mozilla-firefox (Ubuntu Warty) Medium New
    1 Firefox does not support SVG
        mozilla-firefox (Ubuntu) Medium New
    3 Bug Title Test
        mozilla-firefox (Debian Woody) Medium New
    3 Bug Title Test
        mozilla-firefox (Debian Sarge) Medium New
    2 Blackhole Trash folder
        mozilla-firefox (Debian Woody) Medium New
    7 A test bug
        Evolution Medium New
    9 Thunderbird crashes
        thunderbird (Ubuntu) Medium Confirmed
    2 Blackhole Trash folder
        Ubuntu Medium New
    1 Firefox does not support SVG
        Mozilla Firefox Low New
    2 Blackhole Trash folder
        Tomcat Low New
    1 Firefox does not support SVG
        mozilla-firefox (Debian) Low Confirmed
    2 Blackhole Trash folder
        mozilla-firefox (Debian) Low Confirmed
    2 Blackhole Trash folder
        Ubuntu Hoary Undecided New
    5 Firefox install instructions should be complete
        Mozilla Firefox 1.0 Undecided New
    13 Launchpad CSS and JS is not testible
        Launchpad Undecided New

This report is also the default page in the person context on the bugs
virtual host:

    >>> anon_browser.open('http://bugs.launchpad.test/~name12')
    >>> print(anon_browser.title)
    Bugs : Sample Person


More specific listings
----------------------

On a person bugs facet we get links to all listings of bugs we have for
that person.


Assigned bugs
.............

    >>> anon_browser.getLink('Assigned bugs').click()
    >>> print(anon_browser.title)
    Assigned bugs : Bugs : Sample Person

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/~name12/+assignedbugs

    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
        Mozilla Firefox Critical New
    2 Blackhole Trash folder
        mozilla-firefox (Debian)
        Low
        Confirmed


Commented bugs
..............

    >>> anon_browser.getLink('Commented bugs').click()
    >>> print(anon_browser.title)
    Commented bugs : Bugs : Sample Person

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/~name12/+commentedbugs

No Privileges Person has commented on three open non-duplicate bugs (1,
2, and 13) and made metadata-only changes to four others (3, 5, 7, and
9), all of which will be returned by the commented bug search (the bugs
will be listed several times over; it is enough for us to test for the
first instances of each here. This is an instance of Bug 1357).

    >>> print_bugtasks(anon_browser.contents)
    3 Bug Title Test
        mozilla-firefox (Debian) Unknown New
    5 Firefox install instructions should be complete
        Mozilla Firefox Critical New
    ...
    1 Firefox does not support SVG
        mozilla-firefox (Ubuntu) Medium New
    ...
    2 Blackhole Trash folder
        mozilla-firefox (Debian Woody) Medium New
    7 A test bug
        Evolution Medium New
    9 Thunderbird crashes
        thunderbird (Ubuntu) Medium Confirmed
    ...
    13 Launchpad CSS and JS is not testible
        Launchpad Undecided New


Reported bugs
.............

    >>> anon_browser.getLink('Reported bugs').click()
    >>> print(anon_browser.title)
    Reported bugs : Bugs : Sample Person

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/~name12/+reportedbugs

    >>> print_bugtasks(anon_browser.contents)
    5 Firefox install instructions should be complete
        Mozilla Firefox Critical New
    4 Reflow problems with complex page layouts
        Mozilla Firefox Medium New
    5 Firefox install instructions should be complete
        mozilla-firefox (Ubuntu Warty) Medium New
    2 Blackhole Trash folder
        mozilla-firefox (Debian Woody) Medium New
    1 Firefox does not support SVG
        Mozilla Firefox Low New
    2 Blackhole Trash folder
        Tomcat Low New
    1 Firefox does not support SVG
        mozilla-firefox (Debian) Low Confirmed
    2 Blackhole Trash folder
        mozilla-firefox (Debian) Low Confirmed
    13 Launchpad CSS and JS is not testible
        Launchpad Undecided New


Subscribed bugs
...............

    >>> anon_browser.getLink('Subscribed bugs').click()
    >>> print(anon_browser.title)
    Subscribed bugs : Bugs : Sample Person

    >>> print(anon_browser.url)
    http://bugs.launchpad.test/~name12/+subscribedbugs

    >>> print_bugtasks(anon_browser.contents)
    4 Reflow problems with complex page layouts
        Mozilla Firefox Medium New
    1 Firefox does not support SVG
        mozilla-firefox (Ubuntu) Medium New
    9 Thunderbird crashes
        thunderbird (Ubuntu) Medium Confirmed
    1 Firefox does not support SVG
        Mozilla Firefox Low New
    1 Firefox does not support SVG
        mozilla-firefox (Debian) Low Confirmed
    13 Launchpad CSS and JS is not testible
        Launchpad Undecided New


Person bugs menu
................

The person bugs page can be accessed without being in the bugs site, yet
all the menu links point to the bugs site.

    >>> anon_browser.open('http://launchpad.test/~name12/+assignedbugs')
    >>> print(anon_browser.getLink('Commented bugs').url)
    http://bugs.launchpad.test/~name12/+commentedbugs

    >>> print(anon_browser.getLink('Reported bugs').url)
    http://bugs.launchpad.test/~name12/+reportedbugs

    >>> print(anon_browser.getLink('Subscribed bugs').url)
    http://bugs.launchpad.test/~name12/+subscribedbugs

    >>> print(anon_browser.getLink('All related bugs').url)
    http://bugs.launchpad.test/~name12

    >>> print(anon_browser.getLink('Subscribed packages').url)
    http://bugs.launchpad.test/~name12/+packagebugs

    >>> anon_browser.open('http://launchpad.test/~name12/+commentedbugs')
    >>> print(anon_browser.getLink('Assigned bugs').url)
    http://bugs.launchpad.test/~name12/+assignedbugs

    >>> print(anon_browser.getLink('Affecting bugs').url)
    http://bugs.launchpad.test/~name12/+affectingbugs

