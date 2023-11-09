# Copyright 2009-2020 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    "BaseTokenView",
    "BugTrackerHandshakeView",
    "ClaimTeamView",
    "LoginTokenSetNavigation",
    "LoginTokenView",
    "MergePeopleView",
    "ValidateEmailView",
    "ValidateTeamEmailView",
    "ValidateGPGKeyView",
]

from urllib.parse import urlencode, urljoin

from zope.component import getUtility
from zope.formlib.widget import CustomWidgetFactory
from zope.formlib.widgets import TextAreaWidget
from zope.interface import Interface, alsoProvides, directlyProvides
from zope.security.proxy import removeSecurityProxy

from lp import _
from lp.app.browser.launchpadform import (
    LaunchpadEditFormView,
    LaunchpadFormView,
    action,
)
from lp.app.widgets.itemswidgets import LaunchpadRadioWidget
from lp.registry.browser.team import HasRenewalPolicyMixin
from lp.registry.interfaces.person import (
    AlreadyConvertedException,
    IPersonSet,
    ITeam,
)
from lp.services.database.sqlbase import flush_database_updates
from lp.services.gpg.interfaces import (
    GPGKeyExpired,
    GPGKeyNotFoundError,
    GPGKeyRevoked,
    GPGVerificationError,
    IGPGHandler,
)
from lp.services.identity.interfaces.emailaddress import (
    EmailAddressStatus,
    IEmailAddressSet,
)
from lp.services.verification.interfaces.authtoken import LoginTokenType
from lp.services.verification.interfaces.logintoken import (
    IGPGKeyValidationForm,
    ILoginTokenSet,
)
from lp.services.webapp import GetitemNavigation, LaunchpadView, canonical_url
from lp.services.webapp.escaping import structured
from lp.services.webapp.interfaces import IAlwaysSubmittedWidget
from lp.services.webapp.vhosts import allvhosts


class LoginTokenSetNavigation(GetitemNavigation):
    usedfor = ILoginTokenSet


class LoginTokenView(LaunchpadView):
    """The default view for LoginToken.

    This view will check the token type and then redirect to the specific view
    for that type of token, if it's not yet a consumed token. We use this view
    so we don't have to add "+validateemail", "+newaccount", etc, on URLs we
    send by email.

    If this is a consumed token, then we simply display a page explaining that
    they got this token because they tried to do something that required email
    address confirmation, but that confirmation is already concluded.
    """

    PAGES = {
        LoginTokenType.ACCOUNTMERGE: "+accountmerge",
        LoginTokenType.VALIDATEEMAIL: "+validateemail",
        LoginTokenType.VALIDATETEAMEMAIL: "+validateteamemail",
        LoginTokenType.VALIDATEGPG: "+validategpg",
        LoginTokenType.VALIDATESIGNONLYGPG: "+validatesignonlygpg",
        LoginTokenType.TEAMCLAIM: "+claimteam",
        LoginTokenType.BUGTRACKER: "+bugtracker-handshake",
    }
    page_title = "You have already done this"
    label = "Confirmation already concluded"

    def render(self):
        if self.context.date_consumed is None:
            url = urljoin(
                str(self.request.URL), self.PAGES[self.context.tokentype]
            )
            self.request.response.redirect(url)
        else:
            return super().render()


