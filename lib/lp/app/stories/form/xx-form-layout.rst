Form layout
===========

LaunchpadFormView based forms use a tabular layout for the widgets.
In most cases, the label is shown above the actual widget,
but there are some exceptions:


Normal widgets
--------------

The new team form contains an example of a normal text widget.

    >>> user_browser.open("http://launchpad.test/people/+newteam")
    >>> content = find_main_content(user_browser.contents)
    >>> print(content)
    <...
    <tr>
    <td colspan="2">
    <div>
    <label for="field.name">Name:</label>
    <div>
    <input ... name="field.name" .../>
    </div>
    <p class="formHelp">....</p>
    </div>
    </td>
    </tr>
    ...

If the text field is optional, then that is noted after the widget.

    >>> print(content)
    <...
    <tr>
    <td colspan="2">
    <div>
    <label for="field.defaultmembershipperiod">Subscription period:</label>
    <span class="fieldRequired">(Optional)</span>
    <div>
    <input ... id="field.defaultmembershipperiod" .../>
    </div>
    <p class="formHelp">...</p>
    </div>
    </td>
    </tr>
    ...


Checkbox widgets
----------------

Checkboxes have their label to the right. Let's look at one example.

    >>> admin_browser.open("http://launchpad.test/firefox/+review-license")
    >>> print(
    ...     find_tag_by_id(admin_browser.contents, "launchpad-form-widgets")
    ... )
    <...
    <tr>
      <td colspan="2">
       <div>
          <input ... name="field.project_reviewed" type="checkbox" .../>
          <label for="field.project_reviewed">Project reviewed</label>...
      </td>
    </tr>
    ...

Rendering just the form content
-------------------------------

It may be useful in some situations to simply render the form content for a
LaunchpadFormView. For example, when displaying the form in a popup overlay
on the page. This is enabled by a special ++form++ namespace that causes
just the form content to be rendered for any URL corresponding to an
LPFormView:

    >>> admin_browser.open("http://launchpad.test/evolution/+edit/++form++")
    >>> print(admin_browser.contents)
    <div...
    <table class="form" id="launchpad-form-widgets">
    ...
    </div>

Or for another example.

    >>> cprov_browser = setupBrowser(
    ...     auth="Basic celso.providelo@canonical.com:test"
    ... )
    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+edit/++form++"
    ... )
    >>> print(cprov_browser.contents)
    <div...
    <table class="form" id="launchpad-form-widgets">
    ...
    </div>

But it will not work for views that are not LPFormViews - even if they
display forms.

    >>> cprov_browser.open(
    ...     "http://launchpad.test/~cprov/+editsshkeys/++form++"
    ... )
    Traceback (most recent call last):
    ...
    zope.publisher.interfaces.NotFound: ...

Nor will it allow unauthorized access to data that it should not present.

    >>> browser.open(
    ...     "http://launchpad.test/~cprov/+archive/ppa/+edit/++form++"
    ... )
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...
