Branch Vocabularies
===================

Launchpad has a few vocabularies that contain branches filtered in
various ways.

    >>> from zope.schema.vocabulary import getVocabularyRegistry
    >>> vocabulary_registry = getVocabularyRegistry()

BranchVocabulary
----------------

The list of bzr branches registered in Launchpad.

Searchable by branch name or URL, registrant name, and project name.
Results are not restricted in any way by the context, but the results
are restricted based on who is asking (as far as private branches is
concerned).

    # Just use None as the context.
    >>> branch_vocabulary = vocabulary_registry.get(None, "Branch")
    >>> def print_vocab_branches(vocab, search):
    ...     terms = vocab.searchForTerms(search)
    ...     for name in sorted(term.value.unique_name for term in terms):
    ...         print(name)

    >>> print_vocab_branches(branch_vocabulary, 'main')
    ~justdave/+junk/main
    ~kiko/+junk/main
    ~name12/firefox/main
    ~name12/gnome-terminal/main
    ~stevea/thunderbird/main
    ~vcs-imports/evolution/main

A search with the full branch unique name should also find the branch.

    >>> print_vocab_branches(branch_vocabulary, '~name12/firefox/main')
    ~name12/firefox/main

The tokens used by terms retrieved from BranchVocabulary use the
branch unique name as an ID:

    >>> from lp.code.interfaces.branchlookup import IBranchLookup
    >>> branch = getUtility(IBranchLookup).get(15)
    >>> print(branch.unique_name)
    ~name12/gnome-terminal/main
    >>> from zope.security.proxy import removeSecurityProxy
    >>> term = removeSecurityProxy(branch_vocabulary).toTerm(branch)
    >>> print(term.token)
    ~name12/gnome-terminal/main

The BranchVocabulary recognises both unique names and URLs as tokens:

    >>> term = branch_vocabulary.getTermByToken('~name12/gnome-terminal/main')
    >>> term.value == branch
    True
    >>> term = branch_vocabulary.getTermByToken(
    ...     'http://bazaar.launchpad.test/~name12/gnome-terminal/main/')
    >>> term.value == branch
    True
    >>> term = branch_vocabulary.getTermByToken(
    ...     'http://example.com/gnome-terminal/main')
    >>> term.value == branch
    True

The searches that the BranchVocabulary does are private branch aware.
The results are effectively filtered on what the logged in user is
able to see.

    >>> from lp.testing import login, ANONYMOUS
    >>> from lp.testing.sampledata import ADMIN_EMAIL

    >>> login(ADMIN_EMAIL)
    >>> print_vocab_branches(branch_vocabulary, 'trunk')
    ~landscape-developers/landscape/trunk
    ~limi/+junk/trunk
    ~spiv/+junk/trunk

    >>> login(ANONYMOUS)
    >>> print_vocab_branches(branch_vocabulary, 'trunk')
    ~limi/+junk/trunk
    ~spiv/+junk/trunk


BranchRestrictedOnProduct
-------------------------

The BranchRestrictedOnProduct vocabulary restricts the result set to
those of the product of the context.  Currently only two types of
context are supported: Product; and Branch.  If a branch is the context,
then the product of the branch is used to restrict the query.

    >>> from lp.registry.interfaces.product import IProductSet
    >>> gnome_terminal = getUtility(IProductSet)["gnome-terminal"]
    >>> branch_vocabulary = vocabulary_registry.get(
    ...     gnome_terminal, "BranchRestrictedOnProduct")
    >>> print_vocab_branches(branch_vocabulary, 'main')
    ~name12/gnome-terminal/main

If a full unique name is entered that has a different product, the
branch is not part of the vocabulary.

    >>> print_vocab_branches(branch_vocabulary, '~name12/gnome-terminal/main')
    ~name12/gnome-terminal/main

    >>> print_vocab_branches(branch_vocabulary, '~name12/firefox/main')


The BranchRestrictedOnProduct behaves the same way as the more generic
BranchVocabulary with respect to the tokens and privacy awareness.


HostedBranchRestrictedOnOwner
-----------------------------

Here's a vocabulary for all hosted branches owned by the current user.

    >>> from lp.code.enums import BranchType

    >>> a_user = factory.makePerson(name='a-branching-user')
    >>> a_team = factory.makeTeam(name='a-team', members=[a_user])
    >>> product1 = factory.makeProduct(name='product-one')
    >>> mirrored_branch = factory.makeBranch(
    ...     owner=a_user, product=product1, name='mirrored',
    ...     branch_type=BranchType.MIRRORED)
    >>> product2 = factory.makeProduct(name='product-two')
    >>> hosted_branch = factory.makeBranch(
    ...     owner=a_user, product=product2, name='hosted')
    >>> another_hosted_branch = factory.makeBranch(
    ...     owner=a_team, product=product2, name='another_hosted')
    >>> foreign_branch = factory.makeBranch()

It returns branches owned by the user, or teams a user belongs to, but not
ones owned by others, nor ones that aren't hosted on Launchpad.

    >>> branch_vocabulary = vocabulary_registry.get(
    ...     a_user, "HostedBranchRestrictedOnOwner")
    >>> print_vocab_branches(branch_vocabulary, None)
    ~a-branching-user/product-two/hosted
    ~a-team/product-two/another_hosted
