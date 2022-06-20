Comment numbering
=================

Bug respondents frequently refer to other comments by number,
eg. "applied patch in comment #34". This number is stable, and part of
the permalink URL. To help users find the relevant comments more
easily, the numbers are displayed in the comment header.

    >>> anon_browser.open('http://bugs.launchpad.test/jokosher/+bug/11')
    >>> comments = find_tags_by_class(
    ...     anon_browser.contents, 'boardComment')
    >>> for comment in comments:
    ...     number_node = comment.find(None, 'bug-comment-index')
    ...     person_node = comment.find(
    ...         lambda node: 'person' in ' '.join(node.get('class', [])))
    ...     comment_node = comment.find(None, 'comment-text')
    ...     print("%s: %s\n  %s" % (
    ...         extract_text(number_node),
    ...         extract_text(person_node),
    ...         extract_text(comment_node)[:50]))
    #1: Valentina Commissari (tsukimi)
      The solution to this is to make Jokosher use autoa
    #2: Diogo Matsubara (matsubara)
      I'm not sure that autoaudiosink is in fact the bes
    #3: Karl Tilbury (karl)
      Unfortunately, the lead developer of autoaudiosink
    #4: Daniel Henrique Debonzi (debonzi)
      The strangest thing should be happening here. My s
    #5: Edgar Bursic (edgar)
      And so it should be displayed again.
    #6: Dave Miller (justdave)
      This title, however, is the same as the bug title
