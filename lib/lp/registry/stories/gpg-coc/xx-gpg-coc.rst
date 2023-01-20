Claiming GPG Keys
=================


Setup
-----

    >>> import email
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.mail import stub
    >>> from lp.testing.keyserver import KeyServerTac
    >>> from lp.testing.pages import setupBrowserFreshLogin

Set up the stub KeyServer:

    >>> tac = KeyServerTac()
    >>> tac.setUp()


Claim an encrypting GPG key
---------------------------

This test verifies the basic claim a GPG key workflow.

Start out with a clean page containing no imported keys:

    >>> login(ANONYMOUS)
    >>> name12 = getUtility(IPersonSet).getByEmail("test@canonical.com")
    >>> logout()
    >>> browser = setupBrowserFreshLogin(name12)
    >>> browser.open("http://launchpad.test/~name12")
    >>> browser.getLink(url="+editpgpkeys").click()
    >>> print(browser.title)
    Change your OpenPGP keys...

    >>> browser.getControl(name="DEACTIVATE_GPGKEY")
    Traceback (most recent call last):
    ...
    LookupError: name ...'DEACTIVATE_GPGKEY'
    ...

Claim OpenPGP key:

    >>> key = "A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
    >>> browser.getControl(name="fingerprint").value = key
    >>> browser.getControl(name="import").click()
    >>> print_feedback_messages(browser.contents)
    A message has been sent to test@canonical.com, encrypted
    with the key 1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543.
    To confirm the key is yours, decrypt the message and follow the
    link inside.

Recover token URL from the encrypted part, but also make sure there's a clear
text part that provides useful information to users who -- for whatever reason
-- cannot decrypt the token url.  Start by grabbing the confirmation message.

    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_msg)
    >>> msg.get_content_type()
    'text/plain'

The message will be a single text/plain part with clear text instructions,
followed by ASCII armored encrypted confirmation instructions.  Ensure that
the clear text instructions contain the expected URLs pointing to more help.

    >>> cipher_body = msg.get_payload(decode=True)
    >>> print(cipher_body.decode())  # noqa
    Hello,
    <BLANKLINE>
    This message contains the instructions for confirming registration of an
    OpenPGP key for use in Launchpad.  The confirmation instructions have been
    encrypted with the OpenPGP key you have attempted to register.  If you cannot
    read the unencrypted instructions below, it may be because your mail reader
    does not support automatic decryption of "ASCII armored" encrypted text.
    <BLANKLINE>
    Exact instructions for enabling this depends on the specific mail reader you
    are using.  Please see this support page for more information:
    <BLANKLINE>
        https://help.launchpad.net/ReadingOpenPgpMail
    <BLANKLINE>
    For more general information on OpenPGP and related tools such as Gnu Privacy
    Guard (GPG), please see:
    <BLANKLINE>
        https://help.ubuntu.com/community/GnuPrivacyGuardHowto
    <BLANKLINE>
    -----BEGIN PGP MESSAGE-----
    ...
    -----END PGP MESSAGE-----
    <BLANKLINE>
    <BLANKLINE>
    Thanks,
    <BLANKLINE>
    The Launchpad Team

Import the secret keys needed for this test:

    >>> from lp.services.gpg.interfaces import IGPGHandler

    >>> from lp.testing.gpgkeys import import_secret_test_key, decrypt_content


    >>> gpghandler = getUtility(IGPGHandler)

    >>> login(ANONYMOUS)
    >>> key = import_secret_test_key("test@canonical.com.sec")

'cipher_body' is a message encrypted with the just-imported
1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543 OpenPGP key, we need to
access the current IGpghandler instance to access this key and decrypt the
message.

    >>> body = decrypt_content(cipher_body, "test")

Extract the token URL from the email:

    >>> from lp.services.verification.tests.logintoken import (
    ...     get_token_url_from_bytes,
    ... )
    >>> token_url = get_token_url_from_bytes(body)

Go to the link sent by email, to validate the email address.

    >>> logout()
    >>> browser.open(token_url)

Get redirected to +validategpg, and confirm token:

    >>> print(browser.url)
    http://launchpad.test/token/.../+validategpg
    >>> browser.getControl("Continue").click()

Get redirected to the user's homepage with a greeting:

    >>> browser.url
    'http://launchpad.test/~name12'
    >>> print_feedback_messages(browser.contents)
    The key 1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543 was successfully
    validated.

Certify the key is imported:

    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")
    >>> browser.getControl(name="DEACTIVATE_GPGKEY").displayOptions
    ['1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543']

