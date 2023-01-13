Testing LaunchpadFormView Instances
===================================

The LaunchpadFormHarness class is designed to help write tests for
view classes based on LaunchpadFormView.  It provides a convenient way
to check the form's behaviour with different inputs.

To demonstrate its use we'll create a sample schema and view class:

    >>> from zope.interface import Interface, implementer
    >>> from zope.schema import Int, TextLine
    >>> from lp.app.browser.launchpadform import LaunchpadFormView, action

    >>> class IHarnessTest(Interface):
    ...     string = TextLine(title="String")
    ...     number = Int(title="Number")
    ...

    >>> @implementer(IHarnessTest)
    ... class HarnessTest:
    ...     string = None
    ...     number = 0
    ...

    >>> class HarnessTestView(LaunchpadFormView):
    ...     schema = IHarnessTest
    ...     next_url = "https://launchpad.net/"
    ...
    ...     def validate(self, data):
    ...         if len(data.get("string", "")) == data.get("number"):
    ...             self.addError("number must not be equal to string length")
    ...         if data.get("number") == 7:
    ...             self.setFieldError("number", "number can not be 7")
    ...
    ...     @action("Submit")
    ...     def submit_action(self, action, data):
    ...         self.context.string = data["string"]
    ...         self.context.number = data["number"]
    ...

We can then create a harness to drive the view:

    >>> from lp.testing.deprecated import LaunchpadFormHarness
    >>> context = HarnessTest()
    >>> harness = LaunchpadFormHarness(context, HarnessTestView)

As we haven't submitted the form, there are no errors:

    >>> harness.hasErrors()
    False

If we submit the form with some invalid data, we will have some errors
though:

    >>> harness.submit(
    ...     "submit", {"field.string": "abcdef", "field.number": "6"}
    ... )
    >>> harness.hasErrors()
    True

We can then get a list of the whole-form errors:

    >>> for message in harness.getFormErrors():
    ...     print(message)
    ...
    number must not be equal to string length


We can also check for per-widget errors:

    >>> harness.submit(
    ...     "submit",
    ...     {"field.string": "abcdef", "field.number": "not a number"},
    ... )
    >>> harness.hasErrors()
    True
    >>> print(harness.getFieldError("string"))
    <BLANKLINE>
    >>> print(harness.getFieldError("number"))
    Invalid integer data


The getFieldError() method will also return custom error messages set
by setFieldError():

    >>> harness.submit(
    ...     "submit", {"field.string": "abcdef", "field.number": "7"}
    ... )
    >>> harness.hasErrors()
    True
    >>> print(harness.getFieldError("number"))
    number can not be 7


We can check to see if the view tried to redirect us.  When there are
input validation problems, the view will not normally redirect you:

    >>> harness.wasRedirected()
    False

But if we submit correct data to the form and get redirected, we can
see where we were redirected to:

    >>> harness.submit(
    ...     "submit", {"field.string": "abcdef", "field.number": "42"}
    ... )
    >>> harness.wasRedirected()
    True
    >>> harness.redirectionTarget()
    'https://launchpad.net/'

We can also see that the context object was updated by this form
submission:

    >>> print(context.string)
    abcdef
    >>> context.number
    42

By default LaunchpadFormHarness uses LaunchpadTestRequest as its request
class, but it's possible to change that by passing a request_class argument to
it.

    >>> harness.request
    <...LaunchpadTestRequest...

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> class FormHarnessTestRequest(LaunchpadTestRequest):
    ...     pass
    ...
    >>> harness = LaunchpadFormHarness(
    ...     context, HarnessTestView, request_class=FormHarnessTestRequest
    ... )
    >>> harness.request
    <...FormHarnessTestRequest...
