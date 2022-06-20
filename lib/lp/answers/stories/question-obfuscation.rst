Question obfuscation
====================

Launchpad obfuscates email addresses when pages are viewed by
anonymous users to prevent address harvesting by spammers. Logged
in users can see the email address in Question descriptions.
See question-message.rst for additional documentation.


Logged in users can see email addresses
---------------------------------------

No Privileges Person can see the email address in the tooltip of the
questions in the Latest questions solved portlet on the Answers
front page.

    >>> user_browser.open('http://answers.launchpad.test/')
    >>> question_portlet = find_tag_by_id(
    ...     user_browser.contents, 'latest-questions-solved')
    >>> for li in question_portlet.find_all('li'):
    ...     print(li['title'])
    I am not able to ... if i click on a mailto:user@domain.com link ...

They can also see the email address in the tooltip for the question in the
project's questions. When they view the question, they can see the address
in the question's description.

    >>> user_browser.getControl(name='field.search_text').value = 'mailto'
    >>> user_browser.getControl('Find Answers').click()
    >>> user_browser.title
    'Questions matching "mailto"'

    >>> question_listing = find_tag_by_id(
    ...     user_browser.contents, 'question-listing')
    >>> for li in question_portlet.find_all('li'):
    ...     print(li['title'])
    I am not able to ... if i click on a mailto:user@domain.com link ...

    >>> user_browser.getLink('mailto: problem in webpage').click()
    >>> description = find_main_content(user_browser.contents).p
    >>> print(description.decode_contents())
    I am not able to open my email client if i click on a
    <a href="mailto:user@domain.com" ...>mailto:...user@domain...com</a>
    link ...

No Privileges Person can see email addresses in the FAQ's
Related question's portlet.

    >>> user_browser.getLink('Link to a FAQ').click()
    >>> user_browser.title
    'Is question #9 a FAQ...

    >>> user_browser.getControl(name='field.faq-query').value = 'voip'
    >>> user_browser.getControl('Search', index=0).click()
    >>> user_browser.getControl('4').selected = True
    >>> user_browser.getControl('Link to FAQ').click()
    >>> user_browser.getLink('How can I make VOIP calls?').click()
    >>> print(user_browser.title)
    FAQ #4 : Questions : Ubuntu

    >>> portlet = find_portlet(user_browser.contents, 'Related questions')
    >>> print(portlet.a['title'])
    I am not able to open my email client if i click on a
    mailto:user@domain.com link in a webpage in...

No Privileges Person creates a question with an email address in the
description. They can then see the email address in the tooltip in the
'Latest questions asked' portlet for Answers front page.

    >>> user_browser.getLink('#9 mailto: problem in webpage').click()
    >>> user_browser.getLink('Ask a question').click()
    >>> user_browser.title
    'Ask a question about...

    >>> user_browser.getControl('Summary').value = 'email address test'
    >>> user_browser.getControl('Continue').click()
    >>> user_browser.getControl('Description').value = (
    ...     'The clicking mailto:user@domain.com crashes the browser.')
    >>> user_browser.getControl('Post Question').click()
    >>> print(user_browser.title)
    Question #... : ...

    >>> user_browser.open('http://answers.launchpad.test/')
    >>> question_portlet = find_tag_by_id(
    ...     user_browser.contents, 'latest-questions-asked')
    >>> for li in question_portlet.find_all('li'):
    ...     print(li['title'])
    The clicking mailto:user@domain.com crashes the browser.
    ...


Anonymous users cannot see email addresses
------------------------------------------

Anonymous cannot see the email address anywhere on the Answers front
page.

    >>> anon_browser.open('http://answers.launchpad.test/')
    >>> 'user@domain.com' in anon_browser.contents
    False

    >>> question_portlet = find_tag_by_id(
    ...     anon_browser.contents, 'latest-questions-solved')
    >>> for li in question_portlet.find_all('li'):
    ...     print(li['title'])
    I am not able to ... if i click on a
    mailto:<email address hidden> ...

    >>> question_portlet = find_tag_by_id(
    ...     anon_browser.contents, 'latest-questions-asked')
    >>> for li in question_portlet.find_all('li'):
    ...     print(li['title'])
    The clicking mailto:<email address hidden> crashes the browser.
    ...

Nor can they see it in the question listings for the project.
They cannot see the address reading the question either.

    >>> anon_browser.getControl(name='field.search_text').value = 'mailto'
    >>> anon_browser.getControl('Find Answers').click()
    >>> anon_browser.title
    'Questions matching "mailto"'

    >>> 'user@domain.com' in anon_browser.contents
    False

    >>> question_listing = find_tag_by_id(
    ...     anon_browser.contents, 'question-listing')
    >>> for tr in question_listing.tbody.find_all('tr'):
    ...     print(tr['title'])
    I am not able to ... if i click on a mailto:<email address hidden>
    link ...

    >>> anon_browser.getLink('mailto: problem in webpage').click()
    >>> 'user@domain.com' in anon_browser.contents
    False

    >>> description = find_main_content(anon_browser.contents).p
    >>> print(description.decode_contents())
    I am not able to open my email client if i click on a
    mailto:&lt;email address hidden&gt; link ...

Anonymous users cannot see the email addresses in the Related
questions portlet on a FAQ page.

    >>> anon_browser.getLink('How can I make VOIP calls?').click()
    >>> print(anon_browser.title)
    FAQ #4 : Questions : Ubuntu

    >>> portlet = find_portlet(anon_browser.contents, 'Related questions')
    >>> print(portlet.a['title'])
    I am not able to open my email client if i click on a
    mailto:<email address hidden> link in a web...
