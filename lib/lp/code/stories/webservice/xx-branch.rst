Introduction
============

Launchpad provides two ways to programmatically interact with your
branches. You can either interact with the branches themselves using
`breezy`, or you can use Launchpad's webservice APIs to explore
information about the branches and how they relate to the rest of
the things on Launchpad.

    >>> from datetime import datetime
    >>> import pytz
    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.code.enums import BranchLifecycleStatus, BranchType
    >>> from lazr.restful.marshallers import DateTimeFieldMarshaller
    >>> from lp.code.interfaces.branch import IBranch

To make this document a little more readable, we'll have to define some
helpers. This one turns a JSON date/time response into a Python
`datetime` object.

    >>> def get_as_datetime(response):
    ...     """Return a datetime object from a JSON response."""
    ...     returned_time = response.jsonBody()
    ...     marshaller = DateTimeFieldMarshaller(
    ...         IBranch["next_mirror_time"], response
    ...     )
    ...     return marshaller.marshall_from_json_data(returned_time)
    ...


Requesting a mirror
===================

Many of the branches on Launchpad are mirrored branches: branches that
are hosted on other servers and then mirrored regularly by Launchpad's
branch puller.

Normally, the puller fetches branches every six hours or so. However,
it also provides a way for you to request that a mirror be done
immediately.

Let's make a mirrored branch to play with:

    >>> login(ANONYMOUS)
    >>> branch = removeSecurityProxy(
    ...     factory.makeAnyBranch(branch_type=BranchType.MIRRORED)
    ... )
    >>> logout()

At the moment, it's not scheduled to be mirrored.

    >>> print(branch.next_mirror_time)
    None

But we can ask for it to be mirrored using the webservice:

    >>> branch_url = "/" + branch.unique_name
    >>> start_time = datetime.now(pytz.UTC)
    >>> response = webservice.named_post(branch_url, "requestMirror")
    >>> end_time = datetime.now(pytz.UTC)
    >>> new_mirror_time = get_as_datetime(response)
    >>> branch.next_mirror_time == new_mirror_time
    True

The new "next mirror time" is the time when we actually submitted the
request for a mirror:

    >>> print(start_time < branch.next_mirror_time < end_time)
    True


Basic branch attributes
=======================

Not everything about a branch is exposed.  Hopefully most of what users
really care about is exposed, and we will undoubtedly expand this as
time goes on.

    >>> login("admin@canonical.com")
    >>> eric = factory.makePerson(name="eric")
    >>> marley = factory.makePerson(name="marley")
    >>> fooix = factory.makeProduct(name="fooix")
    >>> branch = factory.makeProductBranch(
    ...     branch_type=BranchType.HOSTED,
    ...     owner=eric,
    ...     product=fooix,
    ...     name="trunk",
    ...     title="The Fooix Trunk",
    ...     date_created=datetime(2009, 1, 1, tzinfo=pytz.UTC),
    ... )
    >>> feature_branch = factory.makeAnyBranch(
    ...     owner=eric,
    ...     product=fooix,
    ...     name="feature-branch",
    ...     lifecycle_status=BranchLifecycleStatus.EXPERIMENTAL,
    ... )
    >>> feature_branch_bug = factory.makeBug(
    ...     target=fooix, title="Stuff needs features"
    ... )
    >>> feature_branch_spec = factory.makeSpecification(
    ...     product=fooix, title="Super Feature X"
    ... )
    >>> merge_proposal = factory.makeBranchMergeProposal(
    ...     target_branch=branch,
    ...     source_branch=feature_branch,
    ...     registrant=eric,
    ... )
    >>> branch_url = "/" + branch.unique_name
    >>> feature_branch_url = "/" + feature_branch.unique_name
    >>> feature_branch_bug_url = "/bugs/" + str(feature_branch_bug.id)
    >>> feature_branch_spec_url = "/" + "/".join(
    ...     [
    ...         feature_branch_spec.product.name,
    ...         "+spec",
    ...         feature_branch_spec.name,
    ...     ]
    ... )
    >>> logout()

    >>> from lp.testing.pages import webservice_for_person
    >>> service = webservice_for_person(eric)
    >>> fooix_trunk = webservice.get(branch_url).jsonBody()
    >>> from lazr.restful.testing.webservice import pprint_entry
    >>> pprint_entry(fooix_trunk)
    branch_format: None
    branch_type: 'Hosted'
    bzr_identity: 'lp://dev/~eric/fooix/trunk'
    code_import_link: None
    control_format: None
    date_created: '2009-01-01T00:00:00+00:00'
    date_last_modified: '2009-01-01T00:00:00+00:00'
    dependent_branches_collection_link:
      '.../~eric/fooix/trunk/dependent_branches'
    description: None
    display_name: 'lp://dev/~eric/fooix/trunk'
    explicitly_private: False
    information_type: 'Public'
    landing_candidates_collection_link:
      '.../~eric/fooix/trunk/landing_candidates'
    landing_targets_collection_link: '.../~eric/fooix/trunk/landing_targets'
    last_mirror_attempt: None
    last_mirrored: None
    last_scanned: None
    last_scanned_id: None
    lifecycle_status: 'Development'
    linked_bugs_collection_link: 'http://.../~eric/fooix/trunk/linked_bugs'
    mirror_status_message: None
    name: 'trunk'
    owner_link: '.../~eric'
    private: False
    project_link: '.../fooix'
    recipes_collection_link: 'http://.../~eric/fooix/trunk/recipes'
    registrant_link: '.../~eric'
    repository_format: None
    resource_type_link: '.../#branch'
    reviewer_link: None
    revision_count: 0
    self_link: '.../~eric/fooix/trunk'
    sourcepackage_link: None
    spec_links_collection_link: '.../~eric/fooix/trunk/spec_links'
    subscribers_collection_link: 'http://.../~eric/fooix/trunk/subscribers'
    subscriptions_collection_link:
      'http://.../~eric/fooix/trunk/subscriptions'
    unique_name: '~eric/fooix/trunk'
    url: None
    web_link: 'http://code.../~eric/fooix/trunk'
    webhooks_collection_link: 'http://.../~eric/fooix/trunk/webhooks'
    whiteboard: None

