Person RDF Pages
================

We export FOAF RDF metadata from the /~Person.name/+index document.

    >>> from lp.services.beautifulsoup import (
    ...     BeautifulSoup,
    ...     SoupStrainer,
    ... )
    >>> anon_browser.open("http://launchpad.test/~name16")
    >>> strainer = SoupStrainer(["link"], {"type": ["application/rdf+xml"]})
    >>> soup = BeautifulSoup(anon_browser.contents, parse_only=strainer)
    >>> print(soup.decode_contents())
    <link href="+rdf" rel="meta" title="FOAF" type="application/rdf+xml"/>


Individual RDF
--------------

And this is what the FOAF document for an individual actually looks
like. It includes GPG information, if the user has any.

    >>> anon_browser.open("http://launchpad.test/~name16/+rdf")
    >>> print(anon_browser.contents)  # noqa
    <?xml version="1.0"...?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:foaf="http://xmlns.com/foaf/0.1/"
             xmlns:lp="https://launchpad.net/rdf/launchpad#"
             xmlns:wot="http://xmlns.com/wot/0.1/">
      <foaf:Person>
        <foaf:name>Foo Bar</foaf:name>
        <foaf:nick>name16</foaf:nick>
        <foaf:mbox_sha1sum>D248D2313390766929B6CEC214BD9B640F5EA7E7</foaf:mbox_sha1sum>
        <wot:hasKey>
          <wot:PubKey>
            <wot:hex_id>12345678</wot:hex_id>
            <wot:length>1024</wot:length>
            <wot:fingerprint>ABCDEF0123456789ABCDDCBA0000111112345678</wot:fingerprint>
            <wot:pubkeyAddress rdf:resource="https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&amp;op=index&amp;search=0xABCDEF0123456789ABCDDCBA0000111112345678"/>
          </wot:PubKey>
        </wot:hasKey>
      </foaf:Person>
    </rdf:RDF>

It also includes SSH keys:

    >>> anon_browser.open("http://launchpad.test/~name12/+rdf")
    >>> print(anon_browser.contents)
    <?xml version="1.0"...?>
    ...
    <foaf:name>Sample Person</foaf:name>
    ...
    <lp:sshPubKey>AAAAB3NzaC1kc3MAAAE...</lp:sshPubKey>
    ...

And it's valid XML and RDF:

    >>> from xml.dom.minidom import parseString
    >>> document = parseString(str(anon_browser.contents))
    >>> print(document.documentElement.nodeName)
    rdf:RDF


Team RDF
--------

Teams also have an RDF export, which includes information for each
member of the team. Let's add a logo to Mark's user so we can see the
output:

    >>> from lp.testing.branding import set_branding
    >>> mark_browser = setupBrowser(auth="Basic mark@example.com:test")
    >>> mark_browser.open("http://launchpad.test/~mark/+branding")
    >>> set_branding(mark_browser, icon=False)
    >>> mark_browser.getControl("Change Branding").click()

Now, generate the RDF itself:

    >>> from lp.services.helpers import backslashreplace
    >>> anon_browser.open("http://launchpad.test/~testing-spanish-team/+rdf")
    >>> print(backslashreplace(anon_browser.contents))
    <?xml version="1.0"...?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:foaf="http://xmlns.com/foaf/0.1/"
             xmlns:lp="https://launchpad.net/rdf/launchpad#"
             xmlns:wot="http://xmlns.com/wot/0.1/">
      <foaf:Group>
        <foaf:name>testing Spanish team</foaf:name>
        <foaf:nick>testing-spanish-team</foaf:nick>
        <foaf:member rdf:resource="/~carlos/+rdf"/>
        <foaf:member rdf:resource="/~name16/+rdf"/>
        <foaf:member rdf:resource="/~mark/+rdf"/>
    ...
      </foaf:Group>
    </rdf:RDF>


Corner Cases
------------

Note how ascii and non-ascii names are rendered properly:

    >>> anon_browser.open("http://launchpad.test/~carlos/+rdf")
    >>> strainer = SoupStrainer(["foaf:name"])
    >>> soup = BeautifulSoup(anon_browser.contents, parse_only=strainer)
    >>> for tag in soup:
    ...     print(tag.decode_contents())
    ...
    Carlos Perelló Marín

If the team has no active members no <foaf:member> elements will be
present:

    >>> anon_browser.open("http://launchpad.test/~name21/+rdf")
    >>> strainer = SoupStrainer(["foaf:member"])
    >>> soup = BeautifulSoup(anon_browser.contents, parse_only=strainer)
    >>> len(soup)
    0

And nothing about them is rendered at all:

    >>> print(anon_browser.contents)
    <?xml version="1.0"...?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:foaf="http://xmlns.com/foaf/0.1/"
             xmlns:lp="https://launchpad.net/rdf/launchpad#"
             xmlns:wot="http://xmlns.com/wot/0.1/">
      <foaf:Group>
        <foaf:name>Hoary Gnome Team</foaf:name>
        <foaf:nick>name21</foaf:nick>
      </foaf:Group>
    </rdf:RDF>
