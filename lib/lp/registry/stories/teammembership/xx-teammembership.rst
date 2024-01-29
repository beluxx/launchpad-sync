Creating a new team
-------------------

Regular users can create teams.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/people/")
    >>> browser.getLink("Register a team").click()

    >>> browser.url
    'http://launchpad.test/people/+newteam'

    >>> browser.title
    'Register a new team in Launchpad'

    >>> browser.getControl(name="field.name").value = "myemail"
    >>> browser.getControl("Display Name").value = "your own team"
    >>> browser.getControl("Subscription period").value = "365"
    >>> browser.getControl("Open Team").selected = True
    >>> browser.getControl("Create").click()

    >>> browser.url
    'http://launchpad.test/~myemail'

    >>> browser.title
    'your own team in Launchpad'

The owner of a team is always added as an administrator of their team.

    >>> from lp.registry.model.person import Person
    >>> from lp.services.database.interfaces import IStore
    >>> for a in (
    ...     IStore(Person).find(Person, name="myemail").one().adminmembers
    ... ):
    ...     print(a.name)
    name12


Joining a team
--------------

Karl will join the newly created team.

    >>> browser = setupBrowser(auth="Basic karl@canonical.com:test")
    >>> browser.open("http://launchpad.test/~myemail")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "subscription-policy")
    ...     )
    ... )
    Membership policy:
    Open Team

    >>> browser.getLink("Join the team").click()
    >>> browser.url
    'http://launchpad.test/~myemail/+join'

    >>> browser.getControl(name="field.actions.join").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

Since this is an open team, he's automatically approved.

    >>> for tag in find_tags_by_class(browser.contents, "informational"):
    ...     print(tag.decode_contents())
    ...
    You have successfully joined your own team.

Now, the link to join the team is not present anymore and the +join page will
say that there's no need to join since the user is already a member of that
team.

    >>> browser.getLink("Join the team")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> browser.open("http://launchpad.test/~myemail/+join")
    >>> for tag in find_tags_by_class(browser.contents, "informational"):
    ...     print(tag.decode_contents())
    ...
    You are an active member of this team already.

We have a 'Back' button, though, which just takes the user back to
the team's home page.

    >>> browser.getLink("Back").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

If this was a moderated team, the membership would not have been automatically
approved, though.

    >>> from storm.locals import Store
    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> myemail = IStore(Person).find(Person, name="myemail").one()
    >>> myemail.membership_policy = TeamMembershipPolicy.MODERATED
    >>> Store.of(myemail).flush()

    >>> browser = setupBrowser(
    ...     auth="Basic james.blackwell@ubuntulinux.com:test"
    ... )
    >>> browser.open("http://launchpad.test/~myemail")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "subscription-policy")
    ...     )
    ... )
    Membership policy:
    Moderated Team

    >>> browser.getLink("Join the team").click()
    >>> browser.url
    'http://launchpad.test/~myemail/+join'

    >>> print(
    ...     find_tag_by_id(browser.contents, "maincontent").decode_contents()
    ... )
    <BLANKLINE>
    ...
    One of this team's administrators will have to approve your membership
    before you actually become a member.
    ...

If the user changes their mind because this is a moderated team, they can
hit the 'Cancel' button, going back to the team's page...

    >>> browser.getLink("Cancel").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

...and then do everything again, if they really want to join.

    >>> browser.getLink("Join the team").click()
    >>> browser.getControl(name="field.actions.join").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

    >>> for tag in find_tags_by_class(browser.contents, "informational"):
    ...     print(tag.decode_contents())
    ...
    Your request to join your own team is awaiting approval.

Delegated teams also require approval of direct membership.

    >>> login("test@canonical.com")
    >>> myemail.membership_policy = TeamMembershipPolicy.DELEGATED
    >>> Store.of(myemail).flush()
    >>> logout()

    >>> browser = setupBrowser(auth="Basic colin.watson@ubuntulinux.com:test")
    >>> browser.open("http://launchpad.test/~myemail")
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "subscription-policy")
    ...     )
    ... )
    Membership policy:
    Delegated Team

    >>> browser.getLink("Join the team").click()
    >>> browser.url
    'http://launchpad.test/~myemail/+join'

    >>> print(
    ...     find_tag_by_id(browser.contents, "maincontent").decode_contents()
    ... )
    <BLANKLINE>
    ...
    One of this team's administrators will have to approve your membership
    before you actually become a member.
    ...

    >>> browser.getControl(name="field.actions.join").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

    >>> for tag in find_tags_by_class(browser.contents, "informational"):
    ...     print(tag.decode_contents())
    ...
    Your request to join your own team is awaiting approval.

