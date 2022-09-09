Managing the Sprint Agenda
==========================

It is possible to use Blueprint to manage the agenda of a sprint or meeting.
Essentially, there is a two-stage process whereby people can nominate topics
to the sprint agenda, and then the organising committee can approve or
decline those topics.

First, lets get hold of some people, a product, a sprint and a spec.

    >>> from lp.registry.model.person import PersonSet
    >>> from lp.registry.model.product import ProductSet
    >>> upstream_firefox = ProductSet()["firefox"]
    >>> canvas = upstream_firefox.getSpecification("canvas")
    >>> guacamole = factory.makeSprint(name="uds-guacamole")
    >>> danner = PersonSet().getByName("danner")
    >>> jblack = PersonSet().getByName("jblack")

Now, we should be able to see the list of sprints for the spec:

    >>> print(list(canvas.sprints))
    []

And we should be able to propose the spec for the agenda:

    >>> sl = canvas.linkSprint(guacamole, jblack)
    >>> for sprint in canvas.sprints:
    ...     print(sprint.name)
    ...
    uds-guacamole
    >>> print(sl.registrant.name, sl.status.title)
    jblack Proposed
    >>> print(sl.decider, sl.date_decided)
    None None

Now, it should be possible to accept the proposal. That should set the
status accordingly and also update the decider and the date_decided.

    >>> sl.acceptBy(danner)
    >>> print(sl.status.title, sl.decider.name, sl.date_decided is not None)
    Accepted danner True

It is possible to revise your choice, declining the spec. This should update
the date_decided.

    >>> from storm.store import Store
    >>> from lp.services.database.sqlbase import get_transaction_timestamp
    >>> transaction_timestamp = get_transaction_timestamp(Store.of(sl))

    # Nobody is allowed to write directly to SprintSpecification.date_decided,
    # so we need to remove its security proxy here.
    >>> from zope.security.proxy import removeSecurityProxy
    >>> removeSecurityProxy(sl).date_decided = None
    >>> sl.declineBy(jblack)
    >>> print(sl.status.title, sl.decider.name, sl.date_decided is not None)
    Declined jblack True
    >>> print(sl.date_decided == transaction_timestamp)
    True
