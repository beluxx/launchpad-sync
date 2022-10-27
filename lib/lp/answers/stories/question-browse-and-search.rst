Browsing and Searching Questions
================================

This story describes some common use cases about using the browsing and
searching features of the Answer Tracker.

Make the test browser look like it's coming from an arbitrary South African
IP address, since we'll use that later.

    >>> browser.addHeader("X_FORWARDED_FOR", "196.36.161.227")


When Nobody Uses the Answer Tracker
-----------------------------------

Average Joe has recently installed Kubuntu. He has a problem with his
system and goes to the Kubuntu's support page in Launchpad to see if
somebody had a similar problem.

Kubuntu must enable answers to access questions.

    >>> from zope.component import getUtility
    >>> from lp.app.enums import ServiceUsage
    >>> from lp.registry.interfaces.distribution import IDistributionSet

    >>> login("admin@canonical.com")
    >>> getUtility(IDistributionSet)[
    ...     "kubuntu"
    ... ].answers_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

    >>> browser.open("http://launchpad.test/kubuntu")
    >>> browser.getLink("Answers").click()

He discovers that there are no questions on the Kubuntu Answers page:

    >>> print(browser.title)
    Questions : Kubuntu

    >>> print(find_main_content(browser.contents).find("p").decode_contents())
    There are no questions for Kubuntu with the requested statuses.

For projects that don't have products, the Answers facet is disabled.

    >>> browser.open("http://launchpad.test/aaa")
    >>> browser.getLink("Answers")
    Traceback (most recent call last):
     ...
    zope.testbrowser.browser.LinkNotFoundError

Browsing Questions
------------------

He realises that support for Kubuntu is probably going on in the Ubuntu
Answers page and goes there to check.

    >>> browser.open("http://launchpad.test/ubuntu/+questions")
    >>> print(browser.title)
    Questions : Ubuntu

He sees a listing of the current questions posted on Ubuntu:

    >>> soup = find_main_content(browser.contents)
    >>> for question in soup.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Continue playing after shutdown
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla
    Slow system

None of the listed question titles quite match his problem. He sees that
there is another page of questions, so he goes to the next page of
results. There, he finds only one other question:

    >>> browser.getLink("Next").click()
    >>> print(browser.title)
    Questions : Ubuntu
    >>> soup = find_main_content(browser.contents)
    >>> for question in soup.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Installation failed

This is the last results page, so the next and last links are greyed
out.

    >>> "Next" in browser.contents
    True
    >>> browser.getLink("Next")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> "Last" in browser.contents
    True
    >>> browser.getLink("Last")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError

He decides to go the first page. He remembered one question title that
might have been remotely related to his problem.

    >>> browser.getLink("First").click()

Since he is on the first page, the 'First' and 'Previous' links are
greyed out:

    >>> "Previous" in browser.contents
    True
    >>> browser.getLink("Previous")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> "First" in browser.contents
    True
    >>> browser.getLink("First")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError

When he passes the mouse over the question's row, the beginning of the
description appears in a small pop-up:

    >>> import re
    >>> soup = find_main_content(browser.contents)
    >>> question_link = soup.find("a", text=re.compile("Play DVDs"))
    >>> print(question_link.find_parent("tr")["title"])
    How do you play DVDs in Totem..........?

    >>> question_link = soup.find("a", text=re.compile("Slow system"))
    >>> print(question_link.find_parent("tr")["title"])
    I get really poor hard drive performance.

He clicks on the question title to obtain the question page where the
details of the question are available.

    >>> browser.getLink("Slow system").click()
    >>> print(browser.title)
    Question #7 “Slow system” : ...
    >>> soup = find_main_content(browser.contents)
    >>> soup("div", "report")
    [<div class="report"><p>I get really poor hard drive
    performance.</p></div>]


Jumping to Questions
--------------------

The Answer Tracker main page permits the user to jump to a question by
submitting the question's id in the text input field with the 'Find
Answers' button.

Average Joe learns than he might find the solution to his Firefox
problem from someone on IRC. He is told to read question 9 on the
Launchpad Answer Tracker. He visits the main page and enters '9'
to jump to the question.

    >>> browser.open("http://answers.launchpad.test/")
    >>> browser.getControl(name="field.search_text").value = "9"
    >>> browser.getControl("Find Answers").click()
    >>> print(browser.title)
    Question #9 ...

