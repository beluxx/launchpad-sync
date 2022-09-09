Translation import queue entry error output
===========================================

The approval form translation import queue entries shows any error
or warning output that the entry may have incurred.

By default, this is nothing.

    >>> from lp.translations.model.translationimportqueue import (
    ...     TranslationImportQueue,
    ... )

    >>> def find_error_output(browser):
    ...     """Find error-output section on page."""
    ...     return find_tag_by_id(browser.contents, "error-output")
    ...

    >>> login(ANONYMOUS)
    >>> queue = TranslationImportQueue()
    >>> product = factory.makeProduct()
    >>> trunk = product.getSeries("trunk")
    >>> entry = queue.addOrUpdateEntry(
    ...     "la.po", b"# contents", False, product.owner, productseries=trunk
    ... )
    >>> entry_url = canonical_url(entry, rootsite="translations")
    >>> logout()

    >>> admin_browser.open(entry_url)
    >>> output_panel = find_error_output(admin_browser)
    >>> print(output_panel)
    None

The section showing the output only shows up when there is output to
show.

    >>> entry.error_output = "Things went horribly wrong."
    >>> admin_browser.open(entry_url)
    >>> output_panel = find_error_output(admin_browser)
    >>> print(extract_text(output_panel))
    Error output for this entry:
    Things went horribly wrong.

The output is properly HTML-escaped, so is safe to display in this way.

    >>> entry.error_output = "<h1>Injection &amp; subterfuge</h1>"
    >>> admin_browser.open(entry_url)
    >>> output_panel = find_error_output(admin_browser)
    >>> print(output_panel.decode_contents())
    Error output for this entry:
    ...&lt;h1&gt;Injection &amp;amp; subterfuge&lt;/h1&gt;...
