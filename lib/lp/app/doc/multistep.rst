Multiple step views
===================

Some views need multiple steps, kind of like a wizard where individual pages
collect information along the way.  The MultiStepView abstracts this
functionality for use across Launchpad.

To use multiple steps, you need one subclass of MultiStepView to start your
wizard, and one or more subclasses of StepView for each step of your wizard.

    >>> from lp.app.browser.multistep import (
    ...     MultiStepView, StepView)

The controlling view must define a property `first_step` which is the view
class of the first step in your wizard.  Each step must define a `next_step`
property which is the view class of the next step in the wizard.  When
`next_step` is None, the wizard is done.

    >>> from zope.interface import Interface
    >>> class IStep(Interface):
    ...     """A step."""

StepView subclasses must override next_step and step_name, and provide a
main_action() method to process the form.

    >>> visited_steps = None

    >>> class StepThree(StepView):
    ...     schema = IStep
    ...     step_name = 'three'
    ...     def main_action(self, data):
    ...         assert data['__visited_steps__'] == visited_steps
    ...         print(self.step_name)

    >>> class StepTwo(StepView):
    ...     schema = IStep
    ...     step_name = 'two'
    ...     def main_action(self, data):
    ...         assert data['__visited_steps__'] == visited_steps
    ...         print(self.step_name)
    ...         self.next_step = StepThree

    >>> class StepOne(StepView):
    ...     schema = IStep
    ...     step_name = 'one'
    ...     def main_action(self, data):
    ...         assert data['__visited_steps__'] == visited_steps
    ...         print(self.step_name)
    ...         self.next_step = StepTwo

    >>> class CounterView(MultiStepView):
    ...     total_steps = 3
    ...     first_step = StepOne

    >>> from lp.services.webapp.servers import LaunchpadTestRequest

    >>> view = CounterView(None, LaunchpadTestRequest())
    >>> view.initialize()
    >>> view.view.step_number
    1

    >>> view.view.is_step['1']
    True
    >>> view.view.is_step['2']
    False
    >>> view.view.is_step['3']
    False

The view gets initialized three times to simulate the three clicks on the
'Continue' button of each subsequent page.

    >>> form = {'field.actions.continue': 'Continue'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')

    >>> visited_steps = 'one'
    >>> view = CounterView(None, request)
    >>> view.initialize()
    one

    >>> view.view.step_number
    2

    >>> view.view.is_step['1']
    False
    >>> view.view.is_step['2']
    True
    >>> view.view.is_step['3']
    False

    >>> visited_steps = 'one|two'
    >>> view = CounterView(None, request)
    >>> view.initialize()
    one
    two

    >>> visited_steps = 'one|two|three'
    >>> view = CounterView(None, request)
    >>> view.initialize()
    one
    two
    three


Validation
----------

Step views can validate their data, but they must not do so by overriding
validate().  Instead, they must do this by overriding the validateStep()
method.

    >>> class StepSix(StepView):
    ...     schema = IStep
    ...     step_name = 'six'
    ...     def main_action(self, data):
    ...         pass
    ...     def validateStep(self, data):
    ...         print(self.step_name)

    >>> class StepFive(StepView):
    ...     schema = IStep
    ...     step_name = 'five'
    ...     def main_action(self, data):
    ...         self.next_step = StepSix
    ...     def validateStep(self, data):
    ...         print(self.step_name)

    >>> class StepFour(StepView):
    ...     schema = IStep
    ...     step_name = 'four'
    ...     def main_action(self, data):
    ...         self.next_step = StepFive
    ...     def validateStep(self, data):
    ...         print(self.step_name)

    >>> class CounterView(MultiStepView):
    ...     first_step = StepFour

    >>> form = {'field.actions.continue': 'Continue'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> view = CounterView(None, request)

    >>> view.initialize()
    four
    >>> view.initialize()
    four
    five
    >>> view.initialize()
    four
    five
    six
