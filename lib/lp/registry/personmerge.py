# Copyright 2009-2021 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Person/team merger implementation."""

__metaclass__ = type
__all__ = ['merge_people']

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.code.interfaces.branchcollection import (
    IAllBranches,
    IBranchCollection,
    )
from lp.code.interfaces.gitcollection import IGitCollection
from lp.oci.interfaces.ocirecipe import IOCIRecipeSet
from lp.registry.interfaces.mailinglist import (
    IMailingListSet,
    MailingListStatus,
    PURGE_STATES,
    )
from lp.registry.interfaces.personnotification import IPersonNotificationSet
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.services.database import postgresql
from lp.services.database.interfaces import IStore
from lp.services.database.sqlbase import (
    cursor,
    sqlvalues,
    )
from lp.services.identity.interfaces.emailaddress import IEmailAddressSet
from lp.services.mail.helpers import get_email_template
from lp.snappy.interfaces.snap import ISnapSet
from lp.soyuz.enums import ArchiveStatus
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.livefs import ILiveFSSet


def _merge_person_decoration(to_person, from_person, skip,
    decorator_table, person_pointer_column, additional_person_columns):
    """Merge a table that "decorates" Person.

    Because "person decoration" is becoming more frequent, we create a
    helper function that can be used for tables that decorate person.

    :to_person:       the IPerson that is "real"
    :from_person:     the IPerson that is being merged away
    :skip:            a list of table/column pairs that have been
                        handled
    :decorator_table: the name of the table that decorated Person
    :person_pointer_column:
                        the column on decorator_table that UNIQUE'ly
                        references Person.id
    :additional_person_columns:
                        additional columns in the decorator_table that
                        also reference Person.id but are not UNIQUE

    A Person decorator is a table that uniquely references Person,
    so that the information in the table "extends" the Person table.
    Because the reference to Person is unique, there can only be one
    row in the decorator table for any given Person. This function
    checks if there is an existing decorator for the to_person, and
    if so, it just leaves any from_person decorator in place as
    "noise". Otherwise, it updates any from_person decorator to
    point to the "to_person". There can also be other columns in the
    decorator which point to Person, these are assumed to be
    non-unique and will be updated to point to the to_person
    regardless.
    """
    store = Store.of(to_person)
    # First, update the main UNIQUE pointer row which links the
    # decorator table to Person. We do not update rows if there are
    # already rows in the table that refer to the to_person
    store.execute(
        """UPDATE %(decorator)s
        SET %(person_pointer)s=%(to_id)d
        WHERE %(person_pointer)s=%(from_id)d
            AND ( SELECT count(*) FROM %(decorator)s
                WHERE %(person_pointer)s=%(to_id)d ) = 0
        """ % {
            'decorator': decorator_table,
            'person_pointer': person_pointer_column,
            'from_id': from_person.id,
            'to_id': to_person.id})

    # Now, update any additional columns in the table which point to
    # Person. Since these are assumed to be NOT UNIQUE, we don't
    # have to worry about multiple rows pointing at the to_person.
    for additional_column in additional_person_columns:
        store.execute(
            """UPDATE %(decorator)s
            SET %(column)s=%(to_id)d
            WHERE %(column)s=%(from_id)d
            """ % {
                'decorator': decorator_table,
                'from_id': from_person.id,
                'to_id': to_person.id,
                'column': additional_column})
    skip.append(
        (decorator_table.lower(), person_pointer_column.lower()))


def _mergeAccessArtifactGrant(cur, from_id, to_id):
    # Update only the AccessArtifactGrants that will not conflict.
    cur.execute('''
        UPDATE AccessArtifactGrant
        SET grantee=%(to_id)d
        WHERE
            grantee = %(from_id)d
            AND artifact NOT IN (
                SELECT artifact
                FROM AccessArtifactGrant
                WHERE grantee = %(to_id)d
                )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM AccessArtifactGrant WHERE grantee = %(from_id)d
        ''' % vars())


def _mergeAccessPolicyGrant(cur, from_id, to_id):
    # Update only the AccessPolicyGrants that will not conflict.
    cur.execute('''
        UPDATE AccessPolicyGrant
        SET grantee=%(to_id)d
        WHERE
            grantee = %(from_id)d
            AND policy NOT IN (
                SELECT policy
                FROM AccessPolicyGrant
                WHERE grantee = %(to_id)d
                )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM AccessPolicyGrant WHERE grantee = %(from_id)d
        ''' % vars())


