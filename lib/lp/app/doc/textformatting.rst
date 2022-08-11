Formatting text in Python
=========================

Wrapping multi-paragraph text in emails
---------------------------------------

So, textwrap has this little problem. The problem is that the two
helper functions it currently exports, wrap() and fill() expect their
argument to be one paragraph of text. If you try to pass a
multi-paragraph string to one of these functions, you may well be
unplesantly surprised at the result.

As a solution to this, we imported contrib.docwrapper.DocWrapper
from the Python Cookbook. DocWrapper knows how to wrap multi-paragraph
text. It turned out that it did a bad job wrapping text that originated
from emails, where some lines already are wrapped, and some lines are
expected not to be wrapped at all. So instead we wrote our own text
wrapper, MailWrapper. MailWrapper doesn't provide all functionality
that DocWrapper or TextWrapper do, instead it's designed to handle only
our use cases.

So, with textwrap:

    >>> import textwrap
    >>> description = (
    ...     "A new description that is quite long. But the nice thing is "
    ...     "that the edit notification email generator knows how to indent "
    ...     "and wrap descriptions, so this will appear quite nice in the "
    ...     "actual email that gets sent.\n\n"
    ...     "It's also smart enough to preserve whitespace, finally!")
    >>> wrapped_description = textwrap.fill(description, width=56)
    >>> print(wrapped_description)  #doctest: -NORMALIZE_WHITESPACE
    A new description that is quite long. But the nice thing
    is that the edit notification email generator knows how
    to indent and wrap descriptions, so this will appear
    quite nice in the actual email that gets sent.  It's
    also smart enough to preserve whitespace, finally!


Note in the above example that the "...gets sent.\n\nit's..." got
squished into being on the same line, which is obviously not what
we want.

MailWrapper to the rescue!

    >>> from lp.services.mail.mailwrapper import MailWrapper
    >>> mailwrapper = MailWrapper(width=56)
    >>> print(mailwrapper.format(description)) #doctest: -NORMALIZE_WHITESPACE
    A new description that is quite long. But the nice thing
    is that the edit notification email generator knows how
    to indent and wrap descriptions, so this will appear
    quite nice in the actual email that gets sent.
    <BLANKLINE>
    It's also smart enough to preserve whitespace, finally!


Note how the paragraph that begins after "...email that gets sent." is
preserved.

Let's just make sure that it handles a single paragraph as well.

    >>> single_paragraph = (
    ...     "A new description that is quite long. But the nice thing is "
    ...     "that the edit notification email generator knows how to indent "
    ...     "and wrap descriptions, so this will appear quite nice in the "
    ...     "actual email that gets sent.")
    >>> wrapped_text = mailwrapper.format(single_paragraph)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    A new description that is quite long. But the nice thing
    is that the edit notification email generator knows how
    to indent and wrap descriptions, so this will appear
    quite nice in the actual email that gets sent.


It also handles text where all the lines are of the proper length
already.

    >>> already_wrapped = """\
    ... This paragraph contains only lines that are less than 56
    ... characters. It shouldn't be wrapped.
    ... """
    >>> wrapped_text = mailwrapper.format(already_wrapped)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    This paragraph contains only lines that are less than 56
    characters. It shouldn't be wrapped.


Text where the lines are of proper length, and one empty line consisting
of spaces:

    >>> already_wrapped = """\
    ... This paragraph contains only lines that are less than 56
    ... characters.
    ... """ + "     " + """
    ... It shouldn't be wrapped.
    ... """
    >>> wrapped_text = mailwrapper.format(already_wrapped)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    This paragraph contains only lines that are less than 56
    characters.
    <BLANKLINE>
    It shouldn't be wrapped.


Sometimes when replies get quoted, the lines get longer than the
allowed length. These shouldn't be wrapped.

    >>> long_quoted_lines = """\
    ... > > > > > Someone wrote this a long time ago. When it was written
    ... > > > > > all lines were less than 56 characters, but now they are
    ... > > > > > longer.
    ...
    ... This is a reply to the line above.
    ... """
    >>> wrapped_text = mailwrapper.format(long_quoted_lines)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    > > > > > Someone wrote this a long time ago. When it was written
    > > > > > all lines were less than 56 characters, but now they are
    > > > > > longer.
    <BLANKLINE>
    This is a reply to the line above.


