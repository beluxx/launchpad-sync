Karma for branch related activity
=================================

We want people to register their branches on Launchpad, and also to
link their branches to bugs and specs, so we give them some karma for
it.  By linking bugs and specs to branches the users are enriching
the information that Launchpad has about the work going on in the
branches.  We want to encourage the linking of information, and so
give karma for it.

    >>> from lp.registry.model.karma import KarmaCategory
    >>> code_category = KarmaCategory.byName('code')
    >>> code_karma_actions = code_category.karmaactions
    >>> for summary in sorted(
    ...     [action.summary for action in code_karma_actions]):
    ...     print(summary)
    A new revision by the user is available through Launchpad.
    Reviewer commented on a code review.
    User approved a branch for merging.
    User approved their own branch for merging.
    User commented on a code review.
    User linked a branch to a blueprint.
    User linked a branch to a bug.
    User proposed a branch for merging.
    User registered a new branch.
    User rejected a proposed branch merge.
    User rejected their own proposed branch merge.

    >>> from lp.testing.karma import KarmaAssignedEventListener
    >>> karma_helper = KarmaAssignedEventListener(show_person=True)
    >>> karma_helper.register_listener()

Registering branches
--------------------

Karma is added for registering a branch.

    >>> login('test@canonical.com')
    >>> fooix = factory.makeProduct(name='fooix')
    >>> eric = factory.makePerson(name='eric')
    >>> branch = factory.makeProductBranch(owner=eric, product=fooix)
    Karma added: action=branchcreated, product=fooix, person=eric

However, no karma is added for junk branches.

    >>> junk_branch = factory.makePersonalBranch(owner=eric)


Linking bugs and branches
-------------------------

You get karma for linking a bug to a branch.

    >>> reporter = factory.makePerson(name='reporter')
    >>> bug = factory.makeBug(target=fooix, owner=reporter)
    Karma added: action=bugcreated, product=fooix, person=reporter
    >>> branch_link = bug.linkBranch(branch, eric)
    Karma added: action=bugbranchcreated, product=fooix, person=eric

As long as it is not a junk branch.

    >>> branch_link = bug.linkBranch(junk_branch, eric)


Linking blueprints and branches
-------------------------------

You get karma for linking a blueprint to a branch.

    >>> blueprint = factory.makeSpecification(product=fooix)
    >>> branch_link = blueprint.linkBranch(branch, eric)
    Karma added: action=specbranchcreated, product=fooix, person=eric

But again, not for junk branches.

    >>> branch_link = blueprint.linkBranch(junk_branch, eric)

    # Unregister the event listener to make sure we won't interfere in
    # other tests.
    >>> karma_helper.unregister_listener()