class BaseTokenView:
    """A view class to be used by other {Login,Auth}Token views."""

    expected_token_types = ()
    successfullyProcessed = False
    # The next URL to use when the user clicks on the 'Cancel' button.
    _next_url_for_cancel = None
    _missing = object()
    # To be overridden in subclasses.
    default_next_url = _missing

    @property
    def next_url(self):
        """The next URL to redirect to on successful form submission.

        When the cancel action is used, self._next_url_for_cancel won't be
        None so we return that.  Otherwise we return self.default_next_url.
        """
        if self._next_url_for_cancel is not None:
            return self._next_url_for_cancel
        assert self.default_next_url is not self._missing, (
            "The implementation of %s should provide a value for "
            "default_next_url" % self.__class__.__name__
        )
        return self.default_next_url

    @property
    def page_title(self):
        """The page title."""
        return self.label

    def redirectIfInvalidOrConsumedToken(self):
        """If this is a consumed or invalid token redirect to the LoginToken
        default view and return True.

        An invalid token is a token used for a purpose it wasn't generated for
        (i.e. create a new account with a VALIDATEEMAIL token).
        """
        assert self.expected_token_types
        if (
            self.context.date_consumed is not None
            or self.context.tokentype not in self.expected_token_types
        ):
            self.request.response.redirect(canonical_url(self.context))
            return True
        else:
            return False

    def success(self, message):
        """Indicate to the user that the token was successfully processed.

        This involves adding a notification message, and redirecting the
        user to their Launchpad page.
        """
        self.successfullyProcessed = True
        self.request.response.addInfoNotification(message)

    def _cancel(self):
        """Consume the LoginToken and set self._next_url_for_cancel.

        _next_url_for_cancel is set to the home page of this LoginToken's
        requester.
        """
        self._next_url_for_cancel = canonical_url(self.context.requester)
        self.context.consume()


class ClaimTeamView(
    BaseTokenView, HasRenewalPolicyMixin, LaunchpadEditFormView
):
    schema = ITeam
    field_names = [
        "teamowner",
        "display_name",
        "description",
        "membership_policy",
        "defaultmembershipperiod",
        "renewal_policy",
        "defaultrenewalperiod",
    ]
    invariant_context = None
    label = "Claim Launchpad team"
    custom_widget_description = CustomWidgetFactory(
        TextAreaWidget, height=10, width=30
    )
    custom_widget_renewal_policy = CustomWidgetFactory(
        LaunchpadRadioWidget, orientation="vertical"
    )
    custom_widget_membership_policy = CustomWidgetFactory(
        LaunchpadRadioWidget, orientation="vertical"
    )

    expected_token_types = (LoginTokenType.TEAMCLAIM,)

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            self.claimed_profile = getUtility(IPersonSet).getByEmail(
                self.context.email, filter_status=False
            )
            # Let's pretend the claimed profile provides ITeam while we
            # render/process this page, so that it behaves like a team.
            directlyProvides(removeSecurityProxy(self.claimed_profile), ITeam)
        super().initialize()

    def setUpWidgets(self, context=None):
        self.form_fields["teamowner"].for_display = True
        super().setUpWidgets(context=self.claimed_profile)
        alsoProvides(self.widgets["teamowner"], IAlwaysSubmittedWidget)

    @property
    def initial_values(self):
        return {"teamowner": self.context.requester}

    @property
    def default_next_url(self):
        return canonical_url(self.claimed_profile)

    @action(_("Continue"), name="confirm")
    def confirm_action(self, action, data):
        try:
            self.claimed_profile.convertToTeam(
                team_owner=self.context.requester
            )
        except AlreadyConvertedException as e:
            self.request.response.addErrorNotification(e)
            self.context.consume()
            return
        # Although we converted the person to a team it seems that the
        # security proxy still thinks it's an IPerson and not an ITeam,
        # which means to edit it we need to be logged in as the person we
        # just converted into a team.  Of course, we can't do that, so we'll
        # have to remove its security proxy before we update it.
        self.updateContextFromData(
            data, context=removeSecurityProxy(self.claimed_profile)
        )
        self.request.response.addInfoNotification(
            _("Team claimed successfully")
        )

    @action(_("Cancel"), name="cancel", validator="validate_cancel")
    def cancel_action(self, action, data):
        self._cancel()