There is a branch merge proposal with Fooix trunk as the target branch, so it
should have a branch at the endpoint of landing_candidates.

    >>> landing_candidates = webservice.get(
    ...     fooix_trunk["landing_candidates_collection_link"]
    ... ).jsonBody()
    >>> for candidate in landing_candidates["entries"]:
    ...     print(candidate["source_branch_link"])
    ...
    http://.../~eric/fooix/feature-branch


The source_branch of the landing candidate should have this same merge
proposal in its landing_targets.

    >>> feature_branch_link = "/~eric/fooix/feature-branch"
    >>> feature_branch = webservice.get(feature_branch_link).jsonBody()
    >>> print(feature_branch["unique_name"])
    ~eric/fooix/feature-branch

    >>> landing_targets = webservice.get(
    ...     feature_branch["landing_targets_collection_link"]
    ... ).jsonBody()
    >>> for target in landing_targets["entries"]:
    ...     print(target["target_branch_link"])
    ...
    http://.../~eric/fooix/trunk

The isPersonTrustedReviewer method is exposed, and takes a person link.

    >>> trusted = webservice.named_get(
    ...     feature_branch["self_link"],
    ...     "isPersonTrustedReviewer",
    ...     reviewer=feature_branch["owner_link"],
    ... ).jsonBody()
    >>> print(trusted)
    True


Project branches
================

The branches of a project are also available.

    >>> from operator import itemgetter

    >>> def print_branch(branch):
    ...     print(branch["unique_name"] + " - " + branch["lifecycle_status"])
    ...
    >>> def print_branches(webservice, url, status=None, modified_since=None):
    ...     branches = webservice.named_get(
    ...         url,
    ...         "getBranches",
    ...         status=status,
    ...         modified_since=modified_since,
    ...     ).jsonBody()
    ...     for branch in sorted(
    ...         branches["entries"], key=itemgetter("unique_name")
    ...     ):
    ...         print_branch(branch)
    ...

    >>> print_branches(webservice, "/fooix")
    ~eric/fooix/feature-branch - Experimental
    ~eric/fooix/trunk - Development

The branches can be limited to those that have been modified since a specified
time.

    >>> print_branches(
    ...     webservice, "/fooix", modified_since="2010-01-01T00:00:00+00:00"
    ... )
    ~eric/fooix/feature-branch - Experimental

A list of lifecycle statuses can be provided for filtering.

    >>> print_branches(webservice, "/fooix", ("Experimental"))
    ~eric/fooix/feature-branch - Experimental

Branches for people
===================

The branches owned by a person are available from the person object.

    >>> print_branches(webservice, "/~eric")
    ~eric/fooix/feature-branch - Experimental
    ~eric/fooix/trunk - Development

As with projects, these can be filtered by the branch status.

    >>> print_branches(webservice, "/~eric", ("Experimental"))
    ~eric/fooix/feature-branch - Experimental

Project group branches
======================

Branches are also accessible for a project group.

    >>> login("admin@canonical.com")
    >>> projectgroup = factory.makeProject(name="widgets")
    >>> fooix.projectgroup = projectgroup
    >>> blob = factory.makeProduct(name="blob", projectgroup=projectgroup)
    >>> branch = factory.makeProductBranch(product=blob, name="bar")
    >>> branch.owner.name = "mary"
    >>> logout()

    >>> print_branches(webservice, "/widgets")
    ~eric/fooix/feature-branch - Experimental
    ~eric/fooix/trunk - Development
    ~mary/blob/bar - Development

As with projects, these can be filtered by the branch status.

    >>> print_branches(webservice, "/widgets", ("Experimental"))
    ~eric/fooix/feature-branch - Experimental

Differences between versions
============================

In version 'beta', a branch can be made private or public by invoking
the named operation 'setPrivate'.

    >>> branch = webservice.get(branch_url).jsonBody()
    >>> print(branch["private"])
    False

    >>> response = webservice.named_post(
    ...     branch_url, "setPrivate", api_version="beta", private=True
    ... )
    >>> branch = webservice.get(branch_url).jsonBody()
    >>> print(branch["information_type"])
    Private

In subsequent versions, 'setPrivate' is gone; you have to use the
'transitionToInformationType' method.

    >>> print(
    ...     webservice.named_post(
    ...         branch_url, "setPrivate", api_version="devel", private=True
    ...     )
    ... )
    HTTP/1.1 400 Bad Request
    ...
    No such operation: setPrivate

Removing branches
=================

Branches may have dependencies so it may not necessarily be possible to
delete them.

    >>> deletable = webservice.named_get(
    ...     "/~eric/fooix/feature-branch", "canBeDeleted"
    ... ).jsonBody()
    >>> print(deletable)
    False

    Deleting only works on branches that do not have anything else
    depending on them.

    >>> response = webservice.delete("/~eric/fooix/feature-branch")
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> response = webservice.delete("/~mary/blob/bar")
    >>> print(response)
    HTTP/1.1 200 Ok
    ...

    >>> print_branches(webservice, "/widgets")
    ~eric/fooix/trunk - Development

