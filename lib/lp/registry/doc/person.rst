Person
======

The Person class is what we use to represent Launchpad users, teams and
some people which have done work on the free software community but are
not Launchpad users.

    >>> from lp.services.mail import stub
    >>> import transaction
    >>> from zope.component import getUtility
    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     IEmailAddressSet,
    ... )
    >>> from lp.testing import verifyObject
    >>> from lp.registry.interfaces.person import (
    ...     IHasStanding,
    ...     IPerson,
    ...     IPersonSet,
    ... )
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.translations.interfaces.hastranslationimports import (
    ...     IHasTranslationImports,
    ... )

Any Person object (either a person or a team) implements IPerson...

    >>> personset = getUtility(IPersonSet)
    >>> foobar = personset.getByName("name16")
    >>> foobar.is_team
    False

    >>> verifyObject(IPerson, foobar)
    True

    >>> ubuntu_team = personset.getByName("ubuntu-team")
    >>> ubuntu_team.is_team
    True

    >>> verifyObject(IPerson, ubuntu_team)
    True


...and IHasTranslationImports...

    >>> IHasTranslationImports.providedBy(foobar)
    True

    >>> verifyObject(IHasTranslationImports, foobar)
    True

    >>> IHasTranslationImports.providedBy(ubuntu_team)
    True

    >>> verifyObject(IHasTranslationImports, ubuntu_team)
    True

...and IHasStanding.  Teams can technically also have standing, but it's
meaningless because teams cannot post to mailing lists.

    >>> IHasStanding.providedBy(foobar)
    True

    >>> verifyObject(IHasStanding, foobar)
    True


The IPersonSet utility
----------------------

Access to people (Persons or Teams) is done through the IPersonSet
utility:

    >>> from lp.testing import verifyObject

    >>> verifyObject(IPersonSet, personset)
    True

You can create a new person using the createPersonAndEmail method of
IPersonSet. All you need for that is a valid email address. You can also
hide the user email addresses.

Some of our scripts may create Person entries, and in these cases they
must provide a rationale and a comment (optional) for the creation of
that Person entry. These are displayed on the home pages of unvalidated
Launchpad profiles, to make it clear that those profiles were not
created by the people they represent and why they had to be created.
Because the comment will be displayed verbatim in a web page, it must
start with the word "when" followed by a description of the action that
caused the entry to be created.

    >>> from lp.services.identity.interfaces.emailaddress import (
    ...     EmailAddressStatus,
    ... )
    >>> from lp.registry.interfaces.person import PersonCreationRationale
    >>> p, email = personset.createPersonAndEmail(
    ...     "randomuser@randomhost.com",
    ...     PersonCreationRationale.POFILEIMPORT,
    ...     comment="when importing the Portuguese translation of firefox",
    ...     hide_email_addresses=True,
    ... )
    >>> transaction.commit()
    >>> p.teamowner is None
    True

    >>> email.status == EmailAddressStatus.NEW
    True

    >>> p.is_valid_person  # Not valid because no preferred email address
    False

    >>> p.hide_email_addresses
    True

Since this person has chosen to hide their email addresses they won't be
visible to other users who are not admins.

    >>> from lp.services.webapp.authorization import check_permission
    >>> login("randomuser@randomhost.com")
    >>> check_permission("launchpad.View", email)
    True

    >>> login("test@canonical.com")
    >>> check_permission("launchpad.View", email)
    False

    >>> login("guilherme.salgado@canonical.com")
    >>> check_permission("launchpad.View", email)
    True

    >>> login(ANONYMOUS)

By default, newly created Person entries will have
AccountStatus.NOACCOUNT as their account_status. This is only changed
if/when we turn that entry into an actual user account.  Note that both
the Person and the EmailAddress have accounts when they are created
using the createPersonAndEmail() method.

    >>> p.account_status
    <DBItem AccountStatus.NOACCOUNT...

    >>> p.setPreferredEmail(email)
    >>> email.status
    <DBItem EmailAddressStatus.PREFERRED...

    >>> p.account_status
    <DBItem AccountStatus.NOACCOUNT...

    >>> from lp.services.identity.model.account import Account
    >>> from lp.services.database.interfaces import IPrimaryStore
    >>> account = IPrimaryStore(Account).get(Account, p.account_id)
    >>> account.reactivate("Activated by doc test.")
    >>> p.account_status
    <DBItem AccountStatus.ACTIVE...

The user can add additional email addresses. The
validateAndEnsurePreferredEmail() method verifies that the email belongs
to the person, and it updates the email address's status.

    >>> emailset = getUtility(IEmailAddressSet)
    >>> validated_email = emailset.new("validated@canonical.com", p)
    >>> validated_email.status
    <DBItem EmailAddressStatus.NEW...

    >>> login("randomuser@randomhost.com")
    >>> p.validateAndEnsurePreferredEmail(validated_email)
    >>> validated_email.status
    <DBItem EmailAddressStatus.VALIDATED...

The user can add a new address and set it as the preferred address. The
setPreferredEmail() method updated the address's status. This will generate a
security email notification to the original preferred email address.

    >>> preferred_email = emailset.new("preferred@canonical.com", p)
    >>> preferred_email.status
    <DBItem EmailAddressStatus.NEW...

    >>> login("validated@canonical.com")
    >>> p.setPreferredEmail(preferred_email)
    >>> preferred_email.status
    <DBItem EmailAddressStatus.PREFERRED...
    >>> transaction.commit()
    >>> efrom, eto, emsg = stub.test_emails.pop()
    >>> eto
    ['randomuser@randomhost.com']

    >>> login(ANONYMOUS)

