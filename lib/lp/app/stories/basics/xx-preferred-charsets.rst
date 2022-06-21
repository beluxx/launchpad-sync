In order to minimise problems related to page encodings, we want all
our pages to always be encoded using utf-8, even if the client says
that it doesn't accept it.

    >>> anon_browser.addHeader('Accept-Charset', 'iso8859-1')
    >>> anon_browser.open('http://launchpad.test/')
    >>> anon_browser.headers['Content-Type']
    'text/html;charset=utf-8'

The status is still 200, instead of 406 which is recommended, since it's
better to send the page as it is, letting the client deal with the error
handling. If we would set the status to 406, some browsers (like Opera,
IE, wget) would display a custom (hard to understand) error page instead
of the actual page contents. It's also quite a lot of work returning a
406, since we'd have to make sure that files like CSS and JS files
still return 200, otherwise they won't be processed by for example
Firefox. Also, RFC 2616 states:

"""
      Note: HTTP/1.1 servers are allowed to return responses which are
      not acceptable according to the accept headers sent in the
      request. In some cases, this may even be preferable to sending a
      406 response. User agents are encouraged to inspect the headers of
      an incoming response to determine if it is acceptable.
"""

    >>> anon_browser.headers['status']
    '200 Ok'
