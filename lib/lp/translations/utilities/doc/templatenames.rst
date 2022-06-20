Deriving template names from template paths
===========================================

Template names can be derived from template paths. The name usually matches
the translation domain but translation domains may contain characters that
template names may not, most notably capital characters and underscores.

The template utitlity module provides functions for these conversions. They
also know how to detect xpi templates and generic template file names and
derive translation domains from directory names, if possible.

    >>> from lp.translations.utilities.template import make_domain
    >>> print(make_domain("po/my_domain.pot"))
    my_domain
    >>> print(make_domain("po/my_domain/messages.pot"))
    my_domain
    >>> print(make_domain("my_module/po/messages.pot"))
    my_module
    >>> print(make_domain("my_domain/en-US.xpi"))
    my_domain

If a template path is generic, no translation domain can be derived.

    >>> print(make_domain("po/messages.pot"))
    <BLANKLINE>

The conversion from domain to template name replaces underscores (_) with
dashes (-) and makes all characters lower case. Invalid characters are
removed.

    >>> from lp.translations.utilities.template import make_name
    >>> print(make_name("My_Domain"))
    my-domain
    >>> print(make_name("my #domain@home"))
    mydomainhome

Finally, the convenience function make_name_from_path chains the first two
methods.

    >>> from lp.translations.utilities.template import make_name_from_path
    >>> print(make_name_from_path("po/MyDomain/messages.pot"))
    mydomain

