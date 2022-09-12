Requesting an OOPS from Launchpad
=================================

OOPSes happen from time to time in Launchpad, and they contain lots of
interesting information for helping debug.  Sometimes though it is useful to
get some of this information even if there hasn't been a problem.  The major
use case for this is to get a dump of the blocking activities that a page
does.

A user can request an oops for a page by using the ++oops++ namespace in any
page traversal.

    >>> browser.open("http://launchpad.test/++oops++")

The OOPS id is put into the comment at the end of the document.

    >>> (page, summary) = browser.contents.split("</body>")
    >>> print(summary)
    <!-- ...
    At least ... actions issued in ... seconds OOPS-...
    <BLANKLINE>
    r...
    -->
    ...

The ++oops++ can be anywhere in the traversal.

    >>> browser.open("http://launchpad.test/gnome-terminal/++oops++/trunk")
    >>> (page, summary) = browser.contents.split("</body>")
    >>> print(summary)
    <!-- ...
    At least ... actions issued in ... seconds OOPS-...
    <BLANKLINE>
    r...
    -->
    ...
