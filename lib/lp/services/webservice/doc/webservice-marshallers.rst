LAZR's field marshallers
========================

LAZR defines an interface for converting between the values that
come in on an HTTP request, and the object values appropriate for schema
fields. This is similar to Zope's widget interface, but much smaller.

To test the various marshallers we create a dummy request and
application root.

    >>> from lp.services.webapp.adapter import set_request_started
    >>> from lp.services.webapp.servers import (
    ...     WebServicePublication,
    ...     WebServiceTestRequest,
    ... )
    >>> request = WebServiceTestRequest(method="GET")
    >>> set_request_started()
    >>> request.setPublication(WebServicePublication(None))
    >>> login(ANONYMOUS, request)
    >>> request.processInputs()

    >>> from lp.systemhomes import WebServiceApplication
    >>> root = WebServiceApplication()
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag
    >>> getUtility(IOpenLaunchBag).add(root)


Choice of SQLObjectVocabularyBase
.................................

For vocabularies based on SQLObjectVocabularyBase, the values are
interpreted as URLs referencing objects on the web service. If the given
string is a URL corresponding to a vocabulary item, the marshaller
returns that item. Otherwise it raises a ValueError.

    >>> from zope.component import getMultiAdapter
    >>> from zope.schema import Choice
    >>> from lazr.restful import EntryResource
    >>> from lazr.restful.fields import ReferenceChoice
    >>> from lazr.restful.interfaces import IFieldMarshaller
    >>> from lp.registry.interfaces.person import IPerson

    # Bind the field, to resolve the vocabulary name.
    >>> field = ReferenceChoice(
    ...     __name__="some_person",
    ...     vocabulary="ValidPersonOrTeam",
    ...     schema=IPerson,
    ... )
    >>> field = field.bind(None)
    >>> marshaller = getMultiAdapter((field, request), IFieldMarshaller)
    >>> verifyObject(IFieldMarshaller, marshaller)
    True

    >>> from lp.registry.interfaces.person import IPerson
    >>> person = marshaller.marshall_from_request(
    ...     "http://api.launchpad.test/beta/~salgado"
    ... )
    >>> IPerson.providedBy(person)
    True
    >>> print(person.name)
    salgado

    >>> ubuntu_team = marshaller.marshall_from_json_data(
    ...     "http://api.launchpad.test/beta/~ubuntu-team"
    ... )
    >>> print(ubuntu_team.name)
    ubuntu-team

    >>> marshaller.marshall_from_request(
    ...     "http://api.launchpad.test/beta/~nosuchperson"
    ... )
    Traceback (most recent call last):
    ...
    ValueError: No such object "http://api.launchpad.test/beta/~nosuchperson".

    >>> marshaller.marshall_from_json_data("salgado")
    Traceback (most recent call last):
    ...
    ValueError: "salgado" is not a valid URI.

Instead of unmarshall() returning the Person object (which
wouldn't look nice in a JSON representation), this marshaller returns
the URL to that object.

    >>> person_resource = EntryResource(person, request)

    >>> print(marshaller.unmarshall(person_resource, person))
    http://.../~salgado

This marshaller also appends '_link' to the representation name of
this field, so that clients can know this is a link to another
resource and not a random string.

    >>> print(marshaller.representation_name)
    some_person_link

If you export a Choice that uses an SQLObjectVocabularyBase then you
get an error, as you should be using a ReferenceChoice instead to
ensure that the resulting wadl matches lazr.restful conventions.

    >>> field = Choice(__name__="some_person", vocabulary="ValidPersonOrTeam")
    >>> field = field.bind(None)
    >>> getMultiAdapter((field, request), IFieldMarshaller)
    ... # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    AssertionError: You exported some_person as an IChoice based on an
    SQLObjectVocabularyBase/StormVocabularyBase; you should use
    lazr.restful.fields.ReferenceChoice instead.

Cleanup.

    >>> request.oopsid = None
    >>> request.publication.endRequest(request, None)
