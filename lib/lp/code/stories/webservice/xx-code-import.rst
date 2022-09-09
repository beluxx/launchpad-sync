Introduction
============

Launchpad can tell you about the code imports that power a branch
if it is an import branch.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> from lp.code.tests.helpers import GitHostingFixture
    >>> from lp.services.webapp.interfaces import OAuthPermission
    >>> from lp.testing.pages import webservice_for_person

First we create some objects for use in the tests.

    >>> login(ANONYMOUS)
    >>> person = factory.makePerson(name="import-owner")
    >>> team = factory.makeTeam(name="import-owner-team")
    >>> other_team = factory.makeTeam(name="other-team")
    >>> other_person = factory.makePerson(name="other-person")
    >>> removeSecurityProxy(person).join(team)
    >>> product = factory.makeProduct(name="scruff")
    >>> product_name = product.name
    >>> svn_branch_url = "http://svn.domain.com/source"
    >>> code_import = removeSecurityProxy(
    ...     factory.makeProductCodeImport(
    ...         registrant=person,
    ...         product=product,
    ...         branch_name="import",
    ...         svn_branch_url=svn_branch_url,
    ...     )
    ... )
    >>> no_import_branch = removeSecurityProxy(
    ...     factory.makeProductBranch(
    ...         owner=person, product=product, name="no-import"
    ...     )
    ... )
    >>> logout()
    >>> import_webservice = webservice_for_person(
    ...     person, permission=OAuthPermission.WRITE_PUBLIC
    ... )

If we query a branch with no import then we find that it tells us
it doesn't have one.

    >>> branch_url = "/" + no_import_branch.unique_name
    >>> response = import_webservice.get(branch_url)
    >>> representation = response.jsonBody()
    >>> print(representation["code_import_link"])
    None

For a branch with an import we get a link to the import entry in its
representation.

    >>> branch_url = "/" + code_import.branch.unique_name
    >>> response = import_webservice.get(branch_url)
    >>> representation = response.jsonBody()
    >>> print(representation["code_import_link"])
    http://.../~import-owner/scruff/import/+code-import

We can get some information about the import using this URL.

    >>> import_url = representation["code_import_link"]
    >>> response = import_webservice.get(import_url)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"] == import_url)
    True
    >>> print(representation["branch_link"])
    http://.../~import-owner/scruff/import
    >>> print(representation["review_status"])
    Reviewed
    >>> print(representation["rcs_type"])
    Subversion via bzr-svn
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"])
    http://svn.domain.com/source
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None


Package Branches
----------------

The same is true for package branches.

    >>> login(ANONYMOUS)
    >>> distribution = factory.makeDistribution(name="scruffbuntu")
    >>> distroseries = factory.makeDistroSeries(
    ...     name="manic", distribution=distribution
    ... )
    >>> source_package = factory.makeSourcePackage(
    ...     sourcepackagename="scruff", distroseries=distroseries
    ... )
    >>> code_import = removeSecurityProxy(
    ...     factory.makePackageCodeImport(
    ...         registrant=person,
    ...         sourcepackage=source_package,
    ...         branch_name="import",
    ...         svn_branch_url="http://svn.domain.com/package_source",
    ...     )
    ... )
    >>> logout()
    >>> import_webservice = webservice_for_person(
    ...     person, permission=OAuthPermission.WRITE_PUBLIC
    ... )

There is a link on the branch object

    >>> branch_url = "/" + code_import.branch.unique_name
    >>> response = import_webservice.get(branch_url)
    >>> representation = response.jsonBody()
    >>> print(representation["code_import_link"])
    http://.../~import-owner/scruffbuntu/manic/scruff/import/+code-import

and there is information available about the import itself.

    >>> import_url = representation["code_import_link"]
    >>> response = import_webservice.get(import_url)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"] == import_url)
    True
    >>> print(representation["branch_link"])
    http://.../~import-owner/scruffbuntu/manic/scruff/import
    >>> print(representation["review_status"])
    Reviewed
    >>> print(representation["rcs_type"])
    Subversion via bzr-svn
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"])
    http://svn.domain.com/package_source
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None


Creating Imports
----------------

We can create an import using the API by calling a method on the project.

    >>> product_url = "/" + product_name
    >>> new_remote_url = factory.getUniqueURL()
    >>> response = import_webservice.named_post(
    ...     product_url,
    ...     "newCodeImport",
    ...     branch_name="new-import",
    ...     rcs_type="Git",
    ...     url=new_remote_url,
    ... )
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])
    http://.../~import-owner/scruff/new-import/+code-import
    >>> print(representation["branch_link"])
    http://.../~import-owner/scruff/new-import
    >>> print(representation["git_repository_link"])
    None
    >>> print(representation["rcs_type"])
    Git
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"] == new_remote_url)
    True
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None

If we must we can create a CVS import.

    >>> product_url = "/" + product_name
    >>> new_remote_url = factory.getUniqueURL()
    >>> response = import_webservice.named_post(
    ...     product_url,
    ...     "newCodeImport",
    ...     branch_name="cvs-import",
    ...     rcs_type="Concurrent Versions System",
    ...     cvs_root=new_remote_url,
    ...     cvs_module="foo",
    ... )
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])
    http://.../~import-owner/scruff/cvs-import/+code-import
    >>> print(representation["branch_link"])
    http://.../~import-owner/scruff/cvs-import
    >>> print(representation["git_repository_link"])
    None
    >>> print(representation["rcs_type"])
    Concurrent Versions System
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"])
    None
    >>> print(representation["cvs_root"] == new_remote_url)
    True
    >>> print(representation["cvs_module"] == "foo")
    True
    >>> print(representation["date_last_successful"])
    None

