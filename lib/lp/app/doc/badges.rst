Badges
======

Badges are nifty user interface elements that are used to indicate to
the user that there are interesting features about the thing that the
badges are attached to, for example a bug can have a badge to indicate
that there is a related branch.

Badges are shown in two main places:
  * Object listings
  * Main object pages

In the object listing views, badges are used to show links between
objects, such as bug-branch links or bug-spec links, and object
attribute values such as privacy.

Listings use small icon sized images, and object details pages use
larger logo sized images.

In order to maintain a level of standardisation across the badge uses in
Launchpad, there is a central list of standard badges along with their
alternate text and titles.

    >>> from lp.app.browser.badge import STANDARD_BADGES

Iterating over this collection gives:

    >>> for name in sorted(STANDARD_BADGES):
    ...     print(name)
    blueprint
    branch
    bug
    mergeproposal
    patch
    private
    security


The Badge class
---------------

The badge class has two methods of interest:
  * renderIconImage - the HTML for the icon sized image
  * renderHeadingImage - the HTML for the logo sized image

A badge is constructed with the locations of the images, the default
alternate text and the default title.  An optional id attribute for a
Badge is added to the rendered heading image.

    >>> from lp.app.browser.badge import Badge
    >>> bug = Badge(
    ...     icon_image='/@@/bug', heading_image='/@@/bug-large',
    ...     alt='bug', title='Linked to a bug', id='bugbadge')

Both `alt` and `title` default to the empty string.

Calling the render methods will produce the default image HTML.

    >>> print(bug.renderIconImage())
    <img alt="bug" width="14" height="14" src="/@@/bug"
         title="Linked to a bug"/>
    >>> print(bug.renderHeadingImage())
    <img alt="bug" width="32" height="32" src="/@@/bug-large"
         title="Linked to a bug" id="bugbadge"/>

If the icon_image or heading_image are not specified, then the rendering
the particular size results in the empty string.

    >>> no_large = Badge(icon_image='/@@/bug')
    >>> no_large.renderHeadingImage()
    ''
    >>> no_small = Badge(heading_image='/@@/bug')
    >>> no_small.renderIconImage()
    ''


IHasBadges
----------

How to determine which badges to show for a given object is defined by
the IHasBadges interface.

The base badge implementation class, `HasBadgeBase`, provides an
implementation of IHasBadges. HasBadgeBase is also a default adapter
for Interface, which just provides the privacy badge.

    >>> from zope.interface import Interface, Attribute, implementer
    >>> from lp.app.browser.badge import IHasBadges, HasBadgeBase
    >>> from lp.testing import verifyObject
    >>> @implementer(Interface)
    ... class PrivateClass:
    ...     private = True
    >>> private_object = PrivateClass()
    >>> has_badge_base = HasBadgeBase(private_object)
    >>> verifyObject(IHasBadges, has_badge_base)
    True
    >>> has_badge_base.badges
    ('private',)
    >>> has_badge_base.isPrivateBadgeVisible()
    True

Classes that derive from HasBadgeBase should define a sequence attribute
called `badges` that list the names of possible badges.  These names
are then expanded into method calls to determine the visibility of that
badge.  For example a badge called `bug` will expand to a method call
`isBugBadgeVisible`. The title, which will provide a tooltip in the
UI, can be provided for the `bug` badge by defining the `getBugBadgeVisible`
method.

In order to provide a badge that is not one of the standard ones, the
badger class needs to implement the method `getBadge`.

    >>> class SimpleBadger(HasBadgeBase):
    ...     badges = ["bug", "fish"]
    ...     def isBugBadgeVisible(self):
    ...         return True
    ...     def getBugBadgeTitle(self):
    ...         return 'Bug-Title'
    ...     def isFishBadgeVisible(self):
    ...         return True
    ...     def getFishBadgeTitle(self):
    ...         return 'Fish-Tooltip'
    ...     def getBadge(self, badge_name):
    ...         if badge_name == "fish":
    ...             return Badge('small-fish', 'large-fish', 'fish',
    ...                          'Fish-Title')
    ...         else:
    ...             return HasBadgeBase.getBadge(self, badge_name)

    >>> for badge in SimpleBadger(private_object).getVisibleBadges():
    ...     print(badge.alt, "/", badge.title)
    bug / Bug-Title
    fish / Fish-Title

If the class does not implement the appropriate method you get a
NotImplementedError.

    >>> SimpleBadger.badges.append("blueprint")
    >>> for badge in SimpleBadger(private_object).getVisibleBadges():
    ...     print(badge.alt)
    Traceback (most recent call last):
    ...
    AttributeError:
    'SimpleBadger' object has no attribute 'isBlueprintBadgeVisible'



Preferred badging methodology
-----------------------------

Under normal circumstances the badges for a given content object require
the accessing or counting of attributes and this almost always requires
database queries.  While this is fine for a single object, we do not
want to have this happen for listings of objects.  For example, if there
were 5 possible badges for a branch and 3 of those counted links to
other tables, and we had a listing of 75 branches, then that is 225
database queries just for the badges.

