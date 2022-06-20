We export DOAP RDF metadata for products from a link in the
/productname/+index document:

    >>> anon_browser.open("http://launchpad.test/firefox")
    >>> anon_browser.getLink("RDF metadata").click()
    >>> print(anon_browser.contents)
    <?xml version="1.0" encoding="utf-8"...?>
    <rdf:RDF ...xmlns:lp="https://launchpad.net/rdf/launchpad#"...>
    <lp:Product>
      <lp:specifiedAt rdf:resource="/firefox/+rdf"...
      <lp:name>firefox</lp:name>
      <lp:displayName>Mozilla Firefox</lp:displayName>
      <lp:title>Mozilla Firefox</lp:title>
    ...
      <lp:owner>
        <foaf:Agent>
          <foaf:Account rdf:resource="/~name12/+rdf"/>
        </foaf:Agent>
      </lp:owner>
    ...
    </lp:Product>
    </rdf:RDF>
    <BLANKLINE>

And it's valid XML and RDF:

    >>> from xml.dom.minidom import parseString
    >>> document = parseString(str(anon_browser.contents))
    >>> print(document.documentElement.nodeName)
    rdf:RDF
