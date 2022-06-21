Bug Reporting Guidelines
========================

Guidelines can be set at the Distribution, DistributionSourcePackage,
ProjectGroup or Product level to help users file good bug reports, direct
them to FAQs, and so forth.

    >>> login('foo.bar@canonical.com')

    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.registry.interfaces.projectgroup import IProjectGroupSet

    >>> distribution = getUtility(IDistributionSet).getByName('ubuntu')
    >>> distribution_source_package = (
    ...     distribution.getSourcePackage('alsa-utils'))
    >>> project = getUtility(IProjectGroupSet).getByName('mozilla')
    >>> product = getUtility(IProductSet).getByName('firefox')

    >>> settable_contexts = [
    ...     distribution,
    ...     distribution_source_package,
    ...     project,
    ...     product,
    ...     ]

    >>> for context in settable_contexts:
    ...     context.bug_reporting_guidelines = (
    ...         "Welcome to %s!" % context.displayname)

In fact, all IBugTargets have guidelines available, but the others
delegate to the distribution or product level.

DistroSeries and SourcePackages defer to the Distribution:

    >>> distro_series = distribution.getSeries('warty')
    >>> print(distro_series.bug_reporting_guidelines)
    Welcome to Ubuntu!

    >>> source_package = distro_series.getSourcePackage('alsa-utils')
    >>> print(source_package.bug_reporting_guidelines)
    Welcome to Ubuntu!

ProductSeries defer to the Product:

    >>> product_series = product.getSeries('trunk')
    >>> print(product_series.bug_reporting_guidelines)
    Welcome to Mozilla Firefox!

One day these objects that defer bug_reporting_guidelines may have
their own guidelines. In the meantime the deferral is done with a
read-only property, and the security proxies also only allow read
access.

    >>> distro_series.bug_reporting_guidelines = 'Foobar'
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> source_package.bug_reporting_guidelines = 'Foobar'
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

    >>> product_series.bug_reporting_guidelines = 'Foobar'
    Traceback (most recent call last):
    ...
    zope.security.interfaces.ForbiddenAttribute: ...

The security proxies also prevent unprivileged users from editing the
guidelines.

    >>> from lp.registry.interfaces.person import IPerson

    >>> def check_access(user, context):
    ...     if IPerson.providedBy(user):
    ...         login_person(user)
    ...     else:
    ...         login(user)
    ...     context.bug_reporting_guidelines = (
    ...         "%s let %s have access." % (
    ...             context.displayname,
    ...             getUtility(ILaunchBag).user.displayname))
    ...     print(context.bug_reporting_guidelines)

    >>> check_access("no-priv@canonical.com", distribution)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> check_access("no-priv@canonical.com", distribution_source_package)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> check_access("no-priv@canonical.com", project)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

    >>> check_access("no-priv@canonical.com", product)
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Of course the owner can edit the guidelines.

    >>> check_access(distribution.owner.activemembers[0], distribution)
    Ubuntu let Alexander Limi have access.

    >>> check_access(project.owner, project)
    The Mozilla Project let Sample Person have access.

    >>> check_access(product.owner, product)
    Mozilla Firefox let Sample Person have access.

In the case of DistributionSourcePackages, the owner of the
Distribution can edit the guidelines.

    >>> check_access(
    ...     distribution_source_package.distribution.owner.activemembers[0],
    ...     distribution_source_package)
    alsa-utils in Ubuntu let Alexander Limi have access.
