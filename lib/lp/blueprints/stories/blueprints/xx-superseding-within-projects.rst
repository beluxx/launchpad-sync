Superseeding blueprints
=======================

Bueprints can only be superseded by other blueprints in the same project.
The user interface code for the superseding form passes blueprints by their
name, since blueprint names are unique within projects. We want to test
that when submitted, the system marks the blueprint as superseded by the
correct blueprint, from the same project and not by one with an identical
name but from a different project.

First, we'll create two blueprints with an identical name in two different
projects and another blueprint, to be superseded.

    >>> browser.addHeader('Authorization', 'Basic foo.bar@canonical.com:test')

    >>> browser.open('http://blueprints.launchpad.test/bzr/+addspec')
    >>> browser.getControl('Name').value = 'a-unique-blueprint'
    >>> browser.getControl('Title').value = 'A unique Blueprint'
    >>> browser.getControl('Summary').value = 'A unique bzr Blueprint...'
    >>> browser.getControl('Register Blueprint').click()

    >>> browser.open('http://blueprints.launchpad.test/redfish/+addspec')
    >>> browser.getControl('Name').value = 'a-unique-blueprint'
    >>> browser.getControl('Title').value = 'A unique Blueprint'
    >>> browser.getControl('Summary').value = 'A unique refish Blueprint...'
    >>> browser.getControl('Register Blueprint').click()

    >>> browser.open('http://blueprints.launchpad.test/redfish/+addspec')
    >>> browser.getControl('Name').value = 'another-unique-blueprint'
    >>> browser.getControl('Title').value = 'Another unique Blueprint'
    >>> browser.getControl('Summary').value = 'Another refish Blueprint...'
    >>> browser.getControl('Register Blueprint').click()

Then we'll mark one of the blueprints as superseded by another one from the
same project for which we know there is another blueprint in a different
project with an identical name, which was registered earlier.

    >>> browser.open('http://blueprints.launchpad.test/redfish/' +
    ...     '+spec/another-unique-blueprint/+supersede')
    >>> browser.getControl('Superseded by').value = 'a-unique-blueprint'
    >>> browser.getControl('Continue').click()

    >>> 'This blueprint has been superseded' in browser.contents
    True

The blueprint was successfully marked as superseded. Now, let's check that
the blueprint is superseded by the one from the same project, not with the
one that was registered earlier.

    >>> browser.getLink('A unique Blueprint').click()
    >>> browser.url
    'http://blueprints.launchpad.test/redfish/+spec/a-unique-blueprint'