Verify that the key was imported with the "can encrypt" flag set:

    >>> from lp.registry.model.gpgkey import GPGKey
    >>> from lp.services.database.interfaces import IStore
    >>> key = (
    ...     IStore(GPGKey)
    ...     .find(
    ...         GPGKey, fingerprint="A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
    ...     )
    ...     .one()
    ... )
    >>> print(key.owner.name)
    name12
    >>> print(key.can_encrypt)
    True


Claim a sign-only GPG key
-------------------------

Here, Sample Person wants to claim a GPG key that can only sign
content. They can't verify their key by decrypting content on demand, but
they can verify it by signing content. Launchpad sends them an email
token. The email step ensures that an attacker who knows Sample
Person's Launchpad password can't associate arbitrary GPG keys with
their Launchpad account.

    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")

    >>> fingerprint = "447DBF38C4F9C4ED752246B77D88913717B05A8F"
    >>> browser.getControl(name="fingerprint").value = fingerprint
    >>> browser.getControl(name="import").click()
    >>> print_feedback_messages(browser.contents)
    A message has been sent to test@canonical.com. To
    confirm the key 1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F is yours,
    follow the link inside.

Sample Person checks their email.

    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_msg)
    >>> msg.get_content_type()
    'text/plain'
    >>> body = msg.get_payload(decode=True)

The email is not encrypted, since Sample Person didn't claim the
ability to decrypt text with this key.

    >>> b"-----BEGIN PGP MESSAGE-----" in body
    False

The email does contain some information about the key, and a token URL
Sample Person should visit to verify their ownership of the key.

    >>> print(body.decode())
    <BLANKLINE>
    Hello,
    ...
        User name    : Sample Person
        Email address: test@canonical.com
    ...
        Key type    : 1024D
        Fingerprint : 447DBF38C4F9C4ED752246B77D88913717B05A8F
    <BLANKLINE>
    UIDs:
        sign.only@canonical.com
    ...
        http://launchpad.test/token/...

    >>> token_url = get_token_url_from_bytes(body)

Side note: in a little while, Sample User will be asked to sign some
text which includes the date the token was generated (to avoid replay
attacks). To make this testable, we set the creation date of this
token to a fixed value:

    >>> token_value = token_url.split("http://launchpad.test/token/")[
    ...     1
    ... ].encode("ASCII")

    >>> import datetime, hashlib, pytz
    >>> from lp.services.verification.model.logintoken import LoginToken
    >>> logintoken = LoginToken.selectOneBy(
    ...     _token=hashlib.sha256(token_value).hexdigest()
    ... )
    >>> logintoken.date_created = datetime.datetime(
    ...     2005, 4, 1, 12, 0, 0, tzinfo=pytz.timezone("UTC")
    ... )
    >>> logintoken.sync()

Back to Sample User. They visit the token URL and is asked to sign some
text to prove they own the key.

    >>> browser.open(token_url)
    >>> browser.title
    'Confirm sign-only OpenPGP key'

Let's look at the text.

    >>> verification_content = find_main_content(browser.contents).pre.string
    >>> print(verification_content)
    Please register 447DBF38C4F9C4ED752246B77D88913717B05A8F to the
    Launchpad user name12.  2005-04-01 12:00:00 UTC

If they refuse to sign the text, they get an error message.

    >>> browser.getControl("Continue").click()
    >>> browser.title
    'Confirm sign-only OpenPGP key'
    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    Required input is missing.

If they sign a different text, they get an error message.

    >>> login(ANONYMOUS)
    >>> key = import_secret_test_key("sign.only@canonical.com.sec")
    >>> bad = gpghandler.signContent(
    ...     b"This is not the verification message!", key, "test"
    ... )
    >>> logout()

    >>> browser.getControl("Signed text").value = bad
    >>> browser.getControl("Continue").click()
    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    The signed content does not match the message found in the email.

