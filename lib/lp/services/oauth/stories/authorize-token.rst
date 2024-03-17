Authorizing a request token
===========================

Once the consumer gets a request token, it must send the user to
Launchpad's +authorize-token page in order for the user to authenticate
and authorize or not the consumer to act on their behalf.

    >>> def request_token_for(consumer):
    ...     """Helper method to create a request token."""
    ...     login("salgado@ubuntu.com")
    ...     token, _ = consumer.newRequestToken()
    ...     logout()
    ...     return token
    ...

    # Create a new request token.
    >>> from zope.component import getUtility
    >>> from lp.services.oauth.interfaces import IOAuthConsumerSet
    >>> from lp.testing import ANONYMOUS, login, logout
    >>> login("salgado@ubuntu.com")
    >>> consumer = getUtility(IOAuthConsumerSet).getByKey("foobar123451432")
    >>> logout()
    >>> token = request_token_for(consumer)

According to the OAuth Core 1.0 spec, the request to the service
provider's user authorization URL (+authorize-token in our case) must
use the HTTP GET method and may include the oauth_callback parameter.
The oauth_token parameter, on the other hand, is required in the
Launchpad implementation.

The +authorize-token page is restricted to logged in users, so users will
first be asked to log in. (We won't show the actual login process because
it involves OpenID, which would complicate this test quite a bit.)

    >>> from urllib.parse import urlencode
    >>> params = dict(
    ...     oauth_token=token.key, oauth_callback="http://launchpad.test/bzr"
    ... )
    >>> url = "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    >>> browser.open(url)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> browser.open(url)
    >>> browser.title
    'Authorize application to access Launchpad on your behalf'

    >>> main_content = find_tag_by_id(browser.contents, "maincontent")
    >>> print(extract_text(main_content))
    Authorize application to access Launchpad on your behalf
    Integrating foobar123451432 into your Launchpad account
    The application identified as foobar123451432 wants to access Launchpad on
    your behalf. What level of access do you want to grant?
    ...
    See all applications authorized to access Launchpad on your behalf.

This page contains one submit button for each item of OAuthPermission,
except for 'Desktop Integration', which must be specifically requested.

    >>> def print_access_levels(main_content):
    ...     actions = main_content.find_all("input", attrs={"type": "submit"})
    ...     for action in actions:
    ...         print(action["value"])
    ...

    >>> print_access_levels(main_content)
    No Access
    Read Non-Private Data
    Change Non-Private Data
    Read Anything
    Change Anything

    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> actions = main_content.find_all("input", attrs={"type": "submit"})
    >>> len(actions) == len(OAuthPermission.items) - 1
    True

An application, when asking to access Launchpad on a user's behalf,
may restrict the user to certain items of OAuthPermission. This
prevents annoying cases where the user grants a level of permission
that isn't enough for the application. The user always has the option
to deny permission altogether.

    >>> def authorize_token_browser(allow_permission):
    ...     browser.open(
    ...         "http://launchpad.test/+authorize-token?%s&%s"
    ...         % (urlencode(params), allow_permission)
    ...     )
    ...

    >>> def authorize_token_main_content(allow_permission):
    ...     authorize_token_browser(allow_permission)
    ...     return find_tag_by_id(browser.contents, "maincontent")
    ...

    >>> def print_access_levels_for(allow_permission):
    ...     main_content = authorize_token_main_content(allow_permission)
    ...     print_access_levels(main_content)
    ...

    >>> print_access_levels_for(
    ...     "allow_permission=WRITE_PUBLIC&allow_permission=WRITE_PRIVATE"
    ... )
    No Access
    Change Non-Private Data
    Change Anything

If an application doesn't specify any valid access levels, or only
specifies the UNAUTHORIZED access level, Launchpad will show all the
access levels, except for DESKTOP_INTEGRATION.

    >>> print_access_levels_for("")
    No Access
    Read Non-Private Data
    Change Non-Private Data
    Read Anything
    Change Anything

    >>> print_access_levels_for("allow_permission=UNAUTHORIZED")
    No Access
    Read Non-Private Data
    Change Non-Private Data
    Read Anything
    Change Anything