def _mergeGitRuleGrant(cur, from_id, to_id):
    # Transfer GitRuleGrants that only exist on from_person.
    cur.execute('''
        UPDATE GitRuleGrant
        SET grantee=%(to_id)d
        WHERE
            grantee = %(from_id)d
            AND rule NOT IN (
                SELECT rule
                FROM GitRuleGrant
                WHERE grantee = %(to_id)d
                )
        ''' % vars())
    # Merge permissions on GitRuleGrants that exist on both from_person and
    # to_person.  When multiple grants match a user we take the union of the
    # permissions they confer, so it's safe to do that here too.
    cur.execute('''
        UPDATE GitRuleGrant
        SET
            can_create = GitRuleGrant.can_create OR other.can_create,
            can_push = GitRuleGrant.can_push OR other.can_push,
            can_force_push =
                GitRuleGrant.can_force_push OR other.can_force_push
        FROM GitRuleGrant AS other
        WHERE
            GitRuleGrant.grantee = %(to_id)d
            AND other.grantee = %(from_id)d
            AND GitRuleGrant.rule = other.rule
        ''' % vars())
    # Delete the remaining GitRuleGrants for from_person, which have now all
    # been either transferred or merged.
    cur.execute('''
        DELETE FROM GitRuleGrant WHERE grantee = %(from_id)d
        ''' % vars())


def _mergeBranches(from_person, to_person):
    # This shouldn't use removeSecurityProxy.
    branches = getUtility(IBranchCollection).ownedBy(from_person)
    for branch in branches.getBranches():
        removeSecurityProxy(branch).setOwner(to_person, to_person)


def _mergeGitRepositories(from_person, to_person):
    # This shouldn't use removeSecurityProxy.
    repositories = getUtility(IGitCollection).ownedBy(from_person)
    for repository in repositories.getRepositories():
        removeSecurityProxy(repository).setOwner(to_person, to_person)


def _mergeSourcePackageRecipes(from_person, to_person):
    # This shouldn't use removeSecurityProxy.
    recipes = from_person.recipes
    existing_names = [r.name for r in to_person.recipes]
    for recipe in recipes:
        new_name = recipe.name
        count = 1
        while new_name in existing_names:
            new_name = '%s-%s' % (recipe.name, count)
            count += 1
        naked_recipe = removeSecurityProxy(recipe)
        naked_recipe.owner = to_person
        naked_recipe.name = new_name


def _mergeLoginTokens(cur, from_id, to_id):
    # Remove all LoginTokens.
    cur.execute('''
        DELETE FROM LoginToken WHERE requester=%(from_id)d''' % vars())


