# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'FeatureController',
    'flag_info',
    'NullFeatureController',
    'undocumented_flags',
    'value_domain_info',
    ]


from lp.services.features.rulesource import (
    NullFeatureRuleSource,
    StormFeatureRuleSource,
    )


__metaclass__ = type


value_domain_info = sorted([
    ('boolean',
     'Any non-empty value is true; an empty value is false.'),
    ('float',
     'The flag value is set to the given floating point number.'),
    ])

# This table of flag name, value domain, and prose documentation is used to
# generate the web-visible feature flag documentation.
flag_info = sorted([
    ('code.branchmergequeue',
     'boolean',
     'Enables merge queue pages and lists them on branch pages.',
     ''),
    ('code.incremental_diffs.enabled',
     'boolean',
     'Shows incremental diffs on merge proposals.',
     ''),
    ('code.recipes_enabled',
     'boolean',
     'Enables source package recipes in the API and UI.',
     ''),
    ('code.recipes.beta',
     'boolean',
     'True if recipes are still in beta',
     ''),
    ('hard_timeout',
     'float',
     'Sets the hard request timeout in milliseconds.',
     ''),
    ('malone.advanced-subscriptions.enabled',
     'boolean',
     'Enables advanced bug subscription features.',
     ''),
    ('malone.disable_targetnamesearch',
     'boolean',
     'If true, disables consultation of target names during bug text search.',
     ''),
    ('memcache',
     'boolean',
     'Enables use of memcached where it is supported.',
     'enabled'),
    ('profiling.enabled',
     'boolean',
     'Overrides config.profiling.profiling_allowed to permit profiling.',
     ''),
    ('publicrestrictedlibrarian',
     'boolean',
     'Redirects to private librarian files instead of proxying them.',
     ''),
    ('soyuz.derived-series-ui.enabled',
     'boolean',
     'Enables derivative distributions pages.',
     ''),
    ('soyuz.derived_series_jobs.enabled',
     'boolean',
     "Compute package differences for derived distributions.",
     ''),
    ('translations.sharing_information.enabled',
     'boolean',
     'Enables display of sharing information on translation pages.',
     ''),
    ('visible_render_time',
     'boolean',
     'Shows the server-side page render time in the login widget.',
     ''),
    ])

# The set of all flag names that are documented.
documented_flags = set(info[0] for info in flag_info)
# The set of all the flags names that have been used during the process
# lifetime, but were not documented in flag_info.
undocumented_flags = set()


class Memoize():

    def __init__(self, calc):
        self._known = {}
        self._calc = calc

    def lookup(self, key):
        if key in self._known:
            return self._known[key]
        v = self._calc(key)
        self._known[key] = v
        return v


class ScopeDict():
    """Allow scopes to be looked up by getitem"""

    def __init__(self, features):
        self.features = features

    def __getitem__(self, scope_name):
        return self.features.isInScope(scope_name)


class FeatureController():
    """A FeatureController tells application code what features are active.

    It does this by meshing together two sources of data:

      - feature flags, typically set by an administrator into the database

      - feature scopes, which would typically be looked up based on attributes
      of the current web request, or the user for whom a job is being run, or
      something similar.

    FeatureController presents a high level interface for application code to
    query flag values, without it needing to know that they are stored in the
    database.

    At this level flag names and scope names are presented as strings for
    easier use in Python code, though the values remain unicode.  They
    should always be ascii like Python identifiers.

    One instance of FeatureController should be constructed for the lifetime
    of code that has consistent configuration values.  For instance there will
    be one per web app request.

    Intended performance: when this object is first asked about a flag, it
    will read the whole feature flag table from the database.  It is expected
    to be reasonably small.  The scopes may be expensive to compute (eg
    checking team membership) so they are checked at most once when
    they are first needed.

    The controller is then supposed to be held in a thread-local and reused
    for the duration of the request.

    @see: U{https://dev.launchpad.net/LEP/FeatureFlags}
    """

    def __init__(self, scope_check_callback, rule_source=None):
        """Construct a new view of the features for a set of scopes.

        :param scope_check_callback: Given a scope name, says whether
            it's active or not.

        :param rule_source: Instance of StormFeatureRuleSource or similar.
        """
        self._known_scopes = Memoize(scope_check_callback)
        self._known_flags = Memoize(self._checkFlag)
        # rules are read from the database the first time they're needed
        self._rules = None
        self.scopes = ScopeDict(self)
        if rule_source is None:
            rule_source = StormFeatureRuleSource()
        self.rule_source = rule_source

    def getFlag(self, flag):
        """Get the value of a specific flag.

        :param flag: A name to lookup. e.g. 'recipes.enabled'

        :return: The value of the flag determined by the highest priority rule
        that matched.
        """
        # If this is an undocumented flag, record it.
        if flag not in documented_flags:
            undocumented_flags.add(flag)
        return self._known_flags.lookup(flag)

    def _checkFlag(self, flag):
        self._needRules()
        if flag in self._rules:
            for scope, priority, value in self._rules[flag]:
                if self._known_scopes.lookup(scope):
                    return value

    def isInScope(self, scope):
        return self._known_scopes.lookup(scope)

    def __getitem__(self, flag_name):
        """FeatureController can be indexed.

        This is to support easy zope traversal through eg
        "request/features/a.b.c".  We don't support other collection
        protocols.

        Note that calling this the first time for any key may cause
        arbitrarily large amounts of work to be done to determine if the
        controller is in any scopes relevant to this flag.
        """
        return self.getFlag(flag_name)

    def getAllFlags(self):
        """Return a dict of all active flags.

        This may be expensive because of evaluating many scopes, so it
        shouldn't normally be used by code that only wants to know about one
        or a few flags.
        """
        self._needRules()
        return dict((f, self.getFlag(f)) for f in self._rules)

    def _needRules(self):
        if self._rules is None:
            self._rules = self.rule_source.getAllRulesAsDict()

    def usedFlags(self):
        """Return dict of flags used in this controller so far."""
        return dict(self._known_flags._known)

    def usedScopes(self):
        """Return {scope: active} for scopes that have been used so far."""
        return dict(self._known_scopes._known)


class NullFeatureController(FeatureController):
    """For use in testing: everything is turned off"""

    def __init__(self):
        FeatureController.__init__(self, lambda scope: None,
            NullFeatureRuleSource())