Let's see how it behaves when it contains words that can't fit on a
single line, such as URLs.

    >>> long_word = (
    ...     "This paragraph includes a long URL, "
    ...     "https://launchpad.net/greenishballoon/+bug/1733/+subscriptions. "
    ...     "Even though it's longer than 56 characters, it stays on a "
    ...     "single line.")
    >>> wrapped_text = mailwrapper.format(long_word)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    This paragraph includes a long URL,
    https://launchpad.net/greenishballoon/+bug/1733/+subscriptions.
    Even though it's longer than 56 characters, it stays on
    a single line.


It preserves whitespace in the beginning of the line.

    >>> ascii_cow = r"""
    ...                                               /;    ;\
    ...                                           __  \\____//
    ...                                          /{_\_/   `'\____
    ...                                          \___   (o)  (o  }
    ...               _____________________________/          :--'
    ...           ,-,'`@@@@@@@@       @@@@@@         \_    `__\
    ...          ;:(  @@@@@@@@@        @@@             \___(o'o)
    ...          :: )  @@@@          @@@@@@        ,'@@(  `===='
    ...          :: : @@@@@:          @@@@         `@@@:
    ...          :: \  @@@@@:       @@@@@@@)    (  '@@@'
    ...          ;; /\      /`,    @@@@@@@@@\   :@@@@@)
    ...          ::/  )    {_----------------:  :~`,~~;
    ...         ;;'`; :   )                  :  / `; ;
    ...        ;;;; : :   ;                  :  ;  ; :
    ...        `'`' / :  :                   :  :  : :
    ...            )_ \__;      ";"          :_ ;  \_\       `,','
    ...            :__\  \    * `,'*         \  \  :  \   *  8`;'*  *
    ...                `^'     \ :/           `^'  `-^-'   \v/ :  \/
    ... """
    >>> wrapped_text = mailwrapper.format(ascii_cow)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    <BLANKLINE>
                                                  /;    ;\
                                              __  \\____//
                                             /{_\_/   `'\____
                                             \___   (o)  (o  }
                  _____________________________/          :--'
              ,-,'`@@@@@@@@       @@@@@@         \_    `__\
             ;:(  @@@@@@@@@        @@@             \___(o'o)
             :: )  @@@@          @@@@@@        ,'@@(  `===='
             :: : @@@@@:          @@@@         `@@@:
             :: \  @@@@@:       @@@@@@@)    (  '@@@'
             ;; /\      /`,    @@@@@@@@@\   :@@@@@)
             ::/  )    {_----------------:  :~`,~~;
            ;;'`; :   )                  :  / `; ;
           ;;;; : :   ;                  :  ;  ; :
           `'`' / :  :                   :  :  : :
               )_ \__;      ";"          :_ ;  \_\       `,','
               :__\  \    * `,'*         \  \  :  \   *  8`;'*  *
                   `^'     \ :/           `^'  `-^-'   \v/ :  \/


We can indent text as well:

    >>> mailwrapper = MailWrapper(width=56, indent=4*' ')
    >>> wrapped_text = mailwrapper.format(long_quoted_lines)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
        > > > > > Someone wrote this a long time ago. When it was written
        > > > > > all lines were less than 56 characters, but now they are
        > > > > > longer.
    <BLANKLINE>
        This is a reply to the line above.

    >>> print(mailwrapper.format(description)) #doctest: -NORMALIZE_WHITESPACE
        A new description that is quite long. But the nice
        thing is that the edit notification email generator
        knows how to indent and wrap descriptions, so this
        will appear quite nice in the actual email that gets
        sent.
    <BLANKLINE>
        It's also smart enough to preserve whitespace,
        finally!


