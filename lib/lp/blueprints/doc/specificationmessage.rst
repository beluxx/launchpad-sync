Specification Messages
======================

Specification messages are messages associated with blueprints. A
specification message is described by the ISpecificationMessage
interface.


Creating specification messages
-------------------------------

To create a specification message, use
ISpecificationMessageSet.createMessage:

    >>> from lp.blueprints.interfaces.specificationmessage import (
    ...     ISpecificationMessageSet)
    >>> specmessageset = getUtility(ISpecificationMessageSet)

    >>> test_message = specmessageset.createMessage(
    ...     subject="test message subject",
    ...     content="text message content",
    ...     owner=factory.makePerson(),
    ...     spec=factory.makeSpecification())
    >>> print(test_message.message.subject)
    test message subject


Retrieving specification messages
---------------------------------

ISpecificationMessageSet represents the set of all messages in the
system. An individual ISpecificationMessage can be retrieved with
ISpecificationMessageSet.get:

    >>> from zope.security.proxy import removeSecurityProxy
    >>> specmessage_one = specmessageset.get(
    ...     removeSecurityProxy(test_message).id)
    >>> print(specmessage_one.message.subject)
    test message subject