If they sign the text with a different key, they get an error
message. The following text was signed with the key
A419AE861E88BC9E04B9C26FBA2B9389DFD20543:

    >>> signed_content = """
    ... -----BEGIN PGP SIGNED MESSAGE-----
    ... Hash: SHA1
    ...
    ... Please register 447DBF38C4F9C4ED752246B77D88913717B05A8F to the
    ... Launchpad user name12.  2005-04-01 12:00:00 UTC
    ... -----BEGIN PGP SIGNATURE-----
    ... Version: GnuPG v1.4.1 (GNU/Linux)
    ...
    ... iD8DBQFDcLOh2yWXVgK6XvYRAkpWAKDFHRpVJc2flFwpQMMxub4cl+TcCACgyciu
    ... s7GH1fQGOQMqpvpinwOjGto=
    ... =w7/b
    ... -----END PGP SIGNATURE-----
    ... """
    >>> browser.getControl("Signed text").value = signed_content
    >>> browser.getControl("Continue").click()
    >>> print_feedback_messages(browser.contents)
    There is 1 error.
    The key used to sign the content
    (A419AE861E88BC9E04B9C26FBA2B9389DFD20543) is not the key you were
    registering

If they sign the text correctly, they are redirected to their home page.

    >>> login(ANONYMOUS)
    >>> good = gpghandler.signContent(
    ...     six.ensure_binary(verification_content), key, "test"
    ... )
    >>> logout()

    >>> browser.getControl("Signed text").value = good
    >>> browser.getControl("Continue").click()
    >>> browser.url
    'http://launchpad.test/~name12'
    >>> print_feedback_messages(browser.contents)
    The key 1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F was successfully
    validated.

Now that the key has been validated, the login token is consumed:

    >>> consumed_token = LoginToken.selectOneBy(
    ...     _token=hashlib.sha256(token_value).hexdigest()
    ... )
    >>> consumed_token.date_consumed is not None
    True

Now Sample Person's sign-only key is associated with their account. They
verify this:

    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")

    >>> content = find_main_content(browser.contents)
    >>> browser.getControl(name="DEACTIVATE_GPGKEY").displayOptions
    [...'1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F (sign only)']

On a mad whim they decide to de-activate the key they just imported.

    >>> browser.getControl(name="DEACTIVATE_GPGKEY").displayValue = [
    ...     "1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F (sign only)"
    ... ]
    >>> browser.getControl("Deactivate Key").click()

    >>> print_feedback_messages(browser.contents)
    Deactivated key(s): 1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F

Coming to their senses, they ask for a re-validation of the key.

    >>> browser.getControl(name="REACTIVATE_GPGKEY").value = [
    ...     "447DBF38C4F9C4ED752246B77D88913717B05A8F"
    ... ]
    >>> browser.getControl("Reactivate Key").click()

    >>> print_feedback_messages(browser.contents)
    A message has been sent to test@canonical.com with instructions
    to reactivate these key(s): 1024D/447DBF38C4F9C4ED752246B77D88913717B05A8F

They open the page and checks that the key is displayed as pending
revalidation.

    >>> browser.reload()
    >>> browser.getControl(name="REMOVE_GPGTOKEN").displayOptions
    ['447DBF38C4F9C4ED752246B77D88913717B05A8F']

(We won't run through the whole validation process again, as this key isn't
used in any more tests.)

Teardown
--------

    >>> tac.tearDown()

=========================
Signing a Code of Conduct
=========================

Sample person has never signed a code of conduct.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open("http://launchpad.test/~name12/+codesofconduct")
    >>> print(extract_text(find_main_content(browser.contents)))
    Codes of Conduct for Sample Person
    Launchpad records codes of conduct you sign as commitments to the
    principles of collaboration, tolerance and open communication that
    drive the open source community.
    Sample Person has never signed a code
    of conduct.
    See or sign new code of conduct releases

    # A helper function for reading a code-of-conduct file.
    >>> import os
    >>> def read_file(filename):
    ...     path = os.path.join(os.path.dirname(__file__), filename)
    ...     with open(path) as file_object:
    ...         return file_object.read()
    ...


Code of Conduct registration problems
=====================================

Sample Person tries unsuccessfully to register a truncated code of conduct.

    >>> truncated_coc = read_file("truncated_coc.asc")
    >>> browser.open("http://launchpad.test/codeofconduct/2.0/+sign")
    >>> browser.getControl("Signed Code").value = truncated_coc
    >>> browser.getControl("Continue").click()
    >>> print_errors(browser.contents)
    There is 1 error.
    The signed text does not match the Code of Conduct. Make sure that you
    signed the correct text (white space differences are acceptable).

Sample Person tries unsuccessfully to register an old version of the code.

    >>> coc_version_1_0 = read_file("10_coc.asc")
    >>> browser.getControl("Signed Code").value = coc_version_1_0
    >>> browser.getControl("Continue").click()
    >>> print_errors(browser.contents)
    There is 1 error.
    The signed text does not match the Code of Conduct. Make sure that you
    signed the correct text (white space differences are acceptable).


