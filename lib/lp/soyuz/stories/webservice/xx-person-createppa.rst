Creating a PPA
==============

    >>> from zope.component import getUtility
    >>> from lp.app.interfaces.launchpad import ILaunchpadCelebrities
    >>> from lp.registry.interfaces.distribution import IDistributionSet
    >>> from lp.testing import celebrity_logged_in
    >>> from lp.testing.sampledata import ADMIN_EMAIL
    >>> login(ADMIN_EMAIL)
    >>> getUtility(IDistributionSet)["ubuntutest"].supports_ppas = True
    >>> owner = factory.makePerson()
    >>> url = "/~%s" % owner.name
    >>> logout()
    >>> ppa_owner = webservice.get(url).jsonBody()

    >>> from lp.testing.pages import webservice_for_person
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> ppa_owner_webservice = webservice_for_person(
    ...     owner, permission=OAuthPermission.WRITE_PRIVATE
    ... )

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         distribution="/ubuntu",
    ...         name="yay",
    ...         displayname="My shiny new PPA",
    ...         description="Shinyness!",
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://api.launchpad.test/.../+archive/ubuntu/yay
    ...

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         name="ubuntu",
    ...         displayname="My shiny new PPA",
    ...         description="Shinyness!",
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    A PPA cannot have the same name as its distribution.

Creating private PPAs
---------------------

Our PPA owner now has a single PPA.

    >>> print_self_link_of_entries(
    ...     webservice.get(ppa_owner["ppas_collection_link"]).jsonBody()
    ... )
    http://api.launchpad.test/beta/~.../+archive/ubuntu/yay

They aren't a commercial admin, so they cannot create private PPAs.

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         name="whatever",
    ...         displayname="My secret new PPA",
    ...         description="Secretness!",
    ...         private=True,
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    ... is not allowed to make private PPAs

After attempting and failing to create a private PPA, they still have the same
single PPA they had at the beginning:

    >>> print_self_link_of_entries(
    ...     webservice.get(ppa_owner["ppas_collection_link"]).jsonBody()
    ... )
    http://api.launchpad.test/beta/~.../+archive/ubuntu/yay

However, we can grant them commercial admin access:

    >>> with celebrity_logged_in("admin"):
    ...     comm = getUtility(ILaunchpadCelebrities).commercial_admin
    ...     comm.addMember(owner, comm.teamowner)
    ...
    (True, <DBItem TeamMembershipStatus.APPROVED, (2) Approved>)

Once they have commercial access, they can create private PPAs:

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         name="secret",
    ...         displayname="My secret new PPA",
    ...         description="Secretness!",
    ...         private=True,
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://api.launchpad.test/.../+archive/ubuntu/secret
    ...

And the PPA appears in their list of PPAs:

    >>> print_self_link_of_entries(
    ...     webservice.get(ppa_owner["ppas_collection_link"]).jsonBody()
    ... )
    http://api.launchpad.test/.../+archive/ubuntu/secret
    http://api.launchpad.test/.../+archive/ubuntu/yay

And the PPA is, of course, private:

    >>> ppa = ppa_owner_webservice.named_get(
    ...     ppa_owner["self_link"], "getPPAByName", name="secret"
    ... ).jsonBody()
    >>> ppa["private"]
    True

It's possible to create PPAs for all sorts of distributions.

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         distribution="/ubuntutest",
    ...         name="ppa",
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://api.launchpad.test/.../+archive/ubuntutest/ppa
    ...

But not for distributions that don't have PPAs enabled.

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"],
    ...         "createPPA",
    ...         {},
    ...         distribution="/redhat",
    ...         name="ppa",
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    Red Hat does not support PPAs.


Defaults
--------

createPPA's distribution and name arguments were added years after the
method, so they remain optional and default to Ubuntu and "ppa"
respectively.

    >>> print(
    ...     ppa_owner_webservice.named_post(
    ...         ppa_owner["self_link"], "createPPA", {}
    ...     )
    ... )
    HTTP/1.1 201 Created
    ...
    Location: http://api.launchpad.test/.../+archive/ubuntu/ppa
    ...
