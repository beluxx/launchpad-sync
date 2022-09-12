Asking a New Question from a ProjectGroup
=========================================

Even though project groups are not QuestionTargets, it is still possible
to create a question from a project group. There are some form and
behaviour difference from the regular process for asking a question
(documented in question-add.rst). Firstly, we do not know the product
the product the question is about, so we ask the user to select one.
Secondly, without knowing the product, we cannot show the which of the
user's preferred languages are supported.

Make the test browser look like it's coming from an arbitrary South African
IP address, since we'll use that later.

    >>> user_browser.addHeader("X_FORWARDED_FOR", "196.36.161.227")


Ask a question about a Product in a ProjectGroup
------------------------------------------------

The user must be logged in to ask a question. When they attempt to ask a
question, without being logged in, they encounter an unauthorized
exception (and the user will be prompted to login from another page).
The logged user will see the Ask a Question page, for the Mozilla
Project in this case.

    >>> anon_browser.open("http://answers.launchpad.test/mozilla")
    >>> anon_browser.getLink("Ask a question").click()
    Traceback (most recent call last):
      ...
    zope.security.interfaces.Unauthorized: ...

    >>> user_browser.open("http://answers.launchpad.test/mozilla")
    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question...

The workflow is identical to the regular one, except that the user must
select one of the ProjectGroup's Products. The page displays a list of
products associated with the project. Note that the site policy is to
use the word 'Project' for 'Products' (and 'Distributions') so that
users do not have to learn our business' semantics.

    >>> print(user_browser.getControl("Project").displayOptions)
    ['Mozilla Firefox', 'Mozilla Thunderbird']

The first item in the list is the default value, and it will be
submitted if the user does not change it.

    >>> print(user_browser.getControl("Project").displayValue)
    ['Mozilla Firefox']

Like for the regular workflow, the user is shown a list of languages,
with the supported languages flagged with an asterisk.

    >>> print(user_browser.getControl("Language").displayValue)
    ['English (en) *']

    >>> langs = sorted(user_browser.getControl("Language").displayOptions)
    >>> for lang in langs:
    ...     print(lang)
    ...
    Afrikaans (af)
    English (en) *
    Sotho, Southern (st)
    Xhosa (xh)
    Zulu (zu)

No Privileged Person enters a short summary of their problem, and submits
the form with the 'Continue' button. In this case, a question for
Firefox in English regarding SVG.

    >>> user_browser.getControl("Summary").value = "Problem with SVG"
    >>> user_browser.getControl("Continue").click()

They're shown a list of similar questions related to the product Firefox
that they submitted:

    >>> similar_questions = find_tag_by_id(
    ...     user_browser.contents, "similar-questions"
    ... )
    >>> for row in similar_questions.find_all("li"):
    ...     print(row.a.decode_contents())
    ...
    2: Problem showing the SVG demo on W3C site

No Privileged Person can still change the product for which they're asking
the question. The user chooses Thunderbird from the 'Project' product
list.

    >>> user_browser.getControl("Mozilla Thunderbird").selected = True

If they empty the question summary and submits the form, they'll be
redirected to the first page. Let's assume they do this by accident as
they revise the summary after reading the similar questions.

    >>> user_browser.getControl("Summary").value = ""
    >>> user_browser.getControl("Post Question").click()

An error message in the page informs the user that the summary is
missing:

    >>> soup = find_main_content(user_browser.contents)
    >>> print(soup.find("div", "message").decode_contents())
    You must enter a summary of your problem.

The product Thunderbird that they selected on the previous screen is still
selected. No Privileged Person re-enters their question summary, and
submits the form.

    >>> print(user_browser.getControl("Project").displayValue)
    ['Mozilla Thunderbird']

    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Problem displaying complex SVG"
    >>> user_browser.getControl("Continue").click()

