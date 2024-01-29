Administering POTemplates
=========================


Product templates
-----------------

The POTemplate admin page lets us to edit any aspect of that object, that's
why we need to be a Rosetta Expert or a Launchpad admin to use it.

An unprivileged user cannot reach the POTemplate administration page.

    >>> user_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+admin"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

Jordi, a Rosetta expert, can.

    >>> browser = setupBrowser(auth="Basic jordi@ubuntu.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+admin"
    ... )
    >>> print(browser.url)
    http://translations...test/evolution/trunk/+pots/evolution-2.2/+admin

Now, we should be sure that the admin form gets all required fields to allow
a Rosetta Expert to administer it.

    >>> browser.getControl(name="field.name").value
    'evolution-2.2'
    >>> browser.getControl("Translation domain").value
    'evolution-2.2'
    >>> browser.getControl(name="field.description").value
    'Template for evolution in hoary'
    >>> print(browser.getControl(name="field.header").value)
    Project-Id-Version: PACKAGE VERSION
    Report-Msgid-Bugs-To:
    POT-Creation-Date: 2005-08-25 14:56+0200
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=CHARSET
    Content-Transfer-Encoding: 8bit
    Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;
    <BLANKLINE>
    >>> browser.getControl(name="field.iscurrent").value
    True
    >>> browser.getControl(name="field.owner").value
    'rosetta-admins'
    >>> browser.getControl(name="field.productseries").value
    'evolution/trunk'
    >>> browser.getControl(name="field.distroseries").value
    ['']
    >>> browser.getControl(name="field.sourcepackagename").value
    ''
    >>> browser.getControl(name="field.sourcepackageversion").value
    ''
    >>> bool(browser.getControl(name="field.languagepack").value)
    False
    >>> browser.getControl(name="field.path").value
    'po/evolution-2.2.pot'

An administrator can also access the POTemplate administration page.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+admin"
    ... )
    >>> print(admin_browser.url)
    http://translations...test/evolution/trunk/+pots/evolution-2.2/+admin

Now, we should be sure that the admin form gets all required fields to allow
an admin to administer it.

    >>> admin_browser.getControl(name="field.name").value
    'evolution-2.2'
    >>> admin_browser.getControl("Translation domain").value
    'evolution-2.2'
    >>> admin_browser.getControl(name="field.description").value
    'Template for evolution in hoary'
    >>> print(admin_browser.getControl(name="field.header").value)
    Project-Id-Version: PACKAGE VERSION
    Report-Msgid-Bugs-To:
    POT-Creation-Date: 2005-08-25 14:56+0200
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=CHARSET
    Content-Transfer-Encoding: 8bit
    Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;
    <BLANKLINE>
    >>> admin_browser.getControl(name="field.iscurrent").value
    True
    >>> admin_browser.getControl(name="field.owner").value
    'rosetta-admins'
    >>> admin_browser.getControl(name="field.productseries").value
    'evolution/trunk'
    >>> admin_browser.getControl(name="field.distroseries").value
    ['']
    >>> admin_browser.getControl(name="field.sourcepackagename").value
    ''
    >>> admin_browser.getControl(name="field.sourcepackageversion").value
    ''
    >>> bool(admin_browser.getControl(name="field.languagepack").value)
    False
    >>> admin_browser.getControl(name="field.path").value
    'po/evolution-2.2.pot'
    >>> from zope import datetime as zope_datetime
    >>> old_date_last_updated = zope_datetime.parseDatetimetz(
    ...     admin_browser.getControl("Date for last update").value
    ... )
    >>> old_date_last_updated.isoformat()
    '2005-08-25T15:27:55.264235+00:00'

And that we are able to POST it.

    >>> admin_browser.getControl("Translation domain").value = "foo"
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2

Going back to the form we can see that the changes are saved and also,
the date when the template was last updated is now newer than previous
value.

    >>> admin_browser.getLink("Administer").click()
    >>> admin_browser.getControl("Translation domain").value
    'foo'
    >>> zope_datetime.parseDatetimetz(
    ...     admin_browser.getControl("Date for last update").value
    ... ) > old_date_last_updated
    True

