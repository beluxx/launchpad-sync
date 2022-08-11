Customizing the welcome message
===============================

A team mailing list can have a custom welcome message.  The welcome message is
customizable whether or not the mailing list is currently the team's contact
address.

    >>> login('foo.bar@canonical.com')
    >>> team, mailing_list = factory.makeTeamAndMailingList(
    ...     'aardvarks', 'no-priv')
    >>> logout()
    >>> transaction.commit()

    >>> user_browser.open('http://launchpad.test/~aardvarks')
    >>> user_browser.getLink('Configure mailing list').click()
    >>> welcome_message = user_browser.getControl('Welcome message')
    >>> print(welcome_message.value)
    >>> welcome_message.value = u'Welcome to the Aardvarks.'
    >>> user_browser.getControl('Save').click()

Changes to the welcome message take effect as soon as Mailman can act on it.

    >>> user_browser.getLink('Configure mailing list').click()
    >>> welcome_message = user_browser.getControl('Welcome message')
    >>> print(welcome_message.value)
    Welcome to the Aardvarks.

    >>> from lp.registry.tests import mailinglists_helper
    >>> login('foo.bar@canonical.com')
    >>> mailinglists_helper.mailman.act()
    >>> transaction.commit()
    >>> logout()

What if Mailman failed to apply the change?

    >>> welcome_message.value = u'This change will fail to propagate.'
    >>> user_browser.getControl('Save').click()

    # Re-fetch the mailing list, this time from the utility.
    >>> from lp.registry.interfaces.mailinglist import IMailingListSet
    >>> login('foo.bar@canonical.com')
    >>> from zope.component import getUtility
    >>> mailing_list = getUtility(IMailingListSet).get(u'aardvarks')
    >>> mailing_list.status
    <DBItem MailingListStatus.MODIFIED, (8) Modified>

    # Fake a failure on the Mailman side.
    >>> from lp.registry.interfaces.mailinglist import (
    ...     MailingListStatus)
    >>> from zope.security.proxy import removeSecurityProxy
    >>> naked_list = removeSecurityProxy(mailing_list)
    >>> removeSecurityProxy(
    ...     mailing_list).status = MailingListStatus.MOD_FAILED
    >>> transaction.commit()
    >>> logout()

    >>> user_browser.open('http://launchpad.test/~aardvarks/+mailinglist')
    >>> print(extract_text(find_tag_by_id(
    ...     user_browser.contents, 'mailing_list_status_message').strong))
    This team's mailing list is in an inconsistent state...
