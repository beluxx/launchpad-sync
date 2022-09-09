Default values on the +distrotask form
======================================

Source packages often share names across distributions, especially
Debian and Ubuntu. So when you want to indicate that the bug affects
another distribution, the source package field is pre-filled with the
first source package found in the "Affects" list.

    >>> user_browser.open("http://launchpad.test/tomcat/+bug/2")

    >>> from lp.bugs.tests.bug import print_bug_affects_table
    >>> print_bug_affects_table(user_browser.contents)
    Tomcat                   ... New         Low         Unassigned ...
    Ubuntu                   ... Status tracked in Hoary
    Hoary                        New         Undecided   Unassigned ...
    mozilla-firefox (Debian) ... Confirmed   Low         Sample Person ...
    Woody                        New         Medium      Unassigned ...

    >>> user_browser.getLink(url="+distrotask").click()
    >>> user_browser.url
    'http://bugs.launchpad.test/tomcat/+bug/2/+distrotask'
    >>> user_browser.getControl("Source Package").value
    'mozilla-firefox'

The default value of the distribution drop-down list will be Ubuntu.

    >>> user_browser.getControl("Distribution").value
    ['ubuntu']
