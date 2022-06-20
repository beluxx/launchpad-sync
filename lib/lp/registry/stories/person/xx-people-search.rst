People and Team Search
======================

Searching for people
--------------------

    >>> browser.open('http://launchpad.test/people')
    >>> print(browser.title)
    People and teams in Launchpad

Search for all people and teams with the string "foo bar".  There
should just be the one person named "Foo Bar" found.

    >>> browser.getControl(name='name').value = 'foo bar'
    >>> browser.getControl('Search').click()
    >>> listing = find_tag_by_id(browser.contents, 'people-results')
    >>> print(extract_text(listing))
    Name          Launchpad ID  Karma
    Foo Bar       name16        241

The listing is sortable.

    >>> print(' '.join(listing['class']))
    listing sortable

Search for all people and teams like "launchpad" the users sees three
columns of people and teams..

    >>> browser.getControl(name='name').value = 'launchpad'
    >>> browser.getControl('Search').click()
    >>> listing = find_tag_by_id(browser.contents, 'people-results')
    >>> print(extract_text(listing, formatter='html'))
    Name                         Launchpad ID              Karma
    Julian Edwards               launchpad-julian-edwards  0
    Launchpad Administrators     admins                    &mdash;
    Launchpad Beta Testers Owner launchpad-beta-owner      0
    Launchpad Beta Testers       launchpad-beta-testers    &mdash;
    Launchpad Buildd Admins      launchpad-buildd-admins   &mdash;

Restrict the search to teams and the individuals are no longer
listed.  Due to batching teams that were not displayed before are now
shown. There are only two columns because teams cannot have karma.

    >>> browser.getControl(name='name').value = 'launchpad'
    >>> browser.getControl(name='searchfor').value = ['teamsonly']
    >>> browser.getControl('Search').click()
    >>> listing = find_tag_by_id(browser.contents, 'people-results')
    >>> print(extract_text(listing))
    Name                         Launchpad ID
    Launchpad Administrators     admins
    Launchpad Beta Testers       launchpad-beta-testers
    Launchpad Buildd Admins      launchpad-buildd-admins
    Launchpad Developers         launchpad
    Launchpad PPA Admins         launchpad-ppa-admins

Restrict the search to people and only individuals are listed.

    >>> browser.getControl(name='name').value = 'launchpad'
    >>> browser.getControl(name='searchfor').value = ['peopleonly']
    >>> browser.getControl('Search').click()
    >>> listing = find_tag_by_id(browser.contents, 'people-results')
    >>> print(extract_text(listing))
    Name                         Launchpad ID              Karma
    Julian Edwards               launchpad-julian-edwards  0
    Launchpad Beta Testers Owner launchpad-beta-owner      0
    Launchpad Janitor            janitor                   0
