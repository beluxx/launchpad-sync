Ensure that lp.services.database.sqlbase connects as we expect.

    >>> from lp.services.config import config
    >>> from lp.services.database.sqlbase import (
    ...     connect,
    ...     ISOLATION_LEVEL_DEFAULT,
    ...     ISOLATION_LEVEL_SERIALIZABLE,
    ... )

    >>> def do_connect(user, dbname=None, isolation=ISOLATION_LEVEL_DEFAULT):
    ...     con = connect(user=user, dbname=dbname, isolation=isolation)
    ...     cur = con.cursor()
    ...     cur.execute("SHOW session_authorization")
    ...     who = cur.fetchone()[0]
    ...     cur.execute("SELECT current_database()")
    ...     where = cur.fetchone()[0]
    ...     cur.execute("SHOW transaction_isolation")
    ...     how = cur.fetchone()[0]
    ...     print(
    ...         "Connected as %s to %s in %s isolation." % (who, where, how)
    ...     )
    ...

Specifying the user connects as that user.

    >>> do_connect(user=config.launchpad_session.dbuser)
    Connected as session to ... in read committed isolation.

Specifying the database name connects to that database.

    >>> do_connect(user=config.launchpad.dbuser, dbname="launchpad_empty")
    Connected as launchpad_main to launchpad_empty in read committed
    isolation.

Specifying the isolation level works too.

    >>> do_connect(
    ...     user=config.launchpad.dbuser,
    ...     isolation=ISOLATION_LEVEL_SERIALIZABLE,
    ... )
    Connected as launchpad_main to ... in serializable isolation.