Sometimes we don't want to indent the first line.

    >>> mailwrapper = MailWrapper(
    ...     width=56, indent=4*' ', indent_first_line=False)
    >>> print(mailwrapper.format(description)) #doctest: -NORMALIZE_WHITESPACE
    A new description that is quite long. But the nice thing
        is that the edit notification email generator knows
        how to indent and wrap descriptions, so this will
        appear quite nice in the actual email that gets
        sent.
    <BLANKLINE>
        It's also smart enough to preserve whitespace,
        finally!

    >>> wrapped_text = mailwrapper.format(long_quoted_lines)
    >>> print(wrapped_text) #doctest: -NORMALIZE_WHITESPACE
    > > > > > Someone wrote this a long time ago. When it was written
        > > > > > all lines were less than 56 characters, but now they are
        > > > > > longer.
    <BLANKLINE>
        This is a reply to the line above.

The line endings are normalized to \n, so if we get a text with
dos-style line endings, we get the following result:

    >>> mailwrapper = MailWrapper(width=56)
    >>> dos_style_comment = (
    ...     "This paragraph is longer than 56 characters, so it should"
    ...     " be wrapped even though the paragraphs are separated with"
    ...     " dos-style line endings."
    ...     "\r\n\r\n"
    ...     "Here's the second paragraph.")
    >>> wrapped_text = mailwrapper.format(dos_style_comment)
    >>> wrapped_text.split('\n')
    ['This paragraph is longer than 56 characters, so it',
     'should be wrapped even though the paragraphs are',
     'separated with dos-style line endings.',
     '',
     "Here's the second paragraph."]

Sometimes certain paragraphs should not be wrapped, e.g. a line containing a
long hyphenated URL.  Under normal circumstances, this will get wrapped.

    >>> from lp.services.mail.helpers import get_email_template
    >>> template = get_email_template('new-held-message.txt', app='registry')
    >>> text = template % dict(
    ...     user="Scarlett O'Hara",
    ...     team='frankly-my-dear-i-dont-give-a-damn',
    ...     subject='Thing',
    ...     author_name='Rhett Butler',
    ...     author_url='http://whatever.example.com/rhett',
    ...     date='today',
    ...     message_id='<aardvark>',
    ...     # And this is the one we're really interested in.
    ...     review_url=('http://launchpad.test/~frankly-my-dear-i-'
    ...                 'dont-give-a-damn/+review-moderation-messages'),
    ...     )

    >>> wrapper = MailWrapper(72)
    >>> body = wrapper.format(text, force_wrap=True)
    >>> print(body)
    Hello Scarlett O'Hara,
    <BLANKLINE>
    frankly-my-dear-i-dont-give-a-damn has a new message requiring your
    approval.
    <BLANKLINE>
        Subject: Thing
        Author name: Rhett Butler
        Author url: http://whatever.example.com/rhett
        Date: today
        Message-ID: <aardvark>
    <BLANKLINE>
    A message has been posted to the mailing list for your team, but this
    message requires your approval before it will be sent to the list
    members.  After reviewing the message, you may approve, discard or
    reject it.
    <BLANKLINE>
    To review all messages pending approval, visit:
    <BLANKLINE>
        http://launchpad.test/~frankly-my-dear-i-dont-give-a-damn/+review-
    moderation-messages
    <BLANKLINE>
    Regards,
    The Launchpad team

But if we don't want the line with the url to be wrapped, we can pass in a
callable to format().  This callable prevents wrapping when it returns False.
The callable's argument is the pre-wrapped paragraph.

    >>> def nowrap(paragraph):
    ...     return paragraph.startswith('http://')

    >>> body = wrapper.format(text, force_wrap=True, wrap_func=nowrap)
    >>> print(body)  # noqa
    Hello Scarlett O'Hara,
    <BLANKLINE>
    frankly-my-dear-i-dont-give-a-damn has a new message requiring your
    approval.
    <BLANKLINE>
        Subject: Thing
        Author name: Rhett Butler
        Author url: http://whatever.example.com/rhett
        Date: today
        Message-ID: <aardvark>
    <BLANKLINE>
    A message has been posted to the mailing list for your team, but this
    message requires your approval before it will be sent to the list
    members.  After reviewing the message, you may approve, discard or
    reject it.
    <BLANKLINE>
    To review all messages pending approval, visit:
    <BLANKLINE>
        http://launchpad.test/~frankly-my-dear-i-dont-give-a-damn/+review-moderation-messages
    <BLANKLINE>
    Regards,
    The Launchpad team
