-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE GitRepository ALTER COLUMN repository_type SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 80, 2);
