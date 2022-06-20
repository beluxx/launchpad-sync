Code Import Machines
====================

There is a simple CodeImportMachine table in the database that records
the machines that can perform imports and whether they are online (that
is, currently capable of performing imports).

    >>> from lp.code.enums import CodeImportMachineState
    >>> from lp.code.interfaces.codeimportmachine import (
    ...     ICodeImportMachine, ICodeImportMachineSet)

    >>> machine_set = getUtility(ICodeImportMachineSet)
    >>> from lp.testing import verifyObject
    >>> verifyObject(ICodeImportMachineSet, machine_set)
    True

There are additional unit tests for CodeImportMachine in
lp.code.model.tests.test_codeimportmachine.


Retrieving CodeImportMachines
-----------------------------

The 'getAll' method of ICodeImportMachineSet returns an iterable of all
CodeImportMachine.  There is only one CodeImportMachine in the sample
data.

    >>> [sample_machine] = machine_set.getAll()

Machine objects themselves provide ICodeImportMachine, which includes
hostname and online state information.

    >>> verifyObject(ICodeImportMachine, sample_machine)
    True

    >>> print(sample_machine.hostname)
    bazaar-importer

    >>> print(sample_machine.state.name)
    ONLINE

getByHostname looks for a machine of the given hostname, and returns
None if there is no machine by that name in the database.

    >>> print(machine_set.getByHostname('bazaar-importer'))
    <...CodeImportMachine...>

    >>> print(machine_set.getByHostname('unlikely-to-exist'))
    None


Canonical URLs
--------------

In order to be able to have views for the code import machines, they
need to have a canonical URL.  The CodeImportMachineSet also has a
canonical URL for set based views.

    >>> from lp.services.webapp import canonical_url
    >>> print(canonical_url(machine_set))
    http://code.launchpad.test/+code-imports/+machines

A single code import machine is identified by the hostname of the
machine directly after the canonical URL of the code import machine set.

    >>> print(canonical_url(sample_machine))
    http://code.launchpad.test/+code-imports/+machines/bazaar-importer


Creating CodeImportMachines
---------------------------

CodeImportMachines can be created with the 'new' method of
ICodeImportMachineSet.  New machines can be created in either the ONLINE
or OFFLINE states, but are in the OFFLINE state by default.

    >>> new_machine = machine_set.new('frobisher')
    >>> print(new_machine.state.name)
    OFFLINE

If they are created in the ONLINE state, an ONLINE event is created in
the CodeImportEvent audit trail.  The NewEvents class helps testing the
creation of CodeImportEvent objects.

    >>> from lp.code.enums import (
    ...     CodeImportEventDataType, CodeImportMachineOfflineReason)
    >>> from lp.code.model.tests.test_codeimportjob import (
    ...     NewEvents)

    >>> new_events = NewEvents()
    >>> new_machine2 = machine_set.new(
    ...     'innocent', CodeImportMachineState.ONLINE)
    >>> print(new_machine2.state.name)
    ONLINE

    >>> print(new_events.summary())
    ONLINE innocent


Modifying CodeImportMachine
---------------------------

Directly setting the state information on CodeImportMachines is not
permitted.

    >>> print(new_machine.state.name)
    OFFLINE

    >>> new_machine.state = CodeImportMachineState.ONLINE
    Traceback (most recent call last):
      ...
    zope.security.interfaces.ForbiddenAttribute: ...

Instead, the setOnline() and related methods must be used.  These
methods update the fields and in addition create events in the
CodeImportEvent audit trail.


setOnline
.........

The setOnline method sets the machine's state to ONLINE and records the
corresponding event. It is called when a code-import-controller daemon
goes online.

    >>> new_events = NewEvents()
    >>> new_machine.setOnline()
    >>> print(new_machine.state.name)
    ONLINE

    >>> print(new_events.summary())
    ONLINE frobisher


setOffline
..........

The setOffline method sets the machine's state to OFFLINE and records
the corresponding event. It is called when a code-import-controller
daemon stops, or when the watchdog detects that it has not updated its
heartbeat for some time.

    >>> new_events = NewEvents()
    >>> new_machine.setOffline(CodeImportMachineOfflineReason.STOPPED)
    >>> print(new_machine.state.name)
    OFFLINE

    >>> print(new_events.summary())
    OFFLINE frobisher

    >>> [new_event] = new_events
    >>> print(dict(new_event.items())[CodeImportEventDataType.OFFLINE_REASON])
    STOPPED


