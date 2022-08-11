Language Pack storage
=====================

A LanguagePack represents an exported distribution series' language pack.

A LanuagePack is either a FULL or DELTA export.  If the LanguagePack is a
DELTA, there is also a reference to the related FULL LanguagePack.

A DELTA language pack is an export that has all translation resources that
were updated since the export date for the associate FULL export.

    >>> import io
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.translations.enums import LanguagePackType
    >>> from lp.translations.interfaces.languagepack import (
    ...     ILanguagePack,
    ...     ILanguagePackSet)
    >>> from lp.testing import verifyObject
    >>> from lp.services.librarian.interfaces.client import ILibrarianClient

Let's upload a dummy file to librarian.

    >>> uploader = getUtility(ILibrarianClient)
    >>> content = b'foo'
    >>> file_alias = uploader.addFile(
    ...     name='foo.tar.gz',
    ...     size=len(content),
    ...     file=io.BytesIO(content),
    ...     contentType='application/x-gtar')

We need too a distribution series to link the language pack with it.

    >>> ubuntu = getUtility(IDistributionSet)['ubuntu']
    >>> hoary = ubuntu.getSeries('hoary')

We add the language pack.

    >>> language_pack_set = getUtility(ILanguagePackSet)
    >>> language_pack = language_pack_set.addLanguagePack(
    ...     hoary, file_alias, LanguagePackType.FULL)

And it implements and follow the ILanguagePack interface.

    >>> verifyObject(ILanguagePack, language_pack)
    True
