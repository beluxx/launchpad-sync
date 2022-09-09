"Remove Translations By" script
===============================

Use scripts/remove-translations-by.py to delete selected
TranslationMessages from the database.  This is useful for mislicensed
translations, but also for ones submitted in the wrong language, or in
bad faith, or all messages in a specific POFile, and so on.

    >>> script = "scripts/rosetta/remove-translations-by.py"
    >>> login("foo.bar@canonical.com")

In this example, we have a template with Dutch and German translations.

    >>> nl_pofile = factory.makePOFile("nl")
    >>> potemplate = nl_pofile.potemplate
    >>> de_pofile = factory.makePOFile("de", potemplate=potemplate)
    >>> owner = potemplate.owner

    >>> def set_translation(message, pofile, text):
    ...     """Set text to be a translation for message in pofile."""
    ...     return factory.makeCurrentTranslationMessage(
    ...         pofile,
    ...         message,
    ...         pofile.potemplate.owner,
    ...         translations={0: text},
    ...     )
    ...

    >>> def print_pofile_contents(pofile):
    ...     """Return sorted list of (singular) translations in pofile."""
    ...     contents = sorted(
    ...         message.msgstr0.translation
    ...         for message in pofile.translation_messages
    ...         if message.msgstr0 is not None
    ...     )
    ...     for item in contents:
    ...         print(item)
    ...


== Running the script==

Most options that specify which messages to delete conjunctively
constrain the deletion.  In other words, add options to make the
deletion more specific.  In principle, passing no options at all would
mean "delete absolutely all TranslationMessages."

The "id" option may be repeated to specify the ids of multiple messages
to be deleted.  (But again, they are deleted only if they match all
criteria).

    >>> from lp.testing.script import run_script
    >>> from lp.translations.interfaces.translationmessage import (
    ...     RosettaTranslationOrigin,
    ... )
    >>> from storm.store import Store

    >>> message = factory.makePOTMsgSet(
    ...     potemplate, "My goose is undercooked.", sequence=0
    ... )

    >>> nl_message = set_translation(
    ...     message, nl_pofile, "Maar dan in het Nederlands."
    ... )
    >>> nl_message.is_current_upstream
    True
    >>> nl_message.is_current_ubuntu
    False
    >>> print(nl_message.potmsgset.msgid_singular.msgid)
    My goose is undercooked.
    >>> nl_message.origin == RosettaTranslationOrigin.ROSETTAWEB
    True

    >>> de_message = set_translation(
    ...     message, de_pofile, "Und jetzt auf deutsch."
    ... )
    >>> spare_message = factory.makePOTMsgSet(
    ...     potemplate, "Unrelated notice #931", sequence=0
    ... )
    >>> nl_spare = set_translation(spare_message, nl_pofile, "Bericht 931")
    >>> de_spare = set_translation(spare_message, de_pofile, "Nachricht 931")

    >>> print_pofile_contents(nl_pofile)
    Bericht 931
    Maar dan in het Nederlands.

    >>> print_pofile_contents(de_pofile)
    Nachricht 931
    Und jetzt auf deutsch.

    >>> options = [
    ...     "-v",
    ...     "--submitter=%s" % nl_message.submitter.id,
    ...     "--reviewer=%s" % nl_message.reviewer.id,
    ...     "--id=%s" % str(1),
    ...     "--id=%s" % str(nl_message.id),
    ...     "--id=%s" % str(2),
    ...     "--potemplate=%s" % str(potemplate.id),
    ...     "--not-language",
    ...     "--language=%s" % "de",
    ...     "--is-current-ubuntu=%s" % "false",
    ...     "--is-current-upstream=%s" % "true",
    ...     "--msgid=%s" % "My goose is undercooked.",
    ...     "--origin=%s" % "ROSETTAWEB",
    ...     "--force",
    ... ]

    >>> Store.of(potemplate).commit()
    >>> (returncode, out, err) = run_script(script, args=options)

    # We're going to inspect these POFiles later; make sure we're not
    # gazing at an old cached copy from before the removal.
    >>> Store.of(nl_pofile).flush()

    >>> returncode
    0

The long list of matching options we gave above indicated exactly 1
message.

    >>> print(err)
    WARNING Deleting messages currently in use:
    WARNING Message ... is a current translation in upstream
    DEBUG Sample of messages to be deleted follows.
    DEBUG   [message] [unmasks]
    DEBUG   ...       --
    INFO  Deleting 1 message(s).

Combining the --language-code option with --not-language inverts the
language match: delete messages in any language except the given one.
This can be useful in cases where files with the same translator are
uploaded for several incorrect languages.

In this case, the only other language to delete from is Dutch.  We see
the same messages as before, minus one Dutch one.

    >>> print_pofile_contents(nl_pofile)
    Bericht 931

    >>> print_pofile_contents(de_pofile)
    Nachricht 931
    Und jetzt auf deutsch.


Dry runs
--------

Deleting messages is scary.  You should not do it lightly.  The script
has a --dry-run option that stops it from committing its changes to the
database.

    >>> (returncode, out, err) = run_script(
    ...     script,
    ...     [
    ...         "-v",
    ...         "--potemplate=%s" % de_pofile.potemplate.id,
    ...         "--force",
    ...         "--dry-run",
    ...     ],
    ... )

    >>> returncode
    0

    >>> print(out)
    <BLANKLINE>

    >>> print(err)
    WARNING Safety override in effect.  Deleting translations for template ...
    INFO    Dry run only.  Not really deleting.
    WARNING Deleting messages currently in use:
    WARNING Message ... is a current translation in upstream
    WARNING Message ... is a current translation in upstream
    WARNING Message ... is a current translation in upstream
    DEBUG   Sample of messages to be deleted follows.
    DEBUG   [message] [unmasks]
    DEBUG   ...       --
    DEBUG   ...       --
    DEBUG   ...       --
    INFO    Deleting 3 message(s).

The "deleted" messages are still there.

    >>> print_pofile_contents(de_pofile)
    Nachricht 931
    Und jetzt auf deutsch.
