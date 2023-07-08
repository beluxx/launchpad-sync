destroySelf
===========

(Note: this test runs as rosettaadmin to obtain the necessary
privileges)

With this method, we allow to remove a submission, it comes from SQLObject,
but we test it here to be sure it appears in our public interface.

We will need extra permissions to use this method.

    >>> from lp.translations.model.translationmessage import (
    ...     TranslationMessage,
    ... )
    >>> from lp.testing.dbuser import switch_dbuser
    >>> switch_dbuser("rosettaadmin")

Select an existing ITranslationMessage and try to remove it.

    >>> translationmessage = TranslationMessage.get(1)
    >>> translationmessage.destroySelf()

It should not exist now.

    >>> translationmessage = TranslationMessage.get(1)
    Traceback (most recent call last):
    ...
    storm.sqlobject.SQLObjectNotFound: ...


POFileTranslator update on remove
=================================

In two sharing POTemplates with one shared POTMsgSet with one shared
translation, we get two POFileTranslator records for each of the POFiles.

    # We need to be able to create persons and projects so let's just use
    # a global 'postgres' permission which allows everything.
    >>> switch_dbuser("postgres")
    >>> from lp.services.database.interfaces import IStore
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.testing.factory import LaunchpadObjectFactory
    >>> from lp.translations.model.pofiletranslator import POFileTranslator
    >>> factory = LaunchpadObjectFactory()

    >>> foo = factory.makeProduct(translations_usage=ServiceUsage.LAUNCHPAD)
    >>> foo_devel = factory.makeProductSeries(name="devel", product=foo)
    >>> foo_stable = factory.makeProductSeries(name="stable", product=foo)
    >>> devel_potemplate = factory.makePOTemplate(
    ...     productseries=foo_devel, name="messages"
    ... )
    >>> stable_potemplate = factory.makePOTemplate(
    ...     foo_stable, name="messages"
    ... )
    >>> devel_sr_pofile = factory.makePOFile("sr", devel_potemplate)
    >>> stable_sr_pofile = factory.makePOFile("sr", stable_potemplate)
    >>> potmsgset = factory.makePOTMsgSet(devel_potemplate, sequence=1)
    >>> item = potmsgset.setSequence(stable_potemplate, 1)
    >>> tm = factory.makeCurrentTranslationMessage(
    ...     pofile=devel_sr_pofile, potmsgset=potmsgset, translations=["blah"]
    ... )
    >>> print(
    ...     IStore(POFileTranslator)
    ...     .find(
    ...         POFileTranslator,
    ...         POFileTranslator.pofile_id.is_in(
    ...             (devel_sr_pofile.id, stable_sr_pofile.id)
    ...         ),
    ...     )
    ...     .count()
    ... )
    2