In the case of teams, though, the account_status is not changed as their
account_status must always be set to NOACCOUNT. (Notice how we use
setContactAddress() rather than setPreferredEmail() here, since the
latter can be used only for people and the former only for teams)

    >>> team = factory.makeTeam(name="foo", displayname="foobaz")
    >>> team.account_status
    <DBItem AccountStatus.NOACCOUNT...

    >>> email = emailset.new("foo@baz.com", team)
    >>> team.setContactAddress(email)
    >>> email.status
    <DBItem EmailAddressStatus.PREFERRED...

    >>> team.account_status
    <DBItem AccountStatus.NOACCOUNT...

Unlike people, teams don't need a contact address, so we can pass None
to setContactAddress() to leave a team without a contact address.

    >>> team.setContactAddress(None)
    >>> print(team.preferredemail)
    None

When a new sourcepackage is imported and a Person entry has to be
created because we don't know about the maintainer of that package, the
code to create the person should look like this:

    >>> person, emailaddress = personset.createPersonAndEmail(
    ...     "random@random.com",
    ...     PersonCreationRationale.SOURCEPACKAGEIMPORT,
    ...     comment="when the ed package was imported into Ubuntu Breezy",
    ... )
    >>> person.is_valid_person
    False

    >>> print(person.creation_comment)
    when the ed package was imported into Ubuntu Breezy

Checking .is_valid_person issues a DB query to the
ValidPersonOrTeamCache, unless it's already been cached. To avoid many
small queries when checking whether a lot of people are valid,
getValidPersons() can be used. This is useful for filling the ORM cache,
so that code in other places can check .is_valid_person, without it
issuing a DB query.

    >>> non_valid_person = person
    >>> non_valid_person.is_valid_person
    False

    >>> foobar.is_valid_person
    True

    >>> valid_persons = personset.getValidPersons([non_valid_person, foobar])
    >>> for person in valid_persons:
    ...     print(person.name)
    ...
    name16


Accounts
........

A Person may be linked to an Account.

    >>> login("no-priv@canonical.com")
    >>> person = personset.getByEmail("no-priv@canonical.com")
    >>> print(person.account.openid_identifiers.any().identifier)
    no-priv_oid


Adapting an Account into a Person
.................................

And when the person is linked to an account, it's possible to adapt that
account into an IPerson.

    >>> IPerson(person.account) == person
    True

We can't adapt an account which has no person associated with, though.

    >>> from lp.services.identity.interfaces.account import (
    ...     AccountCreationRationale,
    ...     IAccountSet,
    ... )
    >>> personless_account = getUtility(IAccountSet).new(
    ...     AccountCreationRationale.UNKNOWN, "Display name"
    ... )
    >>> print(IPerson(personless_account, None))
    None

Our security adapters expect to get passed an IPerson, but we use
IAccounts to represent logged in users, so we need to adapt them into
IPerson before passing that to the adapters.  Since our Account table
has no reference to the Person table, the adaptation may end up hitting
the DB, which is something we don't want our security adapters to be
doing as they're called tons of times for every page we render.  For
that reason, whenever there is a browser request, we will cache the
IPerson objects associated to the accounts we adapt.

Up to now there was no browser request we could use, so no caching was
done.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> request = LaunchpadTestRequest()
    >>> print(request.annotations.get("launchpad.person_to_account_cache"))
    None

Now we log in with the request so that whenever we adapt an account into
a Person, the Person is cached in the request.

    >>> login("foo.bar@canonical.com", request)
    >>> IPerson(person.account)
    <Person...No Privileges Person)>

    >>> cache = request.annotations.get("launchpad.person_to_account_cache")
    >>> from zope.security.proxy import removeSecurityProxy
    >>> cache[removeSecurityProxy(person.account)]
    <Person...No Privileges Person)>

If we manually change the cache, the adapter will be fooled and will
return the wrong object.

    >>> cache[removeSecurityProxy(person.account)] = "foo"
    >>> print(IPerson(person.account))
    foo

If the cached value is None, though, the adapter will look up the
correct Person again and update the cache.

    >>> cache[removeSecurityProxy(person.account)] = None
    >>> IPerson(person.account)
    <Person...No Privileges Person)>

    >>> cache[removeSecurityProxy(person.account)]
    <Person...No Privileges Person)>


Personal standing
.................

People have a property called 'personal standing', which affects for
example their ability to post to mailing lists they are not members of.
It's a form of automatic moderation.  Most people have unknown standing,
which is the default.

    >>> login("foo.bar@canonical.com")
    >>> lifeless = personset.getByName("lifeless")
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.UNKNOWN...

A person also has a reason for why their standing is what it is.  The
default value of None means that no reason for the personal_standing
value is available.

    >>> print(lifeless.personal_standing_reason)
    None

A Launchpad administrator may change a person's standing, and may give a
reason for the change.

    >>> from lp.registry.interfaces.person import PersonalStanding
    >>> lifeless.personal_standing = PersonalStanding.GOOD
    >>> lifeless.personal_standing_reason = "Such a cool guy!"

    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...

    >>> print(lifeless.personal_standing_reason)
    Such a cool guy!

Non-administrators may not change a person's standing.

    >>> login("test@canonical.com")
    >>> lifeless.personal_standing = PersonalStanding.POOR
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> lifeless.personal_standing_reason = "Such a cool guy!"
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> login("foo.bar@canonical.com")
    >>> lifeless.personal_standing
    <DBItem PersonalStanding.GOOD...

    >>> print(lifeless.personal_standing_reason)
    Such a cool guy!

    >>> login(ANONYMOUS)


Ubuntu Code of Conduct signees
..............................

Some people have signed the latest version of the Ubuntu Code of Conduct
and others have not.

    >>> foobar.is_ubuntu_coc_signer
    True

    >>> lifeless.is_ubuntu_coc_signer
    False


Teams
-----

