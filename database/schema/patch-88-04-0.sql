SET client_min_messages=ERROR;
ALTER TABLE BugWatch ADD COLUMN last_error_type integer;
INSERT INTO LaunchpadDatabaseRevision VALUES (88, 04, 0);