class ValidateGPGKeyView(BaseTokenView, LaunchpadFormView):
    schema = IGPGKeyValidationForm
    field_names = []
    expected_token_types = (
        LoginTokenType.VALIDATEGPG,
        LoginTokenType.VALIDATESIGNONLYGPG,
    )

    @property
    def label(self):
        if self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
            return "Confirm sign-only OpenPGP key"
        else:
            assert self.context.tokentype == LoginTokenType.VALIDATEGPG, (
                "unexpected token type: %r" % self.context.tokentype
            )
            return "Confirm OpenPGP key"

    @property
    def default_next_url(self):
        return canonical_url(self.context.requester)

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            if self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
                self.field_names = ["text_signature"]
        super().initialize()

    def validate(self, data):
        self.gpg_key = self._getGPGKey()
        if self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
            self._validateSignOnlyGPGKey(data)

    @action(_("Cancel"), name="cancel", validator="validate_cancel")
    def cancel_action(self, action, data):
        self._cancel()

    @action(_("Continue"), name="continue")
    def continue_action_gpg(self, action, data):
        assert self.gpg_key is not None
        can_encrypt = (
            self.context.tokentype != LoginTokenType.VALIDATESIGNONLYGPG
        )
        self._activateGPGKey(self.gpg_key, can_encrypt=can_encrypt)

    def _validateSignOnlyGPGKey(self, data):
        # Verify the signed content.
        signedcontent = data.get("text_signature")
        if signedcontent is None:
            return

        try:
            signature = getUtility(IGPGHandler).getVerifiedSignature(
                signedcontent.encode("ASCII")
            )
        except (GPGVerificationError, GPGKeyExpired, UnicodeEncodeError) as e:
            self.addError(
                _(
                    "Launchpad could not verify your signature: ${err}",
                    mapping=dict(err=str(e)),
                )
            )
            return

        if signature.fingerprint != self.context.fingerprint:
            self.addError(
                _(
                    "The key used to sign the content (${fprint}) is not the "
                    "key you were registering",
                    mapping=dict(fprint=signature.fingerprint),
                )
            )
            return

        # We compare the word-splitted content to avoid failures due
        # to whitespace differences.
        if (
            signature.plain_data.split()
            != self.context.validation_phrase.encode("UTF-8").split()
        ):
            self.addError(
                _(
                    "The signed content does not match the message found "
                    "in the email."
                )
            )
            return

    def _activateGPGKey(self, key, can_encrypt):
        person_url = canonical_url(self.context.requester)
        (
            lpkey,
            new,
        ) = self.context.activateGPGKey(key, can_encrypt)

        if new:
            self.request.response.addInfoNotification(
                _(
                    "The key ${lpkey} was successfully validated. ",
                    mapping=dict(lpkey=lpkey.displayname),
                )
            )
        else:
            msgid = _(
                "Key ${lpkey} successfully reactivated. "
                '<a href="${url}/+editpgpkeys">See more Information'
                "</a>",
                mapping=dict(lpkey=lpkey.displayname, url=person_url),
            )
            self.request.response.addInfoNotification(structured(msgid))

    def _getGPGKey(self):
        """Look up the OpenPGP key for this login token.

        If the key can not be retrieved from the keyserver, the key
        has been revoked or expired, None is returned and an error is set
        using self.addError.
        """
        gpghandler = getUtility(IGPGHandler)

        requester = self.context.requester
        fingerprint = self.context.fingerprint
        assert fingerprint is not None

        person_url = canonical_url(requester)
        try:
            key = gpghandler.retrieveActiveKey(fingerprint)
        except GPGKeyNotFoundError:
            message = _(
                "Launchpad could not import the OpenPGP key %{fingerprint}. "
                "Check that you published it correctly in the "
                "global key ring (using <kbd>gpg --send-keys "
                "KEY</kbd>) and that you entered the fingerprint "
                "correctly (as produced by <kbd>gpg --fingerprint "
                'YOU</kbd>). Try later or <a href="${url}/+editpgpkeys">'
                "cancel your request</a>.",
                mapping=dict(fingerprint=fingerprint, url=person_url),
            )
            self.addError(structured(message))
        except GPGKeyRevoked as e:
            # If key is globally revoked, skip the import and consume the
            # token.
            message = _(
                "The key ${key} cannot be validated because it has been "
                "publicly revoked. You will need to generate a new key "
                "(using <kbd>gpg --genkey</kbd>) and repeat the previous "
                'process to <a href="${url}/+editpgpkeys">find and '
                "import</a> the new key.",
                mapping=dict(key=e.key.fingerprint, url=person_url),
            )
            self.addError(structured(message))
        except GPGKeyExpired as e:
            message = _(
                "The key ${key} cannot be validated because it has expired. "
                "Change the expiry date (in a terminal, enter "
                "<kbd>gpg --edit-key <var>your@email.address</var></kbd> "
                "then enter <kbd>expire</kbd>), and try again.",
                mapping=dict(key=e.key.fingerprint),
            )
            self.addError(structured(message))
        else:
            return key