As we said above, the Person class is overloaded to represent teams so
we may have Person objects which are, in fact, teams. To find out
whether a given object is a person or a team we can use the is_team
property of IPerson or check if the object provides the ITeam interface.

    >>> from lp.registry.interfaces.person import ITeam
    >>> ddaa = personset.getByName("ddaa")
    >>> ddaa.is_team
    False

    >>> ITeam.providedBy(ddaa)
    False

    >>> landscape_devs = personset.getByName("landscape-developers")
    >>> landscape_devs.is_team
    True

    >>> ITeam.providedBy(landscape_devs)
    True

    >>> verifyObject(ITeam, landscape_devs)
    True

Also note that a team will never have a Launchpad account, so its
account_status will always be NOACCOUNT.

    >>> landscape_devs.account_status
    <DBItem AccountStatus.NOACCOUNT...


Creating teams
..............

Teams are created by the IPersonSet.newTeam() method, which takes the
team owner and some of the team's details, returning the newly created
team.

    >>> new_team = personset.newTeam(ddaa, "new-team", "Just a new team")
    >>> print(new_team.name)
    new-team

    >>> print(new_team.teamowner.name)
    ddaa

If the given name is already in use by another team/person, an exception
is raised.

    >>> personset.newTeam(ddaa, "ddaa", "Just a new team")
    Traceback (most recent call last):
    ...
    lp.registry.errors.NameAlreadyTaken: ...

PersonSet.newTeam() will also fire an ObjectCreatedEvent for the newly
created team.

    >>> from zope.lifecycleevent.interfaces import IObjectCreatedEvent
    >>> from lp.testing.fixture import ZopeEventHandlerFixture
    >>> def print_event(team, event):
    ...     print("ObjectCreatedEvent fired for team '%s'" % team.name)
    ...

    >>> listener = ZopeEventHandlerFixture(
    ...     print_event, (ITeam, IObjectCreatedEvent)
    ... )
    >>> listener.setUp()
    >>> another_team = personset.newTeam(ddaa, "new3", "Another a new team")
    ObjectCreatedEvent fired for team 'new3'

    >>> listener.cleanUp()


Turning people into teams
.........................

Launchpad may create Person entries automatically and it always assumes
these are actual people.  Sometimes, though, these should actually be
teams, so we provide an easy way to turn one of these auto created
entries into teams.

    >>> not_a_person, _ = personset.createPersonAndEmail(
    ...     "foo@random.com",
    ...     PersonCreationRationale.SOURCEPACKAGEIMPORT,
    ...     comment="when the ed package was imported into Ubuntu Feisty",
    ... )
    >>> transaction.commit()
    >>> not_a_person.is_team
    False

    >>> not_a_person.is_valid_person
    False

    >>> not_a_person.account_status
    <DBItem AccountStatus.NOACCOUNT...

    # Empty stub.test_emails as later we'll want to show that no
    # notifications are sent when we add the owner as a member of
    # the team.

    >>> stub.test_emails = []

    >>> not_a_person.convertToTeam(team_owner=ddaa)
    >>> not_a_person.is_team
    True

    >>> ITeam.providedBy(not_a_person)
    True

    >>> verifyObject(ITeam, not_a_person)
    True

The team owner is also added as an administrator of its team.

    >>> for member in not_a_person.adminmembers:
    ...     print(member.name)
    ...
    ddaa

    # As said previously, no notifications are sent when we add the
    # team owner as a member of their team.

    >>> transaction.commit()
    >>> stub.test_emails
    []

And we can even add other members to our new team!

    >>> login("foo.bar@canonical.com")
    >>> ignored = not_a_person.addMember(lifeless, reviewer=ddaa)
    >>> login(ANONYMOUS)
    >>> for member in not_a_person.activemembers:
    ...     print(member.name)
    ...
    ddaa
    lifeless

This functionality is only available for non-team Person entries whose
account_status is NOACCOUNT, though.

    >>> ddaa.account_status
    <DBItem AccountStatus.ACTIVE...

    >>> ddaa.convertToTeam(team_owner=landscape_devs)
    Traceback (most recent call last):
    ...
    AssertionError: Only Person entries whose account_status is NOACCOUNT...

    >>> not_a_person.convertToTeam(team_owner=landscape_devs)
    Traceback (most recent call last):
    ...
    lp.registry.interfaces.person.AlreadyConvertedException: foo-... has
    already been converted to a team.


Team members
............

The relationship between a person and a team is stored in
TeamMemberships table. TeamMemberships have a status (which can be any
item of TeamMembershipStatus) and represent the current state of the
relationship between that person and that team. Only
TeamMembershipStatus with an ADMIN or APPROVED status are considered
active.

    >>> for member in landscape_devs.approvedmembers:
    ...     print(member.displayname)
    ...
    Guilherme Salgado

    >>> for member in landscape_devs.adminmembers:
    ...     print(member.displayname)
    ...
    Sample Person

The IPerson.activemembers property will always include all approved and
admin members of that team.

    >>> for member in landscape_devs.activemembers:
    ...     print(member.displayname)
    ...
    Guilherme Salgado
    Sample Person

TeamMemberships with a PROPOSED or INVITED status represent a
person/team which has proposed themselves as a member or which has been
invited to join the team.

    >>> for member in landscape_devs.proposedmembers:
    ...     print(member.displayname)
    ...
    Foo Bar

    >>> for member in landscape_devs.invited_members:
    ...     print(member.displayname)
    ...
    Launchpad Developers

Similarly, we have IPerson.pendingmembers which includes both invited
and proposed members.

    >>> for member in landscape_devs.pendingmembers:
    ...     print(member.displayname)
    ...
    Foo Bar
    Launchpad Developers

Finally, we have EXPIRED and DEACTIVATED TeamMemberships, which
represent former (inactive) members of a team.

    >>> for member in landscape_devs.expiredmembers:
    ...     print(member.displayname)
    ...
    Karl Tilbury

    >>> for member in landscape_devs.deactivatedmembers:
    ...     print(member.displayname)
    ...
    No Privileges Person

We can get a list of all inactive members of a team with the
IPerson.inactivemembers property.

    >>> for member in landscape_devs.inactivemembers:
    ...     print(member.displayname)
    ...
    Karl Tilbury
    No Privileges Person

