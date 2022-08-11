Bug Nomination Pages
====================

Series targeting is done on the +nominate page of a bug. From here,
bug supervisors can propose that the bug be fixed in specific distribution
and product series, and release managers can directly target
the bug to series for which they are drivers.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from zope.component import getUtility, getMultiAdapter

    >>> from lp.testing import login_person
    >>> from lp.services.webapp.interfaces import IOpenLaunchBag
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.bugs.interfaces.bugtask import IBugTaskSet
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.registry.interfaces.person import IPersonSet
    >>> from lp.registry.interfaces.product import IProductSet
    >>> from lp.testing.sampledata import (ADMIN_EMAIL)

    >>> login(ADMIN_EMAIL)
    >>> nominator = factory.makePerson(name='nominator')
    >>> ubuntu = getUtility(IDistributionSet).getByName("ubuntu")
    >>> ubuntu = removeSecurityProxy(ubuntu)
    >>> ubuntu.bug_supervisor = nominator
    >>> firefox = getUtility(IProductSet).getByName("firefox")
    >>> firefox = removeSecurityProxy(firefox)
    >>> firefox.bug_supervisor = nominator

    >>> ignored = login_person(nominator)
    >>> request = LaunchpadTestRequest()
    >>> bug_one_in_ubuntu_firefox = getUtility(IBugTaskSet).get(17)
    >>> print(bug_one_in_ubuntu_firefox.bug.id)
    1
    >>> print(bug_one_in_ubuntu_firefox.target.bugtargetdisplayname)
    mozilla-firefox (Ubuntu)

    >>> nomination_view = getMultiAdapter(
    ...     (bug_one_in_ubuntu_firefox, request), name="+nominate")
    >>> launchbag = getUtility(IOpenLaunchBag)


Submitting Nominations
----------------------

BugNominationView is a LaunchpadFormView. It expects a "submit" action
to process nominations.

Here's an example of nominating a bug for a distroseries.

    >>> ignored = login_person(nominator)

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={"field.actions.submit": "Submit Nominations",
    ...           "field.nominatable_series": ["warty"]})

    >>> nomination_view = getMultiAdapter(
    ...     (bug_one_in_ubuntu_firefox, request), name="+nominate")

(Add objects to the LaunchBag that will be used by the view.)

    >>> launchbag.clear()
    >>> launchbag.add(bug_one_in_ubuntu_firefox)
    >>> launchbag.add(bug_one_in_ubuntu_firefox.distribution)

    >>> ubuntu_warty = ubuntu.getSeries("warty")

    >>> bug_one = bug_one_in_ubuntu_firefox.bug
    >>> bug_one.canBeNominatedFor(ubuntu_warty)
    True

(Process the nominations.)

    >>> nomination_view.initialize()

    >>> bug_one.canBeNominatedFor(ubuntu_warty)
    False

    >>> len(request.response.notifications)
    1

    >>> print(request.response.notifications[0].message)
    Added nominations for: Ubuntu Warty

Here's an example of nominating a bug for a productseries.

    >>> bug_one_in_firefox = getUtility(IBugTaskSet).get(2)
    >>> print(bug_one_in_firefox.bug.id)
    1
    >>> print(bug_one_in_firefox.target.bugtargetdisplayname)
    Mozilla Firefox

    >>> firefox = bug_one_in_firefox.target

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={"field.actions.submit": "Submit Nominations",
    ...           "field.nominatable_series": ["trunk"]})

    >>> nomination_view = getMultiAdapter(
    ...     (bug_one_in_firefox, request), name="+nominate")

(Add objects to the LaunchBag that will be used by the view.)

    >>> launchbag.clear()
    >>> launchbag.add(bug_one_in_firefox)
    >>> launchbag.add(bug_one_in_firefox.product)

    >>> firefox_trunk = firefox.getSeries("trunk")
    >>> bug_one.canBeNominatedFor(firefox_trunk)
    True

(Process the nominations.)

    >>> nomination_view.initialize()

    >>> bug_one.canBeNominatedFor(firefox_trunk)
    False

    >>> len(request.response.notifications)
    1

    >>> print(request.response.notifications[0].message)
    Added nominations for: Mozilla Firefox trunk


