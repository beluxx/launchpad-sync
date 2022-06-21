Adding projects
===============

Sample Person decides to register their new project, which they can do
either from the Launchpad home page or the projects home page.

    >>> user_browser.open('http://launchpad.test')
    >>> user_browser.getLink('Register a project').click()
    >>> print(user_browser.title)
    Register a project in Launchpad...

    >>> user_browser.open('http://launchpad.test/projects')
    >>> user_browser.getLink('Register a project').click()
    >>> print(user_browser.title)
    Register a project in Launchpad...

The user can see links about things that are often assumed to be related to
project registration.

    >>> print(user_browser.getLink('Register a team').url)
    https://help.launchpad.net/Teams

    >>> print(user_browser.getLink('Activate a PPA').url)
    https://help.launchpad.net/Packaging/PPA

    >>> print(user_browser.getLink('Access your personal branches').url)
    https://help.launchpad.net/Code/PersonalBranches

    >>> print(user_browser.getLink('Translate a project').url)
    https://help.launchpad.net/Translations/YourProject

    >>> print(user_browser.getLink('Request a project group').url)
    https://help.launchpad.net/ProjectGroups


Project basics
--------------

Sample Person doesn't want Ubuntu CDs, they want to register their new
project.  This is done in two steps.  First, Sample Person provides some
basic information about their project, such as its name, final URL
component, title, and summary.

    >>> user_browser.getControl('Name').value = 'Aardvark Center'

They make some mistakes though, entering illegal characters for the URL, and
forgetting to enter a title or summary.

    >>> user_browser.getControl('URL').value = 'aard vark'
    >>> user_browser.getControl('Continue').click()

    >>> print_errors(user_browser.contents)
    There are 2 errors.
    URL:
    http://launchpad.test/
    Invalid name 'aard vark'. Names must be at least two characters ...
    At least one lowercase letter or number, followed by letters, numbers,
    dots, hyphens or pluses. Keep this name short; it is used in URLs as
    shown above.
    Summary:
    Required input is missing.
    A short paragraph to introduce the project's work.

Realizing their mistake, Sample Person fills out the project's basic
information correctly this time.

    >>> user_browser.getControl('URL').value = 'aardvark'
    >>> user_browser.getControl('Summary').value = (
    ...     'A project designed to placate ornery aardvarks')

    >>> user_browser.getControl('Continue').click()

The project is not yet created; instead, the project basics are successfully
validated and the second step of the process is entered.

    >>> print(user_browser.title)
    Register a project in Launchpad...


Completing the registration
---------------------------

The second step of the registration process does not allow Sample Person to
modify the project's URL.

    >>> user_browser.getControl(name='field.name')
    <Control name='field.name' type='hidden'>
    >>> print(user_browser.getControl(name='field.name').value)
    aardvark

Sample Person is given the opportunity though to change the summary.
They can also add a longer description.

    >>> user_browser.getControl('Summary').value = (
    ...     'Control pesky aardvarkian fnords')
    >>> user_browser.getControl('Description').value = (
    ...     'The desktop aardvark is an ornery thing.')
    >>> user_browser.getControl('Python Licence').click()
    >>> user_browser.getControl('Complete Registration').click()
    >>> print(user_browser.title)
    Aardvark Center in Launchpad

Let's ensure the summary and description are presented.

    >>> summary = find_tags_by_class(user_browser.contents,
    ...                              'summary', only_first=True)
    >>> print(extract_text(summary))
    Control pesky aardvarkian fnords
    >>> desc = find_tags_by_class(user_browser.contents,
    ...                           'description', only_first=True)
    >>> print(extract_text(desc))
    The desktop aardvark is an ornery thing.

Let's ensure the registrant and maintainer are listed correctly.

    >>> registrant = find_tag_by_id(user_browser.contents,
    ...                             'registration')
    >>> print(extract_text(registrant))
    Registered...by...No Privileges Person...

    >>> maintainer = find_tag_by_id(user_browser.contents,
    ...                             'owner')
    >>> print(extract_text(maintainer))
    Maintainer: No Privileges Person...


Turning over maintainership
---------------------------

Sample Person wants to create a project in Launchpad for a project
that exists elsewhere as an upstream.  They want it to exist in
Launchpad so they can file a bug, for instance, but they are not
interested in being the project maintainer for the long run.

    >>> user_browser.open('http://launchpad.test')
    >>> user_browser.getLink('Register a project').click()

    >>> user_browser.getControl('Name').value = 'kittyhawk'
    >>> user_browser.getControl('URL').value = 'kittyhawk'
    >>> user_browser.getControl('Summary').value = (
    ...     'Kitty Hawk Air Traffic Simulator')
    >>> user_browser.getControl('Continue').click()
    >>> user_browser.getControl('Python Licence').click()
    >>> disclaim = user_browser.getControl(name='field.disclaim_maintainer')
    >>> disclaim.value = True
    >>> user_browser.getControl('Complete Registration').click()

Sample person is shown as the registrant but the maintainer is now
Registry Admins.

    >>> registrant = find_tag_by_id(user_browser.contents,
    ...                             'registration')
    >>> print(extract_text(registrant))
    Registered...by...No Privileges Person...

    >>> maintainer = find_tag_by_id(user_browser.contents,
    ...                             'owner')
    >>> print(extract_text(maintainer))
    Maintainer: Registry Administrators...


Search results
--------------

Sample Person has another project they want to register.  It is similar to
Firefox.

    >>> user_browser.open('http://launchpad.test')
    >>> user_browser.getLink('Register a project').click()
    >>> print(user_browser.title)
    Register a project in Launchpad...

    >>> user_browser.getControl('Name').value = 'Snowdog'
    >>> user_browser.getControl('URL').value = 'snowdog'
    >>> user_browser.getControl('Summary').value = (
    ...     'Snowdog is a browser similar to Firefox')
    >>> user_browser.getControl('Continue').click()

A search is performed using the terms in the URL, title, and summary.  The
Firefox project is discovered.

Instead of registering their new project, Sample Person decides to participate
in the Mozilla Project.

    >>> user_browser.getLink('The Mozilla Project').click()
    >>> print(user_browser.title)
    The Mozilla Project in Launchpad


Redirecting
-----------

The project registration workflow used to get started at
/projects/+new-guided.  To prevent bitrot, we redirect that URL to the new
location at /projects/+new.

    >>> user_browser.open('http://launchpad.test/projects/+new-guided')
    >>> print(user_browser.title)
    Register a project in Launchpad...

    >>> print(user_browser.url)
    http://launchpad.test/projects/+new