class ValidateEmailView(BaseTokenView, LaunchpadFormView):
    schema = Interface
    field_names = []
    expected_token_types = (LoginTokenType.VALIDATEEMAIL,)
    label = "Confirm email address"

    def initialize(self):
        if self.redirectIfInvalidOrConsumedToken():
            return
        super().initialize()

    def validate(self, data):
        """Make sure the email address this token refers to is not in use."""
        validated = (
            EmailAddressStatus.VALIDATED,
            EmailAddressStatus.PREFERRED,
        )
        requester = self.context.requester

        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(self.context.email)
        if email is not None:
            if requester is None or email.person != requester:
                dupe = email.person
                # Yes, hardcoding an autogenerated field name is an evil
                # hack, but if it fails nothing will happen.
                # -- Guilherme Salgado 2005-07-09
                url = allvhosts.configs["mainsite"].rooturl
                query = urlencode([("field.dupe_person", dupe.name)])
                url += "/people/+requestmerge?" + query
                self.addError(
                    structured(
                        "This email address is already registered for another "
                        "Launchpad user account. This account can be a "
                        "duplicate of yours, created automatically, and in "
                        "this case you should be able to "
                        '<a href="%(url)s">merge them</a> into a single one.',
                        url=url,
                    )
                )
            elif email.status in validated:
                self.addError(
                    _(
                        "This email address is already registered and "
                        "validated for your Launchpad account. There's no "
                        "need to validate it again."
                    )
                )
            else:
                # Yay, email is not used by anybody else and is not yet
                # validated.
                pass

    @property
    def default_next_url(self):
        if self.context.redirection_url is not None:
            return self.context.redirection_url
        else:
            assert (
                self.context.requester is not None
            ), "LoginTokens of this type must have a requester"
            return canonical_url(self.context.requester)

    @action(_("Cancel"), name="cancel", validator="validate_cancel")
    def cancel_action(self, action, data):
        self._cancel()

    @action(_("Continue"), name="continue")
    def continue_action(self, action, data):
        """Mark the new email address as VALIDATED in the database.

        If this is the first validated email of this person, it'll be marked
        as the preferred one.

        If the requester is a team, the team's contact address is removed (if
        any) and this becomes the team's contact address.
        """
        email = self._ensureEmail()
        self.markEmailAsValid(email)

        self.context.consume()
        self.request.response.addInfoNotification(
            _("Email address successfully confirmed.")
        )

    def _ensureEmail(self):
        """Make sure self.requester has this token's email address as one of
        its email addresses and return it.
        """
        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(self.context.email)
        if email is None:
            email = emailset.new(
                email=self.context.email, person=self.context.requester
            )
        return email

    def markEmailAsValid(self, email):
        """Mark the given email address as valid."""
        self.context.requester.validateAndEnsurePreferredEmail(email)


class ValidateTeamEmailView(ValidateEmailView):
    expected_token_types = (LoginTokenType.VALIDATETEAMEMAIL,)
    # The desired label is the same as ValidateEmailView.

    def markEmailAsValid(self, email):
        """See `ValidateEmailView`"""
        self.context.requester.setContactAddress(email)