We can also iterate over the TeamMemberships themselves, which is useful
when we want to display details about them rather than just the member.

    >>> for membership in landscape_devs.member_memberships:
    ...     print(
    ...         "%s: %s"
    ...         % (membership.person.displayname, membership.status.name)
    ...     )
    ...
    Guilherme Salgado: APPROVED
    Sample Person: ADMIN

    >>> for membership in landscape_devs.getInvitedMemberships():
    ...     print(
    ...         "%s: %s"
    ...         % (membership.person.displayname, membership.status.name)
    ...     )
    ...
    Launchpad Developers: INVITED

    >>> for membership in landscape_devs.getProposedMemberships():
    ...     print(
    ...         "%s: %s"
    ...         % (membership.person.displayname, membership.status.name)
    ...     )
    ...
    Foo Bar: PROPOSED

    >>> for membership in landscape_devs.getInactiveMemberships():
    ...     print(
    ...         "%s: %s"
    ...         % (membership.person.displayname, membership.status.name)
    ...     )
    ...
    Karl Tilbury: EXPIRED
    No Privileges Person: DEACTIVATED

An IPerson has an inTeam method to allow us to easily check if a person
is a member (directly or through other teams) of a team. It accepts an
object implementing IPerson, which is the common use case when checking
permissions.

    >>> ddaa.is_valid_person
    True

    >>> vcs_imports = personset.getByName("vcs-imports")
    >>> lifeless.inTeam(vcs_imports) and ddaa.inTeam(vcs_imports)
    True

That method can also be used to check that a given IPerson is a member
of itself. We can do that because people and teams have
TeamParticipation entries for themselves.

    >>> ddaa.inTeam(ddaa)
    True

    >>> ddaa.hasParticipationEntryFor(ddaa)
    True

    >>> vcs_imports.inTeam(vcs_imports)
    True

    >>> vcs_imports.hasParticipationEntryFor(vcs_imports)
    True


Email notifications to teams
............................

If a team has a contact email address, all notifications we send to the
team will go to that address.

    >>> login("no-priv@canonical.com")
    >>> ubuntu_team = personset.getByName("ubuntu-team")
    >>> print(ubuntu_team.preferredemail.email)
    support@ubuntu.com

    >>> from lp.services.mail.helpers import get_contact_email_addresses
    >>> for email in get_contact_email_addresses(ubuntu_team):
    ...     print(email)
    ...
    support@ubuntu.com

On the other hand, if a team doesn't have a contact email address, all
notifications we send to the team will go to the preferred email of each
direct member of that team.

    >>> vcs_imports.preferredemail is None
    True

    >>> from operator import attrgetter
    >>> for member in sorted(
    ...     vcs_imports.activemembers, key=attrgetter("preferredemail.email")
    ... ):
    ...     print(member.preferredemail.email)
    david.allouche@canonical.com
    foo.bar@canonical.com
    robertc@robertcollins.net

    >>> sorted(get_contact_email_addresses(vcs_imports))
    ['david.allouche@canonical.com', 'foo.bar@canonical.com',
     'robertc@robertcollins.net']


Team Visibility
...............

A Team can have its visibility attribute set to
PersonVisibility.PUBLIC or PersonVisibility.PRIVATE.

PRIVATE teams are hidden from view from non-members but they are
allowed to actually do things in Launchpad.

The PublicPersonChoice for interface classes and the
validate_public_person for database classes only allow public teams to
be assigned to the specified field.

The validators will raise a PrivatePersonLinkageError exception if an
invalid team is passed to the constructor or is used to set one of the
attributes.

Private teams can be subscribed to bugs.

    >>> login("foo.bar@canonical.com")
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet, PersonVisibility
    >>> from lp.bugs.model.bugsubscription import BugSubscription
    >>> person_set = getUtility(IPersonSet)
    >>> bug_set = getUtility(IBugSet)
    >>> bug = bug_set.get(1)
    >>> guadamen = person_set.getByName("guadamen")
    >>> salgado = personset.getByName("salgado")
    >>> private_team_owner = factory.makePerson()
    >>> private_team = factory.makeTeam(
    ...     private_team_owner,
    ...     name="private-team",
    ...     displayname="Private Team",
    ...     visibility=PersonVisibility.PRIVATE,
    ... )
    >>> bug_subscription = BugSubscription(
    ...     bug=bug, person=private_team, subscribed_by=guadamen
    ... )

And they can subscribe others to bugs.

    >>> bug_subscription = BugSubscription(
    ...     bug=bug, person=guadamen, subscribed_by=private_team
    ... )

Teams also have a 'private' attribute that is true if the team is
private and false for public teams.  It is also false for people.

    >>> private_team.private
    True

    >>> guadamen.private
    False

    >>> salgado.private
    False

Latest Team Memberships
-----------------------

The key concept in displaying the latest team memberships is that the
team list is actually sorted by date joined.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> foobar = personset.getByName("name16")
    >>> membership_list = foobar.getLatestApprovedMembershipsForPerson()
    >>> for membership in membership_list:
    ...     print(membership.datejoined)
    ...
    2009-07-09 11:58:38.122886+00:00
    2008-05-14 12:07:14.227450+00:00
    2007-01-17 14:13:39.692693+00:00
    2006-05-15 22:23:29.062603+00:00
    2005-10-13 13:03:41.668724+00:00


Searching
---------

You can search based on a person's name or displayname, or any of the
email addresses that belongs to a person using the methods provided by
IPersonSet.

