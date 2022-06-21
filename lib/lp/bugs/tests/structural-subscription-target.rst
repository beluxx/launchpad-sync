IStructuralSubscriptionTarget
-----------------------------

Let's subscribe ubuntu-team.

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> personset = getUtility(IPersonSet)
    >>> ubuntu_team = personset.getByName("ubuntu-team")
    >>> no_priv = personset.getByName("no-priv")
    >>> foobar = personset.getByName("name16")
    >>> from lp.testing import login
    >>> login("foo.bar@canonical.com")
    >>> target.addBugSubscription(ubuntu_team, foobar)
    <...StructuralSubscription ...>

We can add and remove these subscriptions.

    >>> def print_subscriptions_list(subscriptions):
    ...     for subscription in subscriptions:
    ...         print(subscription.subscriber.name)

    >>> subscription = target.addBugSubscription(foobar, foobar)
    >>> print_subscriptions_list(target.getSubscriptions())
    name16
    ubuntu-team
    >>> target.removeBugSubscription(foobar, foobar)
    >>> print_subscriptions_list(target.getSubscriptions())
    ubuntu-team

To get a user's subscription to the target, use
IStructuralSubscriptionTarget.getSubscription.

    >>> target.getSubscription(ubuntu_team)
    <...StructuralSubscription ...>
    >>> print(target.getSubscription(no_priv))
    None

To search for all subscriptions on a structure we use getSubscriptions.

    >>> print_subscriptions_list(target.bug_subscriptions)
    ubuntu-team
    >>> subscription = target.addSubscription(no_priv, no_priv)
    >>> print_subscriptions_list(target.bug_subscriptions)
    no-priv
    ubuntu-team


Structural subscriptions and indirect bug subscriptions
=======================================================

    >>> bug = filebug(target, 'test bug one')
    >>> indirect_subscribers = set(
    ...     subscriber.name for subscriber in bug.getIndirectSubscribers())
    >>> structural_subscribers = set(
    ...     sub.subscriber.name for sub in target.bug_subscriptions)
    >>> for name in structural_subscribers.difference(indirect_subscribers):
    ...     print(name)