While reading the Ubuntu forums for a solution to his problem,
Average Joe finds some unlinked text that refers to how to
get extensions to work. He copies the text ' #6 ' from the page
and pastes it into the main page of the Answer Tracker to read
the answer.

    >>> browser.open("http://answers.launchpad.test/")
    >>> browser.getControl(name="field.search_text").value = " #6 "
    >>> browser.getControl("Find Answers").click()
    >>> print(browser.title)
    Question #6 ...

The Answer Tracker cannot identify Question ids within text. Average
Joe finds a reference to question 8 in a blog. He copies 'question 8'
and pastes it into the text field on the Answer Tracker main page. He
is shown search results instead of the question.

    >>> browser.open("http://answers.launchpad.test/")
    >>> browser.getControl(name="field.search_text").value = "question 8"
    >>> browser.getControl("Find Answers").click()
    >>> print(browser.title)
    Questions matching "question 8"

    >>> print(find_main_content(browser.contents).find("p").decode_contents())
    There are no questions matching "question 8" with the requested statuses.


Searching Questions
-------------------

Browsing is fine when the number of questions is small, but searching
is more convenient as the number of questions grow larger.

This time, it's Firefox that brings Average Joe to the Ubuntu Answer
Tracker. He finds that his machine becomes really slow
whenever he has Firefox open. Luckily for Average Joe, searching for
similar questions is easy: on the question listing page, he just
enters his search key and hit the 'Search' button.

    >>> browser.open("http://launchpad.test/ubuntu/+questions")
    >>> browser.getControl(name="field.search_text").value = "firefox is slow"
    >>> browser.getControl("Search", index=0).click()

Unfortunately, the search doesn't return any similar questions:

    >>> print(browser.title)
    Questions : Ubuntu
    >>> search_summary = find_main_content(browser.contents)
    >>> print(search_summary)
    <...
    <p>There are no questions matching "firefox is slow" for Ubuntu with
    the requested statuses.</p>
    ...

Joe observes under the search widget that there are checkboxes to select
the question status to search. He notices that only some statuses are
selected. He adds 'Invalid' to the selection, and run his search again.

    >>> from lp.testing.pages import strip_label

    >>> statuses = browser.getControl(name="field.status").displayValue
    >>> [strip_label(status) for status in statuses]
    ['Open', 'Needs information', 'Answered', 'Solved']
    >>> browser.getControl("Invalid").selected = True
    >>> browser.getControl("Search", index=0).click()

This time, the search returns one item.

    >>> soup = find_main_content(browser.contents)
    >>> for question in soup.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Firefox is slow and consumes too much RAM

He clicks on the link to read the question description.

    >>> browser.getLink("Firefox is slow").click()
    >>> print(browser.title)
    Question #3 “Firefox is slow and consumes too much RAM” : ...

The user must choose at least one status when searching questions. An
error is displayed when the user forgets to select a status.

    >>> browser.open("http://launchpad.test/ubuntu/+questions")
    >>> browser.getControl(name="field.status").displayValue = []
    >>> browser.getControl("Search", index=0).click()
    >>> messages = find_tags_by_class(browser.contents, "message")
    >>> print(messages[0].decode_contents())
    You must choose at least one status.


Controlling the Sort Order
--------------------------

That question isn't exactly what Average Joe was looking for. Now, he'd
like to see all the questions that were related to the firefox package.
The question listing page for distribution displays the source package
related to each question . The source package name is a link to the
source package's question listing.

    # We should use goBack() here but can't because of bug #98372:
    # zope.testbrowser truncates document content after goBack().
    #>>> browser.goBack()
    >>> browser.open("http://launchpad.test/ubuntu/+questions")
    >>> browser.getLink("mozilla-firefox").click()
    >>> browser.title
    'Questions : mozilla-firefox package : Ubuntu'
    >>> soup = find_main_content(browser.contents)
    >>> print(soup.find("table", "listing"))
    <table...
    ...mailto: problem in webpage...2006-07-20...
    ...Installation of Java Runtime Environment for Mozilla...2006-07-20...
    </table>