The user is again shown similar questions, this time for the product
Thunderbird. Since there are no similar questions against Thunderbird,
an appropriate message is displayed to inform them of this:

    >>> soup = find_main_content(user_browser.contents)
    >>> print(soup.find("p").decode_contents())
    There are no existing FAQs or questions similar to the summary you
    entered.

The user then elaborates upon their question by entering a description of
the problem. They submit the form using the 'Post Question' button.

    >>> user_browser.getControl("Description").value = (
    ...     "I received an HTML message containing an inlined SVG\n"
    ...     "representation of a chessboard. It didn't displayed properly.\n"
    ...     "Is there a way to configure Thunderbird to display SVG "
    ...     "properly?\n"
    ... )
    >>> user_browser.getControl("Post Question").click()

No Privileged Person is taken to page displaying their question. From this
point on, the user's interaction with the question follows to regular
workflow. (see question-workflow.rst for the details).

    >>> user_browser.url
    '.../thunderbird/+question/...'

    >>> print(user_browser.title)
    Question #... : Questions : Mozilla Thunderbird


Supported Language behaviour
----------------------------

Following a similar path as demonstrated above with a non-English
language speaker illustrates a less-than-ideal behaviour for supported
languages. (See question-add-in-other-languages.rst for the regular
behaviour).


Register a support contact who speaks a non-English language
............................................................

To illustrate the supported language behaviour, we add an answer contact
to Thunderbird who has Japanese as a preferred language. Japanese will
be a supported language for Thunderbird Questions, which allows us to
test the supported languages behaviour for non-English languages. Dafydd
speaks Japanese, so we will use him.

    >>> daf_browser = setupBrowser(auth="Basic daf@canonical.com:test")
    >>> daf_browser.open("http://launchpad.test/~daf/+editlanguages")
    >>> print(daf_browser.title)
    Language preferences...

    >>> daf_browser.getControl("Japanese").selected
    True

    >>> daf_browser.open(
    ...     "http://answers.launchpad.test/thunderbird/+answer-contact"
    ... )
    >>> print(daf_browser.title)
    Answer contact for...

    >>> daf_browser.getControl(
    ...     "I want to be an answer contact for " "Mozilla Thunderbird"
    ... ).selected = True
    >>> daf_browser.getControl("Continue").click()
    >>> content = find_main_content(daf_browser.contents)
    >>> for message in content.find_all("div", "informational message"):
    ...     print(message.decode_contents())
    ...
    You have been added as an answer contact for Mozilla Thunderbird.

And we add Japanese to No Privileges Person's preferred languages. We
then have a condition for certain products, Thunderbird in this example,
where the user's languages and the answer contact's languages will
match. This condition demonstrates the supported language behaviour.

    >>> user_browser.open("http://launchpad.test/~no-priv/+editlanguages")
    >>> print(user_browser.title)
    Language preferences...

    >>> user_browser.getControl("Japanese").selected = True
    >>> user_browser.getControl("Save").click()
    >>> soup = find_main_content(user_browser.contents)
    >>> print(soup.find("div", "informational message").decode_contents())
    Added Japanese to your preferred languages.

So if No Privileges Person were to visit the Ask a Question page for
Thunderbird directly, they will see that Japanese, as well as English (the
default supported language), have asterisks next to them in the Language
list. This indicates that they can ask a question in Japanese or English
and expect someone to reply in the same language.

    >>> user_browser.open(
    ...     "http://answers.launchpad.test/firefox/+addquestion"
    ... )
    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja)']

The supported languages will not be shown immediately when Sample Person
asks a question Thunderbird question from the context of the Mozilla
Project.


Ask a non-English question about a Product in a ProjectGroup
............................................................

Supported languages are only shown after the user submits the 'Product'
associated with the project. When a user enters the 'Product'
information incorrectly we cannot show the supported languages to the
user.


Supported languages aren't displayed after choosing a product
.............................................................

