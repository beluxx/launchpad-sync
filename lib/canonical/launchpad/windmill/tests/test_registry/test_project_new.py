# Copyright 2009 Canonical Ltd.  All rights reserved.

from windmill.authoring import WindmillTestClient

from canonical.launchpad.windmill.testing import lpuser


def test_projects_plusnew_step_two():
    """Test the dynamic aspects of step 2 of projects/+new page.

    When the project being registered matches existing projects, the step two
    page has some extra javascript-y goodness.  At the start, there's a 'No'
    button that hides the search results and reveals the rest of the project
    registration form.  After that, there's a href that toggles between
    revealing the search results and hiding them.
    """
    client = WindmillTestClient('projects/+new step two dynamism')
    lpuser.SAMPLE_PERSON.ensure_login(client)

    # Perform step 1 of the project registration, using information that will
    # yield search results.
    client.open(url=u'http://launchpad.dev:8085/projects/+new')
    client.waits.forPageLoad(timeout=u'20000')

    client.type(text=u'Badgers', id='field.displayname')
    client.type(text=u'badgers', id='field.name')
    client.type(text=u"There's the Badger", id='field.title')
    client.type(text=u'Badgers ate my firefox', id='field.summary')
    client.click(id=u'field.actions.continue')
    client.waits.forPageLoad(timeout=u'20000')

    client.asserts.assertText(
        id=u'step-title',
        text='Step 2 (of 2): Check for duplicate projects')
