Check that the productseries RDF export works.

    >>> print(http(r"""
    ... GET /firefox/trunk/+rdf HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    Content-Disposition: attachment; filename="firefox-trunk.rdf"
    Content-Length: ...
    Content-Type: application/rdf+xml;charset="utf-8"
    ...
    Vary: ...
    <BLANKLINE>
    <?xml version="1.0" encoding="utf-8"...?>
    <rdf:RDF ...
