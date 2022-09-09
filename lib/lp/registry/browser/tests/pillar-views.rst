Pillar views
============

Pillar views are used to display IPillar objects link distributions and
products in a consistent fashion.

The +get-involved presentation creates a portlet of links to encourage
project involvement. Only links to official applications are rendered.


    >>> distribution = factory.makeDistribution(name="umbra")
    >>> ignored = login_person(distribution.owner)
    >>> view = create_view(
    ...     distribution, "+get-involved", principal=distribution.owner
    ... )

The has_involvement property is used to determine if the portlet should
be rendered. The newly created pillar does not use any launchpad applications.

    >>> view.has_involvement
    False

    >>> print(view.render())
    <BLANKLINE>

Pillars that do use launchpad applications have an involvement menu.

    >>> from lp.app.enums import ServiceUsage
    >>> distribution.answers_usage = ServiceUsage.LAUNCHPAD
    >>> distribution.official_malone = True
    >>> view = create_view(
    ...     distribution, "+get-involved", principal=distribution.owner
    ... )
    >>> view.has_involvement
    True

    >>> view.official_malone
    True
    >>> print(view.answers_usage.name)
    LAUNCHPAD
    >>> print(view.translations_usage.name)
    UNKNOWN
    >>> print(view.blueprints_usage.name)
    UNKNOWN
    >>> print(view.codehosting_usage.name)
    UNKNOWN

The view provides a list of enabled links that is rendered by the template.

    >>> for link in view.enabled_links:
    ...     print(link.name)
    ...
    report_bug ask_question

    >>> print(view.render())
    <div id="involvement" class="portlet">
      <h2>Get Involved</h2>
      <ul class="involvement">
        <li>
          <a class="...bugs" href=...>Report a bug</a>...
        </li>
        <li>
          <a class="...answers" href=...>Ask a question</a>...
        </li>
      </ul>
    ...

Products are supported.

    >>> product = factory.makeProduct(name="bread")
    >>> ignored = login_person(product.owner)
    >>> product.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> view = create_view(product, "+get-involved")
    >>> print(view.blueprints_usage.name)
    LAUNCHPAD
    >>> for link in view.enabled_links:
    ...     print(link.name)
    ...
    register_blueprint

Products subclass the view to display disabled links to encourage
configuring that service in Launchpad for the project. The product
also has configuration links that make it easy to figure out where
to configure each service.

    >>> for link in view.visible_disabled_links:
    ...     print(link.name)
    ...
    report_bug
    ask_question
    help_translate

    >>> for link in view.configuration_links:
    ...     print(link["link"].name)
    ...
    configure_code
    configure_bugtracker
    configure_translations
    configure_answers

The registration status is determined with the 'configuration_states'
property.  Notice that blueprints are not included in the
configuration links nor the completeness computation as the use of
blueprints is not promoted.

    >>> for key in sorted(view.configuration_states.keys()):
    ...     print(key, view.configuration_states[key])
    ...
    configure_answers False
    configure_bugtracker False
    configure_code False
    configure_translations False

The percentage of the registration completed can be determined by
using the 'registration_completeness' property, which returns a
dictionary, which makes it easy for use in the page template.

    >>> print(pretty(view.registration_completeness))
    {'done': 0,
     'undone': 100}

Changing the product's usage is reflected in the view properties.

    >>> product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> view = create_view(product, "+get-involved")
    >>> for key in sorted(view.configuration_states.keys()):
    ...     print(key, view.configuration_states[key])
    ...
    configure_answers False
    configure_bugtracker False
    configure_code False
    configure_translations True

    >>> print(pretty(view.registration_completeness))
    {'done': 25,
     'undone': 75}

The progress bar is shown as a green bar.

    >>> from lp.testing.pages import find_tag_by_id
    >>> rendered = view.render()
    >>> print(find_tag_by_id(rendered, "progressbar"))
    <div id="progressbar" ...>
    <img ...src="/@@/green-bar" ... width: 25%.../>
    ...

Each application is displayed (except for blueprints) with an
indicator showing whether it has been configured or not.

    >>> print(find_tag_by_id(rendered, "configuration_links"))
    <table...
    <a ...href="http://launchpad.test/bread/+configure-code"...
    <span class="sprite no action-icon">...
    <a ...href="http://launchpad.test/bread/+configure-bugtracker"...
    <span class="sprite no action-icon">...
    <a ...href="http://launchpad.test/bread/+configure-translations"...
    <span class="sprite yes action-icon">...
    <a ...href="http://launchpad.test/bread/+configure-answers"...
    <span class="sprite no action-icon">...
    </table>

Project groups are supported too, but they only display the
applications used by their products.

    >>> project_group = factory.makeProject(name="box", owner=product.owner)
    >>> product.projectgroup = project_group

    >>> view = create_view(project_group, "+get-involved")
    >>> print(view.blueprints_usage.name)
    LAUNCHPAD

