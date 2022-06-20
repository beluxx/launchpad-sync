Email Notifications for Specifications
======================================

When a specification is edited, an email notification is sent out to
all the related people. We send out notifications only on certain
changed, this will change in the future though.

Changing the status:

    >>> from zope.component import getMultiAdapter
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.interfaces.product import IProductSet

    >>> login('foo.bar@canonical.com')
    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> svg_support = firefox.getSpecification('svg-support')
    >>> form = {
    ...     'field.actions.change': 'Change',
    ...     'field.definition_status': 'Drafting',
    ...     'field.implementation_status':
    ...         svg_support.implementation_status.title,
    ...     }
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+status')
    >>> edit_view.initialize()

    >>> import transaction
    >>> from lp.services.mail import stub
    >>> transaction.commit()
    >>> len(stub.test_emails)
    7

The notification was sent to the registrant, Foo Bar, the assignee, Carlos,
the approver, Cprov, and the drafter, Robert.

    >>> related_people = [
    ...     svg_support.owner, svg_support.assignee, svg_support.drafter,
    ...     svg_support.approver]
    >>> related_people += [
    ...     subscription.person for subscription in svg_support.subscriptions]
    >>> related_people_addresses = [
    ...     [person.preferredemail.email] for person in set(related_people)]
    >>> for addr in sorted(related_people_addresses): print(pretty(addr))
    ['andrew.bennetts@ubuntulinux.com']
    ['carlos@canonical.com']
    ['celso.providelo@canonical.com']
    ['daf@canonical.com']
    ['foo.bar@canonical.com']
    ['robertc@robertcollins.net']
    ['stuart.bishop@canonical.com']

    >>> sent_addresses = sorted(
    ...     [to_addrs for from_addr, to_addrs, message in stub.test_emails])
    >>> sent_addresses == sorted(related_people_addresses)
    True

The approver and all subscribers also get notified, but since the
approver was cprov, and the only subscriber was Foo Bar, no additional
notifications were sent.

    >>> svg_support.approver is None
    False

    >>> for subscription in svg_support.subscriptions:
    ...     print(subscription.person.preferredemail.email)
    andrew.bennetts@ubuntulinux.com
    daf@canonical.com
    foo.bar@canonical.com
    robertc@robertcollins.net
    stuart.bishop@canonical.com

Let's set a different approver and add a subscriber.

    >>> from lp.registry.interfaces.person import IPersonSet

    >>> stub.test_emails = []
    >>> mark = getUtility(IPersonSet).getByEmail('mark@example.com')
    >>> sample_person = getUtility(IPersonSet).getByEmail(
    ...     'test@canonical.com')
    >>> svg_support.approver = mark
    >>> svg_support.subscribe(sample_person, sample_person, False)
    <...>
    >>> transaction.commit()
    >>> for fromaddr, toaddrs, message in stub.test_emails:
    ...     print(toaddrs)
    ['test@canonical.com']

