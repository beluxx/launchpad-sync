Searching bugtasks with old statuses
====================================

The BugWorkflow spec renames several bug statuses, but we need
bookmarks, etc., to keep working using the old status names. Instead
of simply returning the correct results, we will redirect the user
agent to the new location with a permanent redirect so it has an
opportunity to update bookmarks and so forth.

    >>> from lp.bugs.browser.buglisting import (
    ...     BugTaskSearchListingView, rewrite_old_bugtask_status_query_string)
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> ubuntu = getUtility(IDistributionSet).getByName('ubuntu')

    >>> server_url = 'http://foobar/'
    >>> query_string = 'field.status%3Alist=Unconfirmed'
    >>> request = LaunchpadTestRequest(
    ...     SERVER_URL=server_url, QUERY_STRING=query_string)
    >>> view = BugTaskSearchListingView(ubuntu, request)

    >>> view.initialize()
    >>> view.request.response.getStatus()
    301
    >>> view.request.response.getHeader('Location')
    'http://foobar/?field.status%3Alist=New'

rewrite_old_bugtask_status_query_string is the mapping function that
converts the old query string into an updated one. Only the statuses
'Unconfirmed, 'Needs Info' and 'Rejected' are converted.

    >>> query_string = (
    ...     'freddy=krueger&'
    ...     'field.status%3Alist=Unconfirmed&'
    ...     'field.status%3Alist=Needs+Info&'
    ...     'field.status%3Alist=Rejected&'
    ...     'field.status%3Alist=Fix+Committed&'
    ...     'sid=nancy'
    ...     )
    >>> query_string_rewritten = (
    ...     rewrite_old_bugtask_status_query_string(query_string))
    >>> for param in query_string_rewritten.split('&'):
    ...     print(param)
    freddy=krueger
    field.status%3Alist=New
    field.status%3Alist=Incomplete
    field.status%3Alist=Invalid
    field.status%3Alist=Fix+Committed
    sid=nancy

If the url does not contain any old statuses
rewrite_old_bugtask_status_query_string returns the original query
string unchanged.

    >>> query_string_rewritten == (
    ...     rewrite_old_bugtask_status_query_string(query_string_rewritten))
    True
