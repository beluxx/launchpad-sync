RequestPreferredLanguages.getPreferredLanguages() returns language objects
based on the Accept-language header. If we can't encode the language code
in ASCII we just skip them.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.services.geoip.model import RequestPreferredLanguages

    >>> langs = {'HTTP_ACCEPT_LANGUAGE': 'pt_BR, Espa\xf1ol'}
    >>> request = LaunchpadTestRequest(**langs)
    >>> for l in RequestPreferredLanguages(request).getPreferredLanguages():
    ...     print(l.code)
    pt_BR

    >>> langs = {'HTTP_ACCEPT_LANGUAGE': u'pt_BR, Espa\xf1ol'}
    >>> request = LaunchpadTestRequest(**langs)
    >>> for l in RequestPreferredLanguages(request).getPreferredLanguages():
    ...     print(l.code)
    pt_BR

The getPreferredLanguages() method returns unique codes.

    >>> langs = {
    ...     'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.9,de-CH;q=0.8,de;q=0.6,'
    ...                             'en-GB;q=0.4,en-us;q=0.3,en;q=0.1'
    ...     }
    >>> request = LaunchpadTestRequest(**langs)
    >>> for l in RequestPreferredLanguages(request).getPreferredLanguages():
    ...     print(l.code)
    en
    en_GB
    de
