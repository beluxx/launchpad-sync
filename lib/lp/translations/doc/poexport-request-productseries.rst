Product Series Translation Exports
==================================


    >>> from zope.component import getUtility
    >>> from lp.translations.interfaces.poexportrequest import (
    ...     IPOExportRequestSet,
    ... )

This is a dummy logger class to capture the export's log messages.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.services.log.logger import FakeLogger
    >>> person = getUtility(IPersonSet).getByName("name12")

An arbitrary logged-in user requests an export of all translations for
Evolution series trunk.

At the UI level, this is easy.  At the level we are looking at now, this
consists of a series of requests for all templates and translations attached
to the product series.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.translations.interfaces.potemplate import IPOTemplateSet
    >>> evolution_product = getUtility(IProductSet).getByName("evolution")
    >>> evolution_trunk = evolution_product.getSeries("trunk")
    >>> potemplates = list(
    ...     getUtility(IPOTemplateSet).getSubset(
    ...         productseries=evolution_trunk
    ...     )
    ... )
    >>> pofiles = []
    >>> for template in potemplates:
    ...     pofiles.extend(template.pofiles)
    ...

    >>> request_set = getUtility(IPOExportRequestSet)
    >>> request_set.addRequest(person, potemplates, pofiles)

Now we request that the queue be processed.

    >>> import transaction
    >>> from lp.translations.scripts.po_export_queue import process_queue
    >>> logger = FakeLogger()
    >>> transaction.commit()
    >>> process_queue(transaction, logger)
    DEBUG Exporting objects for ..., related to template evolution-2.2 in
    Evolution trunk
    DEBUG Exporting objects for ..., related to template evolution-2.2-test in
    Evolution trunk
    INFO Stored file at http://.../launchpad-export.tar.gz

The user receives a confirmation email.

    >>> from lp.testing.mail_helpers import pop_notifications, print_emails
    >>> test_emails = pop_notifications()
    >>> len(test_emails)
    1
    >>> print_emails(notifications=test_emails, decode=True)  # noqa
    From: ...
    Subject: Launchpad translation download: Evolution trunk
    Hello ...,
    <BLANKLINE>
    The translation files you requested from Launchpad are ready for
    download from the following location:
    <BLANKLINE>
      http://.../launchpad-export.tar.gz
    <BLANKLINE>
    Note: this link will expire in about 1 week.  If you want to
    download these translations again, you will have to request
    them again at
    <BLANKLINE>
      http://translations.launchpad.test/evolution/trunk/+export
    <BLANKLINE>
    -- 
    Automatic message from Launchpad.net.
    ----------------------------------------

The email contains a URL linking to where the exported file can be downloaded.

    >>> import re

    >>> def extract_url(text):
    ...     urls = re.compile(r"^ *(http://.*)$", re.M).findall(text)
    ...     return urls[0]
    ...

    >>> body = test_emails[0].get_payload()
    >>> url = extract_url(body)

Let's download it and make sure the contents look ok.

    >>> from urllib.request import urlopen
    >>> from lp.services.helpers import bytes_to_tarfile
    >>> tarball = bytes_to_tarfile(urlopen(url).read())
    >>> for name in sorted(tarball.getnames()):
    ...     print(name)
    ...
    evolution-2.2
    evolution-2.2/evolution-2.2-es.po
    po
    po/evolution-2.2-test-pt_BR.po
    po/evolution-2.2-test.pot
    po/evolution-2.2.pot