An application may not request the DESKTOP_INTEGRATION access level
unless its consumer key matches a certain pattern. (Successful desktop
integration has its own section, below.)

    >>> allow_permission = "allow_permission=DESKTOP_INTEGRATION"
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s&%s"
    ...     % (urlencode(params), allow_permission)
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: Consumer "foobar123451432" asked
    for desktop integration, but didn't say what kind of desktop it is, or
    name the computer being integrated.

An application may also specify a context, so that the access granted
by the user is restricted to things related to that context.

    >>> params_with_context = {"lp.context": "firefox"}
    >>> params_with_context.update(params)
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s"
    ...     % urlencode(params_with_context)
    ... )
    >>> main_content = find_tag_by_id(browser.contents, "maincontent")
    >>> print(extract_text(main_content))
    Authorize application to access Launchpad on your behalf
    Integrating foobar123451432 into your Launchpad account
    The application...wants to access things related to Mozilla Firefox...

A client other than a web browser may request a JSON representation of
the list of authentication levels.

    >>> import json
    >>> from lp.testing.pages import setupBrowser

    >>> json_browser = setupBrowser()
    >>> json_browser.addHeader("Accept", "application/json")
    >>> json_browser.addHeader(
    ...     "Authorization", "Basic test@canonical.com:test"
    ... )
    >>> json_browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> json_token = json.loads(json_browser.contents)
    >>> sorted(json_token.keys())
    ['access_levels', 'oauth_token', 'oauth_token_consumer']

    >>> sorted(
    ...     (level["value"], level["title"])
    ...     for level in json_token["access_levels"]
    ... )
    [('READ_PRIVATE', 'Read Anything'),
     ('READ_PUBLIC', 'Read Non-Private Data'),
     ('UNAUTHORIZED', 'No Access'),
     ('WRITE_PRIVATE', 'Change Anything'),
     ('WRITE_PUBLIC', 'Change Non-Private Data')]

    >>> json_browser.open(
    ...     (
    ...         "http://launchpad.test/+authorize-token?%s"
    ...         "&allow_permission=READ_PRIVATE"
    ...     )
    ...     % urlencode(params)
    ... )
    >>> json_token = json.loads(json_browser.contents)
    >>> sorted(
    ...     (level["value"], level["title"])
    ...     for level in json_token["access_levels"]
    ... )
    [('READ_PRIVATE', 'Read Anything'),
     ('UNAUTHORIZED', 'No Access')]

Once the user authorizes the application to access Launchpad on their
behalf, we issue a redirect to the given oauth_callback (if it was
specified by the application).

    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> browser.getControl("Read Non-Private Data").click()

    # This is the URL given to Launchpad in oauth_callback.
    >>> browser.url
    'http://launchpad.test/bzr'

After the authorization is granted the token gets its permission and
person set.

    # Need to get the token again as it's been changed in another
    # transaction.
    >>> login(ANONYMOUS)
    >>> token = consumer.getRequestToken(token.key)
    >>> print(token.person.name)
    no-priv
    >>> token.permission
    <DBItem OAuthPermission.READ_PUBLIC...
    >>> token.is_reviewed
    True

If no oauth_callback is specified, we don't redirect the user.

    # Create a new (unreviewed) token.
    >>> token = request_token_for(consumer)

    >>> params = dict(oauth_token=token.key)
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )

    >>> browser.getControl("Read Anything").click()

    >>> browser.url
    'http://launchpad.test/+authorize-token'
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    To finish authorizing the application identified as foobar123451432 to
    access Launchpad on your behalf you should go back to the application
    window in which you started the process and inform it that you have done
    your part of the process.
    See all applications authorized to access Launchpad on your behalf.

If we can't find the request token (possibly because it was already
exchanged for an access token), we will explain that to the user.

    >>> params = dict(oauth_callback="http://example.com/oauth")
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Unable to identify application
    The information provided by the remote application was incorrect or
    incomplete. Because of that we were unable to identify the application
    which would access Launchpad on your behalf.
    You may have already authorized this application.
    See all applications authorized to access Launchpad on your behalf.

    >>> params = dict(
    ...     oauth_token="zzzzzz", oauth_callback="http://example.com/oauth"
    ... )
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Unable to identify application
    The information provided by the remote application was incorrect or
    incomplete. Because of that we were unable to identify the application
    which would access Launchpad on your behalf.
    You may have already authorized this application.
    See all applications authorized to access Launchpad on your behalf.