setQuiescing
............

The setQuiescing method sets the machine's state to QUIESCING and
records the corresponding event.  A user is passed into the method to be
recorded in the event, and will in almost all cases be a member of the
bazaar experts or more likely a LOSA (administrator).

    >>> login('admin@canonical.com')
    >>> admin = getUtility(ILaunchBag).user

    >>> new_machine.setOnline()
    >>> new_events = NewEvents()
    >>> new_machine.setQuiescing(admin, "1.1.42 rollout")
    >>> print(new_events.summary())
    QUIESCE frobisher name16

    >>> [new_event] = new_events
    >>> print(dict(new_event.items())[CodeImportEventDataType.MESSAGE])
    1.1.42 rollout


Allowed State Transitions
.........................

Not all CodeImportMachine.state transitions are allowed.

The CodeImportMachine.setOffline method needs to be provided a value
from the CodeImportMachineOfflineReason enum. The specific reason value
does not matter to the state machine.

    >>> some_reason = CodeImportMachineOfflineReason.STOPPED

To make the tests more readable, we define a little helper function to
create a new machine with a given state and import the
CodeImportMachineState entries into the local namespace.

    >>> from zope.security.proxy import removeSecurityProxy
    >>> machine_counter = 0
    >>> def new_machine_with_state(state):
    ...     global machine_counter
    ...     new_machine = machine_set.new('machine-%d' % machine_counter)
    ...     machine_counter += 1
    ...     removeSecurityProxy(new_machine).state = state
    ...     return new_machine

    >>> ONLINE = CodeImportMachineState.ONLINE
    >>> OFFLINE = CodeImportMachineState.OFFLINE
    >>> QUIESCING = CodeImportMachineState.QUIESCING

From the OFFLINE state, a machine can only go ONLINE. The setOffline and
setQuiescing methods must fail.

Since our scripts and daemons run at "READ COMMITTED" isolation level,
there are races that we cannot easily detect within the limitation of
SQLObject, when the watchdog process and the controller daemon
concurrently call setOffline. Those undetected races will lead to the
creation of redundant OFFLINE events with different reason values, where
one of the reasons will be WATCHDOG. Those races should not have any
other adverse effect.

If the machine state is already offline, setOffline will defensively
fail, this will usefully detect logic errors where a single thread of
execution makes redundant calls to this method.

    >>> offline_machine = new_machine_with_state(OFFLINE)
    >>> offline_machine.setOffline(some_reason)
    Traceback (most recent call last):
    ...
    AssertionError: State of machine ... was OFFLINE.

Attempting the transition from OFFLINE to QUIESCING is also logic error.

    >>> offline_machine = new_machine_with_state(OFFLINE)
    >>> offline_machine.setQuiescing(admin, "No worky!")
    Traceback (most recent call last):
    ...
    AssertionError: State of machine ... was OFFLINE.

From the ONLINE state, a machine can go OFFLINE or QUIESCING, setOnline
must fail.

    >>> online_machine = new_machine_with_state(ONLINE)
    >>> online_machine.setQuiescing(admin, "Because.")
    >>> print(online_machine.state.name)
    QUIESCING

    >>> online_machine = new_machine_with_state(ONLINE)
    >>> online_machine.setOffline(some_reason)
    >>> print(online_machine.state.name)
    OFFLINE

    >>> online_machine = new_machine_with_state(ONLINE)
    >>> online_machine.setOnline()
    Traceback (most recent call last):
    ...
    AssertionError: State of machine ... was ONLINE.

From the QUIESCING state, a machine can go OFFLINE or ONLINE. The
setQuiescing method must fail.

    >>> quiescing_machine = new_machine_with_state(QUIESCING)
    >>> quiescing_machine.setOnline()
    >>> print(quiescing_machine.state.name)
    ONLINE

    >>> quiescing_machine = new_machine_with_state(QUIESCING)
    >>> quiescing_machine.setQuiescing(admin, "No worky!")
    Traceback (most recent call last):
    ...
    AssertionError: State of machine ... was QUIESCING.

    >>> quiescing_machine = new_machine_with_state(QUIESCING)
    >>> quiescing_machine.setOffline(some_reason)
    >>> print(quiescing_machine.state.name)
    OFFLINE