Average Joe wants to see all questions but listed from the oldest to the
newest. Again, he adds the 'Invalid' status to the selection and
selects the 'oldest first' sort order.

    >>> browser.getControl("Invalid").selected = True
    >>> browser.getControl("oldest first").selected = True
    >>> browser.getControl("Search", index=0).click()

    >>> soup = find_main_content(browser.contents)
    >>> print(soup.find("table", "listing"))
    <table...
    ...Firefox is slow and consumes too much RAM...2005-09-05...
    ...Installation of Java Runtime Environment for Mozilla...2006-07-20...
    ...mailto: problem in webpage...2006-07-20...
    </table>


Common Reports
--------------

In the actions menu, we find links to some common reports.


Open Questions
..............

Nice Guy likes helping others. He uses the 'Open' link to view the most
recent questions on Mozilla Firefox.

    >>> browser.open("http://launchpad.test/firefox/+questions")
    >>> browser.getLink("Open").click()
    >>> print(browser.title)
    Questions : Mozilla Firefox
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Firefox loses focus and gets stuck
    Problem showing the SVG demo on W3C site
    Firefox cannot render Bank Site

Note that the default sort order for this listing is
'recently updated first' so that questions which received new information
from the submitter shows up first:

    >>> browser.getControl(name="field.sort").displayValue
    ['recently updated first']

That listing is also searchable. Since he's has lots of experience
dealing with plugins problems, he always start by a search for such
problems:

    >>> browser.getControl(name="field.search_text").value = "plugin"
    >>> browser.getControl("Search", index=0).click()
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Problem showing the SVG demo on W3C site


Answered Questions
..................

A random user has a problem with firefox in Ubuntu. They use the
'Answered' link on the 'Answers' facet of the distribution to look for
similar problems. (This listing includes both 'Answered' and 'Solved'
questions.)

    >>> browser.open("http://launchpad.test/ubuntu/+questions")
    >>> browser.getLink("Answered").click()
    >>> print(browser.title)
    Questions : Ubuntu
    >>> statuses = browser.getControl(name="field.status").displayValue
    >>> [strip_label(status) for status in statuses]
    ['Answered', 'Solved']
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla

This report is also searchable. They're having a problem with Evolution, so
they enter 'Evolution' as a keyword and hit the search button.

    >>> browser.getControl(name="field.search_text").value = "Evolution"
    >>> browser.getControl("Search", index=0).click()

    >>> search_summary = find_main_content(browser.contents)
    >>> print(search_summary)
    <...
    <p>There are no answered questions matching "Evolution" for Ubuntu.</p>
    ...


My questions
............

Sample Person remembers posting a question on mozilla-firefox. They use
the 'My questions' link on the distribution source package Answers facet
to list all the questions they ever made about that package.

They need to login to access that page:

    >>> anon_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/mozilla-firefox/"
    ...     "+questions"
    ... )
    >>> anon_browser.getLink("My questions").click()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> sample_person_browser = setupBrowser(
    ...     auth="Basic test@canonical.com:test"
    ... )
    >>> sample_person_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/mozilla-firefox/"
    ...     "+questions"
    ... )
    >>> sample_person_browser.getLink("My questions").click()
    >>> print(repr(sample_person_browser.title))
    'Questions you asked about mozilla-firefox in Ubuntu : Questions :
    mozilla-firefox package : Ubuntu'
    >>> questions = find_tag_by_id(
    ...     sample_person_browser.contents, "question-listing"
    ... )
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla

Their problem was about integrating their email client in firefox, so they
enter 'email client in firefox'

    >>> sample_person_browser.getControl(
    ...     name="field.search_text"
    ... ).value = "email client in firefox"

They also remember that their question was answered, so they unselect the
other statuses and hit the search button.

    >>> sample_person_browser.getControl("Open").selected = False
    >>> sample_person_browser.getControl("Invalid").selected = False
    >>> sample_person_browser.getControl("Search", index=0).click()

The exact question they were searching for is displayed!

    >>> questions = find_tag_by_id(
    ...     sample_person_browser.contents, "question-listing"
    ... )
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    mailto: problem in webpage

