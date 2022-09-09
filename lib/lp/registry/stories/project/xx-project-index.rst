Project group overview page
===========================

    # Add some milestones to products to verify the member project listing.
    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet

    >>> login("test@canonical.com")
    >>> productset = getUtility(IProductSet)
    >>> gnome_terminal = productset.getByName("gnome-terminal")
    >>> milestone = factory.makeMilestone(
    ...     name="2.30.0", product=gnome_terminal
    ... )
    >>> gnomebaker = productset.getByName("gnomebaker")
    >>> milestone = factory.makeMilestone(name="2.30.1", product=gnomebaker)
    >>> milestone = factory.makeMilestone(
    ...     name="2.1.7", productseries=gnomebaker.development_focus
    ... )
    >>> release = factory.makeProductRelease(milestone=milestone)
    >>> transaction.commit()
    >>> logout()

The overview page for project groups is accessible to all users.

    >>> anon_browser.open("http://launchpad.test/gnome")
    >>> anon_browser.title
    'GNOME in Launchpad'

The page lists the member projects, together with the releases/milestones of
its development focus.

    >>> print(extract_text(find_tag_by_id(anon_browser.contents, "products")))
    Projects
    Evolution
    GNOME Terminal
    Gnome Applets
    NetApplet
    gnomebaker

The projects are linked.

    >>> print(anon_browser.getLink("gnomebaker").url)
    http://launchpad.test/gnomebaker

The project overview page contains a link to register new products with the
project. It is only available to users which have 'Admin' privileges on the
project.

    >>> browser.open("http://launchpad.test/mozilla")
    >>> browser.getLink("Register a project in The Mozilla Project")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> browser.addHeader("Authorization", "Basic no-priv@canonical.com:test")
    >>> browser.getLink("Register a project in The Mozilla Project")
    Traceback (most recent call last):
      ...
    zope.testbrowser.browser.LinkNotFoundError

    >>> admin_browser.open("http://launchpad.test/mozilla")
    >>> admin_browser.getLink("Register a project in The Mozilla Project").url
    'http://launchpad.test/mozilla/+newproduct'


Empty Project Groups
--------------------

An empty project group needs to be set up first...

    >>> admin_browser.open("http://launchpad.test/projectgroups/+new")
    >>> admin_browser.getControl(name="field.name").value = "a-test-group"
    >>> admin_browser.getControl("Display Name:").value = "Test Group"
    >>> admin_browser.getControl(name="field.summary").value = "Summary"
    >>> admin_browser.getControl("Description:").value = "Define me"
    >>> admin_browser.getControl("Maintainer:").value = "cprov"
    >>> admin_browser.getControl("Add").click()
    >>> admin_browser.url
    'http://launchpad.test/a-test-group'

Empty project group index pages will not display the 'Report a bug', 'Ask a
question' or 'Help translate' buttons.

    >>> user_browser.open("http://launchpad.test/a-test-group")
    >>> user_browser.getLink("Report a bug")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Ask a question")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Help translate")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError

Also, the bugs, blueprints, translations and answers facets will be disabled:

    >>> user_browser.open("http://launchpad.test/a-test-group")
    >>> user_browser.getLink("Bugs")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Blueprints")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Answers")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Answers")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.getLink("Translations")
    Traceback (most recent call last):
      ..
    zope.testbrowser.browser.LinkNotFoundError

A warning message will be displayed at the top of the overview page when the
owner of the project group views it:

    >>> admin_browser.open("http://launchpad.test/a-test-group")
    >>> for warning in find_tags_by_class(admin_browser.contents, "warning"):
    ...     print(extract_text(warning.decode_contents()))
    ...
    There are no projects registered for
    Test Group...

A link is included in the warning message which will take the admin user to
the new product form for the project group.

    >>> admin_browser.getLink(
    ...     "register another project that is part of Test Group"
    ... ).click()
    >>> print(admin_browser.title)
    Register a project in Launchpad...


Products of a project
---------------------

The home page of a project contains a list of all products which are part of
that project.

    >>> browser.open("http://launchpad.test/mozilla")
    >>> products = find_tags_by_class(browser.contents, "sprite product")
    >>> for product in products:
    ...     print(product)
    ...
    <a...Mozilla Firefox</a>
    <a...Mozilla Thunderbird</a>

Inactive products are not included in that list, though.

    # Use the DB classes directly to avoid having to setup a zope interaction
    # (i.e. login()) and bypass the security proxy.
    >>> from lp.registry.model.product import Product
    >>> firefox = Product.byName("firefox")

    # Unlink the source packages so the project can be deactivated.
    >>> from lp.testing import unlink_source_packages
    >>> login("admin@canonical.com")
    >>> unlink_source_packages(firefox)
    >>> firefox.active = False
    >>> firefox.syncUpdate()

    >>> logout()
    >>> browser.open("http://launchpad.test/mozilla")
    >>> products = find_tags_by_class(browser.contents, "sprite product")
    >>> for product in products:
    ...     print(product)
    ...
    <a...Mozilla Thunderbird</a>

    >>> firefox.active = True
    >>> firefox.syncUpdate()


Project Group bug subscriptions
-------------------------------

To receive email notifications about bugs pertaining to a project group, we
can create structural bug subscriptions.

    >>> user_browser.open("http://launchpad.test/mozilla")
    >>> user_browser.getLink("Subscribe to bug mail").click()
    >>> print(user_browser.url)
    http://launchpad.test/mozilla/+subscribe
    >>> print(user_browser.title)
    Subscribe : Bugs : The Mozilla Project
