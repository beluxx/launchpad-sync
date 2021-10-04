# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Email notifications related to code imports."""

import textwrap

from zope.authentication.interfaces import IUnauthenticatedPrincipal
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.code.enums import (
    BranchSubscriptionNotificationLevel,
    CodeImportEventDataType,
    CodeImportEventType,
    CodeImportReviewStatus,
    RevisionControlSystems,
    )
from lp.registry.interfaces.person import IPerson
from lp.services.config import config
from lp.services.mail.helpers import (
    get_contact_email_addresses,
    get_email_template,
    )
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )
from lp.services.webapp import canonical_url


def new_import(code_import, event):
    """Email the vcs-imports team about a new code import."""
    if (event.user is None
        or IUnauthenticatedPrincipal.providedBy(event.user)):
        # If there is no logged in user, then we are most likely in a
        # test.
        return
    user = IPerson(event.user)
    subject = 'New code import: %s' % code_import.target.unique_name
    if code_import.rcs_type == RevisionControlSystems.CVS:
        location = '%s, %s' % (code_import.cvs_root, code_import.cvs_module)
    else:
        location = code_import.url
    rcs_type_map = {
        RevisionControlSystems.CVS: 'CVS',
        RevisionControlSystems.BZR_SVN: 'subversion',
        RevisionControlSystems.GIT: 'git',
        RevisionControlSystems.BZR: 'bazaar',
        }
    body = get_email_template('new-code-import.txt', app='code') % {
        'person': code_import.registrant.displayname,
        'target': canonical_url(code_import.target),
        'rcs_type': rcs_type_map[code_import.rcs_type],
        'location': location,
        }

    from_address = format_address(
        user.displayname, user.preferredemail.email)

    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    headers = {'X-Launchpad-Branch': code_import.target.unique_name,
               'X-Launchpad-Message-Rationale':
                   'Operator @%s' % vcs_imports.name,
               'X-Launchpad-Message-For': vcs_imports.name,
               'X-Launchpad-Notification-Type': 'code-import',
               }
    for address in get_contact_email_addresses(vcs_imports):
        simple_sendmail(from_address, address, subject, body, headers)


def make_email_body_for_code_import_update(
        code_import, event, new_whiteboard):
    """Construct the body of an email describing a MODIFY `CodeImportEvent`.

    :param code_import: Blah.
    :param event: The MODIFY `CodeImportEvent`.
    :param new_whiteboard: Blah.
    """
    if event is not None:
        assert event.event_type == CodeImportEventType.MODIFY, (
            "event type must be MODIFY, not %s" % event.event_type.name)
        event_data = dict(event.items())
    else:
        event_data = {}

    body = []

    if CodeImportEventDataType.OLD_REVIEW_STATUS in event_data:
        if code_import.review_status == CodeImportReviewStatus.INVALID:
            body.append("The import has been marked as invalid.")
        elif code_import.review_status == CodeImportReviewStatus.REVIEWED:
            body.append(
                "The import has been approved and an import will start "
                "shortly.")
        elif code_import.review_status == CodeImportReviewStatus.SUSPENDED:
            body.append("The import has been suspended.")
        elif code_import.review_status == CodeImportReviewStatus.FAILING:
            body.append("The import has been marked as failing.")
        else:
            raise AssertionError('Unexpected review status for code import.')

    if code_import.rcs_type == RevisionControlSystems.CVS:
        old_details = new_details = "%s from %s" % (
            code_import.cvs_module, code_import.cvs_root)
        if (CodeImportEventDataType.OLD_CVS_ROOT in event_data or
                CodeImportEventDataType.OLD_CVS_MODULE in event_data):
            old_root = event_data.get(
                CodeImportEventDataType.OLD_CVS_ROOT,
                code_import.cvs_root)
            old_module = event_data.get(
                CodeImportEventDataType.OLD_CVS_MODULE,
                code_import.cvs_module)
            old_details = "%s from %s" % (old_module, old_root)
    elif code_import.rcs_type in (RevisionControlSystems.BZR_SVN,
                                  RevisionControlSystems.GIT,
                                  RevisionControlSystems.BZR):
        old_details = new_details = code_import.url
        if CodeImportEventDataType.OLD_URL in event_data:
            old_details = event_data[CodeImportEventDataType.OLD_URL]
    else:
        raise AssertionError(
            'Unexpected rcs_type %r for code import.' % code_import.rcs_type)

    if new_details != old_details:
        body.append(
            textwrap.fill(
                "%s is now being imported from:" %
                code_import.target.unique_name) +
            "\n    " + new_details +
            "\ninstead of:\n    " + old_details)

    if new_whiteboard is not None:
        if new_whiteboard != '':
            body.append("The branch whiteboard was changed to:")
            body.append(textwrap.fill(new_whiteboard))
        else:
            body.append("The branch whiteboard was deleted.")

    if new_details == old_details:
        body.append("This code import is from:\n    " + new_details)

    return '\n\n'.join(body)


def code_import_updated(code_import, event, new_whiteboard, person):
    """Email the target subscribers, and the vcs-imports team with new status.
    """
    target = code_import.target
    recipients = target.getNotificationRecipients()
    # Add in the vcs-imports user.
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    herder_rationale = 'Operator @%s' % vcs_imports.name
    recipients.add(vcs_imports, None, herder_rationale)

    headers = {
        'X-Launchpad-Notification-Type': 'code-import-updated',
        'X-Launchpad-Branch': target.unique_name,
        }

    subject = 'Code import %s status: %s' % (
        code_import.target.unique_name, code_import.review_status.title)

    email_template = get_email_template(
        'code-import-status-updated.txt', app='code')
    template_params = {
        'body': make_email_body_for_code_import_update(
            code_import, event, new_whiteboard),
        'target': canonical_url(code_import.target)}

    if person:
        from_address = format_address(
            person.displayname, person.preferredemail.email)
    else:
        from_address = config.canonical.noreply_from_address

    interested_levels = (
        BranchSubscriptionNotificationLevel.ATTRIBUTEONLY,
        BranchSubscriptionNotificationLevel.FULL)

    for email_address in recipients.getEmails():
        subscription, rationale = recipients.getReason(email_address)

        if subscription is None:
            if rationale == herder_rationale:
                template_params['rationale'] = (
                    'You are getting this email because you are a member of'
                    ' the vcs-imports team.')
            else:
                template_params['rationale'] = rationale
            template_params['unsubscribe'] = ''
            for_person = vcs_imports
        else:
            if subscription.notification_level in interested_levels:
                template_params['rationale'] = (
                    'You are receiving this email as you are subscribed '
                    'to the branch.')
                if not subscription.person.is_team:
                    # Give the users a link to unsubscribe.
                    template_params['unsubscribe'] = (
                        "\nTo unsubscribe from this branch go to "
                        "%s/+edit-subscription." % canonical_url(target))
                else:
                    template_params['unsubscribe'] = ''
                for_person = subscription.person
            else:
                # Don't send email to this subscriber.
                continue

        headers['X-Launchpad-Message-Rationale'] = rationale
        headers['X-Launchpad-Message-For'] = for_person.name
        body = email_template % template_params
        simple_sendmail(from_address, email_address, subject, body, headers)
