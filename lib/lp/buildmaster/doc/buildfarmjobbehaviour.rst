BuildFarmJobBehaviour
====================

The Launchpad build farm was originally designed for building binary
packages from source packages, but was subsequently generalised to support
other types of build farm jobs.

The `BuildFarmJobBehaviour` class encapsulates job-type-specific behaviour
with a standard interface to which our generic IBuilder class delegates.
The result is that neither our generic IBuilder class or any call-sites
(such as the build master) need any knowledge of different job types or
how to handle them.


Creating a new behaviour
-----------------------

A new behaviour should implement the `IBuildFarmJobBehaviour` interface
and extend BuildFarmJobBehaviourBase. A new behaviour will only be required
to define one method - dispatchBuildToWorker() - to correctly implement
the interface, but will usually want to customise the other properties and
methods as well.

    >>> from lp.buildmaster.interfaces.buildfarmjobbehaviour import (
    ...     IBuildFarmJobBehaviour,
    ... )
    >>> from lp.buildmaster.model.buildfarmjobbehaviour import (
    ...     BuildFarmJobBehaviourBase,
    ... )
    >>> from zope.interface import implementer

    >>> @implementer(IBuildFarmJobBehaviour)
    ... class MyNewBuildBehaviour(BuildFarmJobBehaviourBase):
    ...     """A custom build behaviour for building blah."""
    ...
    ...     def dispatchBuildToWorker(self, logger):
    ...         print("Did something special to dispatch MySpecialBuild.")

For this documentation, we'll also need a dummy new build farm job.

    >>> from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJob
    >>> class IMyNewBuildFarmJob(IBuildFarmJob):
    ...     """Normally defines job-type specific database fields."""
    ...
    >>> @implementer(IMyNewBuildFarmJob)
    ... class MyNewBuildFarmJob:
    ...     pass

Custom behaviours are not normally instantiated directly, instead an adapter
is specified for the specific IBuildFarmJob. Normally we'd add some ZCML to
adapt our specific build farm job to its behaviour like:

    <!-- MyNewBuildBehaviour -->
    <adapter
        for="lp.myapp.interfaces.mynewbuildfarmjob.IMyNewBuildFarmJob"
        provides="lp.buildmaster.interfaces.buildfarmjobbehaviour.\
                  IBuildFarmJobBehaviour"
        factory="lp.myapp.model.mynewbuildbehaviour.MyNewBuildBehaviour"
        permission="zope.Public" />

But for the sake of this documentation we'll add the adapter manually.

    >>> from zope.component import provideAdapter
    >>> provideAdapter(
    ...     MyNewBuildBehaviour, (IMyNewBuildFarmJob,), IBuildFarmJobBehaviour
    ... )

This will then allow the builder to request and set the required behaviour
from the current job. Bob the builder currently has a binary package job and
so finds itself with a binary package build behaviour which defines
binary-build specific information.

    >>> from lp.buildmaster.model.builder import Builder
    >>> from lp.services.database.interfaces import IStore
    >>> bob = IStore(Builder).find(Builder, Builder.name == "bob").one()

Once the builder has the relevant behaviour, it is able to provide both
general builder functionality of its own accord, while delegating any
build-type specific functionality to the behaviour.

The IBuildFarmJobBehaviour interface currently provides customisation points
throughout the build life-cycle, from logging the start of a build, verifying
that the provided queue item is ready to be built, dispatching the build etc.,
and allows further customisation to be added easily.

Please refer to the IBuildFarmJobBehaviour interface to see the currently
provided build-type specific customisation points.
