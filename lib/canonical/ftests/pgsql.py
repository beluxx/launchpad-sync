# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

'''
Test harness for tests needing a PostgreSQL backend.
'''

__metaclass__ = type

import os
import random
import time

import psycopg2

from canonical.config import config
from canonical.database.postgresql import (
    generateResetSequencesSQL, resetSequences)


class ConnectionWrapper:
    real_connection = None
    committed = False
    last_execute = None
    dirty = False
    auto_close = True

    def __init__(self, real_connection):
        assert not isinstance(real_connection, ConnectionWrapper), \
                "Wrapped the wrapper!"
        self.real_connection = real_connection
        # Set to True to stop test cleanup forcing the connection closed.
        PgTestSetup.connections.append(self)

    def close(self):
        if self in PgTestSetup.connections:
            PgTestSetup.connections.remove(self)
            self.real_connection.close()

    def rollback(self, InterfaceError=psycopg2.InterfaceError):
        # In our test suites, rollback ends up being called twice in some
        # circumstances. Silently ignoring this is probably not correct,
        # but the alternative is wasting further time chasing this
        # and probably refactoring sqlos and/or zope3
        # -- StuartBishop 2005-01-11
        # Need to store InterfaceError cleverly, otherwise it may have been
        # GCed when the world is being destroyed, leading to an odd
        # AttributeError with
        #   except psycopg2.InterfaceError:
        # -- SteveAlexander 2005-03-22
        try:
            self.real_connection.rollback()
        except InterfaceError:
            pass

    def commit(self):
        # flag that a connection has had commit called. This allows
        # optimizations by subclasses, since if no commit has been made,
        # dropping and recreating the database might be unnecessary
        try:
            return self.real_connection.commit()
        finally:
            ConnectionWrapper.committed = True

    def cursor(self):
        return CursorWrapper(self.real_connection.cursor())

    def __getattr__(self, key):
        return getattr(self.real_connection, key)

    def __setattr__(self, key, val):
        if key in ConnectionWrapper.__dict__.keys():
            return object.__setattr__(self, key, val)
        else:
            return setattr(self.real_connection, key, val)


class CursorWrapper:
    """A wrapper around cursor objects.

    Acts like a normal cursor object, except if CursorWrapper.record_sql is set,
    then queries that pass through CursorWrapper.execute will be appended to
    CursorWrapper.last_executed_sql.  This is useful for tests that want to
    ensure that certain SQL is generated.
    """
    real_cursor = None
    last_executed_sql = []
    record_sql = False

    def __init__(self, real_cursor):
        assert not isinstance(real_cursor, CursorWrapper), \
                "Wrapped the wrapper!"
        self.real_cursor = real_cursor

    def execute(self, *args, **kwargs):
        # Detect if DML has been executed. This method isn't perfect,
        # but should be good enough. In particular, it won't notice
        # data modification made by stored procedures.
        mutating_commands = [
                'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'INTO',
                'TRUNCATE', 'REPLACE',
                ]
        for command in mutating_commands:
            if command in args[0].upper():
                ConnectionWrapper.dirty = True
                break

        # Record the last query executed.
        if CursorWrapper.record_sql:
            CursorWrapper.last_executed_sql.append(args[0])
        return self.real_cursor.execute(*args, **kwargs)

    def __getattr__(self, key):
        return getattr(self.real_cursor, key)

    def __setattr__(self, key, val):
        if key in CursorWrapper.__dict__.keys():
            return object.__setattr__(self, key, val)
        else:
            return setattr(self.real_cursor, key, val)


_org_connect = None
def fake_connect(*args, **kw):
    return ConnectionWrapper(_org_connect(*args, **kw))

def installFakeConnect():
    global _org_connect
    assert _org_connect is None
    _org_connect = psycopg2.connect
    psycopg2.connect = fake_connect

def uninstallFakeConnect():
    global _org_connect
    assert _org_connect is not None
    psycopg2.connect = _org_connect
    _org_connect = None


