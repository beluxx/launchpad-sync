Specifications
==============

A feature specification is a document that describes an idea for an
enhancement to a product. Launchpad allows you to register your
specification and then walk it through the approval process. You can
have specifications for products, and also for distributions.

All Milestone creation and retrieval is done through IMilestoneSet.
IMilestoneSet can be accessed as a utility.

    >>> from zope.component import getUtility
    >>> from lp.blueprints.enums import (
    ...     SpecificationDefinitionStatus,
    ...     SpecificationImplementationStatus, SpecificationPriority)
    >>> from lp.blueprints.interfaces.specification import ISpecificationSet
    >>> specset = getUtility(ISpecificationSet)

To create a new Specification, use ISpecificationSet.new:

    >>> from lp.registry.interfaces.product import IProductSet

    >>> productset = getUtility(IProductSet)
    >>> upstream_firefox = productset.get(4)
    >>> from lp.registry.model.person import Person
    >>> mark = Person.byName('mark')
    >>> newspec = specset.new('mng', 'Support MNG Format',
    ...     'http://www.silly.me/SpecName', 'we really need this',
    ...     SpecificationDefinitionStatus.APPROVED, mark,
    ...     target=upstream_firefox)
    >>> print(newspec.name)
    mng

To retrieve a specification by its ID, we use `ISpecificationSet.get`.

    >>> specset.get(newspec.id) == newspec
    True

It should be possible to retrieve a specification by its name

    >>> print(upstream_firefox.getSpecification('mng').name)
    mng

And if we try to retrieve a non-existent specification we should get
None

    >>> print(upstream_firefox.getSpecification('nonexistentspec'))
    None

It's also possible to retrieve a specification by its URL

    >>> print(specset.getByURL(
    ...     'http://developer.mozilla.org/en/docs/SVG').specurl)
    http://developer.mozilla.org/en/docs/SVG

And if there's no specification with the given URL we should get None

    >>> print(specset.getByURL('http://no-url.com'))
    None

A specification could be attached to a distribution, or a product. We
call this the specification target.

    >>> print(newspec.target.name)
    firefox

We attach now a spec to a distribution.

    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    >>> mark = Person.byName('mark')
    >>> ubuspec = specset.new('fix-spec-permissions',
    ...                       'Fix Specification Permissions',
    ...                       'http://www.ubuntu.com/FixBrokenSpecPerms',
    ...                       'we really need this',
    ...                       SpecificationDefinitionStatus.APPROVED,
    ...                       mark,
    ...                       target=ubuntu)
    >>> print(ubuspec.name)
    fix-spec-permissions

The Ubuntu distro is owned by the Ubuntu team, ubuntu-team. jdub is a
member, and therefore should be able to edit any spec attached to it
(but not specs attached to mozilla-firefox).

    >>> from lp.services.webapp.authorization import check_permission
    >>> print(ubuntu.owner.name)
    ubuntu-team

    >>> jdub = Person.byName('jdub')
    >>> jdub.inTeam(ubuntu.owner)
    True

    >>> login(jdub.preferredemail.email)
    >>> check_permission('launchpad.Edit', ubuspec)
    True

    >>> check_permission('launchpad.Edit', newspec)
    False

SpecificationSet implements the ISpecificationSet interface

    >>> from lp.testing import verifyObject
    >>> verifyObject(ISpecificationSet, specset)
    True


SpecificationDelta
------------------

When we modify a specification, we can get a delta of the changes using
ISpecification.getDelta(). If there are no changes, None will be
returned:

    >>> from zope.interface import providedBy
    >>> from lazr.lifecycle.snapshot import Snapshot
    >>> from lp.bugs.interfaces.bug import IBugSet
    >>> unmodified_spec = Snapshot(ubuspec, providing=providedBy(ubuspec))
    >>> ubuspec.getDelta(unmodified_spec, jdub) is None
    True