def _mergeMailingListSubscriptions(cur, from_id, to_id):
    # Update MailingListSubscription. Note that since all the from_id
    # email addresses are set to NEW, all the subscriptions must be
    # removed because the user must confirm them.
    cur.execute('''
        DELETE FROM MailingListSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeBranchSubscription(cur, from_id, to_id):
    # Update only the BranchSubscription that will not conflict.
    cur.execute('''
        UPDATE BranchSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND branch NOT IN
            (
            SELECT branch
            FROM BranchSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM BranchSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeGitSubscription(cur, from_id, to_id):
    # Update only the GitSubscription that will not conflict.
    cur.execute('''
        UPDATE GitSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND repository NOT IN
            (
            SELECT repository
            FROM GitSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM GitSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeBugAffectsPerson(cur, from_id, to_id):
    # Update only the BugAffectsPerson that will not conflict
    cur.execute('''
        UPDATE BugAffectsPerson
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND bug NOT IN
            (
            SELECT bug
            FROM BugAffectsPerson
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM BugAffectsPerson WHERE person=%(from_id)d
        ''' % vars())


def _mergeAnswerContact(cur, from_id, to_id):
    # Update only the AnswerContacts that will not conflict.
    cur.execute('''
        UPDATE AnswerContact
        SET person=%(to_id)d
        WHERE person=%(from_id)d
            AND distribution IS NULL
            AND product NOT IN (
                SELECT product
                FROM AnswerContact
                WHERE person = %(to_id)d
                )
        ''' % vars())
    cur.execute('''
        UPDATE AnswerContact
        SET person=%(to_id)d
        WHERE person=%(from_id)d
            AND distribution IS NOT NULL
            AND (distribution, sourcepackagename) NOT IN (
                SELECT distribution,sourcepackagename
                FROM AnswerContact
                WHERE person = %(to_id)d
                )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM AnswerContact WHERE person=%(from_id)d
        ''' % vars())


def _mergeQuestionSubscription(cur, from_id, to_id):
    # Update only the QuestionSubscriptions that will not conflict.
    cur.execute('''
        UPDATE QuestionSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND question NOT IN
            (
            SELECT question
            FROM QuestionSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM QuestionSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeBugNotificationRecipient(cur, from_id, to_id):
    # Update BugNotificationRecipient entries that will not conflict.
    cur.execute('''
        UPDATE BugNotificationRecipient
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND bug_notification NOT IN (
            SELECT bug_notification FROM BugNotificationRecipient
            WHERE person=%(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM BugNotificationRecipient
        WHERE person=%(from_id)d
        ''' % vars())


def _mergeStructuralSubscriptions(cur, from_id, to_id):
    # Update StructuralSubscription entries that will not conflict.
    # We separate this out from the parent query primarily to help
    # keep within our line length constraints, though it might make
    # things more readable otherwise as well.
    exists_query = '''
        SELECT StructuralSubscription.id
        FROM StructuralSubscription
        WHERE StructuralSubscription.subscriber=%(to_id)d AND (
            StructuralSubscription.product=SSub.product
            OR
            StructuralSubscription.project=SSub.project
            OR
            StructuralSubscription.distroseries=SSub.distroseries
            OR
            StructuralSubscription.milestone=SSub.milestone
            OR
            StructuralSubscription.productseries=SSub.productseries
            OR
            (StructuralSubscription.distribution=SSub.distribution
                AND StructuralSubscription.sourcepackagename IS NULL
                AND SSub.sourcepackagename IS NULL)
            OR
            (StructuralSubscription.sourcepackagename=
                SSub.sourcepackagename
                AND StructuralSubscription.sourcepackagename=
                SSub.sourcepackagename)
            )
        '''
    cur.execute(('''
        UPDATE StructuralSubscription
        SET subscriber=%(to_id)d
        WHERE subscriber=%(from_id)d AND id NOT IN (
            SELECT SSub.id
            FROM StructuralSubscription AS SSub
            WHERE
                SSub.subscriber=%(from_id)d
                AND EXISTS (''' + exists_query + ''')
        )
        ''') % vars())
    # Delete the rest.  We have to explicitly delete the bug subscription
    # filters first because there is not a cascade delete set up in the
    # db.
    cur.execute('''
        DELETE FROM BugSubscriptionFilter
        WHERE structuralsubscription IN (
            SELECT id
            FROM StructuralSubscription
            WHERE subscriber=%(from_id)d)
        ''' % vars())
    cur.execute('''
        DELETE FROM StructuralSubscription WHERE subscriber=%(from_id)d
        ''' % vars())


def _mergeSpecificationSubscription(cur, from_id, to_id):
    # Update the SpecificationSubscription entries that will not conflict
    # and trash the rest
    cur.execute('''
        UPDATE SpecificationSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND specification NOT IN
            (
            SELECT specification
            FROM SpecificationSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    cur.execute('''
        DELETE FROM SpecificationSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeSprintAttendance(cur, from_id, to_id):
    # Update only the SprintAttendances that will not conflict
    cur.execute('''
        UPDATE SprintAttendance
        SET attendee=%(to_id)d
        WHERE attendee=%(from_id)d AND sprint NOT IN
            (
            SELECT sprint
            FROM SprintAttendance
            WHERE attendee = %(to_id)d
            )
        ''' % vars())
    # and delete those left over
    cur.execute('''
        DELETE FROM SprintAttendance WHERE attendee=%(from_id)d
        ''' % vars())


def _mergePOExportRequest(cur, from_id, to_id):
    # Update only the POExportRequests that will not conflict
    # and trash the rest
    cur.execute('''
        UPDATE POExportRequest
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND id NOT IN (
            SELECT a.id FROM POExportRequest AS a, POExportRequest AS b
            WHERE a.person = %(from_id)d AND b.person = %(to_id)d
            AND a.potemplate = b.potemplate
            AND a.pofile = b.pofile
            )
        ''' % vars())
    cur.execute('''
        DELETE FROM POExportRequest WHERE person=%(from_id)d
        ''' % vars())


def _mergeTranslationMessage(cur, from_id, to_id):
    # Update the TranslationMessage. They should not conflict since each
    # of them are independent
    cur.execute('''
        UPDATE TranslationMessage
        SET submitter=%(to_id)d
        WHERE submitter=%(from_id)d
        ''' % vars())
    cur.execute('''
        UPDATE TranslationMessage
        SET reviewer=%(to_id)d
        WHERE reviewer=%(from_id)d
        ''' % vars())


def _mergeTranslationImportQueueEntry(cur, from_id, to_id):
    # Update only the TranslationImportQueueEntry that will not conflict
    # and trash the rest
    cur.execute('''
        UPDATE TranslationImportQueueEntry
        SET importer=%(to_id)d
        WHERE importer=%(from_id)d AND id NOT IN (
            SELECT a.id
            FROM TranslationImportQueueEntry AS a,
                    TranslationImportQueueEntry AS b
            WHERE a.importer = %(from_id)d AND b.importer = %(to_id)d
            AND a.distroseries = b.distroseries
            AND a.sourcepackagename = b.sourcepackagename
            AND a.productseries = b.productseries
            AND a.path = b.path
            )
        ''' % vars())
    cur.execute('''
        DELETE FROM TranslationImportQueueEntry WHERE importer=%(from_id)d
        ''' % vars())


def _mergeCodeReviewVote(cur, from_id, to_id):
    # Update only the CodeReviewVote that will not conflict,
    # and leave conflicts as noise
    cur.execute('''
        UPDATE CodeReviewVote
        SET reviewer=%(to_id)d
        WHERE reviewer=%(from_id)d AND id NOT IN (
            SELECT a.id FROM CodeReviewVote AS a, CodeReviewVote AS b
            WHERE a.reviewer = %(from_id)d AND b.reviewer = %(to_id)d
            AND a.branch_merge_proposal = b.branch_merge_proposal
            )
        ''' % vars())


def _mergeTeamMembership(cur, from_id, to_id):
    # Transfer active team memberships
    approved = TeamMembershipStatus.APPROVED
    admin = TeamMembershipStatus.ADMIN
    cur.execute(
        'SELECT team, status FROM TeamMembership WHERE person = %s '
        'AND status IN (%s,%s)'
        % sqlvalues(from_id, approved, admin))
    for team_id, status in cur.fetchall():
        cur.execute('SELECT status FROM TeamMembership WHERE person = %s '
                    'AND team = %s'
                    % sqlvalues(to_id, team_id))
        result = cur.fetchone()
        if result is not None:
            current_status = result[0]
            # Now we can safely delete from_person's membership record,
            # because we know to_person has a membership entry for this
            # team, so may only need to change its status.
            cur.execute(
                'DELETE FROM TeamMembership WHERE person = %s '
                'AND team = %s' % sqlvalues(from_id, team_id))

            if current_status == admin.value:
                # to_person is already an administrator of this team, no
                # need to do anything else.
                continue
            # to_person is either an approved or an inactive member,
            # while from_person is either admin or approved. That means we
            # can safely set from_person's membership status on
            # to_person's membership.
            assert status in (approved.value, admin.value)
            cur.execute(
                'UPDATE TeamMembership SET status = %s WHERE person = %s '
                'AND team = %s' % sqlvalues(status, to_id, team_id))
        else:
            # to_person is not a member of this team. just change
            # from_person with to_person in the membership record.
            cur.execute(
                'UPDATE TeamMembership SET person = %s WHERE person = %s '
                'AND team = %s'
                % sqlvalues(to_id, from_id, team_id))

    cur.execute('SELECT team FROM TeamParticipation WHERE person = %s '
                'AND person != team' % sqlvalues(from_id))
    for team_id in cur.fetchall():
        cur.execute(
            'SELECT team FROM TeamParticipation WHERE person = %s '
            'AND team = %s' % sqlvalues(to_id, team_id))
        if not cur.fetchone():
            cur.execute(
                'UPDATE TeamParticipation SET person = %s WHERE '
                'person = %s AND team = %s'
                % sqlvalues(to_id, from_id, team_id))
        else:
            cur.execute(
                'DELETE FROM TeamParticipation WHERE person = %s AND '
                'team = %s' % sqlvalues(from_id, team_id))


def _mergeProposedInvitedTeamMembership(cur, from_id, to_id):
    # Memberships in an intermediate state are declined to avoid
    # cyclic membership errors and confusion about who the proposed
    # member is.
    TMS = TeamMembershipStatus
    update_template = ("""
        UPDATE TeamMembership
        SET status = %s
        WHERE
            person = %s
            AND status = %s
        """)
    cur.execute(update_template % sqlvalues(
        TMS.DECLINED, from_id, TMS.PROPOSED))
    cur.execute(update_template % sqlvalues(
        TMS.INVITATION_DECLINED, from_id, TMS.INVITED))


def _mergeKarmaCache(cur, from_id, to_id, from_karma):
    # Merge the karma total cache so the user does not think the karma
    # was lost.
    params = dict(from_id=from_id, to_id=to_id)
    if from_karma > 0:
        cur.execute('''
            SELECT karma_total FROM KarmaTotalCache
            WHERE person = %(to_id)d
            ''' % params)
        result = cur.fetchone()
        if result is not None:
            # Add the karma to the remaining user.
            params['karma_total'] = from_karma + result[0]
            cur.execute('''
                UPDATE KarmaTotalCache SET karma_total = %(karma_total)d
                WHERE person = %(to_id)d
                ''' % params)
        else:
            # Make the existing karma belong to the remaining user.
            cur.execute('''
                UPDATE KarmaTotalCache SET person = %(to_id)d
                WHERE person = %(from_id)d
                ''' % params)
    # Delete the old caches; the daily job will build them later.
    cur.execute('''
        DELETE FROM KarmaTotalCache WHERE person = %(from_id)d
        ''' % params)
    cur.execute('''
        DELETE FROM KarmaCache WHERE person = %(from_id)d
        ''' % params)


def _mergeDateCreated(cur, from_id, to_id):
    cur.execute('''
        UPDATE Person
        SET datecreated = (
            SELECT MIN(datecreated) FROM Person
            WHERE id in (%(to_id)d, %(from_id)d) LIMIT 1)
        WHERE id = %(to_id)d
        ''' % vars())


def _mergeCodeReviewInlineCommentDraft(cur, from_id, to_id):
    params = dict(from_id=from_id, to_id=to_id)
    # Remove conflicting drafts.
    cur.execute('''
    DELETE FROM CodeReviewInlineCommentDraft
    WHERE person = %(from_id)d AND previewdiff IN (
        SELECT previewdiff FROM CodeReviewInlineCommentDraft
            WHERE person = %(to_id)d)
    ''' % params)
    # Update draft comments to the new owner.
    cur.execute('''
    UPDATE CodeReviewInlineCommentDraft SET person = %(to_id)d
    WHERE person = %(from_id)d
    ''' % params)


def _mergeLiveFS(cur, from_person, to_person):
    # This shouldn't use removeSecurityProxy.
    livefses = getUtility(ILiveFSSet).getByPerson(from_person)
    existing_names = [
        l.name for l in getUtility(ILiveFSSet).getByPerson(to_person)]
    for livefs in livefses:
        new_name = livefs.name
        count = 1
        while new_name in existing_names:
            new_name = '%s-%s' % (livefs.name, count)
            count += 1
        naked_livefs = removeSecurityProxy(livefs)
        naked_livefs.owner = to_person
        naked_livefs.name = new_name
    if not livefses.is_empty():
        IStore(livefses[0]).flush()


def _mergeSnap(cur, from_person, to_person):
    # This shouldn't use removeSecurityProxy.
    snaps = getUtility(ISnapSet).findByOwner(from_person)
    existing_names = [
        s.name for s in getUtility(ISnapSet).findByOwner(to_person)]
    for snap in snaps:
        naked_snap = removeSecurityProxy(snap)
        new_name = naked_snap.name
        count = 1
        while new_name in existing_names:
            new_name = '%s-%s' % (snap.name, count)
            count += 1
        naked_snap.owner = to_person
        naked_snap.name = new_name
    if not snaps.is_empty():
        IStore(snaps[0]).flush()


def _mergeSnapSubscription(cur, from_id, to_id):
    # Update only the SnapSubscription that will not conflict.
    cur.execute('''
        UPDATE SnapSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND snap NOT IN
            (
            SELECT snap
            FROM SnapSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM SnapSubscription WHERE person=%(from_id)d
        ''' % vars())


def _mergeOCIRecipe(cur, from_person, to_person):
    # This shouldn't use removeSecurityProxy
    oci_recipes = getUtility(IOCIRecipeSet).findByOwner(from_person)
    existing_names = [
        r.name for r in getUtility(IOCIRecipeSet).findByOwner(to_person)]
    for recipe in oci_recipes:
        naked_recipe = removeSecurityProxy(recipe)
        new_name = naked_recipe.name
        count = 1
        while new_name in existing_names:
            new_name = '%s-%s' % (naked_recipe.name, count)
            count += 1
        naked_recipe.owner = to_person
        naked_recipe.name = new_name
    if not oci_recipes.is_empty():
        IStore(oci_recipes[0]).flush()


def _mergeOCIRecipeSubscription(cur, from_id, to_id):
    # Update only the OCIRecipeSubscription that will not conflict.
    cur.execute('''
        UPDATE OCIRecipeSubscription
        SET person=%(to_id)d
        WHERE person=%(from_id)d AND recipe NOT IN
            (
            SELECT recipe
            FROM OCIRecipeSubscription
            WHERE person = %(to_id)d
            )
        ''' % vars())
    # and delete those left over.
    cur.execute('''
        DELETE FROM OCIRecipeSubscription WHERE person=%(from_id)d
        ''' % vars())


def _purgeUnmergableTeamArtifacts(from_team, to_team, reviewer):
    """Purge team artifacts that cannot be merged, but can be removed."""
    # A team cannot have more than one mailing list.
    mailing_list = getUtility(IMailingListSet).get(from_team.name)
    if mailing_list is not None:
        if mailing_list.status in PURGE_STATES:
            from_team.mailing_list.purge()
        elif mailing_list.status != MailingListStatus.PURGED:
            raise AssertionError(
                "Teams with active mailing lists cannot be merged.")
    # Team email addresses are not transferable.
    from_team.setContactAddress(None)
    # Memberships in the team are not transferable because there
    # is a high probablity there will be a CyclicTeamMembershipError.
    comment = (
        'Deactivating all members as this team is being merged into %s.'
        % to_team.name)
    membershipset = getUtility(ITeamMembershipSet)
    membershipset.deactivateActiveMemberships(
        from_team, comment, reviewer)
    # Memberships in other teams are not transferable because there
    # is a high probablity there will be a CyclicTeamMembershipError.
    all_super_teams = set(from_team.teams_participated_in)
    indirect_super_teams = set(
        from_team.teams_indirectly_participated_in)
    super_teams = all_super_teams - indirect_super_teams
    naked_from_team = removeSecurityProxy(from_team)
    for team in super_teams:
        naked_from_team.retractTeamMembership(team, reviewer)
    IStore(from_team).flush()


def merge_people(from_person, to_person, reviewer, delete=False):
    """Helper for merge and delete methods."""
    # since we are doing direct SQL manipulation, make sure all
    # changes have been flushed to the database
    store = Store.of(from_person)
    store.flush()
    if (from_person.is_team and not to_person.is_team
        or not from_person.is_team and to_person.is_team):
        raise AssertionError("Users cannot be merged with teams.")
    if from_person.is_team and reviewer is None:
        raise AssertionError("Team merged require a reviewer.")
    if getUtility(IArchiveSet).getPPAOwnedByPerson(
        from_person, statuses=[ArchiveStatus.ACTIVE,
                                ArchiveStatus.DELETING]) is not None:
        raise AssertionError(
            'from_person has a ppa in ACTIVE or DELETING status')
    from_person_branches = getUtility(IAllBranches).ownedBy(from_person)
    if not from_person_branches.isPrivate().is_empty():
        raise AssertionError('from_person has private branches.')
    if from_person.is_team:
        _purgeUnmergableTeamArtifacts(from_person, to_person, reviewer)
    if not getUtility(
        IEmailAddressSet).getByPerson(from_person).is_empty():
        raise AssertionError('from_person still has email addresses.')

    # Get a database cursor.
    cur = cursor()

    # These table.columns will be skipped by the 'catch all'
    # update performed later
    skip = [
        # The AccessPolicy.person reference is to allow private teams to
        # see their own +junk branches. We don't allow merges for teams who
        # own private branches so we can skip this column.
        ('accesspolicy', 'person'),
        ('teammembership', 'person'),
        ('teammembership', 'team'),
        ('teamparticipation', 'person'),
        ('teamparticipation', 'team'),
        ('personlanguage', 'person'),
        ('person', 'merged'),
        ('personsettings', 'person'),
        ('emailaddress', 'person'),
        # Polls are not carried over when merging teams.
        ('poll', 'team'),
        # We can safely ignore the mailinglist table as there's a sanity
        # check above which prevents teams with associated mailing lists
        # from being merged.
        ('mailinglist', 'team'),
        # I don't think we need to worry about the votecast and vote
        # tables, because a real human should never have two profiles
        # in Launchpad that are active members of a given team and voted
        # in a given poll. -- GuilhermeSalgado 2005-07-07
        # We also can't afford to change poll results after they are
        # closed -- StuartBishop 20060602
        ('votecast', 'person'),
        ('vote', 'person'),
        ('translationrelicensingagreement', 'person'),
        # These are ON DELETE CASCADE and maintained by triggers.
        ('bugsummary', 'viewed_by'),
        ('bugsummaryjournal', 'viewed_by'),
        ('latestpersonsourcepackagereleasecache', 'creator'),
        ('latestpersonsourcepackagereleasecache', 'maintainer'),
        # Obsolete table.
        ('branchmergequeue', 'owner'),
        # XXX cjwatson 2020-02-05: This needs handling before we deploy the
        # OCI recipe code, but can be ignored for the purpose of deploying
        # the database tables.
        ('ocirecipe', 'owner'),
        # XXX cjwatson 2021-05-24: This needs handling before we deploy the
        # charm recipe code, but can be ignored for the purpose of deploying
        # the database tables.
        ('charmrecipe', 'owner'),
        ]

    references = list(postgresql.listReferences(cur, 'person', 'id'))
    postgresql.check_indirect_references(references)

    # These rows are in a UNIQUE index, and we can only move them
    # to the new Person if there is not already an entry. eg. if
    # the destination and source persons are both subscribed to a bug,
    # we cannot change the source persons subscription. We just leave them
    # as noise for the time being.

    to_id = to_person.id
    from_id = from_person.id

    # Update PersonLocation, which is a Person-decorator table.
    _merge_person_decoration(
        to_person, from_person, skip, 'PersonLocation', 'person',
        ['last_modified_by', ])

    # Update GPGKey. It won't conflict, but our sanity checks don't
    # know that.
    cur.execute(
        'UPDATE GPGKey SET owner=%(to_id)d WHERE owner=%(from_id)d'
        % vars())
    skip.append(('gpgkey', 'owner'))

    _mergeAccessArtifactGrant(cur, from_id, to_id)
    _mergeAccessPolicyGrant(cur, from_id, to_id)
    _mergeGitRuleGrant(cur, from_id, to_id)
    skip.append(('accessartifactgrant', 'grantee'))
    skip.append(('accesspolicygrant', 'grantee'))
    skip.append(('gitrulegrant', 'grantee'))

    # Update the Branches that will not conflict, and fudge the names of
    # ones that *do* conflict.
    _mergeBranches(from_person, to_person)
    skip.append(('branch', 'owner'))

    # Update the GitRepositories that will not conflict, and fudge the names
    # of ones that *do* conflict.
    _mergeGitRepositories(from_person, to_person)
    skip.append(('gitrepository', 'owner'))

    _mergeSourcePackageRecipes(from_person, to_person)
    skip.append(('sourcepackagerecipe', 'owner'))

    _mergeMailingListSubscriptions(cur, from_id, to_id)
    skip.append(('mailinglistsubscription', 'person'))

    _mergeBranchSubscription(cur, from_id, to_id)
    skip.append(('branchsubscription', 'person'))

    _mergeGitSubscription(cur, from_id, to_id)
    skip.append(('gitsubscription', 'person'))

    _mergeBugAffectsPerson(cur, from_id, to_id)
    skip.append(('bugaffectsperson', 'person'))

    _mergeAnswerContact(cur, from_id, to_id)
    skip.append(('answercontact', 'person'))

    _mergeQuestionSubscription(cur, from_id, to_id)
    skip.append(('questionsubscription', 'person'))

    _mergeBugNotificationRecipient(cur, from_id, to_id)
    skip.append(('bugnotificationrecipient', 'person'))

    # We ignore BugSubscriptionFilterMutes.
    skip.append(('bugsubscriptionfiltermute', 'person'))

    # We ignore BugMutes.
    skip.append(('bugmute', 'person'))

    _mergeStructuralSubscriptions(cur, from_id, to_id)
    skip.append(('structuralsubscription', 'subscriber'))

    _mergeSpecificationSubscription(cur, from_id, to_id)
    skip.append(('specificationsubscription', 'person'))

    _mergeSprintAttendance(cur, from_id, to_id)
    skip.append(('sprintattendance', 'attendee'))

    _mergePOExportRequest(cur, from_id, to_id)
    skip.append(('poexportrequest', 'person'))

    _mergeTranslationMessage(cur, from_id, to_id)
    skip.append(('translationmessage', 'submitter'))
    skip.append(('translationmessage', 'reviewer'))

    # Handle the POFileTranslator cache by doing nothing. As it is
    # maintained by triggers, the data migration has already been done
    # for us when we updated the source tables.
    skip.append(('pofiletranslator', 'person'))

    _mergeTranslationImportQueueEntry(cur, from_id, to_id)
    skip.append(('translationimportqueueentry', 'importer'))

    # XXX cprov 2007-02-22 bug=87098:
    # Since we only allow one PPA for each user,
    # we can't reassign the old user archive to the new user.
    # It need to be done manually, probably by reasinning all publications
    # to the old PPA to the new one, performing a careful_publishing on it
    # and removing the old one from disk.
    skip.append(('archive', 'owner'))

    _mergeCodeReviewVote(cur, from_id, to_id)
    skip.append(('codereviewvote', 'reviewer'))

    _mergeKarmaCache(cur, from_id, to_id, from_person.karma)
    skip.append(('karmacache', 'person'))
    skip.append(('karmatotalcache', 'person'))

    _mergeDateCreated(cur, from_id, to_id)

    _mergeLoginTokens(cur, from_id, to_id)
    skip.append(('logintoken', 'requester'))

    _mergeCodeReviewInlineCommentDraft(cur, from_id, to_id)
    skip.append(('codereviewinlinecommentdraft', 'person'))

    _mergeLiveFS(cur, from_person, to_person)
    skip.append(('livefs', 'owner'))

    _mergeSnap(cur, from_person, to_person)
    skip.append(('snap', 'owner'))

    _mergeSnapSubscription(cur, from_id, to_id)
    skip.append(('snapsubscription', 'person'))

    _mergeOCIRecipe(cur, from_person, to_person)
    skip.append(('ocirecipe', 'owner'))

    _mergeOCIRecipeSubscription(cur, from_id, to_id)
    skip.append(('ocirecipesubscription', 'person'))

    # Sanity check. If we have a reference that participates in a
    # UNIQUE index, it must have already been handled by this point.
    # We can tell this by looking at the skip list.
    for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
        uniques = postgresql.listUniques(cur, src_tab, src_col)
        if len(uniques) > 0 and (src_tab, src_col) not in skip:
            raise NotImplementedError(
                    '%s.%s reference to %s.%s is in a UNIQUE index '
                    'but has not been handled' % (
                        src_tab, src_col, ref_tab, ref_col))

    # Handle all simple cases
    for src_tab, src_col, ref_tab, ref_col, updact, delact in references:
        if (src_tab, src_col) in skip:
            continue
        cur.execute('UPDATE %s SET %s=%d WHERE %s=%d' % (
            src_tab, src_col, to_person.id, src_col, from_person.id))

    _mergeTeamMembership(cur, from_id, to_id)
    _mergeProposedInvitedTeamMembership(cur, from_id, to_id)

    # Flag the person as merged
    cur.execute('''
        UPDATE Person SET merged=%(to_id)d WHERE id=%(from_id)d
        ''' % vars())

    # Append a -merged suffix to the person's name.
    name = base = "%s-merged" % from_person.name
    cur.execute("SELECT id FROM Person WHERE name = %s" % sqlvalues(name))
    i = 1
    while cur.fetchone():
        name = "%s%d" % (base, i)
        cur.execute("SELECT id FROM Person WHERE name = %s"
                    % sqlvalues(name))
        i += 1
    cur.execute("UPDATE Person SET name = %s WHERE id = %s"
                % sqlvalues(name, from_person))

    # Since we've updated the database behind Storm's back,
    # flush its caches.
    store.invalidate()

    # Move OpenId Identifiers from the merged account to the new
    # account.
    if from_person.account is not None and to_person.account is not None:
        store.execute("""
            UPDATE OpenIdIdentifier SET account=%s WHERE account=%s
            """ % sqlvalues(to_person.accountID, from_person.accountID))

    if delete:
        # We don't notify anyone about deletes.
        return

    # Inform the user of the merge changes.
    if to_person.is_team:
        mail_text = get_email_template(
            'team-merged.txt', app='registry')
        subject = u'Launchpad teams merged'
    else:
        mail_text = get_email_template(
            'person-merged.txt', app='registry')
        subject = u'Launchpad accounts merged'
    mail_text = mail_text % {
        'dupename': from_person.name,
        'person': to_person.name,
        }
    getUtility(IPersonNotificationSet).addNotification(
        to_person, subject, mail_text)
