List of owned or driven projects
================================

A Team home page displays a list of projects owned or driven by that
team.

    >>> anon_browser.open('http://launchpad.test/~ubuntu-team')
    >>> related_projects = find_tag_by_id(
    ...     anon_browser.contents, 'portlet-related-projects')
    >>> for tr in related_projects.find_all('tr'):
    ...     print(extract_text(tr))
    Ubuntu
    ubuntutest
    Tomcat

The +related-projects page displays a table with project names.

    >>> anon_browser.getLink('Show related projects').click()
    >>> print(anon_browser.title)
    Related projects : ...Ubuntu Team... team

    >>> related_projects = find_tag_by_id(
    ...     anon_browser.contents, 'related-projects')
    >>> print(extract_text(related_projects))
    Name            Owner   Driver      Bug Supervisor
    Ubuntu          yes     no          no
    ubuntutest      yes     no          no
    Tomcat          yes     no          no


A person's projects are accessible via a link on the 'Related packages' page.

    >>> anon_browser.open('http://launchpad.test/~mark')
    >>> anon_browser.getLink('Related packages').click()
    >>> print(anon_browser.url)
    http://launchpad.test/~mark/+related-packages
    >>> print(anon_browser.title)
    Related packages : Mark Shuttleworth

    >>> anon_browser.open('http://launchpad.test/~mark')
    >>> anon_browser.getLink('Related projects').click()
    >>> related_projects = find_tag_by_id(
    ...     anon_browser.contents, 'related-projects')
    >>> print(extract_text(related_projects))
    Name                            Owner   Driver      Bug Supervisor
    Debian                          yes     no          no
    Gentoo                          yes     no          no
    Kubuntu                         yes     no          no
    Red Hat                         yes     no          no
    Apache                          yes     no          no