Sample Person tries to access the old version page to sign it, and is informed
that there is a new version available.

    >>> browser.open("http://launchpad.test/codeofconduct/1.0/+sign")
    >>> browser.getLink("the current version").click()
    >>> print(browser.url)
    http://launchpad.test/codeofconduct/2.0

    >>> browser.getLink("Sign it").click()
    >>> print(browser.url)
    http://launchpad.test/codeofconduct/2.0/+sign


Code of Conduct registration
============================

Sample Person registers the code of conduct, using a reformatted copy which
has leading spaces removed.  This succeeds because the words the same and
appear in the same order.

    >>> reformatted_coc = read_file("reformatted_20_coc.asc")
    >>> browser.getControl("Signed Code").value = reformatted_coc
    >>> browser.getControl("Continue").click()
    >>> print(browser.url)
    http://launchpad.test/~name12/+codesofconduct

And now Sample Person's Codes of Conduct page shows that they've signed it.

    >>> browser.open("http://launchpad.test/~name12/+codesofconduct")
    >>> print(extract_text(find_main_content(browser.contents)))
    Codes of Conduct for Sample Person
    Launchpad records codes of conduct you sign as commitments to the
    principles of collaboration, tolerance and open communication that
    drive the open source community.
    Active signatures
    If you change your mind about agreeing to a code of conduct,
    you can deactivate your signature.
    ...: digitally signed by Sample Person
    (1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543) ...


Now Sample Person will deactivate their key...

    >>> browser = setupBrowserFreshLogin(name12)
    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")
    >>> browser.url
    'http://launchpad.test/~name12/+editpgpkeys'

    >>> print(browser.contents)
    <...
    ...Your active keys...
    ...1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543...


... but they forgot to select the checkbox of the key they want to remove.

    >>> browser.getControl("Deactivate Key").click()
    >>> for tag in find_main_content(browser.contents)("p", "error message"):
    ...     print(tag.decode_contents())
    ...
    No key(s) selected for deactivation.


Now they select the checkbox and deactivate it.

    >>> browser.getControl(
    ...     "1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
    ... ).selected = True
    >>> browser.getControl("Deactivate Key").click()
    >>> soup = find_main_content(browser.contents)
    >>> for tag in soup("p", "informational message"):
    ...     print(tag.decode_contents())
    ...
    Deactivated key(s): 1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543


Sample Person already has a deactivated key.

    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")
    >>> browser.url
    'http://launchpad.test/~name12/+editpgpkeys'

    >>> print(browser.contents)
    <...
    ...Deactivated keys...
    ...1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543...


Now they'll request their key to be reactivated.

    >>> browser.getControl("Reactivate Key").click()
    >>> soup = find_main_content(browser.contents)
    >>> for tag in soup("p", "error message"):
    ...     print(tag.decode_contents())
    ...
    No key(s) selected for reactivation.

    >>> browser.getControl(
    ...     "1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543"
    ... ).selected = True
    >>> browser.getControl("Reactivate Key").click()
    >>> soup = find_main_content(browser.contents)
    >>> for tag in soup("p", "informational message"):
    ...     print(tag.decode_contents())
    ...
    A message has been sent to test@canonical.com with instructions to
    reactivate...


Get the token from the body of the email sent.

    >>> import re
    >>> from lp.services.mail import stub
    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_msg)
    >>> cipher_body = msg.get_payload(decode=1)
    >>> body = decrypt_content(cipher_body, "test")
    >>> link = get_token_url_from_bytes(body)
    >>> token = re.sub(r".*token/", "", link)
    >>> token_url = "http://launchpad.test/token/%s" % token


Going to the token page will get us redirected to the page of that specific
token type (+validategpg).

    >>> browser.open(token_url)
    >>> browser.url == "%s/+validategpg" % token_url
    True

    >>> print(browser.contents)
    <...
    ...Confirm the OpenPGP key...A419AE861E88BC9E04B9C26FBA2B9389DFD20543...
    ...Sample Person...


Now Sample Person confirms the reactivation.

    >>> browser.getControl("Continue").click()
    >>> browser.url
    'http://launchpad.test/~name12'

    >>> print(browser.contents)
    <...
    ...Key 1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543 successfully
    reactivated...


And now we can see the key listed as one of Sample Person's active keys.

    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")
    >>> print(browser.contents)
    <...
    ...Your active keys...
    ...1024D/A419AE861E88BC9E04B9C26FBA2B9389DFD20543...