If it was a restricted team, users wouldn't even see a link to join the team.

    >>> myemail.membership_policy = TeamMembershipPolicy.RESTRICTED
    >>> Store.of(myemail).flush()

    >>> browser = setupBrowser(auth="Basic jeff.waugh@ubuntulinux.com:test")
    >>> browser.open("http://launchpad.test/~myemail")
    >>> browser.url
    'http://launchpad.test/~myemail'
    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(browser.contents, "subscription-policy")
    ...     )
    ... )
    Membership policy:
    Restricted Team

    >>> browser.getLink("Join the team")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

If the user manually crafts the URL to the +join page, they'll only see a
message explaining that this is a restricted team.

    >>> browser.open("http://launchpad.test/~myemail/+join")
    >>> browser.url
    'http://launchpad.test/~myemail/+join'

    >>> for tag in find_tags_by_class(browser.contents, "informational"):
    ...     print(tag.decode_contents())
    ...
    your own team is a restricted team.
    Only a team administrator can add new members.

But we provide a 'Back' button to take the user back to the team's
home page, since they can't join it.

    >>> browser.getLink("Back").click()
    >>> browser.url
    'http://launchpad.test/~myemail'

On the team's +members page we can now see Karl as an approved member,
Colin Watson and James Blackwell as proposed members, and Jeff Waugh won't
be there at all.

    >>> anon_browser.open("http://launchpad.test/~myemail")
    >>> anon_browser.getLink("All members").click()
    >>> anon_browser.url
    'http://launchpad.test/~myemail/+members'

    >>> contents = anon_browser.contents
    >>> for link in find_tag_by_id(contents, "activemembers").find_all("a"):
    ...     print(link.decode_contents())
    ...
    Karl Tilbury
    Sample Person

    >>> for link in find_tag_by_id(contents, "proposedmembers").find_all("a"):
    ...     print(link.decode_contents())
    ...
    Colin Watson
    James Blackwell


Managing team members
---------------------

On a team's +members page we can see all active members of that team, as
well as the former members and the ones which proposed themselves or that
have been invited.

    >>> def print_members(contents, type):
    ...     table = find_tag_by_id(contents, type)
    ...     for link in table.find_all("a"):
    ...         link_contents = link.decode_contents()
    ...         if link_contents != "Edit" and not link.find("img"):
    ...             print(link_contents)
    ...

    >>> browser.open("http://launchpad.test/~landscape-developers")
    >>> browser.getLink("All members").click()
    >>> browser.url
    'http://launchpad.test/~landscape-developers/+members'

    >>> print_members(browser.contents, "activemembers")
    Guilherme Salgado
    Sample Person

    >>> print_members(browser.contents, "invitedmembers")
    Launchpad Developers

    >>> print_members(browser.contents, "proposedmembers")
    Foo Bar

Former members are only viewable by admins of the team.

    >>> print(find_tag_by_id(browser.contents, "inactivemembers"))
    None

    >>> name12_browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> name12_browser.open(browser.url)
    >>> print_members(name12_browser.contents, "inactivemembers")
    Karl Tilbury
    No Privileges Person

The list of active members and former (inactive) members can grow
without bounds, so they are paginated.

    >>> browser.open("http://launchpad.test/~admins/+members")
    >>> print_members(browser.contents, "activemembers")
    Andrew Bennetts
    Carlos Perelló Marín
    Dafydd Harries
    Daniel Henrique Debonzi
    Daniel Silverstone
    >>> browser.getLink("Next").click()
    >>> print_members(browser.contents, "activemembers")
    Foo Bar
    Guilherme Salgado
    Mark Shuttleworth
    Robert Collins
    Steve Alexander

    # The ~admins team doesn't have enough inactive members to overflow
    # the default batch size of 5; set the max batch size to 2.
    >>> from lp.services.config import config
    >>> config.push(
    ...     "default-batch-size",
    ...     """
    ... [launchpad]
    ... default_batch_size: 2
    ... """,
    ... )
    >>> admin_browser.open(
    ...     "http://launchpad.test/~admins/+members?inactive_batch=2"
    ... )
    >>> print_members(admin_browser.contents, "inactivemembers")
    Celso Providelo
    David Allouche
    >>> admin_browser.getLink("Next", index=2).click()
    >>> print_members(admin_browser.contents, "inactivemembers")
    James Blackwell
    >>> config_data = config.pop("default-batch-size")


