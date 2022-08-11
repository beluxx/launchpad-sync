Updating personal standing
==========================

People have a personal standing which controls whether their postings to
mailing lists they are not members require moderation or not.  Personal
standing can be set explicitly by a Launchpad administrator, but it can
also be calculated by a cron script from the history of reviewed and
approved messages.  If a person posts a message to a mailing list they
are not a member of, their message gets held for moderator approval.

    >>> login('foo.bar@canonical.com')
    >>> from lp.registry.tests import mailinglists_helper
    >>> team_one, list_one = mailinglists_helper.new_team('test-one', True)

    >>> from lp.registry.interfaces.person import (
    ...     IPersonSet,
    ...     PersonalStanding,
    ...     )

    >>> person_set = getUtility(IPersonSet)
    >>> lifeless = person_set.getByName('lifeless')
    >>> lifeless.personal_standing = PersonalStanding.UNKNOWN
    >>> lifeless.personal_standing_reason = ''

    # A unique Message-ID generator.
    >>> from itertools import count
    >>> def message_id_generator():
    ...     for numeric_id in count(100100):
    ...         yield '<%s>' % numeric_id
    >>> message_ids = message_id_generator()

    # A helper for posting messages to a list.
    >>> from lp.services.messages.interfaces.message import IMessageSet
    >>> from email.utils import formatdate
    >>> from lp.registry.interfaces.mailinglist import IMailingListSet
    >>> def post_message(from_address, to_team_name):
    ...     message = getUtility(IMessageSet).fromEmail(("""\
    ... From: %s
    ... To: %s@lists.launchpad.test
    ... Subject: Something to think about
    ... Message-ID: %s
    ... Date: %s
    ...
    ... Point of order!
    ... """ % (from_address, to_team_name, next(message_ids),
    ...        formatdate())).encode('UTF-8'))
    ...     mailing_list = getUtility(IMailingListSet).get(to_team_name)
    ...     held_message = mailing_list.holdMessage(message)
    ...     return held_message

    # A helper for the common case.
    >>> from functools import partial
    >>> lifeless_post = partial(post_message, 'robertc@robertcollins.net')

    >>> from lp.registry.scripts.standing import (
    ...     UpdatePersonalStanding)
    >>> from lp.services.config import config
    >>> from lp.testing.dbuser import switch_dbuser
    >>> from lp.testing.layers import LaunchpadZopelessLayer
    >>> from lp.services.log.logger import DevNullLogger
    >>> class TestableScript(UpdatePersonalStanding):
    ...     """A testable version of `UpdatePersonalStanding`."""
    ...     def main(self):
    ...         """Set up and restore the script's environment."""
    ...         # Simulate Mailman acting changed state.
    ...         flush_database_updates()
    ...         mailinglists_helper.mailman.act()
    ...         launchpad_dbuser = config.launchpad.dbuser
    ...         switch_dbuser(config.standingupdater.dbuser)
    ...         self.txn = LaunchpadZopelessLayer.txn
    ...         self.logger = DevNullLogger()
    ...         results = super().main()
    ...         switch_dbuser(launchpad_dbuser)
    ...         return results
    >>> script = TestableScript('update-standing', test_args=[])