class PgTestSetup:

    connections = [] # Shared
    # Use a dynamically generated dbname:
    dynamic = object()

    template = 'template1'
    # Needs to match configs/testrunner*/*:
    dbname = 'launchpad_ftest'
    dbuser = None
    host = None
    port = None

    # Class attributes. With PostgreSQL 8.4, pg_shdepend bloats
    # hugely when we drop and create databases, because this
    # operation cancels any autovacuum process maintaining it.
    # To cope, we need to manually vacuum it ourselves occasionally.
    vacuum_shdepend_every = 10
    _vacuum_shdepend_counter = 0

    # (template, name) of last test. Class attribute.
    _last_db = (None, None)
    # Class attribute. True if we should destroy the DB because changes made.
    _reset_db = True

    def __init__(self, template=None, dbname=dynamic, dbuser=None,
            host=None, port=None, reset_sequences_sql=None):
        '''Construct the PgTestSetup

        Note that dbuser is not used for setting up or tearing down
        the database - it is only used by the connect() method
        '''
        if template is not None:
            self.template = template
        if dbname is PgTestSetup.dynamic:
            from canonical.testing.layers import BaseLayer
            if os.environ.get('LP_TEST_INSTANCE'):
                self.dbname = "%s_%s" % (
                    self.__class__.dbname, os.environ.get('LP_TEST_INSTANCE'))
                # Stash the name we use in the config if a writable config is
                # available.
                # Avoid circular imports
                section = """[database]
rw_main_master: dbname=%s
rw_main_slave:  dbname=%s

""" % (self.dbname, self.dbname)
                if BaseLayer.config is not None:
                    BaseLayer.config.add_section(section)
                if BaseLayer.appserver_config is not None:
                    BaseLayer.appserver_config.add_section(section)
            if config.instance_name in (
                BaseLayer.config_name, BaseLayer.appserver_config_name):
                config.reloadConfig()
            else:
                # Fallback to the class name.
                self.dbname = self.__class__.dbname
        elif dbname is not None:
            self.dbname = dbname
        else:
            # Fallback to the class name.
            self.dbname = self.__class__.dbname
        if dbuser is not None:
            self.dbuser = dbuser
        if host is not None:
            self.host = host
        if port is not None:
            self.port = port
        self.reset_sequences_sql = reset_sequences_sql

    def _connectionString(self, dbname, dbuser=None):
        connection_parameters = ['dbname=%s' % dbname]
        if dbuser is not None:
            connection_parameters.append('user=%s' % dbuser)
        if self.host is not None:
            connection_parameters.append('host=%s' % self.host)
        if self.port is not None:
            connection_parameters.append('port=%s' % self.host)
        return ' '.join(connection_parameters)

    def generateResetSequencesSQL(self):
        """Return a SQL statement that resets all sequences."""
        con = psycopg2.connect(self._connectionString(self.dbname))
        cur = con.cursor()
        try:
            return generateResetSequencesSQL(cur)
        finally:
            con.close()

    def setUp(self):
        '''Create a fresh database (dropping the old if necessary)

        Skips db creation if reset_db is False
        '''
        # This is now done globally in test.py
        #installFakeConnect()
        if (self.template, self.dbname) != PgTestSetup._last_db:
            PgTestSetup._reset_db = True
        if not PgTestSetup._reset_db:
            # The database doesn't need to be reset. We reset the sequences
            # anyway (because they might have been incremented even if
            # nothing was committed), making sure not to disturb the
            # 'committed' flag, and we're done.
            con = psycopg2.connect(self._connectionString(self.dbname))
            cur = con.cursor()
            if self.reset_sequences_sql is None:
                resetSequences(cur)
            else:
                cur.execute(self.reset_sequences_sql)
            con.commit()
            con.close()
            ConnectionWrapper.committed = False
            ConnectionWrapper.dirty = False
            return
        self.dropDb()

        # Create the database from the template. We might need to keep
        # trying for a few seconds in case there are connections to the
        # template database that are slow in dropping off.
        attempts = 60
        for counter in range(0, attempts):
            con = psycopg2.connect(self._connectionString(self.template))
            try:
                con.set_isolation_level(0)
                cur = con.cursor()
                try:
                    cur.execute(
                        "CREATE DATABASE %s TEMPLATE=%s "
                        "ENCODING='UNICODE'" % (
                            self.dbname, self.template))
                    break
                except psycopg2.DatabaseError, x:
                    if counter == attempts - 1:
                        raise
                    x = str(x)
                    if 'being accessed by other users' not in x:
                        raise
            finally:
                con.close()
            # Let the other user complete their copying of the template DB.
            time.sleep(random.random())
        ConnectionWrapper.committed = False
        ConnectionWrapper.dirty = False
        PgTestSetup._last_db = (self.template, self.dbname)
        PgTestSetup._reset_db = False

    def tearDown(self):
        '''Close all outstanding connections and drop the database'''
        for con in self.connections[:]:
            if con.auto_close:
                con.close() # Removes itself from self.connections
        if (ConnectionWrapper.committed and ConnectionWrapper.dirty):
            PgTestSetup._reset_db = True
        ConnectionWrapper.committed = False
        ConnectionWrapper.dirty = False
        if PgTestSetup._reset_db:
            self.dropDb()
        #uninstallFakeConnect()

    def connect(self):
        """Get an open DB-API Connection object to a temporary database"""
        con = psycopg2.connect(
            self._connectionString(self.dbname, self.dbuser)
            )
        if isinstance(con, ConnectionWrapper):
            return con
        else:
            return ConnectionWrapper(con)

    def dropDb(self):
        '''Drop the database if it exists.

        Raises an exception if there are open connections
        '''
        attempts = 100
        for i in range(0, attempts):
            try:
                con = psycopg2.connect(self._connectionString(self.template))
            except psycopg2.OperationalError, x:
                if 'does not exist' in x:
                    return
                raise
            try:
                con.set_isolation_level(0)

                # Kill all backend connections if this helper happens to be
                # available. We could create it if it doesn't exist if not
                # always having this is a problem.
                try:
                    cur = con.cursor()
                    cur.execute('SELECT _killall_backends(%s)', [self.dbname])
                except psycopg2.DatabaseError:
                    pass

                # Drop the database, trying for a number of seconds in case
                # connections are slow in dropping off.
                try:
                    cur = con.cursor()
                    cur.execute('DROP DATABASE %s' % self.dbname)
                except psycopg2.DatabaseError, x:
                    if i == attempts - 1:
                        # Too many failures - raise an exception
                        raise
                    if 'being accessed by other users' in str(x):
                        if i < attempts - 1:
                            time.sleep(0.1)
                            continue
                    if 'does not exist' in str(x):
                        break
                    raise
                PgTestSetup._vacuum_shdepend_counter += 1
                if (PgTestSetup._vacuum_shdepend_counter
                    % PgTestSetup.vacuum_shdepend_every) == 0:
                    cur.execute('VACUUM pg_catalog.pg_shdepend')
            finally:
                con.close()
        # Any further setUp's must make a new DB.
        PgTestSetup._reset_db = True

    def force_dirty_database(self):
        """flag the database as being dirty

        This ensures that the database will be recreated for the next test.
        Tearing down the database is done automatically when we detect
        changes. Currently, however, not all changes are detectable (such
        as database changes made from a subprocess.
        """
        PgTestSetup._reset_db = True