Approving a proposed member
---------------------------

James Blackwell wants to join the team and we know he made some contributions
in the past, so we'll approve his membership.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/~myemail/+members")
    >>> print_members(browser.contents, "proposedmembers")
    Colin Watson
    James Blackwell

    >>> browser.open("http://launchpad.test/~myemail/+member/jblack")
    >>> browser.url
    'http://launchpad.test/~myemail/+member/jblack'

    >>> browser.getControl(name="membership.expirationdate").value = (
    ...     "2048-04-14"
    ... )
    >>> browser.getControl(name="approve").click()

    >>> browser.url
    'http://launchpad.test/~myemail/+members'

    >>> print_members(browser.contents, "activemembers")
    James Blackwell
    Karl Tilbury
    Sample Person


Promoting/Demoting an existing member
-------------------------------------

We'll now promote jblack to an administrator of this team.

    >>> browser.open("http://launchpad.test/~myemail/+member/jblack")
    >>> browser.url
    'http://launchpad.test/~myemail/+member/jblack'

    >>> browser.getControl(name="admin").value
    ['no']
    >>> browser.getControl(name="admin").value = ["yes"]
    >>> browser.getControl(name="change").click()

    >>> browser.open("http://launchpad.test/~myemail/+member/jblack")
    >>> browser.getControl(name="admin").value
    ['yes']

We can also demote him if he doesn't behave himself.

    >>> browser.getControl(name="admin").value = ["no"]
    >>> browser.getControl(name="change").click()

    >>> browser.open("http://launchpad.test/~myemail/+member/jblack")
    >>> browser.getControl(name="admin").value
    ['no']


Deactivating an existing member
-------------------------------

Karl Tilbury has made no contributions lately, so we'll deactivate his
membership for now.

    # We want to test concurrency here, so keep two browsers around:
    # XXX: Guilherme Salgado 2007-02-28 bug=68655:
    # It would be nice to be able to clone the browser and not do
    # the manual copy.
    >>> browser2 = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser2.open("http://launchpad.test/~myemail/+member/karl")

    >>> browser.open("http://launchpad.test/~myemail/+member/karl")
    >>> browser.getControl("Deactivate").click()
    >>> browser.url
    'http://launchpad.test/~myemail/+members'

    >>> print_members(browser.contents, "inactivemembers")
    Karl Tilbury

Attempt to deactivate the user again using our original browser2
instance. No crashes in sight:

    >>> browser2.getControl("Deactivate").click()
    >>> browser2.url
    'http://launchpad.test/~myemail/+members'


Reactivating a deactivated member
---------------------------------

Later we may decide to reactivate Karl Tilbury's membership, so this must be
possible.

    # Again, keep a second browser open to test concurrency.
    >>> browser2.open("http://launchpad.test/~myemail/+member/karl")

    >>> browser.open("http://launchpad.test/~myemail/+member/karl")
    >>> browser.getControl(name="expires").value = ["date"]
    >>> browser.getControl(name="membership.expirationdate").value = (
    ...     "2049-04-16"
    ... )
    >>> browser.getControl("Reactivate").click()

    >>> browser.url
    'http://launchpad.test/~myemail/+members'

    >>> print(find_tag_by_id(browser.contents, "inactivemembers"))
    None
    >>> print_members(browser.contents, "activemembers")
    James Blackwell
    Karl Tilbury
    Sample Person

A second submission for reactivation should not crash but will print an
error message:

    >>> browser2.getControl(name="expires").value = ["date"]
    >>> browser2.getControl(name="membership.expirationdate").value = (
    ...     "2049-04-16"
    ... )
    >>> browser2.getControl("Reactivate").click()
    >>> browser2.url
    'http://launchpad.test/~myemail/+member/karl/+index'
    >>> for tag in find_tags_by_class(browser2.contents, "error message"):
    ...     print(tag.decode_contents())
    ...
    The membership request for Karl Tilbury has already been processed.
