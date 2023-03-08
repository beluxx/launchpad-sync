Editing POTemplates
===================

The POTemplate edit page allows editing a subset of potemplate
attributes. Only product owners, Rosetta Experts or a Launchpad admin
are able to use it.

An unprivileged user cannot reach this page.

    >>> browser = setupBrowser(auth="Basic no-priv@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+edit"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

In fact, the "Change details" option won't even appear for them.

    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/"
    ... )
    >>> browser.getLink("Change details").click()
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError

On the other hand, Rosetta expert (Jordi) can reach the POTemplate edit
page.

    >>> browser = setupBrowser(auth="Basic jordi@ubuntu.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/"
    ... )
    >>> browser.getLink("Change details").click()
    >>> print(browser.url)
    http://translations.../evolution/trunk/+pots/evolution-2.2/+edit

The owner of a product has access to edit page for PO templates.

    >>> browser = setupBrowser(auth="Basic test@canonical.com:test")
    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+edit"
    ... )
    >>> print(browser.url)
    http://translations.../evolution/trunk/+pots/evolution-2.2/+edit

Owner will not see admin fields, only those fields designated for the
edit page.

    >>> browser.getControl(name="field.header").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.productseries").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.distroseries").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.sourcepackagename").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.sourcepackageversion").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.languagepack").value
    Traceback (most recent call last):
    ...
    LookupError:...

    >>> browser.getControl(name="field.description").value
    'Template for evolution in hoary'

    >>> browser.getControl(name="field.path").value
    'po/evolution-2.2.pot'

    >>> browser.getControl(name="field.iscurrent").value
    True

    >>> browser.getControl(name="field.owner").value
    'rosetta-admins'

    >>> browser.getControl(name="field.priority").value
    '0'

    >>> browser.getControl(name="field.translation_domain").value
    'evolution-2.2'

We remember the 'last_update_date' in order to check if it was changed
after updating the template.

    >>> from zope.component import getUtility
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.translations.model.potemplate import POTemplateSubset
    >>> login("foo.bar@canonical.com")
    >>> evolution = getUtility(IProductSet).getByName("evolution")
    >>> evolution_trunk = evolution.getSeries("trunk")
    >>> hoary_subset = POTemplateSubset(productseries=evolution_trunk)
    >>> evolution_template = hoary_subset.getPOTemplateByName("evolution-2.2")
    >>> previous_date_last_updated = evolution_template.date_last_updated
    >>> logout()

The visible fields can be changed and saved.

    >>> browser.getControl(name="field.name").value = "evo"
    >>> browser.getControl(name="field.translation_domain").value = "evo"
    >>> browser.getControl(name="field.priority").value = "100"
    >>> browser.getControl(name="field.iscurrent").value = False
    >>> browser.getControl(name="field.path").value = "po/evolution.pot"
    >>> browser.getControl(name="field.owner").value = "name12"
    >>> browser.getControl(name="field.description").value = "foo"
    >>> browser.getControl("Change").click()
    >>> print(browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evo

The changed values will be stored and visible by accessing again the edit
page.

    >>> browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evo/+edit"
    ... )
    >>> browser.getControl(name="field.name").value
    'evo'

    >>> browser.getControl(name="field.translation_domain").value
    'evo'

    >>> browser.getControl(name="field.priority").value
    '100'

    >>> bool(browser.getControl(name="field.iscurrent").value)
    False

    >>> browser.getControl(name="field.path").value
    'po/evolution.pot'

    >>> browser.getControl(name="field.owner").value
    'name12'

    >>> browser.getControl(name="field.description").value
    'foo'

    >>> previous_date_last_updated != evolution_template.date_last_updated
    True

Restore the template name for further tests.

    >>> browser.getControl(name="field.name").value = "evolution-2.2"
    >>> browser.getControl("Change").click()


Priority range
--------------

The priority value must be between 0 and 100000. When entering a
priority that is not in this range the form validation will inform users
about what values are accepted for the priority field.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+edit"
    ... )
    >>> admin_browser.getControl(name="field.priority").value = "-1"
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.../evolution/trunk/+pots/evolution-2.2/+edit

    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    The priority value must be between ...

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+edit"
    ... )
    >>> admin_browser.getControl(name="field.priority").value = "100001"
    >>> admin_browser.getControl("Change").click()
    >>> print(admin_browser.url)
    http://translations.../evolution/trunk/+pots/evolution-2.2/+edit

    >>> print_feedback_messages(admin_browser.contents)
    There is 1 error.
    The priority value must be between ...


Change and cancel actions
-------------------------

After changing or canceling a form you will be redirected to the
previous page from you navigation.

The edit page can be access from the templates list.

    >>> referrer = (
    ...     "http://translations.launchpad.test/evolution/trunk/+templates"
    ... )
    >>> admin_browser.open(referrer)
    >>> admin_browser.getLink(url="+pots/evolution-2.2/+edit").click()
    >>> admin_browser.getControl("Change").click()
    >>> admin_browser.url == referrer
    True

If you are accessing the edit page using a bookmark (in this case there
was no previous page in the navigation), you will be directed to the
template index page.

    >>> admin_browser.open(
    ...     "http://translations.launchpad.test/evolution/trunk/+pots/"
    ...     "evolution-2.2/+edit"
    ... )
    >>> admin_browser.getLink("Cancel").click()
    >>> print(admin_browser.url)
    http://translations.launchpad.test/evolution/trunk/+pots/evolution-2.2
