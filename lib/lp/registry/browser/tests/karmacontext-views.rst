KarmaContext Pages
==================

For all KarmaContexts we can see their top contributors.  That is, the
people with highest karma on that context.  We can see the top overall
contributors on a given context and the top contributors by category.

    >>> from lp.testing.pages import extract_text, find_tag_by_id
    >>> from lp.registry.interfaces.product import IProductSet

    >>> product = getUtility(IProductSet).getByName("evolution")
    >>> user = product.owner
    >>> ignored = login_person(user)
    >>> view = create_initialized_view(
    ...     product, "+topcontributors", principal=user
    ... )
    >>> contributors = view._getTopContributorsWithLimit(limit=3)
    >>> for contrib in contributors:
    ...     print(contrib.person.name, contrib.karmavalue)
    ...
    name16 175
    mark 22
    carlos 9

    >>> contributors = view.top_contributors_by_category
    >>> categories = sorted(contributors.keys())
    >>> for category in categories:
    ...     print(category)
    ...     for contrib in contributors[category]:
    ...         print(contrib.person.name, contrib.karmavalue)
    ...
    Bug Management
    name16 11
    Specification Tracking
    mark 22
    Translations in Rosetta
    name16 164
    carlos 9

The view renders summaries by category.

    >>> content = find_tag_by_id(view.render(), "maincontent")
    >>> print(extract_text(find_tag_by_id(content, "overall_top")))
    Person             Project Karma  Total Karma
    Foo Bar            175            241
    Mark Shuttleworth   22            130
    Carlos ...           9              9

    >>> print(extract_text(find_tag_by_id(content, "Bug Management")))
    Person   Bug Management Karma  Total Karma
    Foo Bar  11                     241

    >>> print(extract_text(find_tag_by_id(content, "Specification Tracking")))
    Person             Specification Tracking Karma  Total Karma
    Mark Shuttleworth  22                            130

    >>> print(
    ...     extract_text(find_tag_by_id(content, "Translations in Rosetta"))
    ... )
    Person      Translations in Rosetta Karma  Total Karma
    Foo Bar     164                            241
    Carlos ...    9                              9


Top contributors portlet
------------------------

The top contributors portlet shows the top contributors to a project

    >>> view = create_initialized_view(
    ...     product, name="+portlet-top-contributors", principal=user
    ... )
    >>> content = find_tag_by_id(view.render(), "portlet-top-contributors")
    >>> print(extract_text(content))
    More contributors Top contributors
    Foo Bar...
    Mark ...
    Carlos ...

It has a link to +topcontributors page.

    >>> css_class = {"class": "menu-link-top_contributors sprite info"}
    >>> link = content.find("a", css_class)
    >>> print(link["href"])
    http://launchpad.test/evolution/+topcontributors