We can also change the switch to note whether the template must be
exported as part of language packs.

    >>> admin_browser.getControl(name="field.languagepack").value = True
    >>> admin_browser.getControl("Change").click()

Finally, let's rename 'evolution-2.2' to 'evolution-renamed'.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+admin"
    ... )

Lets use this opportunity to check if languagepack was changed successfully
above.

    >>> admin_browser.getControl(name="field.languagepack").value
    True

And now let's get back to renaming.

    >>> admin_browser.getControl(name="field.name").value = (
    ...     "evolution-renamed"
    ... )
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-renamed

Administrators can disable and then make changes to a disabled template.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-renamed/+admin"
    ... )
    >>> admin_browser.getControl(name="field.iscurrent").value = False
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-renamed

Now we will re-enable the template.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-renamed/+admin"
    ... )
    >>> admin_browser.getControl(name="field.iscurrent").value = True
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-renamed


Distribution templates
----------------------

Distributions get slightly wider permissions to manage their templates
autonomously.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.translations.model.potemplate import POTemplateSet
    >>> login("admin@canonical.com")
    >>> ubuntu = getUtility(IDistributionSet)["ubuntu"]
    >>> hoary = ubuntu["hoary"]
    >>> templateset = POTemplateSet()

    >>> login(ANONYMOUS)
    >>> dsp = factory.makeDSPCache(distroseries=hoary)
    >>> templatesubset = templateset.getSubset(
    ...     distroseries=hoary, sourcepackagename=dsp.sourcepackagename
    ... )
    >>> template_owner = factory.makePerson()
    >>> template = templatesubset.new("foo", "foo", "foo.pot", template_owner)

    >>> login("admin@canonical.com")
    >>> distro_owner = factory.makePerson("do@example.com")
    >>> ubuntu.owner = distro_owner

    >>> group_owner = factory.makePerson("go@example.com")
    >>> translation_group = factory.makeTranslationGroup(group_owner)
    >>> ubuntu.translationgroup = translation_group
    >>> template_admin_url = str(
    ...     "http://translations.launchpad.test/ubuntu/hoary/"
    ...     "+source/%s/+pots/%s/+admin"
    ...     % (dsp.sourcepackagename.name, template.name)
    ... )
    >>> logout()

A distribution's owner can manage the distribution's templates.

    >>> distro_owner_browser = setupBrowser(auth="Basic do@example.com:test")
    >>> distro_owner_browser.open(template_admin_url)
    >>> distro_owner_browser.getControl(name="field.path").value = "bar.pot"
    >>> distro_owner_browser.getControl("Change").click()

    >>> print(template.path)
    bar.pot

This privilege also extends to items that require "edit" permissions.

    >>> distro_owner_browser.open(template_admin_url)
    >>> distro_owner_browser.getControl(name="field.priority").value = "321"
    >>> distro_owner_browser.getControl("Change").click()

If the distribution has a translation group assigned, the group's owners
can manage the distribution's translation templates as well.

    >>> group_owner_browser = setupBrowser(auth="Basic go@example.com:test")
    >>> group_owner_browser.open(template_admin_url)
    >>> group_owner_browser.getControl(name="field.path").value = "splat.pot"
    >>> group_owner_browser.getControl(name="field.priority").value = "543"
    >>> group_owner_browser.getControl("Change").click()

    >>> print(template.path)
    splat.pot

Distribution translation coordinators can disable and manage disabled
templates.

    >>> group_owner_browser.open(template_admin_url)
    >>> group_owner_browser.getControl(name="field.iscurrent").value = False
    >>> group_owner_browser.getControl("Change").click()
    >>> group_owner_browser.open(template_admin_url)
    >>> group_owner_browser.getControl(name="field.iscurrent").value = True
    >>> group_owner_browser.getControl("Change").click()
