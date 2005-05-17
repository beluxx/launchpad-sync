# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Choice, Datetime, Int, Text, TextLine, Password
from zope.interface import Interface, Attribute
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.lp.dbschema import TeamSubscriptionPolicy, TeamMembershipStatus


def _valid_person_name(name):
    """See IPersonSet.nameIsValidForInsertion()."""
    return getUtility(IPersonSet).nameIsValidForInsertion(name)


class IPerson(Interface):
    """A Person."""

    id = Int(
            title=_('ID'), required=True, readonly=True,
            )
    name = TextLine(
            title=_('Name'), required=True, readonly=True,
            constraint=_valid_person_name,
            description=_("The short name of this team, which must be unique "
                          "among all other teams. It must be at least one "
                          "lowercase letter (or number) followed by one or "
                          "more letters, numbers, dots, hyphens or plus "
                          "signs.")
            )
    displayname = TextLine(
            title=_('Display Name'), required=False, readonly=False,
            description=_("This is your name as you would like it "
                "displayed throughout The Launchpad. Most people "
                "use their full name here.")
            )
    givenname = TextLine(
            title=_('Given Name'), required=False, readonly=False,
            description=_("Your first name or given name, such as "
                "Mark, or Richard, or Joanna.")
            )
    familyname = TextLine(
            title=_('Family Name'), required=False, readonly=False,
            description=_("Your family name or given name, the name "
                "you acquire from your parents.")
            )
    password = Password(
            title=_('Password'), required=True, readonly=False,
            description=_("The password you will use to access "
                "Launchpad services. ")
            )
    # TODO: This should be required in the DB, defaulting to something
    karma = Int(
            title=_('Karma'), required=False, readonly=True,
            )
    # TODO: This should be required in the DB, defaulting to something
    karmatimestamp = Datetime(
            title=_('Karma Timestamp'), required=False, readonly=True,
            )
    languages = Attribute(_('List of know languages by this person'))

    # bounty relations
    ownedBounties = Attribute('Bounties issued by this person.')
    reviewerBounties = Attribute('Bounties reviewed by this person.')
    claimedBounties = Attribute('Bounties claimed by this person.')
    subscribedBounties = Attribute('Bounties to which this person subscribes.')
    sshkeys = Attribute(_('List of SSH keys'))

    # XXX: This field is used only to generate the form to create a new person.
    password2 = Password(title=_('Confirm Password'), required=True,
            description=_("Enter your password again to make certain "
                "it is correct."))

    # Properties of the Person object.
    ubuntite = Attribute("Ubuntite Flag")
    gpgkeys = Attribute("List of GPGkeys")
    irc = Attribute("IRC")
    bugs = Attribute("Bug")
    wiki = Attribute("Wiki")
    jabber = Attribute("Jabber")
    archuser = Attribute("Arch user")
    packages = Attribute("A Selection of SourcePackageReleases")
    maintainerships = Attribute("This person's Maintainerships")
    activities = Attribute("Karma")
    memberships = Attribute(("List of TeamMembership objects for Teams this "
                             "Person is a member of. Either active, inactive "
                             "or proposed member."))
    translations = Attribute("Translations")
    guessedemails = Attribute("List of emails with status NEW. These email "
                              "addresses probably came from a gina or "
                              "POFileImporter run.")
    validatedemails = Attribute("Emails with status VALIDATED")
    unvalidatedemails = Attribute("Emails this person added in Launchpad "
                                  "but are not yet validated.")

    allmembers = Attribute("List of all direct/indirect members of this team. "
                           "If you want a method to check if a given person is "
                           "a member of a team, you should probably look at "
                           "IPerson.inTeam().")
    activemembers = Attribute("List of members with ADMIN or APPROVED status")
    administrators = Attribute("List of members with ADMIN status")
    expiredmembers = Attribute("List of members with EXPIRED status")
    approvedmembers = Attribute("List of members with APPROVED status")
    proposedmembers = Attribute("List of members with PROPOSED status")
    declinedmembers = Attribute("List of members with DECLINED status")
    inactivemembers = Attribute(("List of members with EXPIRED or "
                                 "DEACTIVATED status"))
    deactivatedmembers = Attribute("List of members with DEACTIVATED status")

    teamowner = Choice(title=_('Team Owner'), required=False, readonly=False,
                       vocabulary='ValidTeamOwner')
    teamdescription = Text(title=_('Team Description'), required=False,
                           readonly=False)

    preferredemail = TextLine(
            title=_("Preferred Email Address"), description=_(
                "The preferred email address for this person. The one "
                "we'll use to communicate with them."), readonly=False)

    preferredemail_sha1 = TextLine(title=_("SHA-1 Hash of Preferred Email"),
            description=_("The SHA-1 hash of the preferred email address as "
                "a hexadecimal string. This is used as a key by FOAF RDF spec"
                ), readonly=True)

    defaultmembershipperiod = Int(
            title=_('Number of days a subscription lasts'), required=False,
            description=_("This is the number of days all "
                "subscriptions will last unless a different value is provided "
                "when the subscription is approved. After this " "period the "
                "subscription is expired and must be renewed. A value of 0 "
                "(zero) means that subscription will never expire."))

    defaultrenewalperiod = Int(
            title=_('Number of days a renewed subscription lasts'),
            required=False,
            description=_("This is the number of days all "
                "subscriptions will last after being renewed. After this "
                "period the subscription is expired and must be renewed "
                "again. A value of 0 (zero) means that subscription renewal "
                "periods will be the same as the membership period."))

    defaultexpirationdate = Attribute(
            "The date, according to team's default values in which a newly "
            "approved membership will expire.")

    defaultrenewedexpirationdate = Attribute(
            "The date, according to team's default values in which a just "
            "renewed membership will expire.")

    subscriptionpolicy = Choice(
            title=_('Subscription Policy'),
            required=True, vocabulary='TeamSubscriptionPolicy',
            default=TeamSubscriptionPolicy.MODERATED,
            description=_('How new subscriptions should be handled for this '
                          'team. "Moderated" means that all subscriptions must '
                          'be approved, "Open" means that any user can join '
                          'whitout approval and "Restricted" means that new '
                          'members can only be added by one of the '
                          'administrators of the team.'))

    merged = Int(title=_('Merged Into'), required=False, readonly=True,
            description=_(
                'When a Person is merged into another Person, this attribute '
                'is set on the Person referencing the destination Person. If '
                'this is set to None, then this Person has not been merged '
                'into another and is still valid')
                )

    # title is required for the Launchpad Page Layout main template
    title = Attribute('Person Page Title')

    def browsername():
        """Return a textual name suitable for display in a browser."""

    def assignKarma(karmatype, points=None):
        """Assign <points> worth of karma to this Person.
        
        If <points> is None, then get the default number of points from the
        given karmatype.
        """

    def addLanguage(language):
        """Add a new language to the list of know languages."""

    def removeLanguage(language):
        """Removed the language from the list of know languages."""

    def inTeam(team):
        """Return true if this person is in the given team.
        
        This method is meant to be called by objects which implement either
        IPerson or ITeam, and it will return True when you ask if a Person is
        a member of himself (i.e. person1.inTeam(person1)).
        """

    def hasMembershipEntryFor(team):
        """Tell if this person is a direct member of the given team."""

    def join(team):
        """Join the given team if its subscriptionpolicy is not RESTRICTED.

        Join the given team according to the policies and defaults of that
        team:
        - If the team subscriptionpolicy is OPEN, the user is added as
          an APPROVED member with a NULL TeamMembership.reviewer.
        - If the team subscriptionpolicy is MODERATED, the user is added as
          a PROPOSED member and one of the team's administrators have to
          approve the membership.

        Teams cannot call this method because they're not allowed to
        login and thus can't "join" another team. Instead, they're added
        as a member (using the addMember() method) by a team administrator.
        """

    def leave(team):
        """Leave the given team.

        If there's a membership entry for this person on the given team and
        its status is either APPROVED or ADMIN, we change the status to
        DEACTIVATED and remove the relevant entries in teamparticipation.

        Teams cannot call this method because they're not allowed to
        login and thus can't "leave" another team. Instead, they have their
        subscription deactivated (using the setMembershipStatus() method) by
        a team administrator.
        """

    def addMember(person, status=TeamMembershipStatus.APPROVED, reviewer=None,
                  comment=None):
        """Add person as a member of this team.

        Make sure status is either APPROVED or PROPOSED and add a
        TeamMembership entry for this person with the given status, reviewer,
        and reviewer comment. This method is also responsible for filling 
        the TeamParticipation table in case the status is APPROVED.
        """

    def setMembershipStatus(person, status, expires, reviewer=None,
                            comment=None):
        """Set the status of the person's membership on this team.

        Also set all other attributes of TeamMembership, which are <comment>,
        <reviewer> and <dateexpires>. This method will ensure that we only 
        allow the status transitions specified in the TeamMembership spec.
        It's also responsible for filling/cleaning the TeamParticipation 
        table when the transition requires it and setting the expiration 
        date, reviewer and reviewercomment.
        """

    def getSubTeams():
        """Return all subteams of this team.
        
        A subteam is any team that is (either directly or indirectly) a 
        member of this team. As an example, let's say we have this hierarchy
        of teams:
        
        Rosetta Translators
            Rosetta pt Translators
                Rosetta pt_BR Translators
        
        In this case, both "Rosetta pt Translators" and "Rosetta pt_BR
        Translators" are subteams of the "Rosetta Translators" team, and all
        members of both subteams are considered members of "Rosetta
        Translators".
        """

    def getSuperTeams():
        """Return all superteams of this team.

        A superteam is any team that this team is a member of. For example,
        let's say we have this hierarchy of teams, and we are the
        "Rosetta pt_BR Translators":

        Rosetta Translators
            Rosetta pt Translators
                Rosetta pt_BR Translators
        
        In this case, we will return both "Rosetta pt Translators" and 
        "Rosetta Translators", because we are member of both of them.
        """