After one approval, Robert's standing does not change.

    >>> foobar = person_set.getByName('name16')
    >>> message = lifeless_post(u'test-one')
    >>> message.approve(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

Even after three approvals, if the message was posted to the same list,
Robert's personal standing does not change.

    >>> message = lifeless_post(u'test-one')
    >>> message.approve(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> message = lifeless_post(u'test-one')
    >>> message.approve(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

Robert needs to get some approvals from a few more mailing lists before
his personal standing can be updated.

    >>> team_two, list_two = mailinglists_helper.new_team('test-two', True)
    >>> team_three, list_three = mailinglists_helper.new_team(
    ...     'test-three', True)

    >>> message = lifeless_post(u'test-two')
    >>> message.approve(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

Rejected and discarded messages don't count.

    >>> message = lifeless_post(u'test-three')
    >>> message.reject(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> message = lifeless_post(u'test-three')
    >>> message.discard(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

Neither do approved messages from someone else.

    >>> message = post_message('carlos@canonical.com', u'test-two')
    >>> message.approve(foobar)

    >>> message = post_message('carlos@canonical.com', u'test-three')
    >>> message.approve(foobar)

    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> carlos = person_set.getByName('carlos')
    >>> carlos.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

Robert's next message goes to a third mailing list, and this gets
approved.  As a result, his personal standing gets updated.

    >>> message = lifeless_post(u'test-three')
    >>> message.approve(foobar)
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...>


Multiple senders
----------------

Along comes Mark who also sends three messages to three different lists.  His
personal standing gets updated to Good also.

    >>> message = post_message('mark@example.com', u'test-one')
    >>> message.approve(foobar)
    >>> script.main()
    >>> mark = person_set.getByName('mark')
    >>> mark.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> message = post_message('mark@example.com', u'test-two')
    >>> message.approve(foobar)
    >>> script.main()
    >>> mark.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> message = post_message('mark@example.com', u'test-three')
    >>> message.approve(foobar)
    >>> script.main()
    >>> mark.personal_standing
    <DBItem PersonalStanding.GOOD...>


Only transition Unknown standings
---------------------------------

However, Robert's standing will only be updated if it was previously
Unknown.  A standing of Poor, Good or Excellent will not be changed by
the cron script.  The most common case of this is when a person's
standing has been set to Poor by a Launchpad administrator.  In that
case, no amount of approved messages will kick them back to Good
standing.

    >>> lifeless.personal_standing = PersonalStanding.POOR
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.POOR...>

    >>> lifeless.personal_standing = PersonalStanding.GOOD
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...>

    >>> lifeless.personal_standing = PersonalStanding.EXCELLENT
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.EXCELLENT...>

Should Robert's standing get kicked back to Unknown, then his approved
messages will count toward his good standing again.

    >>> lifeless.personal_standing = PersonalStanding.UNKNOWN
    >>> script.main()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...>


Cron script
-----------

Really, standing is updated via the update-standing.py cron script.  This
script is essentially a wrapper around the above script class, but its
operation is completely identical.

For example, it will correctly update Robert's standing, but leave Carlos's
standing untouched.

    >>> from lp.services.database.sqlbase import flush_database_caches

    >>> lifeless.personal_standing = PersonalStanding.UNKNOWN
    >>> mark.personal_standing = PersonalStanding.UNKNOWN
    >>> LaunchpadZopelessLayer.txn.commit()
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>
    >>> carlos.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>
    >>> mark.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>

    >>> import subprocess
    >>> process = subprocess.Popen(
    ...     'cronscripts/update-standing.py', shell=True,
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> stdout, stderr = process.communicate()
    >>> print(stdout)
    <BLANKLINE>
    >>> print(stderr)
    INFO    Creating lockfile:
            /var/lock/launchpad-update-personal-standing.lock
    INFO    Updating personal standings
    INFO    Done.
    <BLANKLINE>

    >>> flush_database_caches()

    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...>
    >>> carlos.personal_standing
    <DBItem PersonalStanding.UNKNOWN...>
    >>> mark.personal_standing
    <DBItem PersonalStanding.GOOD...>

Carlos sends one more message, which also gets approved.  Now the
update-standing script bumps his standing to Good too.

    >>> message = post_message('carlos@canonical.com', u'test-one')
    >>> message.approve(foobar)
    >>> LaunchpadZopelessLayer.txn.commit()
    >>> mailinglists_helper.mailman.act()
    >>> LaunchpadZopelessLayer.txn.commit()

    >>> process = subprocess.Popen(
    ...     'cronscripts/update-standing.py', shell=True,
    ...     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ...     stderr=subprocess.PIPE, universal_newlines=True)
    >>> stdout, stderr = process.communicate()
    >>> print(stdout)
    <BLANKLINE>
    >>> print(stderr)
    INFO    Creating lockfile:
            /var/lock/launchpad-update-personal-standing.lock
    INFO    Updating personal standings
    INFO    Done.
    <BLANKLINE>

    >>> flush_database_caches()
    >>> carlos.personal_standing
    <DBItem PersonalStanding.GOOD...>
