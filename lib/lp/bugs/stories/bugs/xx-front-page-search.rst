Searching from the Bugs front page
==================================

It's possible to search bug reports across all of Launchpad from the
Bugs front page.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('Search Bug Reports') is not None
    True

Either all projects, or a specific one can be searched.

    >>> anon_browser.getControl('All projects') is not None
    True
    >>> anon_browser.getControl('One project') is not None
    True

Searching all projects
----------------------

When choosing to search all the projects, all open bug reports in
Launchpad will be searched, and the bug target will be visible in the
bug listing.

    >>> from lp.bugs.tests.bug import print_bugtasks
    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('All projects').selected = True
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> print(anon_browser.title)
    Search all bug reports
    >>> print_bugtasks(anon_browser.contents)
    3 Bug Title Test
      mozilla-firefox (Debian) Unknown New
    3 Bug Title Test
      mozilla-firefox (Debian Woody) Medium New
    3 Bug Title Test
      mozilla-firefox (Debian Sarge) Medium New
    7 A test bug
      Evolution Medium New
    10 another test bug
      linux-source-2.6.15 (Ubuntu) Medium New

Even if a product is specified in the bug target widget, all bug reports
will be searched.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('All projects').selected = True
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl(name='field.scope.target').value = 'evolution'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> anon_browser.title
    'Search all bug reports'

The same is of course true if the target widget contains a non-existent
project name.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('All projects').selected = True
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl(name='field.scope.target').value = 'invalid'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> anon_browser.title
    'Search all bug reports'

It's also possible to go to the search page directly, without submitting
the form at the front page.

    >>> search_url, query = anon_browser.url.split('?', 1)
    >>> anon_browser.open(search_url)
    >>> anon_browser.title
    'Search all bug reports'

Searching one project
---------------------

If the user chooses to search only one project, they will be forwarded to
the project's bug listing, and the search will be performed there. If no
name is specified, an error message will be displayed.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('One project').selected = True
    >>> anon_browser.getControl(name='field.scope.target').value = ''
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> anon_browser.url
    'http://bugs.launchpad.test/bugs?...'
    >>> anon_browser.getControl(name='field.searchtext').value
    'test bug'

    >>> for message in find_tags_by_class(anon_browser.contents, 'message'):
    ...     print(message.decode_contents())
    Please enter a project name

An error message will be displayed also if the project isn't registered
in the Launchpad.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('One project').selected = True
    >>> anon_browser.getControl(name='field.scope.target').value = 'invalid'
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> anon_browser.url
    'http://bugs.launchpad.test/bugs?...&field.scope.target=invalid...'
    >>> anon_browser.getControl(name='field.searchtext').value
    'test bug'
    >>> for message in find_tags_by_class(anon_browser.contents, 'message'):
    ...     print(message.decode_contents())
    There is no project named 'invalid' registered in Launchpad

If the user doesn't know what name to write, they can use the 'Choose'
link if the browser supports javascript. The test browser does not
support javascript, so a 'Find' link pointing to /bugs is displayed.

    >>> find_link = anon_browser.getLink('Find')
    >>> find_link.url
    'http://bugs.launchpad.test/bugs...'

'Project' in this context means either a product, distribution or a
project group.

Searching a product
...................

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('One project').selected = True
    >>> anon_browser.getControl(name='field.scope.target').value = 'evolution'
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> print(anon_browser.title)
    Bugs : Evolution...
    >>> anon_browser.url
    'http://bugs.launchpad.test/evolution/+bugs?field.searchtext=test+bug...'
    >>> print_bugtasks(anon_browser.contents)
    7 A test bug Evolution
      Medium New

Searching a project
...................

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('One project').selected = True
    >>> anon_browser.getControl(name='field.scope.target').value = 'gnome'
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> print(anon_browser.title)
    Bugs : GNOME
    >>> anon_browser.url
    'http://bugs.launchpad.test/gnome/+bugs?field.searchtext=test+bug...'
    >>> print_bugtasks(anon_browser.contents)
    7 A test bug
      Evolution Medium New

Searching a distribution
........................

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl('One project').selected = True
    >>> anon_browser.getControl(name='field.scope.target').value = 'ubuntu'
    >>> anon_browser.getControl(name='field.searchtext').value = 'test bug'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> print(anon_browser.title)
    Bugs : Ubuntu...
    >>> anon_browser.url
    'http://bugs.launchpad.test/ubuntu/+bugs?field.searchtext=test+bug...'
    >>> print_bugtasks(anon_browser.contents)
    10 another test bug
       linux-source-2.6.15 (Ubuntu)  Medium  New

Jumping to a bug
................

Like with all other bug searches, it's possible to jump a bug by
specifying only the bug id as the search term.

    >>> anon_browser.open('http://bugs.launchpad.test/')
    >>> anon_browser.getControl(name='field.searchtext').value = '7'
    >>> anon_browser.getControl('Search Bug Reports').click()
    >>> anon_browser.url
    'http://.../+bug/7'
    >>> anon_browser.title
    'Bug #7...'
