Blueprint dependencies
======================

Blueprints support the idea of dependencies: one blueprint can require
another blueprint be complete before its own implementation can
begin. We record those dependencies in Launchpad.

Let's look at the dependencies of the "canvas" blueprint for Firefox. It
depends on another blueprint, "e4x". No blueprints depend on "canvas"
itself.

    >>> owner_browser = setupBrowser(auth='Basic test@canonical.com:test')
    >>> owner_browser.open(
    ...   'http://blueprints.launchpad.test/firefox/+spec/canvas')
    >>> print(find_main_content(owner_browser.contents))
    <...
    ...Support E4X in EcmaScript...
    >>> 'Blocks' not in (owner_browser.contents)
    True


Adding a new dependency
-----------------------

Let's add a new dependency for the "canvas" blueprint. We'll add the
"extension-manager-upgrades" blueprint as a dependency. First, we
confirm we can see the page for adding a dependency.

    >>> owner_browser.getLink('Add dependency').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas/+linkdependency'

One can decide not to add a dependency after all.

    >>> owner_browser.getLink('Cancel').url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

This +linkdependency page and the link to it are only accessible by
users with launchpad.Edit permission for the blueprint.

    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/canvas')
    >>> user_browser.getLink('Add dependency')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/canvas/'
    ...     '+linkdependency')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...

The page contains a link back to the blueprint, in case we change our
minds.

    >>> back_link = owner_browser.getLink('Support <canvas> Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

Now, lets POST the form, saying we want extension-manager-upgrades as the
dependency.

    >>> owner_browser.getControl(
    ...     'Depends On').value = 'extension-manager-upgrades'
    >>> owner_browser.getControl('Continue').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'


Removing a dependency
---------------------

But we don't want to keep that, so we will remove it as a dependency. First
we make sure we can see the link to remove a dependency. We need to be
authenticated.

    >>> owner_browser.getLink('Remove dependency').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas/+removedependency'

One can decide not to remove a dependency after all.

    >>> owner_browser.getLink('Cancel').url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

Now, we make sure we can load the page. It should show two potential
dependencies we could remove. The extension manager one, and "e4x".

    >>> owner_browser.getControl('Dependency').displayOptions
    ['Extension Manager Upgrades', 'Support E4X in EcmaScript']

Again, the page contains a link back to the blueprint in case we change
our mind.

    >>> back_link = owner_browser.getLink('Support <canvas> Objects')
    >>> back_link.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

We'll POST the form selecting "extension-manager-upgrades" for removal. We
expect to be redirected to the blueprint page.

    >>> owner_browser.getControl(
    ...     'Dependency').value = ['1']
    >>> owner_browser.getControl('Continue').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'

This +removedependency page and the link to it are only accessible by
users with launchpad.Edit permission for the blueprint.

    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/canvas')
    >>> user_browser.getLink('Remove dependency')
    Traceback (most recent call last):
    ...
    zope.testbrowser.browser.LinkNotFoundError
    >>> user_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/canvas/'
    ...     '+removedependency')
    Traceback (most recent call last):
    ...
    zope.security.interfaces.Unauthorized: ...


Corner cases
------------

Cross-project blueprints
........................

Blueprints can only depend on blueprints in the same project. To
show this, we register a blueprint for a different project.

    >>> owner_browser.open(
    ...     'http://blueprints.launchpad.test/jokosher/+addspec')
    >>> owner_browser.getControl('Name').value = 'test-blueprint'
    >>> owner_browser.getControl('Title').value = 'Test Blueprint'
    >>> owner_browser.getControl('Summary').value = (
    ...     'Another blueprint in a different project')
    >>> owner_browser.getControl('Register Blueprint').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/jokosher/+spec/test-blueprint'

We then try to make the canvas blueprint in firefox depend on the
blueprint we registered in jokosher.

    >>> owner_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/'
    ...     '+spec/canvas/+linkdependency')
    >>> owner_browser.getControl(
    ...     'Depends On').value = 'test-blueprint'
    >>> owner_browser.getControl('Continue').click()
    >>> 'no blueprint named &quot;test-blueprint&quot;' in (
    ...     owner_browser.contents)
    True


Circular dependencies
.....................

In order to prevent circular dependencies, it is impossible to mark a
blueprint A as depending on blueprint B, if B is already marked as
depending on A.

We know that "canvas" depends on "e4x". We try to make "e4x" depend on
"canvas".

    >>> owner_browser.open(
    ...     'http://blueprints.launchpad.test/firefox/+spec/e4x/'
    ...     '+linkdependency')
    >>> owner_browser.getControl(
    ...     'Depends On').value = 'canvas'
    >>> owner_browser.getControl('Continue').click()
    >>> 'no blueprint named &quot;canvas&quot;' in owner_browser.contents
    True


Status
......

