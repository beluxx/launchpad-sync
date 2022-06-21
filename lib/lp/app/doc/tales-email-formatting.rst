TALES email formatting
======================

There are many edge-cases when marking up email text for presentation.
There is subtle differences in how people quote text that must be
handled properly. There are also cases were content may look like
quoted text, but it is not.

See 'The fmt: namespace to get strings (hiding)' in tales.rst for
the common use cases.

First, let's bring in a small helper function:

    >>> from lp.testing import test_tales

Quoting styles
--------------

Paragraphs that mix quoted and reply text fold only the quoted lines.

    >>> mixed_quoted_text = ('Mister X wrote:\n'
    ...                      '> This is a quoted line\n'
    ...                      'This is a reply to the line above.\n'
    ...                      'This is a continuation line.'
    ...                      '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=mixed_quoted_text))
    <p>Mister X wrote:<br />
    <span class="foldable-quoted">
    &gt; This is a quoted line<br />
    </span>
    This is a reply to the line above.<br />
    This is a continuation line.</p>

A quoted section is folded without affecting the display of the
surrounding paragraph, even if there are no blank lines to separate
the quoted section from the paragraph.

    >>> quoted_remark_text = ('Attribution line\n'
    ...                       '> quoted_line\n'
    ...                       'Remark line.\n'
    ...                       '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=quoted_remark_text))
    <p>Attribution line<br />
    <span class="foldable-quoted">
    &gt; quoted_line<br />
    </span>
    Remark line.</p>

Multiple quoted paragraphs are treated as a single continuous folded
span.

    >>> quoted_paragraphs = ('Attribution line\n'
    ...                       '> First line in the first paragraph.\n'
    ...                       '> Second line in the first paragraph.\n'
    ...                       '> \n'
    ...                       '> First line in the second paragraph.\n'
    ...                       '> Second line in the second paragraph.\n'
    ...                       '> \n'
    ...                       '> First line in the third paragraph.\n'
    ...                       '> Second line in the third paragraph.\n'
    ...                       '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=quoted_paragraphs))
    <p>Attribution line<br />
    <span class="foldable-quoted">
    &gt; First line in the first paragraph.<br />
    &gt; Second line in the first paragraph.<br />
    &gt;<br />
    &gt; First line in the second paragraph.<br />
    &gt; Second line in the second paragraph.<br />
    &gt;<br />
    &gt; First line in the third paragraph.<br />
    &gt; Second line in the third paragraph.
    </span></p>

Paragraphs with nested quoting fold all the quoted lines. There
is no distinction between the nested levels of quoting.

    >>> nested_quoting = ('>>>> four\n'
    ...                   '>>> three\n'
    ...                   '>> two\n'
    ...                   '> one\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=nested_quoting))
    <p><span class="foldable-quoted">&gt;&gt;&gt;&gt; four<br />
    &gt;&gt;&gt; three<br />
    &gt;&gt; two<br />
    &gt; one
    </span></p>

Quoting styles vary between email clients, and how the user starts the
quote. Starting runs like '>> ' are as valid as '> ', so they are
wrapped in a foldable-quoted span.

    >>> weird_quoted_text = ('Ms. Y wrote:\n'
    ...                      '>> This is a double quoted line\n'
    ...                      '>> > This is a triple quoted line.\n'
    ...                      '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=weird_quoted_text))
    <p>Ms. Y wrote:<br />
    <span class="foldable-quoted">
    &gt;&gt; This is a double quoted line<br />
    &gt;&gt; &gt; This is a triple quoted line.
    </span></p>


Python interpreter and dpkg handling
------------------------------------

The output from the Python interpreter is not quoted text. Passages
of text that start with '>>> ' are exempted from the 'foldable-quoted'
rules. Note that when '>>> ' occurs inside an existing quoted passage
it will be folded because they are a continuation of a quote (see
the preceding nested quoting test).
# Passages may be wrongly be interpreted as Python because they start
# with '>>> '. The formatter does not check that next and previous
# lines of text consistently uses '>>> ' as Python would.

    >>> python = ('>>> tz = pytz.timezone("Asia/Calcutta")\n'
    ...           '>>> mydate = datetime.datetime(2007, 2, 18, 15, 35)\n'
    ...           '>>> print(tz.localize(mydate))\n'
    ...           '2007-02-18 15:35:00+05:30\n'
    ...           '\n')
    >>> not_python = ('> This line really is a quoted passage.\n'
    ...               '>>> This does not invoke an exception rule.\n'
    ...               '\n')
    >>> print(test_tales('foo/fmt:email-to-html',
    ...                  foo='\n'.join([python, not_python])))
    <p>&gt;&gt;&gt; tz = pytz.timezone(<wbr />&quot;Asia/Calcutta&quot;...
    &gt;&gt;&gt; mydate = datetime.<wbr />datetime(<wbr />2007, 2, ...
    2007-02-18 15:35:00+05:30</p>
    <p><span class="foldable-quoted">&gt; This line really is a quoted ...
    &gt;&gt;&gt; This does not invoke an exception rule.
    </span></p>

Dpkg generates lines that start with a '|' that will be confused with
quoted text. Dpkg is common in messages, and when it is, we do not
fold lines that start with a '|'. We sometimes receive bad dpkg output
where the lines are broken, and we must take care to identify that
output and not fold it.

    >>> bar_quoted_text = ('Someone said sometime ago:\n'
    ...                    '| Quote passages are folded.\n'
    ...                    '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=bar_quoted_text))
    <p>Someone said sometime ago:<br />
    <span class="foldable-quoted">
    | Quote passages are folded.
    </span></p>

    >>> dpkg = ('dpkg -l libdvdread3\n'
    ...         'Desired=Unknown/Install/Remove/Purge/Hold\n'
    ...         '| Status=Not/Installed/Config-files/Unpacked/Failed-co\n'
    ...         '|/ Err?=(none)/Hold/Reinst-required/X=both-problems\n'
    ...         '||/ Name Version Description\n'
    ...         '+++-==============-==============-====================\n'
    ...         'ii libdvdread3 0.9.7-2ubuntu1 library for reading DVDs\n'
    ...         '\n')
    >>> print(test_tales('foo/fmt:email-to-html', foo=dpkg))
    <p>dpkg -l libdvdread3<br />
    Desired=<wbr />Unknown/<wbr />Install/<wbr />...
    | Status=<wbr />Not/Installed/<wbr />Config-<wbr />...
    |/ Err?=(none)<wbr />/Hold/Reinst-<wbr />required/...
    ||/ Name Version Description<br />
    +++-===<wbr />=======<wbr />====-==<wbr />=======...
    ii libdvdread3 0.9.7-2ubuntu1 library for reading DVDs</p>

    >>> bad_dpkg = ('When dpkg output is in text, possibly tampered with,\n'
    ...             "we must take care to identify '|' quoted passages.\n"
    ...             '$ Desired=Unknown/Install/Remove/Purge/Hold\n'
    ...             '|\n'
    ...             ' Status=Not/Installed/Config-files/Unpacked/Failed-co\n'
    ...             '|/ Err?=(none)/Hold/Reinst-required/X=both-problems\n'
    ...             '||/ Name Version Description\n'
    ...             '+++-==============-==============-==================\n'
    ...             'ii libdvdread3 0.9.7-2ubuntu1 library for reading DVDs\n'
    ...             '\n')
    >>> print(test_tales('foo/fmt:email-to-html',
    ...                  foo='\n'.join([bad_dpkg])))
    <p>When dpkg output is in text, possibly tampered with,<br />
    we must take care to identify &#x27;|&#x27; quoted passages.<br />
    $ Desired=<wbr />Unknown/<wbr />Install/<wbr />Remove/...
    |<br />
    &nbsp;Status=<wbr />Not/Installed/<wbr />Config-...
    |/ Err?=(none)<wbr />/Hold/Reinst-<wbr />required/...
    ||/ Name Version Description<br />
    +++-===<wbr />=======<wbr />====-==<wbr />=======...
    ii libdvdread3 0.9.7-2ubuntu1 library for reading DVDs</p>

