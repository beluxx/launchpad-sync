LaunchpadForm views
===================

CustomWidgetFactory accepts arbitrary attribute assignments for the
widget.  One that launchpadform utilizes is 'widget_class'.  The
widget rendering is wrapped with a <div> using the widget_class, which
can be used for subordinate field indentation, for example.

    >>> from zope.formlib.widget import CustomWidgetFactory
    >>> from zope.formlib.widgets import TextWidget
    >>> from zope.interface import Interface
    >>> from zope.schema import TextLine
    >>> from lp.services.config import config
    >>> from zope.browserpage import ViewPageTemplateFile
    >>> from lp.app.browser.launchpadform import LaunchpadFormView
    >>> from lp.testing.pages import find_tags_by_class
    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> class ITestSchema(Interface):
    ...     displayname = TextLine(title=u"Title")
    ...     nickname = TextLine(title=u"Nickname")

    >>> class TestView(LaunchpadFormView):
    ...     page_title = 'Test'
    ...     template = ViewPageTemplateFile(
    ...         config.root + '/lib/lp/app/templates/generic-edit.pt')
    ...     schema = ITestSchema
    ...     custom_widget_nickname = CustomWidgetFactory(
    ...         TextWidget, widget_class='field subordinate')

    >>> login('foo.bar@canonical.com')
    >>> person = factory.makePerson()
    >>> request = LaunchpadTestRequest()
    >>> request.setPrincipal(person)
    >>> view = TestView(person, request)
    >>> view.initialize()
    >>> for tag in find_tags_by_class(view.render(), 'subordinate'):
    ...     print(tag)
    <div class="field subordinate">
    <label for="field.nickname">Nickname:</label>
    <div>
    <input class="textType" id="field.nickname" name="field.nickname" .../>
    </div>
    </div>