While we don't have Full Text Indexes in the emailaddress table, we'll
be trying to match the text only against the beginning of an email
address:

    # First we'll define a utility function to help us displaying
    # the results.

    >>> naked_emailset = removeSecurityProxy(getUtility(IEmailAddressSet))
    >>> def print_people(results):
    ...     for person in results:
    ...         emails = [
    ...             email.email
    ...             for email in naked_emailset.getByPerson(person)
    ...         ]
    ...         print(
    ...             "%s (%s): %s"
    ...             % (person.displayname, person.name, pretty(emails))
    ...         )
    ...

    >>> print_people(personset.find("ubuntu"))
    Mirror Administrators (ubuntu-mirror-admins): []
    Sigurd Gartmann (sigurd-ubuntu): ['sigurd-ubuntu@brogar.org']
    Ubuntu Doc Team (doc): ['doc@lists.ubuntu.com']
    Ubuntu Gnome Team (name18): []
    Ubuntu Security Team (ubuntu-security): []
    Ubuntu Single Sign On (ubuntu-sso): ['ubuntu-sso@example.com']
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']
    Ubuntu Technical Board (techboard): []
    Ubuntu Translators (ubuntu-translators): []

    >>> print_people(personset.find("steve.alexander"))
    Steve Alexander (stevea): ['steve.alexander@ubuntulinux.com']

    >>> print_people(personset.find("steve.alexander@"))
    Steve Alexander (stevea): ['steve.alexander@ubuntulinux.com']

    >>> list(personset.find("eve.alexander@"))
    []

    >>> list(personset.find("eve.alexander"))
    []

The teams returned are dependent upon the team's visibility (privacy)
and whether the logged in user is a member of those teams.

Anonymous users cannot see non-public teams, such as 'private-team'.

    >>> login(ANONYMOUS)
    >>> print_people(personset.find("team"))
    Another a new team (new3): []
    Hoary Gnome Team (name21): []
    HWDB Team (hwdb-team): []
    Just a new team (new-team): []
    No Team Memberships (no-team-memberships):
      ['no-team-memberships@test.com']
    Other Team (otherteam): []
    Simple Team (simple-team): []
    Team Membership Janitor (team-membership-janitor): []
    testing Spanish team (testing-spanish-team): []
    Ubuntu Doc Team (doc): ['doc@lists.ubuntu.com']
    Ubuntu Gnome Team (name18): []
    Ubuntu Security Team (ubuntu-security): []
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']
    Warty Gnome Team (warty-gnome): []
    Warty Security Team (name20): []

But Owner, a member of that team, will see it in the results.

    >>> ignored = login_person(private_team_owner)
    >>> print_people(personset.find("team"))
    Another a new team (new3): []
    Hoary Gnome Team (name21): []
    HWDB Team (hwdb-team): []
    Just a new team (new-team): []
    No Team Memberships (no-team-memberships):
      ['no-team-memberships@test.com']
    Other Team (otherteam): []
    Private Team (private-team): []
    Simple Team (simple-team): []
    Team Membership Janitor (team-membership-janitor): []
    testing Spanish team (testing-spanish-team): []
    Ubuntu Doc Team (doc): ['doc@lists.ubuntu.com']
    Ubuntu Gnome Team (name18): []
    Ubuntu Security Team (ubuntu-security): []
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']
    Warty Gnome Team (warty-gnome): []
    Warty Security Team (name20): []

Searching for people and teams without specifying some text to filter
the results will cause no people/teams to be returned.

    >>> list(personset.find(""))
    []

Searching only for People based on their names or email addresses:

    >>> print_people(personset.findPerson("james.blackwell"))
    James Blackwell (jblack): ['james.blackwell@ubuntulinux.com']

    >>> print_people(personset.findPerson("dave"))
    Dave Miller (justdave): ['dave.miller@ubuntulinux.com',
                             'justdave@bugzilla.org']

The created_before and created_after arguments can be used to restrict
the matches by the IPerson.datecreated value.

    >>> from datetime import datetime, timezone

    >>> created_after = datetime(2008, 6, 27, tzinfo=timezone.utc)
    >>> created_before = datetime(2008, 7, 1, tzinfo=timezone.utc)
    >>> print_people(
    ...     personset.findPerson(
    ...         text="",
    ...         created_after=created_after,
    ...         created_before=created_before,
    ...     )
    ... )
    Brad Crittenden (bac): ['bac@canonical.com']

By default, when searching only for people, any person whose account is
inactive is not included in the list, but we can tell findPerson to
include them as well.

    >>> from lp.services.identity.interfaces.account import AccountStatus
    >>> dave = personset.getByName("justdave")
    >>> removeSecurityProxy(dave).setAccountStatus(
    ...     AccountStatus.DEACTIVATED, None, "gbcw"
    ... )
    >>> transaction.commit()
    >>> list(personset.findPerson("dave"))
    []

    >>> print_people(
    ...     personset.findPerson("dave", exclude_inactive_accounts=False)
    ... )
    Dave Miller (justdave): ['dave.miller@ubuntulinux.com',
                             'justdave@bugzilla.org']

    >>> removeSecurityProxy(dave).setAccountStatus(
    ...     AccountStatus.ACTIVE, None, "Welcome back"
    ... )
    >>> flush_database_updates()
    >>> login(ANONYMOUS)

Searching only for Teams based on their names or email addresses:

    >>> print_people(personset.findTeam("support"))
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']

    >>> print_people(personset.findTeam("translators"))
    Ubuntu Translators (ubuntu-translators): []

    >>> print_people(personset.findTeam("team"))
    Another a new team (new3): []
    Hoary Gnome Team (name21): []
    HWDB Team (hwdb-team): []
    Just a new team (new-team): []
    Other Team (otherteam): []
    Simple Team (simple-team): []
    testing Spanish team (testing-spanish-team): []
    Ubuntu Gnome Team (name18): []
    Ubuntu Security Team (ubuntu-security): []
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']
    Warty Gnome Team (warty-gnome): []
    Warty Security Team (name20): []

