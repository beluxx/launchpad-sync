# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from twisted.conch import avatar
from twisted.conch.ssh import session, filetransfer
from twisted.conch.ssh import factory, userauth, connection
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from twisted.internet import defer
from twisted.python import components
from twisted.vfs.pathutils import FileSystem
from twisted.vfs.adapters import sftp
from canonical.supermirrorsftp.bazaarfs import SFTPServerRoot

from zope.interface import implements
import binascii
import os
import os.path


class SubsystemOnlySession(session.SSHSession, object):
    """A session adapter that disables every request except request_subsystem"""
    def __getattribute__(self, name):
        # Get out the big hammer :)
        # (This is easier than overriding all the different request_ methods
        # individually, or writing an ISession adapter to give the same effect.)
        if name.startswith('request_') and name not in ('request_subsystem',
                                                        'request_exec'):
            raise AttributeError(name)
        return object.__getattribute__(self, name)

    def closeReceived(self):
        # Without this, the client hangs when its finished transferring.
        self.loseConnection()


class SFTPOnlyAvatar(avatar.ConchUser):
    def __init__(self, avatarId, homeDirsRoot, userDict, launchpad):
        # Double-check that we don't get unicode -- directory names on the file
        # system are a sequence of bytes as far as we're concerned.  We don't
        # want any tricky login names turning into a security problem.
        # (I'm reasonably sure twisted.cred guarantees this will be str, but in
        # the meantime let's make sure).
        assert type(avatarId) is str

        # XXX: These two asserts should be raise exceptions that cause proper
        #      auth failures, not asserts.  (an assert should never be triggered
        #      by bad user input).  The asserts cause the auth to fail anyway,
        #      but it's ugly.
        #  - Andrew Bennetts, 2005-01-21
        assert '/' not in avatarId
        assert avatarId not in ('.', '..')

        self.avatarId = avatarId
        self.homeDirsRoot = homeDirsRoot
        self._launchpad = launchpad

        # Fetch user details from the authserver
        self.lpid = userDict['id']
        self.lpname = userDict['name']
        self.teams = userDict['teams']

        # Extract the initial branches from the user dict.
        self.branches = {}
        for teamDict in self.teams:
            self.branches[teamDict['id']] = teamDict['initialBranches']

        self._productIDs = {}
        self._productNames = {}

        self.filesystem = FileSystem(SFTPServerRoot(self))

        # Set the only channel as a session that only allows requests for
        # subsystems...
        self.channelLookup = {'session': SubsystemOnlySession}
        # ...and set the only subsystem to be SFTP.
        self.subsystemLookup = {'sftp': filetransfer.FileTransferServer}

    def fetchProductID(self, productName):
        """Fetch the product ID for productName.

        Returns a Deferred of the result, which may be None if no product by
        that name exists.

        This method guarantees repeatable reads: on a particular instance of
        SFTPOnlyAvatar, fetchProductID will always return the same value for a
        given productName.
        """
        productID = self._productIDs.get(productName)
        if productID is not None:
            # XXX: should the None result (i.e. not found) be remembered too, to
            #      ensure repeatable reads?
            #  -- Andrew Bennetts, 2005-12-13
            return defer.succeed(productID)
        deferred = self._launchpad.fetchProductID(productName)
        deferred.addCallback(self._cbRememberProductID, productName)
        return deferred

    def createBranch(self, userID, productID, branchName):
        """Register a new branch in Launchpad.

        Returns a Deferred with the new branch ID.
        """
        return self._launchpad.createBranch(userID, productID, branchName)

    def _cbRememberProductID(self, productID, productName):
        if productID is None:
            return None
        productID = str(productID)
        self._productIDs[productName] = productID
        self._productNames[productID] = productName
        return productID

    def _runAsUser(self, f, *args, **kwargs):
        # Version of UnixConchUser._runAsUser with the setuid bits stripped out
        # -- we don't need them.
        try:
            f = iter(f)
        except TypeError:
            f = [(f, args, kwargs)]
        for i in f:
            func = i[0]
            args = len(i)>1 and i[1] or ()
            kw = len(i)>2 and i[2] or {}
            r = func(*args, **kw)
        return r

    def getHomeDir(self):
        return os.path.join(self.homeDirsRoot, self.avatarId)


components.registerAdapter(sftp.AdaptFileSystemUserToISFTP, SFTPOnlyAvatar,
                           filetransfer.ISFTPServer)