This test verifies that we correctly handle keys which are in some way
special: either invalid, broken, revoked, expired, or already imported.

    >>> from lp.testing.keyserver import KeyServerTac
    >>> from lp.services.mail import stub

    >>> tac = KeyServerTac()
    >>> tac.setUp()

    >>> sign_only = "447D BF38 C4F9 C4ED 7522  46B7 7D88 9137 17B0 5A8F"
    >>> preimported = "A419AE861E88BC9E04B9C26FBA2B9389DFD20543"

Try to import a key which is already imported:

    >>> del stub.test_emails[:]
    >>> browser.open("http://launchpad.test/~name12/+editpgpkeys")
    >>> browser.getControl(name="fingerprint").value = preimported
    >>> browser.getControl(name="import").click()
    >>> "A message has been sent" in browser.contents
    False
    >>> stub.test_emails
    []
    >>> print(browser.contents)
    <BLANKLINE>
    ...
    ...has already been imported...

    >>> tac.tearDown()



Ensure we are raising 404 error instead of System Error

    >>> print(
    ...     http(
    ...         r"""
    ... POST /codeofconduct/donkey HTTP/1.1
    ... Authorization: Basic Zm9vLmJhckBjYW5vbmljYWwuY29tOnRlc3Q=
    ... Referer: https://launchpad.test/
    ... """
    ...     )
    ... )
    HTTP/1.1 404 Not Found
    ...

Check to see no CoC signature is registered for Mark:

    >>> admin_browser.open("http://localhost:9000/codeofconduct/console")
    >>> admin_browser.getControl(name="searchfor").value = ["all"]
    >>> admin_browser.getControl(name="name").value = "mark"
    >>> admin_browser.getControl(name="search").click()
    >>> "No signatures found." in admin_browser.contents
    True

Perform Acknowledge process as Foo bar person:

    >>> admin_browser.open("http://localhost:9000/codeofconduct/console/+new")
    >>> admin_browser.title
    'Register a code of conduct signature'

    >>> admin_browser.getControl(
    ...     name="field.owner"
    ... ).value = "mark@example.com"
    >>> admin_browser.getControl("Register").click()
    >>> admin_browser.url
    'http://localhost:9000/codeofconduct/console'

Ensure the CoC was acknowledge by searching in the CoC Admin Console:

    >>> admin_browser.open("http://launchpad.test/codeofconduct/console")
    >>> admin_browser.getControl(name="searchfor").value = ["all"]
    >>> admin_browser.getControl(name="name").value = "mark"
    >>> admin_browser.getControl(name="search").click()
    >>> print(extract_text(find_tag_by_id(admin_browser.contents, "matches")))
    Mark ... paper submission accepted by Foo Bar [ACTIVE]

Test if the advertisement email was sent:

    >>> from lp.services.mail import stub
    >>> from_addr, to_addrs, raw_msg = stub.test_emails.pop()
    >>> msg = email.message_from_bytes(raw_msg)
    >>> print(msg.get_payload(decode=True).decode())
    <BLANKLINE>
    ...
    User: 'Mark Shuttleworth'
    Paper Submitted acknowledge by Foo Bar
    ...

  Let's login with an Launchpad Admin

    >>> browser.addHeader(
    ...     "Authorization", "Basic guilherme.salgado@canonical.com:test"
    ... )

  Check if we can see the Code of conduct page

    >>> browser.open("http://localhost:9000/codeofconduct")
    >>> "Ubuntu Codes of Conduct" in browser.contents
    True

  The link to the Administrator console

    >>> admin_console_link = browser.getLink("Administration console")
    >>> admin_console_link.url
    'http://localhost:9000/codeofconduct/console'

  Let's follow the link

    >>> admin_console_link.click()

  We are in the Administration page

    >>> browser.url
    'http://localhost:9000/codeofconduct/console'

    >>> "Administer code of conduct signatures" in browser.contents
    True

    >>> browser.getLink("register signatures").url
    'http://localhost:9000/codeofconduct/console/+new'


  Back to the CoC front page let's see the current version of the CoC

    >>> browser.open("http://localhost:9000/codeofconduct")
    >>> browser.getLink("current version").click()

    >>> "Ubuntu Code of Conduct - 2.0" in browser.contents
    True

    >>> browser.getLink("Sign it").url
    'http://localhost:9000/codeofconduct/2.0/+sign'

    >>> browser.getLink("Download this version").url
    'http://localhost:9000/codeofconduct/2.0/+download'