It should be possible to indicate any blueprint as a dependency,
regardless of its status. Let's mark mergewin as Implemented:

    >>> owner_browser.open(
    ...   'http://blueprints.launchpad.test/firefox/+spec/mergewin')
    >>> owner_browser.getLink(url='+status').click()
    >>> owner_browser.getControl(
    ...     'Implementation Status').value = ['IMPLEMENTED']
    >>> owner_browser.getControl('Change').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/mergewin'

And ensure it works:

    >>> owner_browser.open(
    ...   'http://blueprints.launchpad.test/firefox/+spec/canvas')
    >>> owner_browser.getLink('Add dependency').click()
    >>> owner_browser.getControl(
    ...     'Depends On').value = 'mergewin'
    >>> owner_browser.getControl('Continue').click()
    >>> owner_browser.url
    'http://blueprints.launchpad.test/firefox/+spec/canvas'


Project dependency charts
-------------------------

We know that no blueprints depend on "canvas", but "canvas" depends on
"e4x" and "e4x" depends on "svg-support". So the big picture is that
"canvas" needs to have both "e4x" and "svg-support" implemented before
it can be implemented, and nothing depends on having "canvas"
implemented. The "dependency tree" page for "canvas" should show exactly
that.

    >>> anon_browser.open(
    ...     'http://launchpad.test/firefox/+spec/canvas/+deptree')
    >>> print('----'); print(anon_browser.contents)
    ----
    ...Blueprints that must be implemented first...
    ...Support E4X in EcmaScript...
    ...Merge Open Browser Windows with "Consolidate Windows"...
    ...Support Native SVG Objects...
    ...This blueprint...
    ...Support &lt;canvas&gt; Objects...
    ...Blueprints that can then be implemented...
    ...No blueprints depend on this one...

We have some nice tools to display the dependency tree as a client side
image and map.

    >>> anon_browser.open(
    ...     'http://launchpad.test/firefox/+spec/canvas/+deptreeimgtag')
    >>> print(anon_browser.contents)
    <img src="deptree.png" usemap="#deptree" />
    <map id="deptree" name="deptree">
    <area shape="poly"
      ...title="Support &lt;canvas&gt; Objects" .../>
    <area shape="poly"
      ...href="http://blueprints.launchpad.test/firefox/+spec/e4x" .../>
    <area shape="poly"
      ...href="http://blueprints.launchpad.test/firefox/+spec/mergewin" .../>
    <area shape="poly"
      ...href="http://blueprints.launchpad.test/firefox/+spec/svg...support"
      .../>
    </map>


Get the dependency chart, and check that it is a PNG.

    >>> anon_browser.open(
    ...   'http://launchpad.test/firefox/+spec/canvas/deptree.png')
    >>> anon_browser.contents.startswith(b'\x89PNG')
    True
    >>> anon_browser.headers['content-type']
    'image/png'

We can also get the DOT output for a blueprint dependency graph.  This
is useful for experimenting with the dot layout using production data.

    >>> anon_browser.open(
    ...   'http://launchpad.test/firefox/+spec/canvas/+deptreedotfile')
    >>> anon_browser.headers['content-type']
    'text/plain;charset=utf-8'
    >>> print(anon_browser.contents)
    digraph "deptree" {
    ...

Distro blueprints
-----------------

Let's look at blueprints targetting a distribution, rather than a product.
We create two blueprints in `ubuntu`.

    >>> owner_browser.open('http://blueprints.launchpad.test/ubuntu/+addspec')
    >>> owner_browser.getControl('Name').value = 'distro-blueprint-a'
    >>> owner_browser.getControl('Title').value = 'A blueprint for a distro'
    >>> owner_browser.getControl('Summary').value = (
    ...     'This is a blueprint for the Ubuntu distribution')
    >>> owner_browser.getControl('Register Blueprint').click()
    >>> print(owner_browser.url)
    http://blueprints.launchpad.test/ubuntu/+spec/distro-blueprint-a

    >>> owner_browser.open('http://blueprints.launchpad.test/ubuntu/+addspec')
    >>> owner_browser.getControl('Name').value = 'distro-blueprint-b'
    >>> owner_browser.getControl('Title').value = (
    ...     'Another blueprint for a distro')
    >>> owner_browser.getControl('Summary').value = (
    ...     'This is a blueprint for the Ubuntu distribution')
    >>> owner_browser.getControl('Register Blueprint').click()
    >>> print(owner_browser.url)
    http://blueprints.launchpad.test/ubuntu/+spec/distro-blueprint-b

    >>> owner_browser.getLink('Add dependency').click()
    >>> print(owner_browser.url)
    http.../ubuntu/+spec/distro-blueprint-b/+linkdependency

    >>> owner_browser.getControl('Depends On').value = 'distro-blueprint-a'
    >>> owner_browser.getControl('Continue').click()

The blueprint was linked successfully, and it appears in the dependency
image map.

    >>> find_tag_by_id(owner_browser.contents, 'deptree')
    <...A blueprint for a distro...>