Approving and Declining Nominations
-----------------------------------

On the bug page
...............

Nominations are listed in the same table on the bug page that shows
bugtasks, rendered in a way that makes them look obviously different
from bugtasks.

The +edit-form renders the form that lets a driver approve and decline
nominations.

    >>> ubuntu_hoary = ubuntu.getSeries("hoary")
    >>> hoary_nomination = bug_one.getNominationFor(ubuntu_hoary)

A Proposed nomination shows as "Nominated", including an approve/decline
buttons for a user with release management privileges.

    >>> login("foo.bar@canonical.com")

    >>> hoary_nomination_edit_form = getMultiAdapter(
    ...     (hoary_nomination, request), name="+edit-form")

    >>> hoary_nomination_edit_form.shouldShowApproveButton(None)
    True
    >>> hoary_nomination_edit_form.shouldShowDeclineButton(None)
    True

If the nomination is declined, the only possible status change is
approval.

    >>> hoary_nomination.decline(launchbag.user)
    >>> print(hoary_nomination.status.title)
    Declined

    >>> hoary_nomination_edit_form.shouldShowApproveButton(None)
    True
    >>> hoary_nomination_edit_form.shouldShowDeclineButton(None)
    False


Series Targeting For Release Managers
-------------------------------------

When a release manager "nominates" a bug, the nomination is immediately
approved. The nomination is created only to communicate when and by whom
the bug was proposed, so users aren't left wondering why some tasks have
nominations and others don't.

For example, bug one is currently nominated for Hoary and Warty.

    >>> ubuntu_nominations = bug_one.getNominations(ubuntu)
    >>> for nomination in ubuntu_nominations:
    ...     print(nomination.target.bugtargetdisplayname)
    Ubuntu Hoary
    Ubuntu Warty

Bug #1 currently has three tasks.

    >>> for bugtask in bug_one.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    Mozilla Firefox
    mozilla-firefox (Ubuntu)
    mozilla-firefox (Debian)

But when we submit a "nomination" for Grumpy as a privileged user, it is
immediately approved, and a new task added. By "privileged user" in this
context, we mean a user that has, either directly or through a team,
launchpad.Driver permission on the nomination.

    >>> ubuntu_team = getUtility(IPersonSet).getByName("ubuntu-team")

    >>> login("celso.providelo@canonical.com")

    >>> cprov = launchbag.user
    >>> print(cprov.name)
    cprov

    >>> cprov.inTeam(ubuntu_team)
    True

    >>> request = LaunchpadTestRequest(
    ...     method="POST",
    ...     form={"field.actions.submit": "Submit Nominations",
    ...           "field.nominatable_series": ["grumpy"]})

    >>> nomination_view = getMultiAdapter(
    ...     (bug_one_in_ubuntu_firefox, request), name="+nominate")
    >>> launchbag.clear()
    >>> launchbag.add(bug_one_in_ubuntu_firefox)
    >>> launchbag.add(bug_one_in_ubuntu_firefox.distribution)

    >>> def print_nominations(nominations):
    ...     for nomination in nominations:
    ...         print("%s, %s" % (
    ...             nomination.target.bugtargetdisplayname,
    ...             nomination.status.title))
    >>> print_nominations(bug_one.getNominations(ubuntu))
    Ubuntu Hoary, Declined
    Ubuntu Warty, Nominated

(Process the nominations.)

    >>> nomination_view.initialize()

An approved nomination, for Ubuntu Grumpy, has been added, and another
bugtask has been added.

    >>> print_nominations(bug_one.getNominations(ubuntu))
    Ubuntu Grumpy, Approved
    Ubuntu Hoary, Declined
    Ubuntu Warty, Nominated

    >>> for bugtask in bug_one.bugtasks:
    ...     print(bugtask.bugtargetdisplayname)
    Mozilla Firefox
    mozilla-firefox (Ubuntu)
    mozilla-firefox (Ubuntu Grumpy)
    mozilla-firefox (Debian)

The notification message also changes slightly.

    >>> print(request.response.notifications[0].message)
    Targeted bug to: Ubuntu Grumpy
