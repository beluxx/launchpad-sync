# Copyright 2004 Canonical Ltd
from datetime import datetime

# sqlobject/sqlos
from sqlobject import LIKE, AND, SQLObjectNotFound
from canonical.database.sqlbase import quote

# lp imports
from canonical.lp.dbschema import EmailAddressStatus, SSHKeyType, \
                                  LoginTokenType
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.auth.browser import well_formed_email
from canonical.foaf.nickname import generate_nick

# database imports
from canonical.launchpad.database import WikiName
from canonical.launchpad.database import JabberID
from canonical.launchpad.database import TeamParticipation, Membership
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID
from canonical.launchpad.database import createPerson
from canonical.launchpad.database import createTeam
from canonical.launchpad.database import newLoginToken
from canonical.launchpad.database import Person
from canonical.launchpad.database import SSHKey

# interface import
from canonical.launchpad.interfaces import IPerson, IPersonSet
from canonical.launchpad.interfaces import ILaunchBag
from canonical.launchpad.interfaces import IPasswordEncryptor

from canonical.launchpad.mail.sendmail import simple_sendmail

# zope imports
import zope
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages
BATCH_SIZE = 40


class BaseListView(object):

    header = ""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _getBatchNavigator(self, list):
        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=list, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def getTeamsList(self):
        results = Person.select(Person.q.teamownerID!=None,
                                orderBy='displayname')
        return self._getBatchNavigator(list(results))

    def getPeopleList(self):
        results = Person.select(Person.q.teamownerID==None,
                                orderBy='displayname')
        return self._getBatchNavigator(list(results))


class PeopleListView(BaseListView):

    header = "People List"

    def getList(self):
        return self.getPeopleList()


class TeamListView(BaseListView):

    header = "Team List"

    def getList(self):
        return self.getTeamsList()


class FOAFSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def searchPeopleBatchNavigator(self):
        name = self.request.get("name")
        searchfor = self.request.get("searchfor")

        if not name:
            return None

        if searchfor == "all":
            results = self._findPeopleByName(name)
        elif searchfor == "peopleonly":
            results = self._findPeopleByName(name, peopleonly=True)
        elif searchfor == "teamsonly":
            results = self._findPeopleByName(name, teamsonly=True)

        people = list(results)
        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=people, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def _findPeopleByName(self, name, peopleonly=False, teamsonly=False):
        # This method is somewhat weird, cause peopleonly and teamsonly
        # are mutually exclusive.
        query = "fti @@ ftq(%s)" % quote(name)
        if peopleonly:
            query += " AND teamowner is NULL"
        elif teamsonly:
            query += " AND teamowner is not NULL"
        return Person.select(query, orderBy='displayname')


class BaseAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL


class NewAccountView(BaseAddView):

    def __init__(self, context, request):
        BaseAddView.__init__(self, context, request)

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        password = kw['password']
        # We don't want to pass password2 to PersonSet.new().
        password2 = kw.pop('password2')
        if password2 != password:
            # Do not display the password in the form when an error
            # occurs.
            kw.pop('password')
            # XXX: salgado: 2005-07-01: I must find a way to tell the user
            # that the password didn't match.
            self._nextURL = '+newaccount'
            return False

        nick = generate_nick(self.context.email)
        kw['name'] = nick
        person = getUtility(IPersonSet).new(**kw)
        email = EmailAddress(person=person.id, email=self.context.email,
                             status=int(EmailAddressStatus.PREFERRED))
        self._nextURL = '/foaf/people/%s' % person.name
        return True


class TeamAddView(BaseAddView):

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        person = IPerson(self.request.principal, None)
        team = createTeam(kw['displayname'], person.id,
                          kw['teamdescription'], kw['email'])
        notify(ObjectCreatedEvent(team))
        self._nextURL = '/foaf/people/%s' % team.name
        return team


class JoinLaunchpadView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.email = None

    def formSubmitted(self):
        if self.request.method != "POST":
            return False

        self.email = self.request.form.get("email", "").strip()
        if not well_formed_email(self.email):
            self.errormessage = ("The email address you provided isn't "
                                 "valid.  Please check it.")
            return False

        # New user: requester and requesteremail are None.
        token = newLoginToken(None, None, self.email,
                              LoginTokenType.NEWACCOUNT)
        sendNewUserEmail(token)
        return True