class ITeam(IPerson):
    """ITeam extends IPerson.

    The teamowner should never be None."""


class IPersonSet(Interface):
    """The set of Persons."""

    title = Attribute('Title')

    def __getitem__(personid):
        """Return the person with the given id.

        Raise KeyError if there is no such person.
        """

    def nameIsValidForInsertion(name):
        """Return true if <name> is valid and is not yet in the database.

        <name> will be valid if valid_name(name) returns True.
        """

    def newPerson(**kwargs):
        """Create a new Person with given keyword arguments.

        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed."""

    def newTeam(**kwargs):
        """Create a new Team with given keyword arguments.

        These keyword arguments will be passed to Person, which is an
        SQLBase class and will do all the checks needed before inserting
        anything in the database. Please refer to the Person implementation
        to see what keyword arguments are allowed."""

    def get(personid, default=None):
        """Return the person with the given id.

        Return the default value if there is no such person.
        """

    def getByEmail(email, default=None):
        """Return the person with the given email address.

        Return the default value if there is no such person.
        """

    def getByName(name, default=None):
        """Return the person with the given name, ignoring merged persons.

        Return the default value if there is no such person.
        """

    def search(password=None):
        # The search API is minimal for the moment, to solve an
        # immediate problem. It will gradually be filled out with
        # more parameters as necessary.
        """Return a set of IPersons that satisfy the query arguments.

        Keyword arguments should always be used. The argument passing
        semantics are as follows:

        * personset.search(arg = 'foo'): Match all IPersons where
          IPerson.arg == 'foo'.

        * personset.search(arg = NULL): Match all the IPersons where
          IPerson.arg IS NULL.
        """

    def getAllTeams(orderBy=None):
        """Return all Teams.
        
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def getAllPersons(orderBy=None):
        """Return all Persons, ignoring the merged ones.
        
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def peopleCount():
        """Return the number of non-merged persons in the database."""

    def teamsCount():
        """Return the number of teams in the database."""

    def findByName(name, orderBy=None):
        """Return all non-merged Persons and Teams with name matching.
        
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def findPersonByName(name, orderBy=None):
        """Return all not-merged Persons with name matching.

        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def findTeamByName(name, orderBy=None):
        """Return all Teams with name matching.

        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def getContributorsForPOFile(pofile):
        """Return the list of persons that have an active contribution for a
        concrete POFile."""

    def getUbuntites():
        """Return a set of person with valid Ubuntite flag."""

    # TODO: Currently not declared part of the interface - we need to
    # sort out permissions as we need to ensure it can only be called
    # in specific instances. -- StuartBishop 20050331
    # XXX: salgado, 2005-03-31: can't we have this method declared in IPerson?
    # I can't see why we need it here.
    def merge(from_person, to_person):
        """Merge a person into another."""


class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""

    id = Int(title=_('ID'), required=True, readonly=True)
    email = Text(title=_('Email Address'), required=True, readonly=False)
    status = Int(title=_('Email Address Status'), required=True, readonly=False)
    person = Int(title=_('Person'), required=True, readonly=False)
    statusname = Attribute("StatusName")

    def destroySelf():
        """Delete this email from the database."""


class IEmailAddressSet(Interface):
    """The set of EmailAddresses."""

    def new(email, status, personID):
        """Create a new EmailAddress with the given email, pointing to person.

        Also make sure that the given status is in dbschema.
        """

    def __getitem__(emailid):
        """Return the email address with the given id.

        Raise KeyError if there is no such email address.
        """

    def get(emailid, default=None):
        """Return the email address with the given id.

        Return the default value if there is no such email address.
        """

    def getByPerson(personid):
        """Return all email addresses for the given person."""

    def getByEmail(email, default=None):
        """Return the EmailAddress object for the given email.

        Return the default value if there is no such email address.
        """


class ITeamMembership(Interface):
    """TeamMembership for Users"""

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("Team"), required=True, readonly=False)
    person = Int(title=_("Member"), required=True, readonly=False)
    reviewer = Int(title=_("Reviewer"), required=False, readonly=False)

    datejoined = Text(title=_("Date Joined"), required=True, readonly=True)
    dateexpires = Text(title=_("Date Expires"), required=False, readonly=False)
    reviewercomment = Text(title=_("Reviewer Comment"), required=False,
                           readonly=False)
    status= Int(title=_("If Membership was approved or not"), required=True,
                readonly=False)

    # Properties
    statusname = Attribute("Status Name")

    def isExpired():
        """Return True if this membership's status is EXPIRED."""


