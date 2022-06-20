Bug Count Summaries
===================

The BugSummary table contains summaries of bug counts. It contains one
or more rows row for every unique public BugTask targetting:

    - product
    - productseries
    - distribution
    - distroseries
    - sourcepackagename
    - ociproject
    - tag
    - status
    - milestone
    - importance
    - has_patch


First we should setup some helpers to use in the examples. These will
let us dump the BugSummary table in a readable format.

    ----------------------------------------------------------
    prod ps   dist ds   spn   ocip  tag mile status import pa   #
    ----------------------------------------------------------

The columns are product, productseries, distribution, distroseries,
sourcepackagename, tag, milestone, status, importance, has_patch,
viewed_by and the count. viewed_by is a team reference and used to
query private bug counts.

    >>> from lp.services.database.interfaces import IMasterStore
    >>> from lp.bugs.interfaces.bugtask import BugTaskStatus
    >>> from lp.bugs.model.bugsummary import BugSummary
    >>> from lp.testing import login_celebrity
    >>> me = login_celebrity("admin")
    >>> store = IMasterStore(BugSummary)

    >>> def name(object_or_none):
    ...     if object_or_none is None:
    ...         return 'x'
    ...     return object_or_none.name

    >>> def ap_desc(policy_or_none):
    ...    if policy_or_none is None:
    ...        return 'x'
    ...    type_names = {
    ...        InformationType.PRIVATESECURITY: 'se',
    ...        InformationType.USERDATA: 'pr',
    ...        InformationType.PROPRIETARY: 'pp',
    ...        }
    ...    return '%-4s/%-2s' % (
    ...        policy_or_none.pillar.name, type_names[policy_or_none.type])

    >>> def print_result(bugsummary_resultset, include_privacy=False):
    ...     # First, flush and invalidate the cache so we see the effects
    ...     # of the underlying database triggers. Normally you don't want
    ...     # to bother with this as you are only interested in counts of
    ...     # bugs created in previous transactions.
    ...     store.flush()
    ...     store.invalidate()
    ...
    ...     # And rollup the BugSummaryJournal into BugSummary
    ...     # so all the records are in one place.
    ...     store.execute("SELECT bugsummary_rollup_journal()")
    ...
    ...     # Make sure our results are in a consistent order.
    ...     ordered_results = bugsummary_resultset.order_by(
    ...         BugSummary.product_id, BugSummary.productseries_id,
    ...         BugSummary.distribution_id, BugSummary.distroseries_id,
    ...         BugSummary.sourcepackagename_id,
    ...         BugSummary.ociproject_id,
    ...         BugSummary.tag,
    ...         BugSummary.milestone_id, BugSummary.status,
    ...         BugSummary.importance, BugSummary.has_patch,
    ...         BugSummary.viewed_by_id, BugSummary.access_policy_id,
    ...         BugSummary.id)
    ...     fmt = (
    ...         "%-4s %-4s %-4s %-4s %-5s %-3s %-3s %-4s "
    ...         "%-6s %-6s %-2s")
    ...     titles = (
    ...         'prod', 'ps', 'dist', 'ds', 'spn', 'ocip', 'tag', 'mile',
    ...         'status', 'import', 'pa')
    ...     if include_privacy:
    ...         fmt += ' %-4s %-7s'
    ...         titles += ('gra', 'pol')
    ...     fmt += ' %3s'
    ...     titles += ('#',)
    ...     header = fmt % titles
    ...     print("-" * len(header))
    ...     print(header)
    ...     print("-" * len(header))
    ...     for bugsummary in ordered_results:
    ...         if not include_privacy:
    ...             assert bugsummary.viewed_by is None
    ...             assert bugsummary.access_policy is None
    ...         data = (
    ...             name(bugsummary.product),
    ...             name(bugsummary.productseries),
    ...             name(bugsummary.distribution),
    ...             name(bugsummary.distroseries),
    ...             name(bugsummary.sourcepackagename),
    ...             name(bugsummary.ociproject),
    ...             bugsummary.tag or 'x',
    ...             name(bugsummary.milestone),
    ...             str(bugsummary.status)[:6],
    ...             str(bugsummary.importance)[:6],
    ...             str(bugsummary.has_patch)[:1])
    ...         if include_privacy:
    ...             data += (
    ...                 name(bugsummary.viewed_by),
    ...                 ap_desc(bugsummary.access_policy),
    ...                 )
    ...         print(fmt % (data + (bugsummary.count,)))
    ...     print(" " * (len(header) - 4), end=" ")
    ...     print("===")
    ...     sum = bugsummary_resultset.sum(BugSummary.count)
    ...     print(" " * (len(header) - 4), end=" ")
    ...     print("%3s" % sum)

    >>> def print_find(*bs_query_args, **bs_query_kw):
    ...     include_privacy = bs_query_kw.pop('include_privacy', False)
    ...     resultset = store.find(BugSummary, *bs_query_args, **bs_query_kw)
    ...     print_result(resultset, include_privacy=include_privacy)


