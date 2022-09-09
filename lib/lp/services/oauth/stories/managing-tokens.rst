Managing OAuth access tokens
============================

All access tokens and request tokens for a given user can be seen
and/or revoked from that user's +oauth-tokens page.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.webapp.interfaces import OAuthPermission

    # Create a desktop integration token.
    >>> login("salgado@ubuntu.com")
    >>> consumer = factory.makeOAuthConsumer(
    ...     "System-wide: Ubuntu (mycomputer)"
    ... )
    >>> salgado = getUtility(IPersonSet).getByName("salgado")
    >>> desktop_token, _ = factory.makeOAuthAccessToken(
    ...     consumer, salgado, OAuthPermission.DESKTOP_INTEGRATION
    ... )

    # Create a request token, authorize it for READ_PRIVATE access,
    # but don't exchange it for an access token.
    >>> consumer = factory.makeOAuthConsumer(
    ...     "Example consumer for READ_PRIVATE"
    ... )
    >>> request_token = factory.makeOAuthRequestToken()
    >>> request_token.review(salgado, OAuthPermission.READ_PRIVATE)
    >>> logout()

    # View the tokens.
    >>> my_browser = setupBrowser(auth="Basic salgado@ubuntu.com:test")
    >>> my_browser.open("http://launchpad.test/~salgado/+oauth-tokens")
    >>> print(my_browser.title)
    Authorized applications...
    >>> main_content = find_tag_by_id(my_browser.contents, "maincontent")
    >>> print(extract_text(main_content))
    Authorized applications
    ...
    Claimed tokens:
    Application name: System-wide: Ubuntu (mycomputer)
    Authorized...to integrate an entire system
    Application name: foobar123451432
    Authorized...to read non-private data
    Application name: launchpad-library
    Authorized...to change anything
    Unclaimed tokens:
    Application name: oauthconsumerkey...
    Authorized...to read anything
    Must be claimed before

For each token we have a separate <form> with the token and consumer
keys stored in hidden <input>s as well as the button to revoke the
authorization.

    >>> li = find_tag_by_id(main_content, "tokens").find("li")
    >>> for input in li.find("form").find_all("input"):
    ...     print(input["name"], input["value"])
    ...
    consumer_key System-wide: Ubuntu (mycomputer)
    token_key ...
    token_type access_token
    revoke Revoke Authorization

    >>> li2 = li.find_next_sibling("li")
    >>> for input in li2.find("form").find_all("input"):
    ...     print(input["name"], input["value"])
    ...
    consumer_key foobar123451432
    token_key salgado-read-nonprivate
    token_type access_token
    revoke Revoke Authorization

    >>> li3 = li2.find_next("li")
    >>> for input in li3.find("form").find_all("input"):
    ...     print(input["name"], input["value"])
    ...
    consumer_key launchpad-library
    token_key salgado-change-anything
    token_type access_token
    revoke Revoke Authorization

    >>> li4 = li3.find_next("li")
    >>> for input in li4.find("form").find_all("input"):
    ...     print(input["name"], input["value"])
    ...
    consumer_key oauthconsumerkey...
    token_key ...
    token_type request_token
    revoke Revoke Authorization

If a token is revoked the application will not be able to access
Launchpad on that user's behalf anymore, nor will that application be
shown as one of the authorized ones.

    >>> my_browser.getControl("Revoke Authorization", index=2).click()
    >>> print(my_browser.title)
    Authorized applications...
    >>> print_feedback_messages(my_browser.contents)
    Authorization revoked successfully.

    >>> my_browser.open("http://launchpad.test/~salgado/+oauth-tokens")
    >>> print(
    ...     extract_text(find_tag_by_id(my_browser.contents, "maincontent"))
    ... )
    Authorized applications
    ...
    Claimed tokens:
    Application name: System-wide: Ubuntu (mycomputer)
    Authorized...to integrate an entire system
    Application name: foobar123451432
    Authorized...to read non-private data
    Unclaimed tokens:
    Application name: oauthconsumerkey...
    Authorized...to read anything
    Must be claimed before

Some tokens grant access only to a certain context in Launchpad.  If
that's the case, the description of the authorization granted will
include that.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.services.oauth.interfaces import IOAuthConsumerSet
    >>> login("salgado@ubuntu.com")
    >>> token, _ = (
    ...     getUtility(IOAuthConsumerSet)
    ...     .getByKey("launchpad-library")
    ...     .newRequestToken()
    ... )
    >>> token.review(
    ...     salgado,
    ...     OAuthPermission.WRITE_PUBLIC,
    ...     context=getUtility(IProductSet)["firefox"],
    ... )
    >>> access_token, _ = token.createAccessToken()
    >>> logout()
    >>> my_browser.open("http://launchpad.test/~salgado/+oauth-tokens")
    >>> print(
    ...     extract_text(find_tag_by_id(my_browser.contents, "maincontent"))
    ... )
    Authorized applications
    ...
    launchpad-library
    ...
    to change non-private data related to Mozilla Firefox
    ...

That page is protected with the launchpad.Edit permission, for obvious
reasons, so users can only access their own.

    >>> user_browser.open("http://launchpad.test/~salgado/+oauth-tokens")
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...launchpad.Edit...
