Asking New Questions
====================

There are two paths available to a user to ask a new question. The first
one involves two steps. First, go to the product or distribution for
which support is desired:

    >>> browser.open("http://answers.launchpad.test/ubuntu")
    >>> print(browser.title)
    Questions : Ubuntu

The user sees an involvement link to ask a question.

    >>> link = find_tag_by_id(browser.contents, "involvement").a
    >>> print(extract_text(link))
    Ask a question

Asking a new question requires logging in:

    >>> browser.getLink("Ask a question").click()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...
    >>> user_browser.open("http://answers.launchpad.test/ubuntu/")
    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question...


Get Help Online
---------------

The other way is by using the 'Get Help Online' menu item that is found
in all GTK2 applications packaged for Ubuntu (and soon in QT
applications too). That page also has a 'ask a question' link that will
start the creation process. Questions created this way will be
associated with the source package of the used application.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/hoary/"
    ...     "+sources/mozilla-firefox/+gethelp"
    ... )
    >>> print(user_browser.title)
    Help and support...

    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question...


Searching for Similar FAQs and Questions
----------------------------------------

Asking a new question is a two-step process. In the first step, the user
enters a summary of their problem. Using that summary, a search
is performed to find similar questions and similar FAQs that might
exists.

That step cannot be skipped by the user, if they just click 'Continue',
an error message will be displayed.

    >>> user_browser.getControl("Summary").value
    ''
    >>> user_browser.getControl("Continue").click()
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    You must enter a summary of your problem.

The user enters their problem summary and a list of similar FAQs and
questions are displayed.

XXX: Original search, disabled due to performance issues RBC 20100725. This
will be reinstated when cheap relevance filtering is available / when search
is overhauled.

    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Visiting a web page requiring java crashes firefox"

For now, use a closer search:

    >>> user_browser.getControl("Summary").value = "java web pages"
    >>> user_browser.getControl("Continue").click()
    >>> contents = find_main_content(user_browser.contents)
    >>> similar_faqs = contents.find(id="similar-faqs")
    >>> print(extract_text(similar_faqs))
    How can I play MP3/Divx/DVDs/Quicktime/Realmedia files or view
        Flash/Java web pages
    >>> print(similar_faqs.a["href"])
    http://answers.launchpad.test/ubuntu/+faq/...

    >>> similar_questions = contents.find(id="similar-questions")
    >>> print(backslashreplace(extract_text(similar_questions)))
    8: Installation of Java Runtime Environment for Mozilla  (Answered)
        posted on ... in ...mozilla-firefox... package in Ubuntu
    >>> print(similar_questions.a["href"])
    http://answers.../ubuntu/+source/mozilla-firefox/+question/...

The beginning of the description appears in a small pop-up when the
mouse is left over the question's title.

    >>> import re
    >>> question_link = contents.find(
    ...     "a", text=re.compile("Installation of Java")
    ... )
    >>> print(question_link.find_parent("li")["title"])
    <BLANKLINE>
    When opening http://www.gotomypc.com/ with Mozilla, a java run time
    ennvironment plugin is requested.
    <BLANKLINE>
    1) The plugin finder service indicates that JRE is available
    2) next screen indicates JRE "not available" and requests
    "manual install"
    3) clicking on "manual install" open java web site.......

Similarly, the beginning of the FAQ's content appears when the mouse
hovers on the FAQ's title:

    >>> faq_link = contents.find(
    ...     "a", text=re.compile("How can I play MP3/Divx")
    ... )
    >>> print(faq_link.find_parent("li")["title"])
    Playing many common formats such as DVIX, MP3, DVD, or Flash
    animations require the installation of plugins.
    <BLANKLINE>
    See https://help.ubuntu.com/community/RestrictedFormats for all the
    details.


Creating a New Question
-----------------------

If the shown questions don't help the user, they may post a new question
by filling in the 'Description' field. They may also edit the
summary they provided.

    >>> user_browser.getControl("Summary").value
    'java web pages'

If the user doesn't provide details, they'll get an error message:

    >>> user_browser.getControl("Post Question").click()
    >>> print_feedback_messages(user_browser.contents)
    There is 1 error.
    You must provide details about your problem.

And if they decide to remove the title, they'll be brought back to the
first step:

    >>> user_browser.getControl("Summary").value = ""
    >>> user_browser.getControl("Post Question").click()
    >>> print_feedback_messages(user_browser.contents)
    There are 2 errors.
    You must enter a summary of your problem.

Entering a valid title and description will create the new question and
redirect the user to the question page.

    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Visiting a web page requiring java crashes firefox"
    >>> user_browser.getControl("Continue").click()
    >>> user_browser.getControl(
    ...     "Description"
    ... ).value = "I use Ubuntu on AMD64 and firefox is slow."
    >>> user_browser.getControl("Post Question").click()
    >>> user_browser.url
    '.../ubuntu/+source/mozilla-firefox/+question/...'
    >>> print(user_browser.title)
    Question #... : Questions : mozilla-firefox package : Ubuntu

    >>> print(
    ...     extract_text(
    ...         find_tag_by_id(user_browser.contents, "registration")
    ...     )
    ... )
    Asked by No Privileges Person ...
    >>> contents = find_main_content(user_browser.contents)
    >>> print(extract_text(contents.find("div", "report")))
    I use Ubuntu on AMD64 ...