Now, let's do a bunch of changes, and see what the result looks like:

    >>> ubuspec.title = 'New Title'
    >>> ubuspec.summary = 'New summary.'
    >>> ubuspec.specurl = 'http://www.ubuntu.com/NewSpec'
    >>> ubuspec.proposeGoal(ubuntu.getSeries('hoary'), jdub)
    >>> ubuspec.name = 'new-spec'
    >>> ubuspec.priority = SpecificationPriority.LOW
    >>> ubuspec.definition_status = SpecificationDefinitionStatus.DRAFT
    >>> ubuspec.whiteboard = 'New whiteboard comments.'
    >>> ubuspec.approver = mark
    >>> ubuspec.assignee = jdub
    >>> ubuspec.drafter = jdub
    >>> ubuspec.linkBug(getUtility(IBugSet).get(2))
    True

    >>> delta = ubuspec.getDelta(unmodified_spec, jdub)
    >>> delta.specification == ubuspec
    True

    >>> delta.user == jdub
    True

    >>> print(delta.title)
    New Title

    >>> print(delta.summary)
    New summary.

    >>> print(delta.specurl)
    http://www.ubuntu.com/NewSpec

    >>> print(delta.distroseries.name)
    hoary

    >>> print(delta.name['old'])
    fix-spec-permissions

    >>> print(delta.name['new'])
    new-spec

    >>> print(delta.priority['old'].title)
    Undefined

    >>> print(delta.priority['new'].title)
    Low

    >>> print(delta.definition_status['old'].title)
    Approved

    >>> print(delta.definition_status['new'].title)
    Drafting

    >>> print(delta.approver['old'] is None)
    True

    >>> print(delta.approver['new'] == mark)
    True

    >>> print(delta.assignee['old'] is None)
    True

    >>> print(delta.assignee['new'] == jdub)
    True

    >>> print(delta.drafter['old'] is None)
    True

    >>> print(delta.drafter['new'] == jdub)
    True

    >>> print(delta.whiteboard['old'] is None)
    True

    >>> print(delta.whiteboard['new'])
    New whiteboard comments.

    >>> [linked_bug.id for linked_bug in delta.bugs_linked]
    [2]

    >>> delta.bugs_unlinked is None
    True

    >>> delta.milestone is None
    True

    >>> delta.productseries is None
    True

    >>> delta.target is None
    True


Specification Searching
-----------------------

The "SpecificationSet" can be used to search across all specifications.

We can filter for specifications that contain specific text, across all
specifications:

    >>> for spec in specset.specifications(None, filter=[u'install']):
    ...     print(spec.name, spec.target.name)
    cluster-installation kubuntu
    extension-manager-upgrades firefox
    media-integrity-check ubuntu

Specs from inactive products are filtered out.

    >>> from lp.services.database.sqlbase import flush_database_updates
    >>> login('mark@example.com')

    # Unlink the source packages so the project can be deactivated.

    >>> from lp.testing import unlink_source_packages
    >>> unlink_source_packages(upstream_firefox)
    >>> upstream_firefox.active = False
    >>> flush_database_updates()
    >>> for spec in specset.specifications(None, filter=[u'install']):
    ...     print(spec.name, spec.target.name)
    cluster-installation kubuntu
    media-integrity-check ubuntu

Reset firefox so we don't mess up later tests.

    >>> upstream_firefox.active = True
    >>> flush_database_updates()


Specification Blockers and Dependencies
---------------------------------------

We keep track of specification blocking and dependencies. For each spec,
you can ask for its dependencies, or the specs which it blocks. And you
can ask for the full set of dependencies-and-their-dependencies, as well
as the full set of specs-which-block-this-one-and-all-the-specs-that-
block-them-too.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> efourx = getUtility(IProductSet).getByName(
    ...     'firefox').getSpecification('e4x')
    >>> for spec in efourx.getDependencies(): print(spec.name)
    svg-support

    >>> for spec in efourx.all_deps(): print(spec.name)
    svg-support

    >>> for spec in efourx.getBlockedSpecs(): print(spec.name)
    canvas

    >>> for spec in efourx.all_blocked(): print(spec.name)
    canvas

    >>> canvas = efourx.getBlockedSpecs()[0]
    >>> svg = efourx.getDependencies()[0]
    >>> for spec in svg.all_blocked(): print(spec.name)
    canvas
    e4x

    >>> for spec in canvas.all_deps(): print(spec.name)
    e4x
    svg-support