The Owner user is a member of the private team 'myteam' so
the previous search will include myteam in the results.

    >>> login("owner@canonical.com")
    >>> print_people(personset.findTeam("team"))
    Another a new team (new3): []
    Hoary Gnome Team (name21): []
    HWDB Team (hwdb-team): []
    Just a new team (new-team): []
    My Team (myteam): []
    Other Team (otherteam): []
    Simple Team (simple-team): []
    testing Spanish team (testing-spanish-team): []
    Ubuntu Gnome Team (name18): []
    Ubuntu Security Team (ubuntu-security): []
    Ubuntu Team (ubuntu-team): ['support@ubuntu.com']
    Warty Gnome Team (warty-gnome): []
    Warty Security Team (name20): []

Searching for users with non-ASCII characters in their name works.

    >>> [found_person] = personset.find("P\xf6ll\xe4")
    >>> print(found_person.displayname)
    Matti Pöllä

    >>> bjorns_team = factory.makeTeam(
    ...     salgado, name="bjorn-team", displayname="Team Bj\xf6rn"
    ... )
    >>> [found_person] = personset.find("Bj\xf6rn")
    >>> print(found_person.displayname)
    Team Björn

You can get the top overall contributors, that is, the people with the
most karma.

    >>> for person in personset.getTopContributors(limit=3):
    ...     print("%s: %s" % (person.name, person.karma))
    ...
    name16: 241
    name12: 138
    mark: 130


Packages related to a person
----------------------------

To obtain the packages a person is related to, we can use:

 1. getLatestMaintainedPackages(),
 2. getLatestUploadedButNotMaintainedPackages(),
 3. getLatestUploadedPPAPackages

The 1st will return the latest SourcePackageReleases related to a person
in which they are listed as the Maintainer. The second will return the
latest SourcePackageReleases a person uploaded (and where they aren't the
maintainer).

Both, 1st and 2nd methods, only consider sources upload to primary
archives.

The 3rd method returns SourcePackageReleases uploaded by the person in
question to any PPA.

There are also analogous methods to see if a person has any of the above
related packages:
 1. hasMaintainedPackages(),
 2. hasUploadedButNotMaintainedPackages(),
 3. hasUploadedPPAPackages

    >>> mark = personset.getByName("mark")
    >>> mark.hasMaintainedPackages()
    True
    >>> for sprelease in mark.getLatestMaintainedPackages():
    ...     print(
    ...         pretty(
    ...             (
    ...                 sprelease.name,
    ...                 sprelease.upload_distroseries.fullseriesname,
    ...                 sprelease.version,
    ...             )
    ...         )
    ...     )
    ...
    ('alsa-utils', 'Debian Sid', '1.0.9a-4')
    ('pmount', 'Ubuntu Hoary', '0.1-2')
    ('netapplet', 'Ubuntu Warty', '0.99.6-1')
    ('netapplet', 'Ubuntu Hoary', '1.0-1')
    ('alsa-utils', 'Ubuntu Warty', '1.0.8-1ubuntu1')
    ('mozilla-firefox', 'Ubuntu Warty', '0.9')
    ('evolution', 'Ubuntu Hoary', '1.0')

    >>> mark.hasUploadedButNotMaintainedPackages()
    True
    >>> for sprelease in mark.getLatestUploadedButNotMaintainedPackages():
    ...     print(
    ...         pretty(
    ...             (
    ...                 sprelease.name,
    ...                 sprelease.upload_distroseries.fullseriesname,
    ...                 sprelease.version,
    ...             )
    ...         )
    ...     )
    ...
    ('foobar', 'Ubuntu Breezy-autotest', '1.0')
    ('cdrkit', 'Ubuntu Breezy-autotest', '1.0')
    ('libstdc++', 'Ubuntu Hoary', 'b8p')
    ('cnews', 'Ubuntu Hoary', 'cr.g7-37')
    ('linux-source-2.6.15', 'Ubuntu Hoary', '2.6.15.3')
    ('alsa-utils', 'Ubuntu Hoary', '1.0.9a-4ubuntu1')

    >>> mark.hasUploadedPPAPackages()
    True
    >>> mark_spreleases = mark.getLatestUploadedPPAPackages()
    >>> for sprelease in mark_spreleases:
    ...     print(
    ...         pretty(
    ...             (
    ...                 sprelease.name,
    ...                 sprelease.version,
    ...                 sprelease.creator.name,
    ...                 sprelease.maintainer.name,
    ...                 sprelease.upload_archive.owner.name,
    ...                 sprelease.upload_distroseries.fullseriesname,
    ...             )
    ...         )
    ...     )
    ...
    ('iceweasel', '1.0', 'mark', 'name16', 'mark', 'Ubuntu Warty')

We will change modify the first SourcePackageRelease to reproduce the
issue mentioned in bug 157303, where source with same creator and
maintainer got omitted from the results:

    >>> any_spr = mark_spreleases[0]
    >>> naked_spr = removeSecurityProxy(any_spr)
    >>> naked_spr.maintainer = mark
    >>> flush_database_updates()

    >>> mark_spreleases = mark.getLatestUploadedPPAPackages()
    >>> for sprelease in mark_spreleases:
    ...     print(
    ...         pretty(
    ...             (
    ...                 sprelease.name,
    ...                 sprelease.version,
    ...                 sprelease.creator.name,
    ...                 sprelease.maintainer.name,
    ...                 sprelease.upload_archive.owner.name,
    ...                 sprelease.upload_distroseries.fullseriesname,
    ...             )
    ...         )
    ...     )
    ...
    ('iceweasel', '1.0', 'mark', 'mark', 'mark', 'Ubuntu Warty')

Unlike Mark, this next person is very lazy and has no related packages:

    >>> lazy = personset.getByName("name12")
    >>> lazy.hasMaintainedPackages()
    False
    >>> lazy.hasUploadedButNotMaintainedPackages()
    False
    >>> lazy.hasUploadedPPAPackages()
    False


Packages a Person is subscribed to
----------------------------------

