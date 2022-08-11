Template export sets
====================

POTemplate.getTranslationRows serialises a template's rows for export.

    >>> from lp.translations.model.potemplate import POTemplate

We need a template to export, for instance, the one with id = 1.

    >>> potemplate = POTemplate.get(1)
    >>> vpot_rows = list(potemplate.getTranslationRows())

There are rows.

    >>> len(vpot_rows) > 0
    True


Template export set entry
=========================

VPOTExport represent a row for an entry in the POTemplate. Each row has
the following information, among other things:

 * potemplate: Template which this row is for.
 * template_header: The template header.
 * sequence: The order in which this row's message appears inside the
       exported file.
 * context: Context text for the message represented in this row.
 * msgid_singular: The message to translate in this row (in the singular).

 And some metadata information:

 * comment
 * source_comment
 * file_references
 * flags_comment

Get the first row from the set. It represents the first message of the
template.

    >>> first = vpot_rows[0]

We are working with the evolution-2.2 template.

    >>> print(first.potemplate.title)
    Template "evolution-2.2" in Evolution trunk

And this first row has the information for the 'Found %i invalid file.'
message.

    >>> print(first.msgid_singular)
    Found %i invalid file.

    # We will need the potmsgset of this message to demonstrate the values
    # we get.
    >>> potmsgset = first.potemplate.getPOTMsgSetByMsgIDText(
    ...     u'Found %i invalid file.', u'Found %i invalid files.')

The sequence specifies the ordering of the message represented by this row in
the template it belongs to. In this case, it's zero, which means it shouldn't
appear in the exported file.

    >>> first.sequence
    0
    >>> potmsgset.getSequence(first.potemplate)
    0

The POT file header is a template of common information that will get filled
in with language specifics by translators.

    >>> print(first.template_header)
    Project-Id-Version: PACKAGE VERSION
    Report-Msgid-Bugs-To:
    POT-Creation-Date: 2005-08-25 14:56+0200
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=CHARSET
    Content-Transfer-Encoding: 8bit
    Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;

Each message could have a singular form (identified by the index 0) and a
plural form (identified by the index 1). In this case, the message has both.

    >>> first.msgid_singular is None
    False
    >>> first.msgid_plural is None
    False

Comment text is a comment added by a translator.

    >>> print(first.comment)
    <BLANKLINE>
    >>> print(potmsgset.commenttext)
    <BLANKLINE>

Source comment is the comment added by a developer to help translators
to understand the message they are translating.

    >>> print(first.source_comment)
    <BLANKLINE>
    >>> print(potmsgset.sourcecomment)
    <BLANKLINE>

File references is a reference to the source code file and line number where
this message was extracted from.

    >>> print(first.file_references)
    encfs/encfsctl.cpp:346
    >>> print(potmsgset.filereferences)
    encfs/encfsctl.cpp:346

flags comment represent a set of flags used to validate the message
translation.

    >>> print(first.flags_comment)
    c-format
    >>> print(potmsgset.flagscomment)
    c-format