The offical_codehosting for a project is based on whether the project's
development focus series has a branch.

    >>> print(product.development_focus.branch)
    None
    >>> product.official_codehosting
    False
    >>> view = create_view(product, "+get-involved")
    >>> print(view.codehosting_usage.name)
    UNKNOWN

    >>> product.development_focus.branch = factory.makeBranch(product=product)
    >>> product.official_codehosting
    True
    >>> view = create_view(product, "+get-involved")
    >>> print(view.codehosting_usage.name)
    LAUNCHPAD

    >>> from lp.code.enums import BranchType
    >>> remote = factory.makeProduct()
    >>> branch = factory.makeProductBranch(
    ...     product=remote, branch_type=BranchType.REMOTE
    ... )
    >>> remote.official_codehosting
    False
    >>> view = create_view(remote, "+get-involved")
    >>> print(view.codehosting_usage.name)
    UNKNOWN


Project groups cannot make links to register a branch, so
official_codehosting is always false.

    >>> view = create_view(project_group, "+get-involved")
    >>> print(view.codehosting_usage.name)
    NOT_APPLICABLE

Project groups ignore products translations_usage setting if none of the
products are fully configured as translatable.

    >>> product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> project_group.has_translatable()
    False

    >>> view = create_view(project_group, "+get-involved")
    >>> print(view.translations_usage.name)
    UNKNOWN

If a product is translatable, translations is enabled in the involvment menu.

    >>> series = factory.makeProductSeries(product=product)
    >>> pot = factory.makePOTemplateAndPOFiles(
    ...     productseries=series, language_codes=["es"]
    ... )
    >>> product.translations_usage = ServiceUsage.LAUNCHPAD
    >>> from lp.services.propertycache import clear_property_cache
    >>> clear_property_cache(project_group)
    >>> project_group.has_translatable()
    True

    >>> view = create_view(project_group, "+get-involved")
    >>> print(view.translations_usage.name)
    LAUNCHPAD

DistroSeries can use this view. The distribution is used to set the links.

    >>> series = factory.makeDistroSeries(distribution=distribution)
    >>> view = create_view(series, "+get-involved")
    >>> for link in view.enabled_links:
    ...     print(link.name)
    ...
    report_bug

DistributionSourcePackages can use this view. The distribution is used to
set the links.  Despite the fact that the distribution uses blueprints,
and translations those links are not enabled for DistributionSourcePackages.

    >>> from lp.app.enums import ServiceUsage
    >>> ignored = login_person(distribution.owner)
    >>> distribution.blueprints_usage = ServiceUsage.LAUNCHPAD
    >>> distribution.translations_usage = ServiceUsage.LAUNCHPAD
    >>> package = factory.makeDistributionSourcePackage(
    ...     sourcepackagename="box", distribution=distribution
    ... )
    >>> view = create_view(package, "+get-involved")
    >>> for link in view.enabled_links:
    ...     print(link.name)
    ...
    report_bug ask_question


Involvement links
-----------------

The pillar involvement view uses the InvolvedMenu when rendering links.

    >>> from lp.app.browser.tales import MenuAPI
    >>> from operator import attrgetter

The menu when viewed from a product page.

    >>> view = create_view(product, "+get-involved")
    >>> menuapi = MenuAPI(view)
    >>> for link in sorted(
    ...     menuapi.navigation.values(), key=attrgetter("sort_key")
    ... ):
    ...     print(link.url)
    http://bugs.launchpad.test/bread/+filebug
    http://answers.launchpad.test/bread/+addquestion
    http://translations.launchpad.test/bread
    http://blueprints.launchpad.test/bread/+addspec

    >>> from lp.registry.browser.pillar import InvolvedMenu
    >>> from lp.testing.menu import check_menu_links
    >>> check_menu_links(InvolvedMenu(product))
    True

The menu when viewed from a distribution page.

    >>> view = create_view(distribution, "+get-involved")
    >>> menuapi = MenuAPI(view)
    >>> for link in sorted(
    ...     menuapi.navigation.values(), key=attrgetter("sort_key")
    ... ):
    ...     if link.enabled:
    ...         print(link.url)
    http://bugs.launchpad.test/umbra/+filebug
    http://answers.launchpad.test/umbra/+addquestion
    http://translations.launchpad.test/umbra
    http://blueprints.launchpad.test/umbra/+addspec

The menu when viewed from a distribution source package page.

    >>> view = create_view(package, "+get-involved")
    >>> menuapi = MenuAPI(view)
    >>> for link in sorted(
    ...     menuapi.navigation.values(), key=attrgetter("sort_key")
    ... ):
    ...     if link.enabled:
    ...         print(link.url)
    http://bugs.launchpad.test/umbra/+source/box/+filebug
    http://answers.launchpad.test/umbra/+source/box/+addquestion