IPerson.getBugSubscriberPackages returns this list of packages, sorted
alphabetically by package name.

    >>> login("no-priv@canonical.com")
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> no_priv = getUtility(IPersonSet).getByName("no-priv")
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> pmount = ubuntu.getSourcePackage("pmount")
    >>> pmount.addBugSubscription(no_priv, no_priv)
    <...StructuralSubscription object>

    >>> mozilla_firefox = ubuntu.getSourcePackage("mozilla-firefox")
    >>> mozilla_firefox.addBugSubscription(no_priv, no_priv)
    <...StructuralSubscription object>

    >>> for package in no_priv.getBugSubscriberPackages():
    ...     print(package.name)
    ...
    mozilla-firefox
    pmount


Project owned by a person or team
---------------------------------

To obtain active projects owned by a person or team, we can use the
getOwnedProjects() method of IPerson.  This method returns projects
ordered by displayname.

    >>> for project in mark.getOwnedProjects():
    ...     print(project.displayname)
    ...
    Derby
    alsa-utils

We can also ask for projects owned through team memberships.

    >>> for project in mark.getOwnedProjects(transitive=True):
    ...     print(project.displayname)
    ...
    Derby
    Tomcat
    alsa-utils

The method does not return inactive projects.

    >>> login("foo.bar@canonical.com")
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> registry_member = factory.makePerson()
    >>> celebs = getUtility(ILaunchpadCelebrities)
    >>> registry = celebs.registry_experts
    >>> ignored = registry.addMember(registry_member, registry.teamowner)

    >>> ignored = login_person(registry_member)
    >>> derby = getUtility(IProductSet).getByName("derby")
    >>> derby.active = False
    >>> for project in mark.getOwnedProjects(transitive=True):
    ...     print(project.displayname)
    ...
    Tomcat
    alsa-utils

    >>> for project in ubuntu_team.getOwnedProjects():
    ...     print(project.displayname)
    ...
    Tomcat

David does not own any projects.

    >>> list(ddaa.getOwnedProjects())
    []

The results returned can be filtered by providing a token to refine the
search.

    >>> for project in mark.getOwnedProjects(
    ...     match_name="java", transitive=True
    ... ):
    ...     print(project.displayname)
    Tomcat

Searching for a non-existent project returns no matches.

    >>> list(mark.getOwnedProjects(match_name="nosuchthing"))
    []


Languages
---------

Users can set their preferred languages, retrievable as
Person.languages.

    >>> daf = personset.getByName("daf")
    >>> carlos = personset.getByName("carlos")

    >>> for language in carlos.languages:
    ...     print(language.code, language.englishname)
    ...
    ca     Catalan
    en     English
    es     Spanish

To add new languages we use Person.addLanguage().

    >>> from lp.services.worlddata.interfaces.language import ILanguageSet
    >>> languageset = getUtility(ILanguageSet)
    >>> login("carlos@test.com")
    >>> carlos.addLanguage(languageset["pt_BR"])
    >>> for lang in carlos.languages:
    ...     print(lang.code)
    ...
    ca
    en
    pt_BR
    es

Adding a language which is already in the person's preferred ones will
be a no-op.

    >>> carlos.addLanguage(languageset["es"])
    >>> for lang in carlos.languages:
    ...     print(lang.code)
    ...
    ca
    en
    pt_BR
    es

And to remove languages we use Person.removeLanguage().

    >>> carlos.removeLanguage(languageset["pt_BR"])
    >>> for lang in carlos.languages:
    ...     print(lang.code)
    ...
    ca
    en
    es

Trying to remove a language which is not in the person's preferred ones
will be a no-op.

    >>> carlos.removeLanguage(languageset["pt_BR"])
    >>> for lang in carlos.languages:
    ...     print(lang.code)
    ...
    ca
    en
    es

The Person.languages list is ordered alphabetically by the languages'
English names.

    >>> for language in daf.languages:
    ...     print(language.code, language.englishname)
    ...
    en_GB  English (United Kingdom)
    ja     Japanese
    cy     Welsh


Specification Lists
-------------------

We should be able to generate lists of specifications for people based
on certain criteria:

First, Carlos does not have any completed specifications assigned to
him:

    >>> from lp.blueprints.enums import SpecificationFilter
    >>> carlos.specifications(
    ...     None,
    ...     filter=[
    ...         SpecificationFilter.ASSIGNEE,
    ...         SpecificationFilter.COMPLETE,
    ...     ],
    ... ).count()
    0

Next, Carlos has two incomplete specs *related* to him:

    >>> filter = []
    >>> for spec in carlos.specifications(None, filter=filter):
    ...     print(spec.name, spec.is_complete, spec.informational)
    ...
    svg-support False False
    extension-manager-upgrades False True

These 2 specifications are assigned to Carlos:

    >>> assigned_specs = carlos.specifications(
    ...     carlos, filter=[SpecificationFilter.ASSIGNEE]
    ... )
    >>> for spec in assigned_specs:
    ...     print(spec.name)
    ...
    svg-support
    extension-manager-upgrades

But from these two, only one has started.

    >>> for spec in carlos.findVisibleAssignedInProgressSpecs(None):
    ...     print("%s: %s" % (spec.name, spec.is_started))
    ...
    svg-support: True

Just for fun, lets check the SAB. He should have one spec for which he
is the approver.

    >>> mark = getUtility(IPersonSet).getByName("mark")
    >>> filter = [SpecificationFilter.APPROVER]
    >>> for spec in mark.specifications(None, filter=filter):
    ...     print(spec.name)
    ...
    extension-manager-upgrades

But has registered 5 of them:

    >>> filter = [SpecificationFilter.CREATOR]
    >>> print(foobar.specifications(None, filter=filter).count())
    5

Now Celso, on the other hand, has 2 specs related to him:

    >>> cprov = personset.getByName("cprov")
    >>> cprov.specifications(None).count()
    2

