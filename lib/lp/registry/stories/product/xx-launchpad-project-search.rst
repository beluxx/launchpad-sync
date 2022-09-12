Searching for projects, project-groups and distributions
========================================================

Launchpad provides a way for people to search across products, projects and
distributions.

    >>> anon_browser.open("http://launchpad.test/projects")
    >>> project_search = anon_browser.getForm(id="project-search")
    >>> project_search.getControl(name="text").value = "whizzbar"
    >>> anon_browser.getControl("Search", index=0).click()
    >>> anon_browser.url
    'http://launchpad.test/projects/+index?text=whizzbar'

The user is informed when no matches are found.

    >>> print(
    ...     extract_text(find_tag_by_id(anon_browser.contents, "no-matches"))
    ... )
    No projects matching ...whizzbar... were found...

Launchpad shows up to config.launchpad.default_batch_size results; if there
are more results than that, the user sees an informational message that asks
the user to refine their search.

    >>> from lp.services.config import config
    >>> config.launchpad.default_batch_size
    5

    >>> anon_browser.open("http://launchpad.test/projects")
    >>> project_search = anon_browser.getForm(id="project-search")
    >>> project_search.getControl(name="text").value = "ubuntu"
    >>> project_search.getControl("Search").click()
    >>> anon_browser.url
    'http://launchpad.test/projects/+index?text=ubuntu'

    >>> content = find_main_content(anon_browser.contents)
    >>> print(extract_text(find_tag_by_id(content, "search-summary")))
    6 projects found matching ...ubuntu..., showing the most relevant 5

    >>> print(extract_text(find_tag_by_id(content, "too-many-matches")))
    More than 5 projects were found.
    You can do another search with more relevant search terms.

A lower search form is shown when there are matches.

    >>> print(find_tag_by_id(content, "project-search-lower").name)
    form

The search results contain projects, project-groups, and distributions.

    >>> def print_search_results(abrowser):
    ...     search_results = find_tag_by_id(
    ...         abrowser.contents, "search-results"
    ...     )
    ...     for tr in search_results.tbody("tr"):
    ...         print(" ".join(tr.td.a["class"]), extract_text(tr.td.a))
    ...
    >>> print_search_results(anon_browser)
    sprite distribution Ubuntu
    sprite distribution ubuntutest
    sprite product Evolution
    sprite product Tomcat
    sprite product Gnome Applets

The user can follow one of these links to go straight to the project,
project-group, or distribution.

    >>> anon_browser.getLink("Tomcat").click()
    >>> anon_browser.url
    'http://launchpad.test/tomcat'

If the user searches without any search terms, the page asks them to enter
some terms and do another search.

    >>> anon_browser.open("http://launchpad.test/projects")
    >>> project_search = anon_browser.getForm(id="project-search")
    >>> project_search.getControl(name="text").value
    ''
    >>> project_search.getControl("Search").click()
    >>> empty_search = find_tag_by_id(
    ...     anon_browser.contents, "empty-search-string"
    ... )
    >>> print(empty_search.decode_contents())
    <BLANKLINE>
    ...Enter one or more words related to the project you want to find.
    <BLANKLINE>

Searching only for project groups
---------------------------------

A similar page is available for only searching project groups.

    >>> anon_browser.open("http://launchpad.test/projectgroups")
    >>> search = anon_browser.getForm(id="projectgroup-search")
    >>> search.getControl(name="text").value = "gnome"
    >>> search.getControl("Search").click()
    >>> anon_browser.url
    'http://launchpad.test/projectgroups/+index?text=gnome'

    >>> tags = find_tags_by_class(
    ...     anon_browser.contents, "informational message"
    ... )
    >>> for tag in tags:
    ...     print(tag.decode_contents())
    ...

The search results contains only project-groups.

    >>> print(
    ...     extract_text(
    ...         find_main_content(anon_browser.contents).find_all("p")[1]
    ...     )
    ... )
    1 project group found matching ...gnome...