class MergePeopleView(BaseTokenView, LaunchpadFormView):
    schema = Interface
    field_names = []
    expected_token_types = (LoginTokenType.ACCOUNTMERGE,)
    mergeCompleted = False
    label = "Merge Launchpad accounts"

    @property
    def default_next_url(self):
        return canonical_url(self.context.requester)

    def initialize(self):
        self.redirectIfInvalidOrConsumedToken()
        self.dupe = getUtility(IPersonSet).getByEmail(
            self.context.email, filter_status=False
        )
        super().initialize()

    @action(_("Cancel"), name="cancel", validator="validate_cancel")
    def cancel_action(self, action, data):
        self._cancel()

    @action(_("Confirm"), name="confirm")
    def confirm_action(self, action, data):
        """Perform the merge."""
        # Merge requests must have a valid user account (one with a preferred
        # email) as requester.
        assert self.context.requester.preferredemail is not None
        self._doMerge()
        if self.mergeCompleted:
            self.success(
                _(
                    "The accounts are being merged. This can take up to an "
                    "hour to complete, after which everything that belonged "
                    "to the duplicated account will belong to your own "
                    "account."
                )
            )
        else:
            self.success(
                _(
                    "The email address %s has been assigned to you, but the "
                    "duplicate account you selected has other registered "
                    "email addresses too. To complete the merge, you have to "
                    "prove that you have access to all those email addresses."
                    % self.context.email
                )
            )
        self.context.consume()

    def _doMerge(self):
        """Merges a duplicate person into a target person.

        - Reassigns the duplicate user's primary email address to the
          requesting user.

        - Ensures that the requesting user has a preferred email address, and
          uses the newly acquired one if not.

        - If the duplicate user has no other email addresses, does the merge.

        """
        # The user proved that they have access to this email address of the
        # dupe account, so we can assign it to them.
        requester = self.context.requester
        emailset = getUtility(IEmailAddressSet)
        email = removeSecurityProxy(emailset.getByEmail(self.context.email))
        # As a person can have at most one preferred email, ensure
        # that this new email does not have the PREFERRED status.
        email.status = EmailAddressStatus.NEW
        email.person = requester
        requester.validateAndEnsurePreferredEmail(email)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()

        # Now we must check if the dupe account still have registered email
        # addresses. If it hasn't we can actually do the merge.
        if not emailset.getByPerson(self.dupe).is_empty():
            self.mergeCompleted = False
            return
        getUtility(IPersonSet).mergeAsync(
            self.dupe, requester, requester, reviewer=requester
        )
        merge_message = _(
            "A merge is queued and is expected to complete in a few minutes."
        )
        self.request.response.addInfoNotification(merge_message)
        self.mergeCompleted = True


class BugTrackerHandshakeView(BaseTokenView):
    """A view for authentication BugTracker handshake tokens."""

    expected_token_types = (LoginTokenType.BUGTRACKER,)

    def __call__(self):
        # We don't render any templates from this view as it's a
        # machine-only one, so we set the response to be plaintext.
        self.request.response.setHeader("Content-type", "text/plain")

        # Reject the request if it is not a POST - but do not consume
        # the token.
        if self.request.method != "POST":
            self.request.response.setStatus(405)
            self.request.response.setHeader("Allow", "POST")
            return (
                "Only POST requests are accepted for bugtracker " "handshakes."
            )

        # If the token has been used already or is invalid, return an
        # HTTP 410 (Gone).
        if self.redirectIfInvalidOrConsumedToken():
            self.request.response.setStatus(410)
            return "Token has already been used or is invalid."

        # The token is valid, so consume it and return an HTTP 200. This
        # tells the remote tracker that authentication was successful.
        self.context.consume()
        self.request.response.setStatus(200)
        self.request.response.setHeader("Content-type", "text/plain")
        return "Handshake token validated."