On one of those, he is the approver:

    >>> filter = [SpecificationFilter.APPROVER]
    >>> for spec in cprov.specifications(None, filter=filter):
    ...     print(spec.name)
    ...
    svg-support

And on another one, he is the drafter

    >>> filter = [SpecificationFilter.DRAFTER]
    >>> for spec in cprov.specifications(None, filter=filter):
    ...     print(spec.name)
    ...
    e4x

We can filter for specifications that contain specific text:

    >>> for spec in cprov.specifications(None, filter=["svg"]):
    ...     print(spec.name)
    ...
    svg-support

Inactive products are excluded from the listings.

    >>> from lp.testing import login
    >>> from lp.registry.interfaces.product import IProductSet
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> login("mark@example.com")

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(firefox)
    >>> firefox.active = False
    >>> flush_database_updates()
    >>> cprov.specifications(None, filter=["svg"]).count()
    0

Reset firefox so we don't mess up later tests.

    >>> firefox.active = True
    >>> flush_database_updates()


Branches
--------

** See branch.rst for API related to branches.


Bug contribution
----------------

We can check whether a person has any bugs assigned to them, either
within the context of a specific bug target, or in Launchpad in general.

A person with bugs assigned to them in a context is considered a 'Bug
Contributor'.

    >>> from lp.bugs.interfaces.bugtasksearch import BugTaskSearchParams

    >>> cprov.searchTasks(
    ...     BugTaskSearchParams(user=foobar, assignee=cprov)
    ... ).count()
    0

Celso has no bug tasks assigned to him. In other words, he isn't a bug
contributor.

    >>> cprov.isBugContributor(user=foobar)
    False

We assign a bug task to Celso.

    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> search_params = BugTaskSearchParams(user=foobar)
    >>> search_params.setProduct(firefox)
    >>> firefox_bugtask = getUtility(IBugTaskSet).search(search_params)[0]
    >>> firefox_bugtask.transitionToAssignee(cprov)
    >>> flush_database_updates()

Now Celso is a bug contributor in Launchpad.

    >>> cprov.isBugContributor(user=foobar)
    True

Celso is a bug contributor in the context of the `firefox` product.

    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet
    >>> cprov.isBugContributorInTarget(user=foobar, target=firefox)
    True

And also in the context of the `mozilla` project, by association.

    >>> cprov.isBugContributorInTarget(
    ...     user=foobar,
    ...     target=getUtility(IProjectGroupSet).getByName("mozilla"),
    ... )
    True

But not in other contexts.

    >>> cprov.isBugContributorInTarget(
    ...     user=foobar, target=getUtility(IProductSet).getByName("jokosher")
    ... )
    False


Creating a Person without an email address
------------------------------------------

Although createPersonAndEmail() is the usual method to use when creating
a new Person, there is also a method that can be used when a Person
needs to be created without an email address, for example when the
Person is being created as the result of an import from an external
bugtracker.

The method createPersonWithoutEmail() is used in these situations. This
takes some parameters similar to those taken by createPersonAndEmail()
but, since an emailless Person cannot be considered to be valid, it
takes no parameters regarding to emails.

    >>> foo_bar = getUtility(IPersonSet).getByEmail("foo.bar@canonical.com")
    >>> new_person = person_set.createPersonWithoutEmail(
    ...     "ix",
    ...     PersonCreationRationale.BUGIMPORT,
    ...     comment="when importing bugs",
    ...     displayname="Ford Prefect",
    ...     registrant=foo_bar,
    ... )

    >>> print(new_person.name)
    ix

    >>> print(new_person.displayname)
    Ford Prefect

    >>> print(new_person.preferredemail)
    None

    >>> print(new_person.creation_rationale.name)
    BUGIMPORT

    >>> print(new_person.registrant.name)
    name16


The _newPerson() method
-----------------------

The PersonSet database class has a method _newPerson(), which is used to
create new Person objects. This isn't exposed in the interface, so to
test it we need to instantiate PersonSet directly.

    >>> from lp.registry.model.person import PersonSet
    >>> person_set = PersonSet()

_newPerson() accepts parameters for name displayname and rationale. It
also takes the parameters hide_email_addresses, comment and registrant.

    >>> person_set._newPerson(
    ...     "new-name",
    ...     "New Person",
    ...     True,
    ...     PersonCreationRationale.BUGIMPORT,
    ...     "testing _newPerson().",
    ...     foo_bar,
    ... )
    <Person ...>

If the name passed to _newPerson() is already taken, a NameAlreadyTaken
error will be raised.

    >>> person_set._newPerson(
    ...     "new-name", "New Person", True, PersonCreationRationale.BUGIMPORT
    ... )
    Traceback (most recent call last):
      ...
    lp.registry.errors.NameAlreadyTaken: The name 'new-name' is already taken.

If the name passed to _newPerson() isn't valid an InvalidName error will
be raised.

    >>> person_set._newPerson(
    ...     "ThisIsn'tValid",
    ...     "New Person",
    ...     True,
    ...     PersonCreationRationale.BUGIMPORT,
    ... )
    Traceback (most recent call last):
      ...
    lp.registry.errors.InvalidName: ThisIsn'tValid is not a valid name for a
    person.


Probationary users
------------------

Users without karma have not demonstrated their intentions and may not
have the same privileges as users who have made contributions. Users who
have made recent contributions are not on probation.

    >>> active_user = personset.getByName("name12")
    >>> active_user.is_probationary
    False

    >>> active_user.karma > 0
    True

    >>> active_user.is_valid_person
    True

New users (those without karma) are on probation.

    >>> new_user = factory.makePerson()
    >>> new_user.is_probationary
    True

    >>> new_user.karma > 0
    False

    >>> new_user.is_valid_person
    True

Teams are never on probation.

    >>> team = factory.makeTeam()
    >>> team.is_probationary
    False

    >>> team.karma > 0
    False

    >>> team.is_valid_person
    False