We can create a Git-to-Git import.

    >>> product_url = "/" + product_name
    >>> new_remote_url = factory.getUniqueURL()
    >>> with GitHostingFixture():
    ...     response = import_webservice.named_post(
    ...         product_url,
    ...         "newCodeImport",
    ...         branch_name="new-import",
    ...         rcs_type="Git",
    ...         target_rcs_type="Git",
    ...         url=new_remote_url,
    ...     )
    ...
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])
    http://.../~import-owner/scruff/+git/new-import/+code-import
    >>> print(representation["branch_link"])
    None
    >>> print(representation["git_repository_link"])
    http://.../~import-owner/scruff/+git/new-import
    >>> print(representation["rcs_type"])
    Git
    >>> print(representation["target_rcs_type"])
    Git
    >>> print(representation["url"] == new_remote_url)
    True
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None

We can also create an import targeting a source package.

    >>> login(ANONYMOUS)
    >>> source_package_url = (
    ...     "/"
    ...     + distribution.name
    ...     + "/"
    ...     + distroseries.name
    ...     + "/+source/"
    ...     + source_package.name
    ... )
    >>> logout()
    >>> new_remote_url = factory.getUniqueURL()
    >>> response = import_webservice.named_post(
    ...     source_package_url,
    ...     "newCodeImport",
    ...     branch_name="new-import",
    ...     rcs_type="Git",
    ...     url=new_remote_url,
    ... )
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])
    http://.../~import-owner/scruffbuntu/manic/scruff/new-import/+code-import
    >>> print(representation["branch_link"])
    http://.../~import-owner/scruffbuntu/manic/scruff/new-import
    >>> print(representation["git_repository_link"])
    None
    >>> print(representation["rcs_type"])
    Git
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"] == new_remote_url)
    True
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None

We can create a Git-to-Git import targeting a distribution source package.

    >>> login(ANONYMOUS)
    >>> distro_source_package_url = (
    ...     "/" + distribution.name + "/+source/" + source_package.name
    ... )
    >>> logout()
    >>> new_remote_url = factory.getUniqueURL()
    >>> with GitHostingFixture():
    ...     response = import_webservice.named_post(
    ...         distro_source_package_url,
    ...         "newCodeImport",
    ...         branch_name="new-import",
    ...         rcs_type="Git",
    ...         target_rcs_type="Git",
    ...         url=new_remote_url,
    ...     )
    ...
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])  # noqa
    http://.../~import-owner/scruffbuntu/+source/scruff/+git/new-import/+code-import
    >>> print(representation["branch_link"])
    None
    >>> print(representation["git_repository_link"])
    http://.../~import-owner/scruffbuntu/+source/scruff/+git/new-import
    >>> print(representation["rcs_type"])
    Git
    >>> print(representation["target_rcs_type"])
    Git
    >>> print(representation["url"] == new_remote_url)
    True
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None

If we wish to create a branch owned by a team we are part of then we can.

    >>> team_url = import_webservice.getAbsoluteUrl("/~import-owner-team")
    >>> new_remote_url = factory.getUniqueURL()
    >>> response = import_webservice.named_post(
    ...     product_url,
    ...     "newCodeImport",
    ...     branch_name="team-import",
    ...     rcs_type="Git",
    ...     url=new_remote_url,
    ...     owner=team_url,
    ... )
    >>> print(response.status)
    201
    >>> location = response.getHeader("Location")
    >>> response = import_webservice.get(location)
    >>> representation = response.jsonBody()
    >>> print(representation["self_link"])
    http://.../~import-owner-team/scruff/team-import/+code-import
    >>> print(representation["branch_link"])
    http://.../~import-owner-team/scruff/team-import
    >>> print(representation["git_repository_link"])
    None
    >>> print(representation["rcs_type"])
    Git
    >>> print(representation["target_rcs_type"])
    Bazaar
    >>> print(representation["url"] == new_remote_url)
    True
    >>> print(representation["cvs_root"])
    None
    >>> print(representation["cvs_module"])
    None
    >>> print(representation["date_last_successful"])
    None


Requesting an Import
--------------------

You can request that an approved, working import happen soon over the
API using the requestImport() method.

    >>> login(ANONYMOUS)
    >>> git_import = factory.makeProductCodeImport(
    ...     registrant=person,
    ...     product=product,
    ...     branch_name="git-import",
    ...     git_repo_url=factory.getUniqueURL(),
    ... )
    >>> git_import_url = "/" + git_import.branch.unique_name + "/+code-import"
    >>> logout()
    >>> import_webservice = webservice_for_person(
    ...     person, permission=OAuthPermission.WRITE_PUBLIC
    ... )
    >>> response = import_webservice.named_post(
    ...     git_import_url, "requestImport"
    ... )
    >>> print(response.status)
    200
    >>> print(response.jsonBody())
    None