XXX sinzui 2007-05-02 #111793 (Supported languages will not be shown in
some cases when asking questions from the ProjectGroup facet) No
Privileges Person visits the Ask a question page from a project just as
No Privileged Person did above, but this time in wants to do so in
Japanese.

    >>> user_browser.open("http://answers.launchpad.test/mozilla")
    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question...

The page displays a list of products associated with the project. The
first item in the list is the default value, and it will be submitted if
the user does not change it.

    >>> print(user_browser.getControl("Project").displayOptions)
    ['Mozilla Firefox', 'Mozilla Thunderbird']

    >>> print(user_browser.getControl("Project").displayValue)
    ['Mozilla Firefox']

Like for the regular workflow, the user is shown a list of languages,
with the supported languages flagged with an asterisk. Note that only
English is flagged because we do not know which Product the question is
about. Without knowing the product, we cannot flag the supported
languages other than the default language of English. If the user were
to submit their question in another language, they might find that the
language is supported on the next page.

    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja)']

    >>> user_browser.getControl("Language").value = ["en"]

No Privileges Person enters a short summary of their problem in English
because Japanese is not listed as supported. They submits the form with
the 'Continue' button without setting the product. In this case, they are
asking a question for Firefox in English regarding SVG.

    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Problem displaying complex SVG"
    >>> user_browser.getControl("Continue").click()

They're shown a list of similar questions related to the product Firefox.
They can see which of their preferred languages are supported for the
Firefox product by reviewing which languages has asterisks in the
Languages list--only English in the example.

    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja)']

No Privileges Person can still change the product for which they're asking
the question. They realize they should have selected Thunderbird as the
subject of the question. They choose Thunderbird from the 'Project'
product list and reviews the list of supported languages again. The
language list does not change because the Thunderbird was not submitted
as the product.

    >>> user_browser.getControl("Mozilla Thunderbird").selected = True
    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja)']

If No Privileges Person asks a question in Japanese, it will be
supported by Dafydd, but No Privileges Person will never know that.
Let's stop here. The rest of this scenario is just adding a question as
described above--filling in a description and submitting the data with
the 'Post Question' button.


Supported languages are displayed after the submitting a product
................................................................

Let's try this again from the starting page, but this time, No
Privileges Person correctly chooses Thunderbird as the subject of their
question.

    >>> user_browser.open("http://answers.launchpad.test/mozilla")
    >>> user_browser.getLink("Ask a question").click()
    >>> print(user_browser.title)
    Ask a question...

    >>> user_browser.getControl("Mozilla Thunderbird").selected = True

They write their summary in English as he sees that is the only supported
Language, and 'Continues' to the next page.

    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja)']

    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Problem displaying complex SVG"
    >>> user_browser.getControl("Continue").click()

The product Thunderbird that they selected on the previous screen is still
selected. They can see that this product has support for Japanese as well
as English when they see the asterisks next to both in the Languages
list. Japanese is supported because Dafydd speaks Japanese and is an
answer contact for Thunderbird. We see this only after a question
summary is submitted for a product.

    >>> print(user_browser.getControl("Language").displayOptions)
    ['English (en) *', 'Japanese (ja) *']

No Privileges Person sets the language to Japanese, changes their question
summary, writes a description, and submits the form with the 'Post
Question' button.

    >>> print(user_browser.getControl("Project").displayValue)
    ['Mozilla Thunderbird']

    >>> user_browser.getControl("Japanese (ja) *").selected = True
    >>> user_browser.getControl(
    ...     "Summary"
    ... ).value = "Pretend this is written in Japanese"
    >>> user_browser.getControl(
    ...     "Description"
    ... ).value = "Something in kanji and hiragana."
    >>> user_browser.getControl("Post Question").click()

The user is taken to page displaying their question. Changing the language
or the summary did not search for similar questions again--the question
is created.

    >>> user_browser.url
    '.../thunderbird/+question/...'

    >>> print(user_browser.title)
    Question #... : Questions : Mozilla Thunderbird
