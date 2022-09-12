Object privacy
==============

Some of our content objects can be flagged as private so that they are
invisible to most users while still being there and visible to certain
people.

To tell whether or not an object is private we adapt it into an
IObjectPrivacy and check its is_private attribute.

    >>> from lp.services.privacy.interfaces import IObjectPrivacy
    >>> from lp.answers.interfaces.questioncollection import IQuestionSet
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> bug = getUtility(IBugSet).get(4)
    >>> bug.private
    False
    >>> IObjectPrivacy(bug).is_private
    False
    >>> login("salgado@ubuntu.com")
    >>> bug.setPrivate(True, getUtility(IPersonSet).getByName("salgado"))
    True
    >>> bug.private
    True
    >>> IObjectPrivacy(bug).is_private
    True

That attribute will always be False for objects that can't be made
private.

    >>> question = getUtility(IQuestionSet).get(1)
    >>> question.private
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...
    >>> IObjectPrivacy(question).is_private
    False

    >>> from lp.answers.model.question import QuestionSet
    >>> QuestionSet().private
    Traceback (most recent call last):
    ...
    AttributeError:...
    >>> IObjectPrivacy(QuestionSet()).is_private
    False
