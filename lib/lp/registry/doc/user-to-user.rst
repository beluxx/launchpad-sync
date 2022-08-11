Direct user-to-user email
=========================

Launchpad users can send emails to each other directly, through the Launchpad
web interface.  Launchpad tracks these both for informational purposes and to
limit or throttle the number of messages that any one person can send.  The
throttling happens over a configurable interval.

Anne and Bart are Launchpad users.

    >>> anne = factory.makePerson('anne@example.com', 'anne')
    >>> bart = factory.makePerson('bart@example.com', 'bart')

Anne wants to contact Bart to ask him a question about his Launchpad project,
but Bart's email addresses are hidden.  Anne decides to use Launchpad's direct
user-to-user contact form to send Bart a message.  Is she allowed to?

    # For testing purposes, we can't use the current date and time.
    >>> from lp.services.messages.model.message import (
    ...     utcdatetime_from_field)
    >>> date = utcdatetime_from_field('Thu, 25 Sep 2008 15:29:37 +0100')

    >>> from lp.services.messages.interfaces.message import (
    ...     IDirectEmailAuthorization)
    >>> IDirectEmailAuthorization(anne)._isAllowedAfter(date)
    True

    # Similarly, test the implicit date interface, which real code will use.
    # The outcome is the same in this case.
    >>> IDirectEmailAuthorization(anne).is_allowed
    True

Launchpad records the event when Anne sends the message to Bart.

    >>> from lp.services.messages.model.message import UserToUserEmail
    >>> from email import message_from_string

    >>> contact = UserToUserEmail(message_from_string("""\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Date: Thu, 25 Sep 2008 15:29:38 +0100
    ... Message-ID: <aardvark>
    ... Subject: Project Bumstead
    ...
    ... This looks just like project Blonde.  Please contact me.
    ... """))

    >>> import transaction
    >>> transaction.commit()

Anne really likes Bart's project, so she sends him another message.

    # Use an explicit cutoff date instead of yesterday.
    >>> from lp.services.messages.model.message import (
    ...     utcdatetime_from_field)
    >>> after = utcdatetime_from_field('Thu, 25 Sep 2008 15:20:00 +0100')

    >>> IDirectEmailAuthorization(anne)._isAllowedAfter(date)
    True

    >>> contact = UserToUserEmail(message_from_string("""\
    ... From: anne@example.com
    ... To: bart@example.com
    ... Date: Thu, 25 Sep 2008 15:30:38 +0100
    ... Message-ID: <badger>
    ... Subject: Re: Project Bumstead
    ...
    ... No really, this is so cool!
    ... """))
    >>> transaction.commit()

Anne also likes Cris's project, and wants to contact her directly.

    >>> IDirectEmailAuthorization(anne)._isAllowedAfter(date)
    True

    >>> cris = factory.makePerson('cris@example.com', 'cris')
    >>> contact = UserToUserEmail(message_from_string("""\
    ... From: anne@example.com
    ... To: cris@example.com
    ... Date: Thu, 25 Sep 2008 15:31:38 +0100
    ... Message-ID: <cougar>
    ... Subject: Project Dagwood
    ...
    ... Not as cool as Bumstead, but still neat.
    ... """))
    >>> transaction.commit()

Anne is no longer allowed to contact any Launchpad users directly, at least
until tomorrow.

    >>> IDirectEmailAuthorization(anne)._isAllowedAfter(date)
    False


Non-ASCII Subjects
------------------

Dave wants to contact Elly but since both speak non-ASCII, so the message Dave
sends has a Subject header encoded by RFC 2047.

    >>> dave = factory.makePerson('dave@example.com', 'dave')
    >>> elly = factory.makePerson('elly@example.com', 'elly')
    >>> contact = UserToUserEmail(message_from_string("""\
    ... From: dave@example.com
    ... To: elly@example.com
    ... Date: Thu, 25 Sep 2008 15:30:38 +0100
    ... Message-ID: <dolphin>
    ... Subject: =?iso-8859-1?q?Sm=F6rg=E5sbord?=
    ...
    ... I am hungry!
    ... """))
    >>> transaction.commit()

    >>> from storm.locals import Store
    >>> entry = Store.of(dave).find(
    ...     UserToUserEmail,
    ...     UserToUserEmail.message_id == u'<dolphin>').one()
    >>> print(entry.subject)
    Smörgåsbord


Full names
----------

Again, Dave wants to contact Elly, but this time, he's configured his mailer
to include his full name.  His contact is still recorded correctly.

    >>> contact = UserToUserEmail(message_from_string("""\
    ... From: Dave Person <dave@example.com>
    ... To: elly@example.com (Elly Person)
    ... Date: Thu, 25 Sep 2008 15:31:38 +0100
    ... Message-ID: <elephant>
    ... Subject: Hello again
    ...
    ... I am still hungry.
    ... """))
    >>> transaction.commit()

    >>> from storm.locals import Store
    >>> entry = Store.of(dave).find(
    ...     UserToUserEmail,
    ...     UserToUserEmail.message_id == u'<elephant>').one()
    >>> entry.sender
    <Person at ... dave (Dave)>
    >>> entry.recipient
    <Person at ... elly (Elly)>


Adapters
--------

As noticed above, we can adapt from an IPerson to an
IDirectEmailAuthorization.

    >>> from zope.interface.verify import verifyObject
    >>> adapted = IDirectEmailAuthorization(anne)
    >>> verifyObject(IDirectEmailAuthorization, adapted)
    True

But adapting from other types fails.

    >>> IDirectEmailAuthorization(anne.preferredemail)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', ...