Dependency mapping - `ISpecificationSet.getDependencyDict`
..........................................................

In order to implement the specification plan page efficiently,
`ISpecificationSet` provides a utility method that returns a mapping
from a sequence of specifications to their dependencies.

    >>> spec_a = specset.new(
    ...     'spec-a', 'Spec A',
    ...     'http://www.example.com/SpecA', 'Specification A',
    ...     SpecificationDefinitionStatus.APPROVED, mark,
    ...     target=ubuntu)
    >>> spec_b = specset.new(
    ...     'spec-b', 'Spec B',
    ...     'http://www.example.com/SpecB', 'Specification B',
    ...     SpecificationDefinitionStatus.APPROVED, mark,
    ...     target=ubuntu)
    >>> spec_c = specset.new(
    ...     'spec-c', 'Spec C',
    ...     'http://www.example.com/SpecC', 'Specification C',
    ...     SpecificationDefinitionStatus.APPROVED, mark,
    ...     target=ubuntu)
    >>> spec_d = specset.new(
    ...     'spec-d', 'Spec D',
    ...     'http://www.example.com/SpecD', 'Specification D',
    ...     SpecificationDefinitionStatus.APPROVED, mark,
    ...     target=ubuntu)

When the specs provided have no dependencies, an empty dict is returned.

    >>> specset.getDependencyDict([spec_a, spec_b, spec_c, spec_d])
    {}

If there are dependencies between the specs, the method returns a
mapping between them.

    >>> spec_a.createDependency(spec_b)
    <SpecificationDependency at ...>

    >>> spec_a.createDependency(spec_c)
    <SpecificationDependency at ...>

    >>> spec_c.createDependency(spec_d)
    <SpecificationDependency at ...>

    >>> deps_dict = specset.getDependencyDict(
    ...     [spec_a, spec_b, spec_c, spec_d])
    >>> spec_deps = [(specset.get(key).name, value) for
    ...              (key,value) in deps_dict.items()]
    >>> for (spec_name, deps) in sorted(spec_deps):
    ...     print('%s --> %s' % (
    ...         spec_name,
    ...         ', '.join([dep.name for dep in deps])))
    spec-a --> spec-b, spec-c
    spec-c --> spec-d

Passing in an empty sequences returns an empty dict:

    >>> specset.getDependencyDict([])
    {}


Specification Subscriptions
---------------------------

You can subscribe to a specification, which means that you will be
notified of changes to that spec (and changes to the wiki page for that
spec will be passed on to you too!).

It is possible to indicate that some subscribers are essential to the
discussion of the spec.

    >>> for subscriber in canvas.subscribers: print(subscriber.name)

    >>> from lp.registry.interfaces.person import IPersonSet
    >>> jdub = getUtility(IPersonSet).getByName('jdub')
    >>> sub = canvas.subscribe(jdub, jdub, False)
    >>> print(sub.essential)
    False

    >>> samesub = canvas.getSubscriptionByName('jdub')
    >>> print(samesub.essential)
    False


Specification Goals
-------------------

We can propose a specification as a feature goal for a particular series
or distroseries. That spec can then be approved or declined by the
series drivers.

First, we will show how to propose a goal, and what metadata is recorded
when we do.

    >>> e4x = upstream_firefox.getSpecification('e4x')
    >>> onezero = upstream_firefox.getSeries('1.0')
    >>> e4x.goal is not None
    False

    >>> e4x.goal_proposer is not None
    False

    >>> e4x.date_goal_proposed is not None
    False

    >>> e4x.proposeGoal(onezero, jdub)
    >>> e4x.goal is not None
    True

    >>> print(e4x.goal_proposer.name)
    jdub

    >>> e4x.date_goal_proposed is not None
    True

    >>> e4x.goalstatus.title
    'Proposed'

At this stage, the feature goal is not approved.

    >>> e4x.goal_decider is not None
    False

    >>> e4x.date_goal_decided is not None
    False

