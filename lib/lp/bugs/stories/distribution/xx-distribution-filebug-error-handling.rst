When filing a distribution bug, an error is raised if you enter a
package name that doesn't exist in the distribution.

    >>> browser = setupBrowser(auth="Basic foo.bar@canonical.com:test")
    >>> browser.open("http://launchpad.test/ubuntu/+filebug")

    >>> browser.getControl(name="field.title", index=0).value = "test"
    >>> browser.getControl('Continue').click()

    >>> browser.getControl(name="field.comment").value = "test"
    >>> browser.getControl(name="packagename_option").value = ["choose"]
    >>> browser.getControl(name="field.packagename").value = "jellybelly"

    >>> browser.getControl("Submit Bug Report").click()

    >>> '&quot;jellybelly&quot; does not exist in Ubuntu' in browser.contents
    True

An error is also raised if you choose the radio button to enter a
package name, but don't specify a package.

    >>> browser.open("http://launchpad.test/ubuntu/+filebug")

    >>> browser.getControl(name="field.title", index=0).value = "test"
    >>> browser.getControl('Continue').click()

    >>> browser.getControl(name="field.comment").value = "test"
    >>> browser.getControl(name="packagename_option").value = ["choose"]

    >>> browser.getControl("Submit Bug Report").click()

    >>> 'Please enter a package name' in browser.contents
    True
