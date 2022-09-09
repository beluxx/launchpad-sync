================
Codes of Conduct
================

Administrators can see the signed Ubuntu Code of Conducts of any given person.

    >>> admin_browser.open("http://launchpad.test/~name16")
    >>> admin_browser.url
    'http://launchpad.test/~name16'
    >>> print(
    ...     extract_text(find_tag_by_id(admin_browser.contents, "ubuntu-coc"))
    ... )
    Signed Ubuntu Code of Conduct: Yes

    >>> admin_browser.getLink(url="+codesofconduct").click()
    >>> signatures = find_tags_by_class(admin_browser.contents, "signature")
    >>> for signature in signatures:
    ...     print(extract_text(signature))
    ...
    2005-09-27: digitally signed by Foo Bar
    (1024D/ABCDEF0123456789ABCDDCBA0000111112345678)

A regular user can't see the link to Foo Bar's signed codes of conduct.

    >>> browser.open("http://launchpad.test/~name16")
    >>> print(extract_text(find_tag_by_id(browser.contents, "ubuntu-coc")))
    Signed Ubuntu Code of Conduct: Yes

    >>> browser.getLink(url="+codesofconduct")
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

No-priv hasn't signed the Ubuntu Code of Conduct yet.  Their homepage has a
link to the Ubuntu Code of Conduct forms.

    >>> browser.addHeader("Authorization", "Basic no-priv@canonical.com:test")
    >>> browser.open("http://launchpad.test/~no-priv")
    >>> print(extract_text(find_tag_by_id(browser.contents, "ubuntu-coc")))
    Signed Ubuntu Code of Conduct: No

    >>> browser.getLink(url="codeofconduct")
    <Link
      text='Sign the Ubuntu Code of Conduct[IMG]'
      url='http://launchpad.test/codeofconduct'>
