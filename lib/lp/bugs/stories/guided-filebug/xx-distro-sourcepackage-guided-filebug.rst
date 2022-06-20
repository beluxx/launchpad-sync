The guided filebug form for source packages is similar to the filebug
workflow for distributions. First, you start by checking if your bug
already exists. We given a summary that would match an existing
Thunderbird bug.

    >>> user_browser.open(
    ...     "http://launchpad.test/ubuntu/+source/mozilla-firefox/"
    ...     "+filebug")
    >>> user_browser.getControl(name="field.title", index=0).value = (
    ...     "Thunderbird crashes when opening large emails")
    >>> user_browser.getControl("Continue").click()

In this case, since we search only Ubuntu Firefox bugs, there are no
similar matching bugs.

    >>> similar_bugs_table = find_tag_by_id(
    ...     user_browser.contents, "similar-bugs")
    >>> similar_bugs_table is None
    True

    >>> print(find_main_content(user_browser.contents).decode_contents())
    <...
    No similar bug reports were found...

The filebug form looks similar to the normal distro form, but the
package name is prepopulated.

    >>> user_browser.getControl(name="packagename_option").value
    ['choose']
    >>> user_browser.getControl(name="field.packagename").value
    'mozilla-firefox'

So we need fill in only a title and description.

    >>> user_browser.getControl(name="field.title").value = "a test bug"
    >>> user_browser.getControl(name="field.comment").value = "test"
    >>> user_browser.getControl("Submit Bug Report").click()

    >>> print(user_browser.url)
    http://bugs.launchpad.test/ubuntu/+source/mozilla-firefox/+bug/...
