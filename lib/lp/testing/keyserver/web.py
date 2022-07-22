# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""GPG Key Information Server Prototype.

It follows the standard URL schema for PKS/SKS systems

It implements the operations:

 - 'index' : returns key index information
 - 'get': returns an ASCII armored public key
 - 'add': adds a key to the collection (does not update the index)

It only depends on GPG for key submission; for retrieval and searching
it just looks for files in the root (eg. /var/tmp/testkeyserver). The files
are named like this:

0x<keyid|fingerprint>.<operation>

Example:

$ gpg --list-key cprov > 0x681B6469.index

note: remove the lines containing 'sub' or 'secret' keys

$ gpg --export -a cprov > 0x681B6469.get
"""

__all__ = [
    "KeyServerResource",
]

import glob
import html
import os
from time import sleep

from twisted.web.resource import Resource
from zope.component import getUtility

from lp.services.gpg.interfaces import (
    GPGKeyNotFoundError,
    IGPGHandler,
    MoreThanOneGPGKeyFound,
    SecretGPGKeyImportDetected,
)

GREETING = b"Copyright 2004-2009 Canonical Ltd.\n"


def locate_key(root, suffix):
    """Find a key file in the root with the given suffix.

    This does some globbing to possibly find a fingerprint-named key
    file when given a key ID.

    :param root: The root directory in which to look.
    :param suffix: The key ID or fingerprint, of the form
        0x<FINGERPRINT|KEYID>.<METHOD>
    :returns: An absolute path to the key file.
    """
    path = os.path.join(root, suffix)

    if not os.path.exists(path):
        # GPG might request a key ID from us, but we name the keys by
        # fingerprint. Let's glob.
        if suffix.startswith("0x"):
            suffix = suffix[2:]
        keys = glob.glob(os.path.join(root, "*" + suffix))
        if len(keys) == 1:
            path = keys[0]
        else:
            return None

    return path


class _BaseResource(Resource):
    def getChild(self, name, request):
        """Redirect trailing slash correctly."""
        if name == b"":
            return self
        return Resource.getChild(self, name, request)


class KeyServerResource(_BaseResource):
    """Root resource for the test keyserver."""

    def __init__(self, root):
        _BaseResource.__init__(self)
        self.putChild(b"pks", PksResource(root))

    def render_GET(self, request):
        return GREETING


class PksResource(_BaseResource):
    def __init__(self, root):
        _BaseResource.__init__(self)
        self.putChild(b"lookup", LookUp(root))
        self.putChild(b"add", SubmitKey(root))

    def render_GET(self, request):
        return b"Welcome To Fake SKS service.\n"


KEY_NOT_FOUND_BODY = (
    b"<html><head><title>Error handling request</title></head>\n"
    b"<body><h1>Error handling request</h1>No results found: "
    b"No keys found</body></html>"
)


class LookUp(Resource):

    isLeaf = True
    permitted_actions = ["index", "get"]

    def __init__(self, root):
        Resource.__init__(self)
        self.root = root

    def render_GET(self, request):
        try:
            action = request.args[b"op"][0].decode("ISO-8859-1")
            keyid = request.args[b"search"][0].decode("ISO-8859-1")
        except KeyError:
            return ("Invalid Arguments %s" % request.args).encode("UTF-8")

        return self.processRequest(action, keyid, request)

    def processRequest(self, action, keyid, request):
        # Sleep a short time so that tests can ensure that timeouts
        # are properly handled by setting an even shorter timeout.
        sleep(0.02)
        if (action not in self.permitted_actions) or not keyid:
            message = 'Forbidden: "%s" on ID "%s"' % (action, keyid)
            return message.encode("UTF-8")

        filename = "%s.%s" % (keyid, action)

        path = locate_key(self.root, filename)
        if path is not None:
            with open(path) as f:
                content = html.escape(f.read(), quote=False)
            page = (
                "<html>\n<head>\n"
                "<title>Results for Key %s</title>\n"
                "</head>\n<body>"
                "<h1>Results for Key %s</h1>\n"
                "<pre>\n%s\n</pre>\n</html>"
            ) % (keyid, keyid, content)
            return page.encode("UTF-8")
        else:
            request.setResponseCode(404)
            return KEY_NOT_FOUND_BODY


SUBMIT_KEY_PAGE = """
<html>
  <head>
    <title>Submit a key</title>
  </head>
  <body>
    <h1>Submit a key</h1>
    <p>%(banner)s</p>
    <form method="post">
      <textarea name="keytext" rows="20" cols="66"></textarea> <br>
      <input type="submit" value="Submit">
    </form>
  </body>
</html>
"""


class SubmitKey(Resource):
    isLeaf = True

    def __init__(self, root):
        Resource.__init__(self)
        self.root = root

    def render_GET(self, request):
        return (SUBMIT_KEY_PAGE % {"banner": ""}).encode("UTF-8")

    def render_POST(self, request):
        try:
            keytext = request.args[b"keytext"][0]
        except KeyError:
            return ("Invalid Arguments %s" % request.args).encode("UTF-8")
        return self.storeKey(keytext)

    def storeKey(self, keytext):
        gpghandler = getUtility(IGPGHandler)
        try:
            key = gpghandler.importPublicKey(keytext)
        except (
            GPGKeyNotFoundError,
            SecretGPGKeyImportDetected,
            MoreThanOneGPGKeyFound,
        ) as err:
            return (SUBMIT_KEY_PAGE % {"banner": str(err)}).encode("UTF-8")

        filename = "0x%s.get" % key.fingerprint
        path = os.path.join(self.root, filename)

        with open(path, "wb") as fp:
            fp.write(keytext)

        return (SUBMIT_KEY_PAGE % {"banner": "Key added"}).encode("UTF-8")