If the user didn't make any questions on the product, a message
informing them of this fact is displayed.

gnomebaker must enable answers to access questions.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> login("admin@canonical.com")
    >>> getUtility(IProductSet)[
    ...     "gnomebaker"
    ... ].answers_usage = ServiceUsage.LAUNCHPAD
    >>> transaction.commit()
    >>> logout()

    >>> sample_person_browser.open(
    ...     "http://launchpad.test/gnomebaker/+questions"
    ... )
    >>> sample_person_browser.getLink("My questions").click()
    >>> print(
    ...     find_main_content(sample_person_browser.contents)
    ...     .find("p")
    ...     .decode_contents()
    ... )
    You didn't ask any questions about gnomebaker.


Need attention
..............

A user can often forget which questions need their attention. For
this purpose, there is a 'Need attention' report which displays the
questions made by the user which require a reply. It also lists
the questions on which they provided an answer or requested for more
information and that are now back in the 'Open' state.

They need to login to access that page:

    >>> anon_browser.open("http://launchpad.test/distros/ubuntu/+questions")
    >>> anon_browser.getLink("Need attention").click()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> sample_person_browser.open(
    ...     "http://launchpad.test/distros/ubuntu/+questions"
    ... )
    >>> sample_person_browser.getLink("Need attention").click()
    >>> print(sample_person_browser.title)
    Questions needing your attention for Ubuntu : Questions : Ubuntu
    >>> questions = find_tag_by_id(
    ...     sample_person_browser.contents, "question-listing"
    ... )
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Play DVDs in Totem
    Installation of Java Runtime Environment for Mozilla

Like all other report, this one is searchable:

    >>> sample_person_browser.getControl(
    ...     name="field.search_text"
    ... ).value = "evolution"
    >>> sample_person_browser.getControl("Search", index=0).click()
    >>> print(sample_person_browser.title)
    Questions matching "evolution" needing your attention for Ubuntu :
    Questions : Ubuntu
    >>> search_summary = find_main_content(sample_person_browser.contents)
    >>> print(search_summary)
    <...
    <p>No questions matching "evolution" need your attention for Ubuntu.</p>
    ...

If there is no questions needing the user's attention, a message
informing them of this fact is displayed.

    >>> sample_person_browser.open(
    ...     "http://launchpad.test/products/gnomebaker/+questions"
    ... )
    >>> sample_person_browser.getLink("Need attention").click()
    >>> print(
    ...     find_main_content(sample_person_browser.contents)
    ...     .find("p")
    ...     .decode_contents()
    ... )
    No questions need your attention for gnomebaker.


Person Reports
--------------

The Answers facet on on person also contains various searchable
listings.

The default listing on the person Answers facet lists all the questions
that the person was involved with. This includes questions that
the person asked, answered, is assigned to, is subscribed to, or
commented on.

    >>> browser.open("http://launchpad.test/~name16")
    >>> browser.getLink("Answers").click()
    >>> print(browser.title)
    Questions : Foo Bar

    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Continue playing after shutdown
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla
    Slow system

That listing is batched when there are many questions:

    >>> browser.getLink("Next")
    <Link...>

The listing contains a 'In' column that shows the context where the
questions was made.

    >>> for question in questions.find_all("td", "question-target"):
    ...     print(question.find("a").decode_contents())
    ...
    Ubuntu
    Ubuntu
    mozilla-firefox in Ubuntu
    mozilla-firefox in Ubuntu
    Ubuntu

These contexts are links to the context question listing.

    >>> browser.getLink("mozilla-firefox in Ubuntu").click()
    >>> print(repr(browser.title))
    'Questions : mozilla-firefox package : Ubuntu'

The listing is searchable and can restrict also the list of displayed
questions to a particular status:

    # goBack() doesn't work.
    >>> browser.open("http://launchpad.test/~name16/+questions")
    >>> browser.getControl(name="field.search_text").value = "Firefox"
    >>> browser.getControl(name="field.status").displayValue = [
    ...     "Solved",
    ...     "Invalid",
    ... ]
    >>> browser.getControl("Search", index=0).click()
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Firefox is slow and consumes too much RAM
    mailto: problem in webpage