class Realm:
    implements(IRealm)

    def __init__(self, homeDirsRoot, authserver):
        self.homeDirsRoot = homeDirsRoot
        self.authserver = authserver

    def requestAvatar(self, avatarId, mind, *interfaces):
        # Fetch the user's details from the authserver
        deferred = self.authserver.getUser(avatarId)
        
        # Then fetch more details: the branches owned by this user (and the
        # teams they are a member of).
        def getInitialBranches(userDict):
            # XXX: this makes many XML-RPC requests where a better API could
            #      require only one (or include it in the team dict in the first
            #      place).
            #  -- Andrew Bennetts, 2005-12-13
            deferreds = []
            for teamDict in userDict['teams']:
                deferred = self.authserver.getBranchesForUser(teamDict['id'])
                def _gotBranches(branches, teamDict=teamDict):
                    teamDict['initialBranches'] = branches
                deferred.addCallback(_gotBranches)
                deferreds.append(deferred)
            def allDone(ignore):
                return userDict

            # This callback will complete when all the getBranchesForUser calls
            # have completed and added initialBranches to each team dict, and
            # will return the userDict.
            return defer.DeferredList(deferreds,
                    fireOnOneErrback=True).addCallback(allDone)
        deferred.addCallback(getInitialBranches)

        # Once all those details are retrieved, we can construct the avatar.
        def gotUserDict(userDict):
            avatar = SFTPOnlyAvatar(avatarId, self.homeDirsRoot, userDict,
                                    self.authserver)
            return interfaces[0], avatar, lambda: None
        return deferred.addCallback(gotUserDict)


class Factory(factory.SSHFactory):
    services = {
        'ssh-userauth': userauth.SSHUserAuthServer,
        'ssh-connection': connection.SSHConnection
    }

    def __init__(self, hostPublicKey, hostPrivateKey):
        self.publicKeys = {
            'ssh-rsa': hostPublicKey
        }
        self.privateKeys = {
            'ssh-rsa': hostPrivateKey
        }

    def startFactory(self):
        factory.SSHFactory.startFactory(self)
        os.umask(0022)


class PublicKeyFromLaunchpadChecker(SSHPublicKeyDatabase):
    """Cred checker for getting public keys from launchpad.

    It knows how to get the public keys from the authserver, and how to unmunge
    usernames for baz.
    """
    implements(ICredentialsChecker)

    def __init__(self, authserver):
        self.authserver = authserver

    def _unmungeUsername(username):
        """Unmunge usernames, because baz doesn't work with @ in usernames.

        Examples:

        Usernames that aren't munged are unaffected.

            >>> unmunge = PublicKeyFromLaunchpadChecker._unmungeUsername
            >>> unmunge('foo@bar')
            'foo@bar'
            >>> unmunge('foo_bar@baz')
            'foo_bar@baz'

        Anything without an underscore is also not munged, and so unaffected.

        (Usernames without an underscore aren't valid for the Bazaar 1.x part of
        the supermirror, but are for the bzr part)

            >>> unmunge('foo-bar')
            'foo-bar'

        Munged usernames have the last underscore converted.

            >>> unmunge('foo_bar')
            'foo@bar'
            >>> unmunge('foo_bar_baz')
            'foo_bar@baz'
        """
        
        if '@' in username:
            # Not munged, don't try to unmunge it.
            return username

        underscore = username.rfind('_')
        if underscore == -1:
            # No munging, return as-is.  (Although with an _ or a @, it won't
            # auth, but let's keep it simple).
            return username

        # Replace the final underscore with an at sign.
        unmunged = username[:underscore] + '@' + username[underscore+1:]
        return unmunged
    _unmungeUsername = staticmethod(_unmungeUsername)

    def checkKey(self, credentials):
        # Query the authserver with an unmunged username
        username = self._unmungeUsername(credentials.username)
        authorizedKeys = self.authserver.getSSHKeys(username)

        # Add callback to try find the authorised key
        authorizedKeys.addCallback(self._cb_hasAuthorisedKey, credentials)
        return authorizedKeys
                
    def _cb_hasAuthorisedKey(self, keys, credentials):
        for keytype, keytext in keys:
            try:
                if keytext.decode('base64') == credentials.blob:
                    return True
            except binascii.Error:
                continue

        return False
        
    def requestAvatarId(self, credentials):
        # Do everything the super class does, plus unmunge the username if the
        # key works.
        d = SSHPublicKeyDatabase.requestAvatarId(self, credentials)
        d.addCallback(self._unmungeUsername)
        return d


if __name__ == "__main__":
    # Run doctests.
    import doctest
    doctest.testmod()