/!\ A Note About Privacy in These Examples
------------------------------------------

All the examples, except for the ones in the Privacy section, are
dealing with public bugs only. This is why they all are using
''BugSummary.viewed_by == None'' in their queries.

To count private bugs, these queries need to join with the
TeamParticipation table as detailed in the Privacy section.


Product Bug Counts
------------------

We can query for how many bugs are targeted to a product.

    >>> prod_a = factory.makeProduct(name='pr-a')
    >>> task = factory.makeBugTask(target=prod_a)
    >>> bug_summaries = store.find(
    ...     BugSummary,
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None)

    >>> print_result(bug_summaries)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-a x    x    x    x     x    x   x    New    Undeci F    1
                                                              ===
                                                                1

An OCI project based in that product will produce an extra row

    >>> oci_project = factory.makeOCIProject(
    ...     pillar=prod_a, ociprojectname='op-1')
    >>> task = factory.makeBugTask(target=oci_project)
    >>> bug_summaries = store.find(
    ...     BugSummary,
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None)

    >>> print_result(bug_summaries)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-a x    x    x    x     op-1 x   x    New    Undeci F    1
    pr-a x    x    x    x     x    x   x    New    Undeci F    2
                                                              ===
                                                                3

There is one row per tag per combination of product, status and milestone.
If we are interested in all bugs targeted to a product regardless of how
they are tagged, we must specify BugSummary.tag == None. If we are
interested in all bugs targeted to a product regardless of their status
or milestone, we need to aggregate them.

    >>> bug = factory.makeBug(target=prod_a, status=BugTaskStatus.NEW)
    >>> bug = factory.makeBug(target=prod_a, status=BugTaskStatus.CONFIRMED)
    >>> bug = factory.makeBug(
    ...     target=prod_a, status=BugTaskStatus.CONFIRMED, tags=['t-a'])


Here are the untagged rows. This will show us the oci-project one, and there
are 2 New and 2 Confirmed bug tasks targetted to the pr-a product.:

    >>> print_find(
    ...     BugSummary.product == prod_a,
    ...     BugSummary.tag == None,
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-a x    x    x    x     op-1 x   x    New    Undeci F    1
    pr-a x    x    x    x     x   x   x    New    Undeci F    3
    pr-a x    x    x    x     x   x   x    Confir Undeci F    2
                                                            ===
                                                              6

Here are the rows associated with the 't-a' tag. There is 1 Confirmed
bug task targetted to the pr-a product who's bug is tagged 't-a'.:

    >>> print_find(
    ...     BugSummary.product == prod_a,
    ...     BugSummary.tag == u't-a',
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-a x    x    x    x     x    t-a x    Confir Undeci F    1
                                                             ===
                                                               1

You will normally want to get the total count counted in the database
rather than waste transmission time to calculate the rows client side.
Note that sum() will return None if there are no matching rows, so we
need to cope with that:

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    6

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == u't-a').sum(BugSummary.count) or 0
    1

If you neglect to specify the tag clause, you will get an incorrect
total (so far, we have created only 4 bugs):

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.product==prod_a).sum(BugSummary.count) or 0
    7