class ITeamMembershipSet(Interface):
    """A Set for TeamMembership objects."""

    def getActiveMemberships(teamID, orderBy=None):
        """Return all active TeamMemberships for the given team.
        
        Active memberships are the ones with status APPROVED or ADMIN.
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def getInactiveMemberships(teamID, orderBy=None):
        """Return all inactive TeamMemberships for the given team.
        
        Inactive memberships are the ones with status EXPIRED or DEACTIVATED.
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def getProposedMemberships(teamID, orderBy=None):
        """Return all proposed TeamMemberships for the given team.
        
        Proposed memberships are the ones with status PROPOSED.
        If you want the results ordered, you have to explicitly specify an
        <orderBy>. Otherwise the order used is not predictable.
        <orderBy> can be either a string with the column name you want to sort
        or a list of column names as strings.
        """

    def getByPersonAndTeam(personID, teamID, default=None):
        """Return the TeamMembership object for the given person and team.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """

    def getTeamMembersCount(teamID):
        """Return the number of members this team have.

        This includes active, inactive and proposed members.
        """


class ITeamMembershipSubset(Interface):
    """A Set for TeamMembership objects of a given team."""

    newmember = Choice(title=_('New member'), required=True,
                       vocabulary='Person',
                       description=_("The user or team which is going to be "
                                     "added as the new member of this team."))

    team = Attribute(_("The team for which this subset is for."))

    def getByPersonName(name, default=None):
        """Return the TeamMembership object for the person with the given name.

        If there's no TeamMembership for this person in this team, return the
        default value.
        """

    def getInactiveMemberships():
        """Return all TeamMembership objects for inactive members of this team.

        Inactive members are the ones with membership status of EXPIRED or 
        DEACTIVATED.
        """

    def getActiveMemberships():
        """Return all TeamMembership objects for active members of this team.

        Active members are the ones with membership status of APPROVED or ADMIN.
        """

    def getProposedMemberships():
        """Return all TeamMembership objects for proposed members of this team.

        Proposed members are the ones with membership status of PROPOSED.
        """


class ITeamParticipation(Interface):
    """A TeamParticipation.
    
    A TeamParticipation object represents a person being a member of a team.
    Please note that because a team is also a person in Launchpad, we can
    have a TeamParticipation object representing a team that is a member of
    another team. We can also have an object that represents a person being a
    member of itself.
    """

    id = Int(title=_('ID'), required=True, readonly=True)
    team = Int(title=_("The team"), required=True, readonly=False)
    person = Int(title=_("The member"), required=True, readonly=False)


class IRequestPeopleMerge(Interface):
    """This schema is used only because we want the PersonVocabulary."""

    dupeaccount = Choice(title=_('Duplicated Account'), required=True,
                         vocabulary='Person',
                         description=_("The duplicated account you found in "
                                       "Launchpad"))