In order to allow efficient database queries for listings, the suggested
badging methodology is to provide an adapter for the content class to
adapt the content class to `IHasBadges`.  The implementation of this
adapter can do the simple determination of a badge based on the
accessing or counting of the content object's attributes.  The listing
views then use a delegating object in order to override the badge
determination methods to use the results of an alternative query.

    >>> class IFoo(Interface):
    ...     bugs = Attribute('Some linked bugs')
    ...     blueprints = Attribute('Some linked blueprints')

    >>> from zope.interface import implementer
    >>> @implementer(IFoo)
    ... class Foo:
    ...     @property
    ...     def bugs(self):
    ...         print("Foo.bugs")
    ...         return ['a']
    ...     @property
    ...     def blueprints(self):
    ...         print("Foo.blueprints")
    ...         return []

Now define the adapter for the Foo content class.

    >>> class FooBadges(HasBadgeBase):
    ...     badges = "bug", "blueprint"
    ...     def __init__(self, context):
    ...         self.context = context
    ...     def isBugBadgeVisible(self):
    ...         return len(self.context.bugs) > 0
    ...     def isBlueprintBadgeVisible(self):
    ...         return len(self.context.blueprints) > 0

Usually, one would register an adapter in ZCML from the content type to
IHasBadges.  Here is the sample from the branch.zcml to illustrate.

  <adapter
      for="lp.code.interfaces.branch.IBranch"
      provides="lp.app.browser.badge.IHasBadges"
      factory="lp.code.browser.branchlisting.BranchBadges"
      />

Luckily zope provides a way to do this in doctests:

    >>> from zope.component import provideAdapter
    >>> provideAdapter(FooBadges, (IFoo,), IHasBadges)

Now adapting a Foo to IHasBadges should provide an instance of FooBadges.

    >>> foo = Foo()
    >>> foo
    <Foo object at ...>

    >>> badger = IHasBadges(foo)
    >>> badger
    <FooBadges object at ...>

Getting the visible badges for foo calls the underlying methods on foo,
as illustrated by the printed method calls.

    >>> for badge in badger.getVisibleBadges():
    ...     print(badge.renderIconImage())
    Foo.bugs
    Foo.blueprints
    <img alt="bug" width="14" height="14" src="/@@/bug"
    title="Linked to a bug"/>

When showing listings of Foos, you often want to use
`lazr.delegates.delegate_to`. By having the DelegatingFoo inherit from the
FooBadges class, we provide two things: a default implementation for each of
the badge methods; and direct implementation of IHasBadges. This allows the
wrapping, delegating class to provide an alternative method to decide on badge
visibility. For example, with branches the visibility of the bug badge is
determined by the users ability to see the bugs for any bug branch links. On
listings we don't want to do 100 queries just to check bug badges. The batch
handler for branches executes a single query for the BugBranch links for the
branches in the batch and that is used to construct the DecoratedBranch.

    >>> from lazr.delegates import delegate_to
    >>> @delegate_to(IFoo, context='foo')
    ... class DelegatingFoo(FooBadges):
    ...     def __init__(self, foo):
    ...         FooBadges.__init__(self, foo)
    ...         self.foo = foo
    ...     def isBugBadgeVisible(self):
    ...         return True
    ...     def isBlueprintBadgeVisible(self):
    ...         return False

    >>> delegating_foo = DelegatingFoo(foo)
    >>> delegating_foo
    <DelegatingFoo object at ...>

Since the DelegatingFoo implements IHasBadges through the class hierarchy
FooBadges and then HasBadgeBase, getting an IHasBadges for the
DelegatingFoo returns the same object.

    >>> badger = IHasBadges(delegating_foo)
    >>> badger is delegating_foo
    True

Getting the visible badges for the delegating_foo bypasses the underlying
method calls, and thus avoiding unnecessary database hits (for normal
content classes).

    >>> for badge in badger.getVisibleBadges():
    ...     print(badge.renderIconImage())
    <img alt="bug" width="14" height="14" src="/@@/bug"
    title="Linked to a bug"/>


Tales expressions
-----------------

There is a tales formatter defined for badges.  These can be shown
as either small or large.

Using the tales formatter on the context object itself ends up using the
adapter that is defined for the content class, and as shown below
through the printed attribute accessors, uses the attributes of the
content class.

    >>> from lp.testing import test_tales
    >>> print(test_tales('context/badges:small', context=foo))
    Foo.bugs
    Foo.blueprints
    <img alt="bug" width="14" height="14" src="/@@/bug"
         title="Linked to a bug"/>

    >>> print(test_tales('context/badges:large', context=foo))
    Foo.bugs
    Foo.blueprints
    <img alt="bug" width="32" height="32" src="/@@/bug-large"
         title="Linked to a bug" id="bugbadge"/>

Using the delegating foo, we get the delegated methods called and avoid
the content class method calls.

    >>> print(test_tales('context/badges:small', context=delegating_foo))
    <img alt="bug" width="14" height="14" src="/@@/bug"
         title="Linked to a bug"/>
    >>> print(test_tales('context/badges:large', context=delegating_foo))
    <img alt="bug" width="32" height="32" src="/@@/bug-large"
         title="Linked to a bug" id="bugbadge"/>