If the token is already reviewed (perhaps by the same user in another
window or tab), but has not yet been exchanged for an access token,
the success message is printed.

    # Need to get the token again as it's been changed in another
    # transaction.
    >>> token = consumer.getRequestToken(token.key)
    >>> token.is_reviewed
    True
    >>> params = dict(
    ...     oauth_token=token.key, oauth_callback="http://example.com/oauth"
    ... )
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    To finish authorizing the application identified as foobar123451432
    ...
    See all applications authorized to access Launchpad on your behalf.

If the token has expired, we notify the user, and inhibit the callback.

    >>> token = request_token_for(consumer)
    >>> from datetime import datetime, timedelta, timezone
    >>> from zope.security.proxy import removeSecurityProxy
    >>> date_created = datetime.now(timezone.utc) - timedelta(hours=3)
    >>> removeSecurityProxy(token).date_created = date_created
    >>> params = dict(
    ...     oauth_token=token.key, oauth_callback="http://example.com/oauth"
    ... )
    >>> browser.open(
    ...     "http://launchpad.test/+authorize-token?%s" % urlencode(params)
    ... )
    >>> browser.getControl("Read Anything").click()
    >>> browser.url
    'http://launchpad.test/+authorize-token'
    >>> [tag] = find_tags_by_class(browser.contents, "error message")
    >>> print(extract_text(tag))
    This request token has expired and can no longer be reviewed.

Desktop integration
===================

The test case given above shows how to integrate a single application
or website into Launchpad. But it's also possible to integrate an
entire desktop environment into Launchpad.

The desktop integration option is only available for OAuth consumers
that say what kind of desktop they are (eg. Ubuntu) and give a name
that a user can identify with their computer (eg. the hostname). Here,
we'll create such a consumer, and then a request token for that consumer.

    >>> login("foo.bar@canonical.com")
    >>> consumer = factory.makeOAuthConsumer(
    ...     "System-wide: Ubuntu (mycomputer)"
    ... )
    >>> logout()

    >>> token = request_token_for(consumer)

When a desktop tries to integrate with Launchpad, the user gets a
special warning about giving access to every program running on their
desktop.

    >>> params = dict(oauth_token=token.key)
    >>> print(
    ...     extract_text(
    ...         authorize_token_main_content(
    ...             "allow_permission=DESKTOP_INTEGRATION"
    ...         )
    ...     )
    ... )
    Authorize application to access Launchpad on your behalf
    Confirm Computer Access
    The Ubuntu computer called mycomputer wants access to your
    Launchpad account. If you allow this, every application running on
    mycomputer will have read-write access to your Launchpad account,
    including to your private data.
    If you're using a public computer, if mycomputer is not the
    computer you're using right now, or if something just doesn't feel
    right about this situation, you should choose "Do Not Allow
    'mycomputer' to Access my Launchpad Account", or close this window
    now. You can always try again later.
    Even if you decide to give mycomputer access to your Launchpad
    account, you can change your mind later.
    Allow mycomputer to access my Launchpad account:
    or
    See all applications authorized to access Launchpad on your behalf.

The only time the 'Desktop Integration' permission shows up in the
list of permissions is if the client specifically requests it, and no
other permission. (Also requesting UNAUTHORIZED is okay--it will show
up anyway.)

    >>> allow_desktop = "allow_permission=DESKTOP_INTEGRATION"
    >>> print_access_levels_for(allow_desktop)
    Until I Disable It
    For One Hour
    For One Day
    For One Week
    Do Not Allow "mycomputer" to Access my Launchpad Account.

    >>> print_access_levels_for(
    ...     "allow_permission=DESKTOP_INTEGRATION&"
    ...     "allow_permission=UNAUTHORIZED"
    ... )
    Until I Disable It
    For One Hour
    For One Day
    For One Week
    Do Not Allow "mycomputer" to Access my Launchpad Account.