def sendNewUserEmail(token):
    template = open('lib/canonical/foaf/newuser-email.txt').read()
    fromaddress = "Launchpad <noreply@canonical.com>"

    replacements = {'longstring': token.token, 'toaddress': token.email }
    message = template % replacements

    subject = "Launchpad: Complete your registration process"
    simple_sendmail(fromaddress, token.email, subject, message)


class PersonView(object):
    """A simple View class to be used in Person's pages where we don't have
    actions and all we need is the context/request."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class TeamView(object):
    """A simple View class to be used in Team's pages where we don't have
    actions and all we need is the context/request."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class PersonEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.user = getUtility(ILaunchBag).user

    def edit_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return False

        person = self.context
        request = self.request

        password = request.form.get("password")
        newpassword = request.form.get("newpassword")
        newpassword2 = request.form.get("newpassword2")
        displayname = request.form.get("displayname")

        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, person.password):
            self.errormessage = "Wrong password. Please try again."
            return False

        if not displayname:
            self.errormessage = "Your display name cannot be emtpy."
            return False

        if newpassword:
            if newpassword != newpassword2:
                self.errormessage = "New password didn't match."
                return False
            else:
                newpassword = encryptor.encrypt(newpassword)
                person.password = newpassword

        person.displayname = displayname
        person.givenname = request.form.get("givenname")
        person.familyname = request.form.get("familyname")

        wiki = request.form.get("wiki")
        wikiname = request.form.get("wikiname")
        network = request.form.get("network")
        nickname = request.form.get("nickname")
        jabberid = request.form.get("jabberid")
        archuserid = request.form.get("archuserid")

        #WikiName
        if person.wiki:
            person.wiki.wiki = wiki
            person.wiki.wikiname = wikiname
        elif wiki and wikiname:
            WikiName(personID=person.id, wiki=wiki, wikiname=wikiname)

        #IrcID
        if person.irc:
            person.irc.network = network
            person.irc.nickname = nickname
        elif network and nickname:
            IrcID(personID=person.id, network=network, nickname=nickname)

        #JabberID
        if person.jabber:
            person.jabber.jabberid = jabberid
        elif jabberid:
            JabberID(personID=person.id, jabberid=jabberid)

        #ArchUserID
        if person.archuser:
            person.archuser.archuserid = archuserid
        elif archuserid:
            ArchUserID(personID=person.id, archuserid=archuserid)

        return True


class EmailAddressEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = "Your changes have been saved."
        self.user = getUtility(ILaunchBag).user

    def formSubmitted(self):
        if "SUBMIT_CHANGES" in self.request.form:
            self.processEmailChanges()
            return True
        elif "VALIDATE_EMAIL" in self.request.form:
            self.processValidationRequest()
            return True
        else:
            return False

    def processEmailChanges(self):
        user = self.user
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, user.password):
            self.message = "Wrong password. Please try again."
            return

        newemail = self.request.form.get("newemail", "").strip()
        if not well_formed_email(newemail):
            self.message = "'%s' is not a valid email address." % newemail
            return

        results = EmailAddress.selectBy(email=newemail)
        if results.count() > 0:
            email = results[0]
            self.message = ("The email address '%s' was already registered "
                            "by user '%s'. If you think this is your email "
                            "address, you can hijack it by clicking here.") % \
                           (email.email, email.person.browsername())
            return

        login = getUtility(ILaunchBag).login
        token = newLoginToken(user, login, newemail, 
                              LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token)
        self.message = ("A new message was sent to '%s', please follow "
                        "the instructions on that message to validate "
                        "your email address.") % newemail

        # XXX: salgado 2005-01-12: If we change the preferred email address,
        # the view is displaying the old preferred one, even that the change
        # is stored in the DB, as one can see by Reloading/Opening the page
        # again.
        id = self.request.form.get("PREFERRED_EMAIL")
        if id is not None:
            # XXX: salgado 2005-01-06: Ideally, any person that is able to
            # login *must* have a PREFERRED email, and this will not be
            # needed anymore. But for now we need this cause id may be "".
            id = int(id)
            if getattr(user.preferredemail, 'id', None) != id:
                email = EmailAddress.get(id)
                assert email.person == user
                assert email.status == int(EmailAddressStatus.VALIDATED)
                user.preferredemail = email

        ids = self.request.form.get("REMOVE_EMAIL")
        if ids is not None:
            # We can have multiple email adressess marked for deletion, and in
            # this case ids will be a list. Otherwise ids will be str or int
            # and we need to make a list with that value to use in the for 
            # loop.
            if not isinstance(ids, list):
                ids = [ids]

            for id in ids:
                email = EmailAddress.get(id)
                assert email.person == user
                if user.preferredemail != email:
                    email.destroySelf()

    def processValidationRequest(self):
        id = self.request.form.get("NOT_VALIDATED_EMAIL")
        email = EmailAddress.get(id)
        self.message = ("A new email was sent to '%s' with instructions "
                        "on how to validate it.") % email.email
        login = getUtility(ILaunchBag).login
        token = newLoginToken(self.user, login, email.email,
                              LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token)


