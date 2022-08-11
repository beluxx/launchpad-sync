Imports and setup of stub keyserver:

    >>> from zope.component import getUtility
    >>> from lp.services.verification.interfaces.authtoken import (
    ...     LoginTokenType)
    >>> from lp.testing import login, logout, ANONYMOUS
    >>> from lp.services.verification.interfaces.logintoken import (
    ...     ILoginTokenSet)
    >>> from lp.testing.keyserver import KeyServerTac
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.testing.pages import setupBrowserFreshLogin

    >>> tokenset = getUtility(ILoginTokenSet)
    >>> tac = KeyServerTac()
    >>> tac.setUp()

The following keys are used in these tests:

  pub   1024D/AACCD97C 2005-10-12 [revoked: 2005-10-12]
        Key fingerprint = 84D2 05F0 3E1E 6709 6CB5  4E26 2BE8 3793 AACC D97C
  uid                  Revoked Key <revoked.key@canonical.com>

  pub   1024D/02F53CC6 2005-10-12 [expires: 2005-10-13]
        Key fingerprint = 0DD6 4D28 E5F4 1138 5334  9520 0E3D B4D4 02F5 3CC6
  uid                  Expired Key <expired.key@canonical.com>
  sub   1024g/86163BC7 2005-10-12 [expires: 2005-10-13]


Attempts to claim a revoked OpenPGP key fail:

    >>> login(ANONYMOUS)
    >>> name12 = getUtility(IPersonSet).getByEmail('test@canonical.com')
    >>> logout()
    >>> browser = setupBrowserFreshLogin(name12)
    >>> browser.open('http://launchpad.test/~name12/+editpgpkeys')
    >>> browser.getControl(
    ...     name='fingerprint').value = (
    ...     '84D205F03E1E67096CB54E262BE83793AACCD97C')
    >>> browser.getControl('Import Key').click()
    >>> for tag in find_tags_by_class(browser.contents, 'error message'):
    ...     print(tag.decode_contents())
    <BLANKLINE>
    The key 84D205F03E1E67096CB54E262BE83793AACCD97C cannot be validated
    because it has been publicly revoked.
    You will need to generate a new key (using <kbd>gpg --genkey</kbd>) and
    repeat the process to import it.
    <BLANKLINE>


Attempts to claim an expired OpenPGP key also fail:

    >>> browser.getControl(
    ...     name='fingerprint').value = (
    ...     '0DD64D28E5F41138533495200E3DB4D402F53CC6')
    >>> browser.getControl('Import Key').click()
    >>> for tag in find_tags_by_class(browser.contents, 'error message'):
    ...     print(tag.decode_contents())
    <BLANKLINE>
    The key 0DD64D28E5F41138533495200E3DB4D402F53CC6 cannot be validated
    because it has expired. Change the expiry date (in a terminal, enter
    <kbd>gpg --edit-key <var>your@email.address</var></kbd> then enter
    <kbd>expire</kbd>), and try again.
    <BLANKLINE>


It is possible for a key to be revoked or expire between the time it
is claimed and the time the claim is verified.  Therefore, it is
necessary to check the validity at that point too.  To test this, we
will create login tokens for the revoked and expired test keys:

    >>> login(ANONYMOUS)
    >>> person = getUtility(IPersonSet).getByEmail('test@canonical.com')
    >>> logintoken = tokenset.new(
    ...     person, 'test@canonical.com', 'test@canonical.com',
    ...     LoginTokenType.VALIDATEGPG,
    ...     '84D205F03E1E67096CB54E262BE83793AACCD97C')
    >>> revoked_key_token = logintoken.token
    >>> logintoken = tokenset.new(
    ...     person, 'test@canonical.com', 'test@canonical.com',
    ...     LoginTokenType.VALIDATEGPG,
    ...     '0DD64D28E5F41138533495200E3DB4D402F53CC6')
    >>> expired_key_token = logintoken.token
    >>> logout()


Try to validate the revoked OpenPGP key:

    >>> browser.open(
    ...     'http://launchpad.test/token/%s/+validategpg' % revoked_key_token)
    >>> browser.getControl('Continue').click()
    >>> for tag in find_tags_by_class(browser.contents, 'error message'):
    ...     print(tag.decode_contents())
    There is 1 error.
    The key 84D205F03E1E67096CB54E262BE83793AACCD97C cannot be validated
    because it has been publicly revoked.
    You will need to generate a new key (using <kbd>gpg --genkey</kbd>) and
    repeat the previous process to
    <a href="http://launchpad.test/~name12/+editpgpkeys">find and import</a>
    the new key.


Try to validate the revoked OpenPGP key:

    >>> browser.open(
    ...     'http://launchpad.test/token/%s/+validategpg' % expired_key_token)
    >>> browser.getControl('Continue').click()
    >>> for tag in find_tags_by_class(browser.contents, 'error message'):
    ...     print(tag.decode_contents())
    There is 1 error.
    The key 0DD64D28E5F41138533495200E3DB4D402F53CC6 cannot be validated
    because it has expired. Change the expiry date (in a terminal, enter
    <kbd>gpg --edit-key <var>your@email.address</var></kbd> then enter
    <kbd>expire</kbd>), and try again.

The login tokens are only consumed if they're successfully processed.
Otherwise they're kept around so the user can try again after fixing their
key.

    >>> login(ANONYMOUS)
    >>> tokenset[revoked_key_token].date_consumed is not None
    False
    >>> tokenset[expired_key_token].date_consumed is not None
    False
    >>> logout()


    >>> tac.tearDown()

