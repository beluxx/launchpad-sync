Retrieving bug tasks
*********************

The IBugTaskSet interface provide a couple of methods for retrieving
IBugTask instances. For convenience, Launchpad provides a default
implementation of IBugTaskSet, allowing retrieval of any bug task in
Launchpad. We'll use this implementation for demonstration purposes:

    >>> from lp.bugs.interfaces.bugtask import (
    ...     IBugTask,
    ...     IBugTaskSet,
    ... )
    >>> from lp.services.database.interfaces import IStore
    >>> task_set = getUtility(IBugTaskSet)


Retrieving a single bug task
*****************************

The IBugTaskSet get method retrieves a single bug task matching a given
ID:

    >>> retrieved_task = task_set.get(2)
    >>> retrieved_task
    <BugTask ...>

    >>> from lp.testing import verifyObject
    >>> verifyObject(IBugTask, retrieved_task)
    True

    <<< retrieved_task.id
    2

When given a bug task ID that doesn't exist in the database, the method
raises a NotFoundError:

    >>> no_such_task = task_set.get(0)
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...


Retrieving multiple bug tasks
******************************

The IBugTaskSet getMultiple method can retrieve multiple bug tasks in a
single operation. To demonstrate, we'll begin by generating a list of
sample bug tasks:

    >>> from lp.bugs.model.bugtask import BugTask
    >>> store = IStore(BugTask)
    >>> sample_task_count = 10
    >>> sample_tasks = store.find(BugTask)[:sample_task_count]
    >>> sample_task_ids = [task.id for task in sample_tasks]

When given a sequence of bug task IDs, the method returns a dictionary
of bug tasks indexed by bug task ID. The dictionary contains an entry
for every bug task ID from the given sequence that also matches a bug
task in the database:

    >>> retrieved_tasks = task_set.getMultiple(sample_task_ids)
    >>> assert len(retrieved_tasks) == sample_task_count
    >>> for task in sample_tasks:
    ...     assert retrieved_tasks[task.id].id == task.id
    ...

When given a singleton sequence containing a valid bug task ID, the
method returns a singleton dictionary:

    >>> task_set.getMultiple([2])
    {2: <BugTask ...>}

When given an empty sequence, the method returns an empty dictionary:

    >>> task_set.getMultiple([])
    {}

When given a sequence containing some bug task IDs not present in the
database, the method returns a dictionary containing entries only for
those bug task IDs that are present in the database:

    >>> task_set.getMultiple([1, 2])
    {2: <BugTask ...>}

    >>> task_set.get(1)
    Traceback (most recent call last):
    ...
    lp.app.errors.NotFoundError: ...
    >>> task_set.get(2)
    <BugTask ...>

When given an argument that isn't a valid sequence, or a sequence
containing one or more entries that aren't valid bug task IDs, the
method raises errors appropriately:

    >>> task_set.getMultiple(None)
    Traceback (most recent call last):
    ...
    TypeError: ...
    >>> print(task_set.getMultiple(["1; DROP TABLE person;"]))
    Traceback (most recent call last):
    ...
    ValueError: ...