The actions menu contains links to listing that contain only a specific
type of involvement.


Assigned
........

The assigned report only lists the questions to which the person is
assigned.

    >>> browser.getLink("Assigned").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> print(find_main_content(browser.contents).find("p").decode_contents())
    No questions assigned to Foo Bar found with the requested statuses.


Answered
........

The 'Answered' link displays all the questions where the person is the
answerer.

    >>> browser.getLink("Answered").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    mailto: problem in webpage


Commented
.........

The report available under the 'Commented' link displays all the
questions commented on by the person.

    >>> browser.getLink("Commented").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Continue playing after shutdown
    Play DVDs in Totem
    mailto: problem in webpage
    Installation of Java Runtime Environment for Mozilla
    Newly installed plug-in doesn't seem to be used


Asked
.....

The 'Asked' link displays a listing containing all the questions
asked by the person.

    >>> browser.getLink("Asked").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Slow system
    Firefox loses focus and gets stuck


Need attention
..............

The 'Need attention' link displays all the questions that need
the attention of that person.

    >>> browser.getLink("Need attention").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Continue playing after shutdown
    Slow system


Subscribed
..........

Foo Bar can find all the questions to which they are subscribed by
visiting the 'Subscribed' link in the 'Answers' facet.

    >>> browser.getLink("Subscribed").click()
    >>> print(browser.title)
    Questions for Foo Bar : Questions : Foo Bar
    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Slow system


Browsing and Searching Questions in a ProjectGroup
--------------------------------------------------

When going to the Answers facet of a project, a listing of all the
questions filed against any of the project's products is displayed.

    >>> browser.open("http://launchpad.test/mozilla")
    >>> browser.getLink("Answers").click()
    >>> print(browser.title)
    Questions : The Mozilla Project

The results are displayed in a format similar to the Person reports:
there is an 'In' column displaying where the questions were filed.

    >>> def print_questions_with_target(contents):
    ...     questions = find_tag_by_id(contents, "question-listing")
    ...     for question in questions.tbody.find_all("tr"):
    ...         question_title = (
    ...             question.find("td", "questionTITLE")
    ...             .find("a")
    ...             .decode_contents()
    ...         )
    ...         question_target = (
    ...             question.find("td", "question-target")
    ...             .find("a")
    ...             .decode_contents()
    ...         )
    ...         print(question_title, question_target)
    ...
    >>> print_questions_with_target(browser.contents)
    Newly installed plug-in doesn't seem to be used Mozilla Firefox
    Firefox loses focus and gets stuck  Mozilla Firefox
    Problem showing the SVG demo on W3C site    Mozilla Firefox
    Firefox cannot render Bank Site     Mozilla Firefox

That listing is searchable:

    >>> browser.getControl(name="field.search_text").value = "SVG"
    >>> browser.getControl("Search", index=0).click()

    >>> questions = find_tag_by_id(browser.contents, "question-listing")
    >>> for question in questions.find_all("td", "questionTITLE"):
    ...     print(question.find("a").decode_contents())
    ...
    Problem showing the SVG demo on W3C site

The same standard reports than on regular QuestionTarget are available:

    >>> browser.getLink("Open").click()
    >>> print(browser.title)
    Questions : The Mozilla Project

    >>> browser.getLink("Answered").click()
    >>> print(browser.title)
    Questions : The Mozilla Project

    # The next two reports are only available to a logged-in user.
    >>> user_browser.open("http://launchpad.test/mozilla/+questions")
    >>> user_browser.getLink("My questions").click()
    >>> print(user_browser.title)
    Questions you asked about The Mozilla Project : Questions : The Mozilla
    Project

    >>> user_browser.getLink("Need attention").click()
    >>> print(user_browser.title)
    Questions needing your attention for The Mozilla Project : Questions : The
    Mozilla Project


Searching All Questions
-----------------------

It is possible from the Answer Tracker front page to search among all
questions ever filed on Launchpad.

    >>> browser.open("http://answers.launchpad.test/")
    >>> browser.getControl(name="field.search_text").value = "firefox"
    >>> browser.getControl("Find Answers").click()

    >>> print(browser.title)
    Questions matching "firefox"

    >>> print(browser.url)
    http://answers.launchpad.test/questions/+questions?...