A desktop may not request a level of access other than
DESKTOP_INTEGRATION, since the whole point is to have a permission
level that specifically applies across the entire desktop.

    >>> print_access_levels_for("allow_permission=WRITE_PRIVATE")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: Desktop integration token
    requested a permission ("Change Anything") not supported for
    desktop-wide use.

    >>> print_access_levels_for(
    ...     "allow_permission=WRITE_PUBLIC&" + allow_desktop
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: Desktop integration token
    requested a permission ("Change Non-Private Data") not supported for
    desktop-wide use.

You can't specify a callback URL when authorizing a desktop-wide
token, since callback URLs should only be used when integrating
websites into Launchpad.

    >>> params["oauth_callback"] = "http://launchpad.test/bzr"
    >>> print_access_levels_for(allow_desktop)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: A desktop integration may not
    specify an OAuth callback URL.

This is true even if the desktop token isn't asking for the
DESKTOP_INTEGRATION permission.

    >>> print_access_levels_for("allow_permission=WRITE_PRIVATE")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: A desktop integration may not
    specify an OAuth callback URL.

    >>> del params["oauth_callback"]

Accepting full integration
--------------------------

Now let's create a helper function to go through the entire desktop
integration process, given the name of the desktop and the level of
integration desired.

    >>> def integrate_desktop(button_to_click):
    ...     """Authorize (or don't) a desktop integration request token.
    ...     The token is authorized for the computer "mycomputer".
    ...
    ...     :return: the IOAuthRequestToken, possibly authorized.
    ...     """
    ...     token = request_token_for(consumer)
    ...     params["oauth_token"] = token.key
    ...     authorize_token_browser(allow_desktop)
    ...     button = browser.getControl(button_to_click)
    ...     button.click()
    ...     return token
    ...

If the client chooses a permanent desktop integration, the request
token is approved and has no expiration date.

    >>> token = integrate_desktop("Until I Disable It")
    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    The Ubuntu computer called mycomputer now has access to your
    Launchpad account. Within a few seconds, you should be able to
    start using its Launchpad integration features.
    See all applications authorized to access Launchpad on your behalf.

    >>> print(token.is_reviewed)
    True
    >>> print(token.permission.name)
    DESKTOP_INTEGRATION
    >>> print(token.date_expires)
    None

Accepting time-limited integration
----------------------------------

If you allow integration for a limited time, the request token is
reviewed and given an expiration date. Here, we authorize a token for
one hour.

    >>> token = integrate_desktop("For One Hour")

    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    The Ubuntu computer called mycomputer now has access to your
    Launchpad account. Within a few seconds, you should be able to
    start using its Launchpad integration features.
    The integration you just authorized will expire in 59 minutes. At
    that time, you'll have to re-authorize mycomputer, if you want to
    keep using its Launchpad integration features.
    See all applications authorized to access Launchpad on your behalf.

    >>> print(token.is_reviewed)
    True
    >>> print(token.permission.name)
    DESKTOP_INTEGRATION
    >>> token.date_expires is None
    False

Note that a single computer (in this case "mycomputer") may have more
than one desktop integration token. This is because there's no way to
know that a user hasn't given more than one computer the same name
(eg. "ubuntu" or "localhost"). The assignment of computer names to
integration tokens is a useful convention, not something we try to
enforce.

Here we authorize a token for one day.

    >>> token = integrate_desktop("For One Day")

    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    The integration you just authorized will expire in 23 hours.
    ...

    >>> print(token.is_reviewed)
    True
    >>> token.date_expires is None
    False

Here, we authorize a token for a week. The expiration time is given as
a date.

    >>> token = integrate_desktop("For One Week")

    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    Almost finished ...
    The integration you just authorized will expire 2...
    ...

    >>> print(token.is_reviewed)
    True
    >>> print(token.permission.name)
    DESKTOP_INTEGRATION
    >>> token.date_expires is None
    False

Declining integration
---------------------

If the client declines integration, the request token is reviewed but
cannot be exchanged for an access token.

    >>> token = integrate_desktop(
    ...     """Do Not Allow "mycomputer" to Access my Launchpad Account."""
    ... )

    >>> print(extract_text(find_tag_by_id(browser.contents, "maincontent")))
    Authorize application to access Launchpad on your behalf
    You decided against desktop integration
    You decided not to give mycomputer access to your Launchpad
    account. You can always change your mind later.
    See all applications authorized to access Launchpad on your behalf.

    >>> print(token.is_reviewed)
    True
    >>> print(token.permission.name)
    UNAUTHORIZED
