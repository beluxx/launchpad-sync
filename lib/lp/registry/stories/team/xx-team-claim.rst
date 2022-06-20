Claiming an automatically created team
======================================

Sometimes (mostly when processing package uploads) Launchpad will create new
people when in fact it should have created teams.  When that happens, it
should be possible for a user to claim these profiles and turn them into
teams.

On the home page of any automatically created person, there is a link which
allow the logged in user to claim that profile, but if we have any
indication the profile may actually represent a team, we instead provide a
link to turn it into a team.

For instance, we have an auto-created profile for Matsubara, which
definitely doesn't seem to be a team.

    >>> browser.open('http://launchpad.test/~matsubara')
    >>> browser.getLink(url='+requestmerge')
    <Link text='Are you Diogo Matsubara?'...

If a profile does look like a team and there is a logged in user, the link
is different...

    >>> from lp.registry.model.person import PersonSet
    >>> doc_team = PersonSet().getByName('doc')
    >>> for email in doc_team.guessedemails:
    ...     print(email.email)
    doc@lists.ubuntu.com

While logged-in users get a link to claim that profile and turn it into a
team. This works even if the profile's email addresses would normally be
hidden.

    >>> doc_team.hide_email_addresses = True
    >>> user_browser.open('http://launchpad.test/~doc')
    >>> user_browser.getLink('Is this a team you run?').click()
    >>> user_browser.title
    'Claim team...

Now we enter the doc team's email address to continue the process of
turning that profile into a team.

    >>> user_browser.getControl(
    ...     'Email address').value = 'doc@lists.ubuntu.com'
    >>> user_browser.getControl('Continue').click()
    >>> user_browser.title
    'Ubuntu Doc Team does not use Launchpad'

    >>> print_feedback_messages(user_browser.contents)
    A confirmation message has been sent to
    'doc@lists.ubuntu.com'. Follow the instructions in that
    message to finish claiming this team. (If the above address is from
    a mailing list, it may be necessary to talk with one of its admins
    to accept the message from Launchpad so that you can finish the
    process.)

That will send an email to the address given, with a link to finish the
claiming process.

    >>> from lp.services.mail import stub
    >>> from lp.services.verification.tests.logintoken import (
    ...     get_token_url_from_email)
    >>> from_addr, to_addr, msg = stub.test_emails.pop()
    >>> to_addr
    ['doc@lists.ubuntu.com']
    >>> token_url = get_token_url_from_email(msg)
    >>> token_url
    'http://launchpad.test/token/...'

    >>> user_browser.open(token_url)
    >>> user_browser.title
    'Claim Launchpad team'

Here the user sees a form where they can enter a few more details about the
team and finish the claiming process, making the person who started the
claim process the team's owner.

    # The 'Team Owner' widget is rendered as read-only in this page, so we
    # can't use browser.getControl() to see its value.
    >>> user_browser.getControl('Team Owner')
    Traceback (most recent call last):
    ...
    LookupError:...
    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> soup = BeautifulSoup(user_browser.contents)
    >>> print(extract_text(
    ...     soup.find(attrs={'for': 'field.teamowner'}).find_previous('tr')))
    Team Owner: No Privileges Person...

    >>> user_browser.getControl('Display Name').value = 'Ubuntu Doc Team'
    >>> user_browser.getControl('Description').value = 'The doc team'
    >>> user_browser.getControl('Continue').click()

Once the conversion is finished the user is redirected to the team's home
page.

    >>> user_browser.title
    'Ubuntu Doc Team in Launchpad'
    >>> print_feedback_messages(user_browser.contents)
    Team claimed successfully

    >>> print(extract_text(
    ...     find_tag_by_id(user_browser.contents, 'team-owner')))
    Owner:
    No Privileges Person
