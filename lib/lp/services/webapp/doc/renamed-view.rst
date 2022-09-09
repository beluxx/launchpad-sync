RenamedView
===========

As Launchpad is reorganized, views are renamed. It is usually advisable
to leave a permanent redirect from the old name to the new name. This
allows search engines and bookmark to update transparently from the old
name to the new one.

For this case, we have a RenamedView that will take care of the
redirection.

    >>> from lp.services.webapp.publisher import RenamedView
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

Let's say we rename the '+old_tickets_page' view on IQuestionTarget to
'+questions'. A RenamedView redirecting to the new name would be created
like this:

    >>> request = LaunchpadTestRequest()
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> view = RenamedView(ubuntu, request, "+questions")

(Note that the RenamedView class doesn't need to be aware of the
previous name. The old name will be hooked up with the RenamedView
via ZCML.)

When the view is called, it redirects to the same context but with
the new name. The redirection status is 301 (Moved permently) which
will make search engines discards the old URLs and some browser to
update bookmarks.

    >>> print(view())
    <BLANKLINE>
    >>> request.response.getStatus()
    301
    >>> print(request.response.getHeader("Location"))
    http://launchpad.test/ubuntu/+questions

The view can also work for names registered on the root, and the
new_name can be a relative path.

    >>> from lp.services.webapp.interfaces import ILaunchpadRoot
    >>> root = getUtility(ILaunchpadRoot)
    >>> view = RenamedView(root, LaunchpadTestRequest(), "+tour/index.html")
    >>> print(view())
    <BLANKLINE>
    >>> request.response.getStatus()
    301
    >>> print(view.request.response.getHeader("Location"))
    http://launchpad.test/+tour/index.html


Handling GET parameters
-----------------------

If there was any query parameters on the request, they are appended
to the redirected URL.

    >>> request = LaunchpadTestRequest(QUERY_STRING="field.status=Open")
    >>> view = RenamedView(ubuntu, request, "+questions")
    >>> print(view())
    <BLANKLINE>
    >>> print(request.response.getHeader("Location"))
    http://launchpad.test/ubuntu/+questions?field.status=Open


Redirecting to another virtual host
-----------------------------------

The view also takes an optional 'rootsite' parameter, which will
change the virtual host used for the redirection.

    >>> request = LaunchpadTestRequest()
    >>> view = RenamedView(ubuntu, request, "+questions", rootsite="answers")
    >>> print(view())
    <BLANKLINE>
    >>> print(request.response.getHeader("Location"))
    http://answers.launchpad.test/ubuntu/+questions


Traversal errors
----------------

If an object cannot be found during traversal, RenamedView will raise
a NotFound error. For example, requesting a non-existent question will
raise an error. e.g. http://launchpad.test/ubuntu/+tickets/foo

    >>> request = LaunchpadTestRequest()
    >>> view = RenamedView(ubuntu, request, "+tickets")
    >>> view.publishTraverse(request, "foo")
    Traceback (most recent call last):
     ...
    zope.publisher.interfaces.NotFound:
    Object: <Distribution 'Ubuntu' (ubuntu)>, name: 'foo'


Registering from ZCML
---------------------

Finally, it is possible to register RenamedView from ZCML. The
browser:renamed-page is available for this purpose.

    >>> from zope.configuration import xmlconfig
    >>> zcmlcontext = xmlconfig.string(
    ...     """
    ... <configure xmlns:browser="http://namespaces.zope.org/browser">
    ...   <include package="zope.component" file="meta.zcml" />
    ...   <include package="lp.services.webapp" file="meta.zcml" />
    ...   <browser:renamed-page
    ...       for="lp.answers.interfaces.questiontarget.IQuestionTarget"
    ...       name="+old_tickets_page"
    ...       new_name="+questions"
    ...       rootsite="answers"
    ...       />
    ... </configure>
    ... """
    ... )

    >>> from zope.component import getMultiAdapter
    >>> request = LaunchpadTestRequest()
    >>> view = getMultiAdapter((ubuntu, request), name="+old_tickets_page")
    >>> print(view())
    <BLANKLINE>
    >>> print(request.response.getHeader("Location"))
    http://answers.launchpad.test/ubuntu/+questions
