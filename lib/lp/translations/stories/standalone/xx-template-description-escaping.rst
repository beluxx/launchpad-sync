Make the test browser look like it's coming from an arbitrary South African
IP address, since we'll use that later.

    >>> user_browser.addHeader('X_FORWARDED_FOR', '196.36.161.227')

    >>> import re
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.app.enums import ServiceUsage

    >>> login('foo.bar@canonical.com')
    >>> package = factory.makeSourcePackage()
    >>> template = removeSecurityProxy(factory.makePOTemplate(
    ...     distroseries=package.distroseries,
    ...     sourcepackagename=package.sourcepackagename))
    >>> distribution = template.distroseries.distribution
    >>> distribution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> template.distroseries.hide_all_translations = False
    >>> template.description = "See http://example.com/ for an example!"
    >>> package_url = canonical_url(package, rootsite='translations')
    >>> template_url = canonical_url(template, rootsite='translations')
    >>> logout()
    >>> transaction.commit()

    >>> def find_description(url):
    ...     user_browser.open(url)
    ...     main = find_main_content(user_browser.contents)
    ...     return re.findall("See[^!]*!", main.decode_contents(), re.DOTALL)

The template's description is linkified, so the URL is clickable.

    >>> description = find_description(template_url)
    >>> len(description)
    1
    >>> print(description[0])
    See <a href="http://example.com/" ...>...</a> for an example!

The same description also shows up on the +translate page for the
package.  Again,the URL is clickable.

    >>> description = find_description(package_url + '/+translations')
    >>> len(description)
    1
    >>> print(description[0])
    See <a href="http://example.com/" ...>...</a> for an example!
