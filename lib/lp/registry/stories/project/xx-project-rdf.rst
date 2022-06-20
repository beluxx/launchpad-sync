We export DOAP RDF metadata for projects from a link in the
/projectname/+index document:

    >>> anon_browser.open("http://launchpad.test/mozilla")
    >>> anon_browser.getLink("Download RDF metadata").click()
    >>> print(anon_browser.contents)
    <?xml version="1.0" encoding="utf-8"...
    <rdf:RDF ...xmlns:lp="https://launchpad.net/rdf/launchpad#"...
    <lp:Project>
      <lp:specifiedAt rdf:resource="/mozilla/+rdf"...
      <lp:name>mozilla</lp:name>
      <lp:displayName>The Mozilla Project</lp:displayName>
      <lp:title>The Mozilla Project</lp:title>
    ...
      <lp:owner>
        <foaf:Agent>
          <foaf:Account rdf:resource="/~name12/+rdf"/>
        </foaf:Agent>
      </lp:owner>
    ...
     </lp:Project>
    </rdf:RDF>

It's valid XML and RDF:

    >>> from xml.dom.minidom import parseString
    >>> document = parseString(str(anon_browser.contents))
    >>> print(document.documentElement.nodeName)
    rdf:RDF
