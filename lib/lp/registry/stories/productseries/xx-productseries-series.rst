ProductSeries series page
=========================

    # There are no obsolete series in the data, create one.
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.series import SeriesStatus

    >>> login('test@canonical.com')
    >>> productset = getUtility(IProductSet)
    >>> firefox = productset.getByName('firefox')
    >>> series = factory.makeProductSeries(
    ...     name='xxx', product=firefox, summary='Use true GTK UI.')
    >>> series.status = SeriesStatus.OBSOLETE
    >>> transaction.commit()
    >>> logout()

Each project has a page that lists the status of all its series.

    >>> anon_browser.open('http://launchpad.test/firefox')
    >>> anon_browser.getLink('View full history').click()
    >>> print(anon_browser.title)
    timeline...

Each series, the status, milestones, releases, bugs and blueprints are
listed.

    >>> content = find_main_content(anon_browser.contents)
    >>> series_trunk = find_tag_by_id(content, 'series-trunk')
    >>> print(extract_text(series_trunk))
    trunk series Focus of Development
    Latest milestones: 1.0    Latest releases: 0.9.2, 0.9.1, 0.9
    Bugs targeted: None
    Blueprints targeted: 1 Unknown
    The "trunk" series represents the primary line of development rather ...

Any user can see that the trunk series is the focus of development and that
it is highlighted.

    >>> print(' '.join(series_trunk['class']))
    highlight series

The 1.0 series is not the focus of development, it is active, so it is not
highlighted.

    >>> series_1_0 = find_tag_by_id(content, 'series-1-0')
    >>> print(extract_text(series_1_0))
    1.0 series Active Development
    Latest releases: 1.0.0
    Bugs targeted: 1 New
    Blueprints targeted: None
    The 1.0 branch of the Mozilla web browser. Currently, this is the ...

    >>> print(' '.join(series_1_0['class']))
    series

Any user can see that obsolete series are lowlight. Obsolete series do not
show bug status counts because it is expensive to retrieve the information.

    >>> series_xxx = find_tag_by_id(content, 'series-xxx')
    >>> print(extract_text(series_xxx))
    xxx series Obsolete
    Blueprints targeted: None
    Use true GTK UI.

    >>> print(' '.join(series_xxx['class']))
    lowlight series