We can then accept the goal.

    >>> e4x.acceptBy(mark)
    >>> e4x.goalstatus.title
    'Accepted'

    >>> print(e4x.goal_decider.name)
    mark

    >>> e4x.date_goal_decided is not None
    True

We can change our mind, and decline the goal now.

    >>> e4x.declineBy(mark)
    >>> e4x.goalstatus.title
    'Declined'

And finally, if we propose a new goal, then the decision status is
invalidated. (Notice that we propose the goal as jdub as goals proposed by one
of their drivers [e.g. mark] would be automatically accepted)

    >>> trunk = upstream_firefox.getSeries('trunk')
    >>> e4x.proposeGoal(trunk, jdub)
    >>> e4x.goalstatus.title
    'Proposed'

    >>> e4x.goal_decider is not None
    False

    >>> e4x.date_goal_decided is not None
    False


Specification Lifecycle
-----------------------

We keep track of the progress of the specification, from being "not
started", to "started", to "complete", and we track who started it and
who finished it, and when they updated the relevant status bits.
Currently this is done by setting the statuses, then calling a method
which examines the state of the spec and updates any lifecycle metadata
that needs updating.

We will use the "canvas" spec to show of this lifecycle tracking.

First, lets show that canvas has not really progressed very far.

    >>> canvas.definition_status.title
    'New'

    >>> canvas.implementation_status.title
    'Unknown'

    >>> print(canvas.starter)
    None

    >>> canvas.informational
    False

Now, we want to show that setting the states can update the relevant
metadata. First we will make the spec "started".

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.STARTED)
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Started

    >>> canvas.starter is not None # update should have set starter
    True

    >>> canvas.date_started is not None # and date started
    True

    >>> canvas.completer is not None # but this is still incomplete
    False

    >>> canvas.date_completed is not None
    False

Now we are making slow progress. We want to show that, from a lifecycle
point of view, nothing has changed, so we expect the lifecycle update to
return None.

    >>> canvas.implementation_status = SpecificationImplementationStatus.SLOW
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    True

Oops! Let's say that was a mistake, we instead want to DEFER the start
of this work.

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.DEFERRED)
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Not started

    >>> canvas.starter is not None # update should have reset starter
    False

    >>> canvas.date_started is not None # and date started
    False

    >>> canvas.completer is not None # but this is still incomplete
    False

    >>> canvas.date_completed is not None
    False

Now, let's say that we have actually completed this spec.

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.IMPLEMENTED)
    >>> canvas.definition_status = SpecificationDefinitionStatus.APPROVED
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Complete

    >>> canvas.starter is not None # update should have set starter
    True

    >>> canvas.date_started is not None # and date started
    True

    >>> canvas.completer is not None # but this is still incomplete
    True

    >>> canvas.date_completed is not None
    True

Hmm... now we want to roll back. We can roll back either to "started" or
all the way to "not started".

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.NOTSTARTED)
    >>> canvas.definition_status = SpecificationDefinitionStatus.APPROVED
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Not started

    >>> canvas.starter is not None # update should have reset starter
    False

    >>> canvas.date_started is not None # and date started
    False

    >>> canvas.completer is not None # but this is still incomplete
    False

    >>> canvas.date_completed is not None
    False

OK. Let's make it complete again.

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.IMPLEMENTED)
    >>> canvas.definition_status = SpecificationDefinitionStatus.APPROVED
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Complete

    >>> canvas.starter is not None # update should have set starter
    True

    >>> canvas.date_started is not None # and date started
    True

    >>> canvas.completer is not None # this is complete
    True

    >>> canvas.date_completed is not None
    True

And finally show the rollback to "started".

    >>> canvas.implementation_status = (
    ...     SpecificationImplementationStatus.STARTED)
    >>> canvas.definition_status = SpecificationDefinitionStatus.APPROVED
    >>> newstate = canvas.updateLifecycleStatus(jdub)
    >>> newstate is None
    False

    >>> print(newstate.title)
    Started

    >>> canvas.starter is not None # update should have set starter
    True

    >>> canvas.date_started is not None # and date started
    True

    >>> canvas.completer is not None # but this is still incomplete
    False

    >>> canvas.date_completed is not None
    False
