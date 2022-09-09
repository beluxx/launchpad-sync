The CodeImportScheduler
=======================

The code import scheduler is an XMLRPC service that provides (ids of)
CodeImportJobs for code import workers to run.  It is available as the
codeimportscheduler attribute of our private XMLRPC instance.

    >>> from lp.code.interfaces.codeimportscheduler import (
    ...     ICodeImportSchedulerApplication,
    ... )
    >>> from lp.xmlrpc.interfaces import IPrivateApplication
    >>> from lp.testing import verifyObject

    >>> private_root = getUtility(IPrivateApplication)
    >>> verifyObject(
    ...     ICodeImportSchedulerApplication, private_root.codeimportscheduler
    ... )
    True

The CodeImportSchedulerAPI view provides the ICodeImportScheduler
XML-RPC API:

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.code.interfaces.codeimportscheduler import (
    ...     ICodeImportScheduler,
    ... )
    >>> from lp.code.xmlrpc.codeimportscheduler import CodeImportSchedulerAPI

    >>> codeimportscheduler_api = CodeImportSchedulerAPI(
    ...     private_root.codeimportscheduler, LaunchpadTestRequest()
    ... )
    >>> verifyObject(ICodeImportScheduler, codeimportscheduler_api)
    True

The ICodeImportScheduler interface defines a single method,
getJobForMachine(), that returns the id of the job that the code
import worker should next run.

    >>> codeimportscheduler_api.getJobForMachine("bazaar-importer", 2)
    1

The method just calls the 'getJobForMachine' method from the
ICodeImportJobSet interface, and tests all the details of what it does
can be found in the tests for ICodeImportJobSet.

The point of all this is for it to be accessed over XMLRPC.

    >>> import xmlrpc.client
    >>> from lp.testing.xmlrpc import XMLRPCTestTransport
    >>> codeimportscheduler = xmlrpc.client.ServerProxy(
    ...     "http://xmlrpc-private.launchpad.test:8087/codeimportscheduler",
    ...     transport=XMLRPCTestTransport(),
    ... )
    >>> codeimportscheduler.getJobForMachine("bazaar-importer", 2)
    0

This includes the behaviour of auto-creating machine rows for
previously unseen hostnames.

    >>> from lp.code.interfaces.codeimportmachine import ICodeImportMachineSet
    >>> print(
    ...     getUtility(ICodeImportMachineSet).getByHostname(
    ...         "doesnt-exist-yet"
    ...     )
    ... )
    None
    >>> codeimportscheduler.getJobForMachine("doesnt-exist-yet", 1)
    0
    >>> new_machine = getUtility(ICodeImportMachineSet).getByHostname(
    ...     "doesnt-exist-yet"
    ... )
    >>> print(new_machine.hostname)
    doesnt-exist-yet
    >>> new_machine.state.name
    'ONLINE'