def sendEmailValidationRequest(token):
    template = open('lib/canonical/foaf/validate-email.txt').read()
    fromaddress = "Launchpad Email Validator <noreply@canonical.com>"

    replacements = {'longstring': token.token,
                    'requester': token.requester.browsername(),
                    'requesteremail': token.requesteremail,
                    'toaddress': token.email
                    }

    message = template % replacements

    subject = "Launchpad: Validate your email address"
    simple_sendmail(fromaddress, [token.email], subject, message)


class ValidateEmailView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.errormessage = ""

    def formSubmitted(self):
        if self.request.method == "POST":
            self.validate()
            return True
        return False

    def validate(self):
        # Email validation requests must have a registered requester.
        assert self.context.requester is not None
        assert self.context.requesteremail is not None
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please try again."
            return 

        results = EmailAddress.selectBy(email=self.context.requesteremail)
        assert results.count() == 1
        reqemail = results[0]
        assert reqemail.person == requester

        status = int(EmailAddressStatus.VALIDATED)
        if not requester.preferredemail and not requester.validatedemails:
            # This is the first VALIDATED email for this Person, and we
            # need it to be the preferred one, to be able to communicate
            # with the user.
            status = int(EmailAddressStatus.PREFERRED)

        results = EmailAddress.selectBy(email=self.context.email)
        if results.count() > 0:
            # This email was obtained via gina or lucille and have been
            # marked as NEW on the DB. In this case all we have to do is
            # set that email status to VALIDATED.
            assert results.count() == 1
            email = results[0]
            email.status = status
            return

        # New email validated by the user. We must add it to our emailaddress
        # table.
        email = EmailAddress(email=self.context.email, status=status,
                             person=requester.id)


class GPGKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return self.context.gpg.pubkey


class SSHKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "\n".join([key.keytext for key in self.context.sshkeys])


class SSHKeyEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def form_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return ''

        action = self.request.form.get('action')
        if action == 'add':
            return self.add_action()
        elif action == 'remove':
            return self.remove_action()

    def add_action(self):
        sshkey = self.request.form.get('sshkey')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            return 'Invalid public key'
        
        if kind == 'ssh-rsa':
            keytype = int(SSHKeyType.RSA)
        elif kind == 'ssh-dss':
            keytype = int(SSHKeyType.DSA)
        else:
            return 'Invalid public key'
        
        SSHKey(personID=self.user.id, keytype=keytype, keytext=keytext,
               comment=comment)
        return 'SSH public key added.'

    def remove_action(self):
        try:
            id = self.request.form.get('key')
        except ValueError:
            return "Can't remove key that doesn't exist"

        try:
            sshkey = SSHKey.get(id)
        except SQLObjectNotFound:
            return "Can't remove key that doesn't exist"

        if sshkey.person != self.user:
            return "Cannot remove someone else's key"

        comment = sshkey.comment
        sshkey.destroySelf()
        return 'Key "%s" removed' % comment


class TeamMembersEditView:

    # XXX: salgado, 2005-01-12: Not yet ready for review. I'm working on
    # this.
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

