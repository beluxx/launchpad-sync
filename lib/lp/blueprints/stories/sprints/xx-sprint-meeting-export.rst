Add some attendees to the sprint.

    >>> admin_browser.open('http://launchpad.test/sprints/ubz')
    >>> admin_browser.getLink('Register yourself').click()
    >>> admin_browser.getControl('Register').click()
    >>> admin_browser.getLink('Register someone else').click()
    >>> admin_browser.getControl(name='field.attendee').value='cprov'
    >>> admin_browser.getControl('Register').click()

Get the sprint meeting export:

    >>> browser.open('http://launchpad.test/sprints/ubz/+temp-meeting-export')
    >>> print(browser.headers['content-type'])
    application/xml;charset=utf-8


The meeting export should have a reference to the
extension-manager-upgrades spec:

    >>> 'extension-manager-upgrades' in browser.contents
    True

Verify that the data is valid XML and has the expected toplevel
element name:

    >>> from xml.dom.minidom import parseString
    >>> document = parseString(str(browser.contents))
    >>> print(document.documentElement.nodeName)
    schedule

The attendees element contains a list of person elements.

    >>> import operator
    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> soup = BeautifulSoup(browser.contents, 'xml')
    >>> people = soup.find('attendees').find_all('person')
    >>> for person in sorted(people, key=operator.itemgetter("displayname")):
    ...     print("%(displayname)s, %(name)s, %(start)s -> %(end)s" % person)
    Celso Providelo, cprov, 2005-10-07T23:30:00Z -> 2005-11-17T00:11:00Z
    Foo Bar, name16, 2005-10-07T23:30:00Z -> 2005-11-17T00:11:00Z

The <unscheduled /> element contains a list of meetings. Each of these
actually refers to a Specification.

    >>> soup = BeautifulSoup(browser.contents, 'xml')
    >>> meetings = soup.find('unscheduled').find_all('meeting')
    >>> for meeting in meetings:
    ...     print("%(id)s: %(name)s, %(lpurl)s" % meeting)
    3: svg-support, .../+spec/svg-support
    1: extension-manager-upgrades, .../+spec/extension-manager-upgrades