Now if we edit the status, a notification will be sent to all the
previous people, and to the approver and the added subscriber:

    >>> stub.test_emails = []
    >>> form = {
    ...     'field.actions.change': 'Change',
    ...     'field.definition_status': 'Pending Approval',
    ...     'field.implementation_status':
    ...         svg_support.implementation_status.title,
    ...     'field.needs_discussion': '1'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+status')
    >>> edit_view.initialize()
    >>> transaction.commit()

The added subscriber will also receive a notification that they
are now subscribed.

    >>> x = sorted(toaddrs for fromaddr, toaddrs, message in stub.test_emails)
    >>> for addr in x: print(addr)
    ['andrew.bennetts@ubuntulinux.com']
    ['carlos@canonical.com']
    ['daf@canonical.com']
    ['foo.bar@canonical.com']
    ['mark@example.com']
    ['robertc@robertcollins.net']
    ['stuart.bishop@canonical.com']
    ['test@canonical.com']

Now let's take a look at what the notification looks like:

    >>> import email
    >>> notifications = [
    ...     email.message_from_bytes(raw_message)
    ...     for from_addr, to_addrs, raw_message in sorted(stub.test_emails)]
    >>> status_notification = notifications[0]
    >>> status_notification['To']
    'andrew.bennetts@ubuntulinux.com'
    >>> status_notification['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> status_notification['Subject']
    '[Blueprint svg-support] Support Native SVG Objects'
    >>> body = status_notification.get_payload(decode=True)
    >>> print(body.decode('UTF-8'))
    Blueprint changed by Foo Bar:
    <BLANKLINE>
        Definition Status: Drafting => Pending Approval
    <BLANKLINE>
    --
    Support Native SVG Objects
    http://blueprints.launchpad.test/firefox/+spec/svg-support
    <BLANKLINE>

Whiteboard change:

    >>> stub.test_emails = []
    >>> new_whiteboard = (
    ...     "This is a long line, which will be wrapped in the email,"
    ...     " since it's longer than 72 characters.\n"
    ...     "\n"
    ...     "Another paragraph")
    >>> form = {
    ...     'field.actions.change': 'Change',
    ...     'field.definition_status': 'Pending Approval',
    ...     'field.implementation_status':
    ...         svg_support.implementation_status.title,
    ...     'field.whiteboard': new_whiteboard}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+status')
    >>> edit_view.initialize()
    >>> transaction.commit()

    >>> notifications = [
    ...     email.message_from_bytes(raw_message)
    ...     for from_addr, to_addrs, raw_message in sorted(stub.test_emails)]
    >>> status_notification = notifications[0]
    >>> status_notification['To']
    'andrew.bennetts@ubuntulinux.com'
    >>> status_notification['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> status_notification['Subject']
    '[Blueprint svg-support] Support Native SVG Objects'
    >>> body = status_notification.get_payload(decode=True)
    >>> print(body.decode('UTF-8'))
    Blueprint changed by Foo Bar:
    <BLANKLINE>
    Whiteboard set to:
    This is a long line, which will be wrapped in the email, since it's
    longer than 72 characters.
    <BLANKLINE>
    Another paragraph
    <BLANKLINE>
    --
    Support Native SVG Objects
    http://blueprints.launchpad.test/firefox/+spec/svg-support
    <BLANKLINE>


Definition status and whiteboard change:

    >>> stub.test_emails = []
    >>> form = {
    ...     'field.actions.change': 'Change',
    ...     'field.definition_status': 'Approved',
    ...     'field.implementation_status':
    ...         svg_support.implementation_status.title,
    ...     'field.whiteboard': 'Excellent work.'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+status')
    >>> edit_view.initialize()
    >>> transaction.commit()

    >>> notifications = [
    ...     email.message_from_bytes(raw_message)
    ...     for from_addr, to_addrs, raw_message in sorted(stub.test_emails)]
    >>> status_notification = notifications[0]
    >>> status_notification['To']
    'andrew.bennetts@ubuntulinux.com'
    >>> status_notification['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> status_notification['Subject']
    '[Blueprint svg-support] Support Native SVG Objects'
    >>> body = status_notification.get_payload(decode=True)
    >>> print(body.decode('UTF-8'))
    Blueprint changed by Foo Bar:
    <BLANKLINE>
        Definition Status: Pending Approval => Approved
    <BLANKLINE>
    Whiteboard changed:
    - This is a long line, which will be wrapped in the email, since it's
    - longer than 72 characters.
    -
    - Another paragraph
    + Excellent work.
    <BLANKLINE>
    --
    Support Native SVG Objects
    http://blueprints.launchpad.test/firefox/+spec/svg-support
    <BLANKLINE>

Change priority:

    >>> stub.test_emails = []
    >>> form = {
    ...     'field.actions.change': 'Change', 'field.priority': 'Essential',
    ...     'field.direction_approved': 'on',
    ...     'field.whiteboard': svg_support.whiteboard}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+priority')
    >>> edit_view.initialize()
    >>> transaction.commit()

    >>> notifications = [
    ...     email.message_from_bytes(raw_message)
    ...     for from_addr, to_addrs, raw_message in sorted(stub.test_emails)]
    >>> status_notification = notifications[0]
    >>> status_notification['To']
    'andrew.bennetts@ubuntulinux.com'
    >>> status_notification['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> status_notification['Subject']
    '[Blueprint svg-support] Support Native SVG Objects'
    >>> body = status_notification.get_payload(decode=True)
    >>> print(body.decode('UTF-8'))
    Blueprint changed by Foo Bar:
    <BLANKLINE>
        Priority: High => Essential
    <BLANKLINE>
    --
    Support Native SVG Objects
    http://blueprints.launchpad.test/firefox/+spec/svg-support
    <BLANKLINE>

Change approver, assignee and drafter:

    >>> svg_support.assignee = None

    >>> stub.test_emails = []
    >>> form = {
    ...     'field.actions.change': 'Change', 'field.assignee': 'mark',
    ...     'field.approver': '', 'field.drafter': 'foo.bar@canonical.com'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter((svg_support, request), name='+people')
    >>> edit_view.initialize()
    >>> transaction.commit()

    >>> notifications = [
    ...     email.message_from_bytes(raw_message)
    ...     for from_addr, to_addrs, raw_message in sorted(stub.test_emails)]
    >>> status_notification = notifications[0]
    >>> status_notification['To']
    'andrew.bennetts@ubuntulinux.com'
    >>> status_notification['From']
    'Foo Bar <foo.bar@canonical.com>'
    >>> status_notification['Subject']
    '[Blueprint svg-support] Support Native SVG Objects'
    >>> body = status_notification.get_payload(decode=True)
    >>> print(body.decode('UTF-8'))
    Blueprint changed by Foo Bar:
    <BLANKLINE>
        Approver: Mark Shuttleworth => (none)
        Assignee: (none) => Mark Shuttleworth
        Drafter: Robert Collins => Foo Bar
    <BLANKLINE>
    --
    Support Native SVG Objects
    http://blueprints.launchpad.test/firefox/+spec/svg-support
    <BLANKLINE>

If we do a change, which we don't yet support sending a notification
about, no notification is sent:

    >>> stub.test_emails = []
    >>> form = {
    ...     'FORM_SUBMIT': 'Continue', 'field.productseries': '1',
    ...     'field.whiteboard': 'Proposing for milestones...'}
    >>> request = LaunchpadTestRequest(form=form, method='POST')
    >>> edit_view = getMultiAdapter(
    ...     (svg_support, request), name='+setproductseries')
    >>> edit_view.initialize()
    >>> transaction.commit()
    >>> len(stub.test_emails)
    0