Milestones works similarly, except you leave out the milestone clause
to calculate totals regardless of milestone. If you explicitly query for
the NULL milestone, you are retrieving information on bugs that have not
been assigned to a milestone:

    >>> milestone = factory.makeMilestone(product=prod_a, name='ms-a')
    >>> bug = factory.makeBug(milestone=milestone, tags=['t-b', 't-c'])
    >>> print_find(
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-a x    x    x    x     op-1 x   x    New    Undeci F    1
    pr-a x    x    x    x     x    t-a x    Confir Undeci F    1
    pr-a x    x    x    x     x    t-b ms-a New    Undeci F    1
    pr-a x    x    x    x     x    t-c ms-a New    Undeci F    1
    pr-a x    x    x    x     x    x   ms-a New    Undeci F    1
    pr-a x    x    x    x     x    x   x    New    Undeci F    3
    pr-a x    x    x    x     x    x   x    Confir Undeci F    2
                                                             ===
                                                              10

Number of New bugs not targeted to a milestone. Note the difference
between selecting records where tag is None, and where milestone is None:

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.product == prod_a,
    ...     BugSummary.status == BugTaskStatus.NEW,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.milestone == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    4

Number of bugs targeted to prod_a, grouped by milestone:

    >>> from lp.registry.model.milestone import Milestone
    >>> from storm.expr import Sum, LeftJoin
    >>> join = LeftJoin(
    ...     BugSummary, Milestone, BugSummary.milestone_id == Milestone.id)
    >>> results = store.using(join).find(
    ...     (Milestone, Sum(BugSummary.count)),
    ...     BugSummary.product == prod_a,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None
    ...     ).group_by(Milestone).order_by(Milestone.name)
    >>> for milestone, count in results:
    ...     if milestone:
    ...         print(milestone.name, count)
    ...     else:
    ...         print(None, count)
    ms-a 1
    None 6


ProductSeries Bug Counts
------------------------

Querying for ProductSeries information is identical to querying for
Product information except you patch on the productseries column instead
of the product column. Note that if there is a BugTask targetting a
ProductSeries, there also must be a BugTask record targetting that
ProductSeries' Product:

    >>> prod_b = factory.makeProduct(name='pr-b')
    >>> productseries_b = factory.makeProductSeries(
    ...     product=prod_b, name='ps-b')
    >>> bug_task = factory.makeBugTask(target=productseries_b)
    >>> from storm.expr import Or
    >>> print_find(
    ...     Or(
    ...         BugSummary.productseries == productseries_b,
    ...         BugSummary.product == prod_b),
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    pr-b x    x    x    x     x    x   x    New    Undeci F    1
    x    ps-b x    x    x     x    x   x    New    Undeci F    1
                                                             ===
                                                               2

Distribution Bug Counts
-----------------------

Querying for Distribution bug count information is similar to querying
for Product information. Firstly, of course, you need to match on the
distribution column instead of the product column. The second difference
is you also have the sourcepackagename column to deal with, which acts
the same as tag.

    >>> distribution = factory.makeDistribution(name='di-a')
    >>> package = factory.makeDistributionSourcePackage(
    ...     distribution=distribution, sourcepackagename='sp-a')

    >>> bug = factory.makeBug(
    ...     target=distribution, status=BugTaskStatus.CONFIRMED)
    >>> bug_task = factory.makeBugTask(target=package) # status is NEW

    >>> print_find(
    ...     BugSummary.distribution == distribution,
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    x    x    di-a x    sp-a  x     x   x    New    Undeci F    1
    x    x    di-a x    x     x     x   x    New    Undeci F    1
    x    x    di-a x    x     x     x   x    Confir Undeci F    1
                                                             ===
                                                               3

How many bugs targeted to a distribution?

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.distribution == distribution,
    ...     BugSummary.sourcepackagename == None,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    2

How many NEW bugs targeted to a distribution?

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.distribution == distribution,
    ...     BugSummary.sourcepackagename == None,
    ...     BugSummary.status == BugTaskStatus.NEW,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    1

How many bugs targeted to a particular sourcepackage in a distribution?

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.distribution == distribution,
    ...     BugSummary.sourcepackagename == package.sourcepackagename,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    1

How many Confirmed bugs for a distribution have not been linked to a
sourcepackage? This is tricky, as we cannot directly ask for counts
not linked to a sourcepackage. We can however ask for counts linked to
a sourcepackage, so we subtract this count from the total number of bugs
targeted to the distribution:

    >>> from storm.expr import SQL
    >>> print(store.find(
    ...     BugSummary,
    ...     BugSummary.distribution == distribution,
    ...     BugSummary.status == BugTaskStatus.CONFIRMED,
    ...     BugSummary.viewed_by == None,
    ...     BugSummary.tag == None).sum(SQL("""
    ...         CASE WHEN sourcepackagename IS NULL THEN count ELSE -count END
    ...         """)) or 0)
    1


DistroSeries Bug Counts
-----------------------

DistroSeries bug summary queries work the same as Distribution ones.
Just query using the distroseries column instead of the distribution
column.

    >>> distribution_c = factory.makeDistribution(name='di-c')
    >>> series_c = factory.makeDistroSeries(
    ...     distribution=distribution_c, name='ds-c')
    >>> bug = factory.makeBugTask(target=series_c)
    >>> print_find(
    ...     BugSummary.distroseries == series_c,
    ...     BugSummary.viewed_by == None)
    ------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa   #
    ------------------------------------------------------------
    x    x    x    ds-c x     x    x   x    New    Undeci F    1
                                                             ===
                                                               1


Privacy
-------

So far, all the examples have been dealing with public bugs only.
They can all be extended to include private bug totals by using the
BugSummary.viewed_by column to join with the TeamParticipation table.
This join needs to be an OUTER JOIN.

    >>> from lp.registry.model.teammembership import TeamParticipation

For our examples, first create three people. person_z will not
be subscribed to any bugs, so will have no access to any private bugs.

    >>> person_a = factory.makePerson(name='p-a')
    >>> person_b = factory.makePerson(name='p-b')
    >>> person_z = factory.makePerson(name='p-z')
    >>> owner = factory.makePerson(name='own')

Create some teams too. team_a just has person_a as a member. team_c
has both person_a and person_b as members. These teams will be subscribed
to private bugs.

    >>> from lp.registry.interfaces.person import TeamMembershipPolicy
    >>> team_a = factory.makeTeam(
    ...     name='t-a',
    ...     members=[person_a],
    ...     membership_policy=TeamMembershipPolicy.MODERATED)
    >>> team_c = factory.makeTeam(
    ...     name='t-c',
    ...     members=[person_a, person_b],
    ...     membership_policy=TeamMembershipPolicy.MODERATED)

Create some bugs.
    - bug_a is a private distribution bug, subscribed by team_a
    - bug_b is a private distribution bug, subscribed by person_b
    - bug_c is a private distroseries bug, which also gets an implicit
      distribution task. Subscribed to by team_c.
    - bug_z is public.

    >>> from lp.app.enums import InformationType
    >>> distro_p = factory.makeDistribution(name='di-p')
    >>> series_p = factory.makeDistroSeries(
    ...     distribution=distro_p, name='ds-p')
    >>> bug_a = factory.makeBug(
    ...     owner=owner, target=distro_p,
    ...     information_type=InformationType.USERDATA)
    >>> bug_b = factory.makeBug(
    ...     owner=owner, target=distro_p,
    ...     information_type=InformationType.USERDATA)
    >>> bug_c = factory.makeBug(
    ...     owner=owner, series=series_p,
    ...     information_type=InformationType.USERDATA)
    >>> bug_z = factory.makeBug(owner=owner, target=distro_p)

    >>> sub = bug_a.subscribe(team_a, person_a)
    >>> sub = bug_b.subscribe(person_b, person_b)
    >>> sub = bug_c.subscribe(team_c, person_a)

Whew! Check out what the BugSummary records now look like:

    >>> distro_or_series = Or(
    ...     BugSummary.distribution == distro_p,
    ...     BugSummary.distroseries == series_p)
    >>> print_find(distro_or_series, include_privacy=True)
    -------------------------------------------------------------------------
    prod ps   dist ds   spn   ocip tag mile status import pa gra  pol       #
    -------------------------------------------------------------------------
    x    x    di-p x    x     x   x   x    New    Undeci F  p-b  x         1
    x    x    di-p x    x     x   x   x    New    Undeci F  own  x         3
    x    x    di-p x    x     x   x   x    New    Undeci F  t-a  x         1
    x    x    di-p x    x     x   x   x    New    Undeci F  t-c  x         1
    x    x    di-p x    x     x   x   x    New    Undeci F  x    di-p/pr   3
    x    x    di-p x    x     x   x   x    New    Undeci F  x    x         1
    x    x    x    ds-p x     x   x   x    New    Undeci F  own  x         1
    x    x    x    ds-p x     x   x   x    New    Undeci F  t-c  x         1
    x    x    x    ds-p x     x   x   x    New    Undeci F  x    di-p/pr   1
                                                                          ===
                                                                           13

So how many public bugs are there on the distro?

    >>> store.find(
    ...     BugSummary,
    ...     BugSummary.distribution == distro_p,
    ...     BugSummary.viewed_by == None, # Public bugs only
    ...     BugSummary.access_policy == None, # Public bugs only
    ...     BugSummary.sourcepackagename == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    1

But how many can the owner see?

    >>> from storm.expr import And
    >>> join = LeftJoin(
    ...     BugSummary, TeamParticipation,
    ...     BugSummary.viewed_by_id == TeamParticipation.teamID)
    >>> store.using(join).find(
    ...     BugSummary,
    ...     BugSummary.distribution == distro_p,
    ...     Or(
    ...         And(BugSummary.viewed_by == None,
    ...             BugSummary.access_policy == None),
    ...         TeamParticipation.person == owner),
    ...     BugSummary.sourcepackagename == None,
    ...     BugSummary.tag == None).sum(BugSummary.count) or 0
    4