The results are displayed in a format similar to the Person reports:
there is an 'In' column displaying where the questions were filed.

    >>> print_questions_with_target(browser.contents)
    Firefox loses focus and gets stuck  Mozilla Firefox
    Firefox cannot render Bank Site     Mozilla Firefox
    mailto: problem in webpage          mozilla-firefox in Ubuntu
    Newly installed plug-in doesn't seem to be used Mozilla Firefox
    Problem showing the SVG demo on W3C site    Mozilla Firefox

Only the default set of statuses is searched:

    >>> statuses = browser.getControl(name="field.status").displayValue
    >>> [strip_label(status) for status in statuses]
    ['Open', 'Needs information', 'Answered', 'Solved']

When no results are found, a message informs the user of this fact:

    >>> browser.getControl(name="field.status").displayValue = ["Expired"]
    >>> browser.getControl("Search", index=0).click()

    >>> print(find_main_content(browser.contents).find("p").decode_contents())
    There are no questions matching "firefox" with the requested statuses.

Clicking the 'Search' button without entering any search text will
display all questions asked in Launchpad with the selected statuses.

    >>> browser.getControl(name="field.status").displayValue = ["Open"]
    >>> browser.getControl(name="field.search_text").value = ""
    >>> browser.getControl("Search", index=0).click()

    >>> print_questions_with_target(browser.contents)
    Continue playing after shutdown             Ubuntu
    Installation failed                         Ubuntu
    Firefox loses focus and gets stuck          Mozilla Firefox
    Problem showing the SVG demo on W3C site    Mozilla Firefox
    Firefox cannot render Bank Site             Mozilla Firefox


Searching in a Selected Project
-------------------------------

From the Answers front page, the user can select to search questions
only in a particular project. In this context a "project" means either
a distribution, product or project group.

They must enter the project's name in the text field:

    >>> anon_browser.open("http://answers.launchpad.test")
    >>> anon_browser.getControl("One project").selected = True
    >>> anon_browser.getControl("Find Answers").click()

    >>> for message in find_tags_by_class(anon_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    Please enter a project name

Entering an invalid project also displays an error message:

    >>> anon_browser.getControl(name="field.scope.target").value = "invalid"
    >>> anon_browser.getControl("Find Answers").click()

    >>> for message in find_tags_by_class(anon_browser.contents, "message"):
    ...     print(message.decode_contents())
    ...
    There is no project named 'invalid' registered in Launchpad

If the browser supports javascript, there is a 'Choose' link available
to help the user find an existing project. Since the test browser does
not support javascript, it is turned into a "Find" link to the /questions.

    >>> find_link = anon_browser.getLink("Find")
    >>> print(find_link.url)
    http://answers.launchpad.test/questions...


The form field can be filled manually without using the ajax widget.

    >>> anon_browser.open("http://answers.launchpad.test")
    >>> anon_browser.getControl(name="field.search_text").value = "plugins"
    >>> anon_browser.getControl("One project").selected = True
    >>> anon_browser.getControl(name="field.scope.target").value = "mozilla"
    >>> anon_browser.getControl("Find Answers").click()
    >>> print(anon_browser.title)
    Questions : The Mozilla Project

This works also with distributions:

    >>> anon_browser.open("http://answers.launchpad.test")
    >>> anon_browser.getControl(name="field.search_text").value = "firefox"
    >>> anon_browser.getControl("One project").selected = True
    >>> anon_browser.getControl(name="field.scope.target").value = "ubuntu"
    >>> anon_browser.getControl("Find Answers").click()
    >>> print(anon_browser.title)
    Questions : Ubuntu

And also with products:

    >>> anon_browser.open("http://answers.launchpad.test")
    >>> anon_browser.getControl(name="field.search_text").value = "plugins"
    >>> anon_browser.getControl("One project").selected = True
    >>> anon_browser.getControl(name="field.scope.target").value = "firefox"
    >>> anon_browser.getControl("Find Answers").click()
    >>> print(anon_browser.title)
    Questions : Mozilla Firefox
