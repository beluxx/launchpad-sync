Check that the productrelease RDF export works.

    >>> print(http(r"""
    ... GET /firefox/trunk/0.9/+rdf HTTP/1.1
    ... """))
    HTTP/1.1 200 Ok
    Content-Disposition: attachment; filename="firefox-trunk-0.9.rdf"
    Content-Length: ...
    Content-Type: application/rdf+xml;charset="utf-8"
    ...
    Vary: ...
    <BLANKLINE>
    <?xml version="1.0" encoding="utf-8"...?>
    <rdf:RDF ...
