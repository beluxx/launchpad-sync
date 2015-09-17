-- Copyright 2015 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE TABLE CrossReference (
    object1_id text NOT NULL,
    object2_id text NOT NULL,
    creator text,
    date_created timestamp without time zone
        DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') NOT NULL,
    metadata text,
    PRIMARY KEY (object1_id, object2_id)
);

CREATE UNIQUE INDEX crossreference__object2_id__object1_id__key
    ON CrossReference(object2_id, object1_id);

CREATE INDEX crossreference__creator__idx ON CrossReference(creator);

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 70, 0);
