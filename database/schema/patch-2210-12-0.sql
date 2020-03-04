-- Copyright 2020 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;


ALTER TABLE binarypackagepublishinghistory
    ADD COLUMN creator INT REFERENCES person;

CREATE INDEX binarypackagepublishinghistory__creator__idx ON
    binarypackagepublishinghistory(creator) WHERE creator IS NOT NULL;


INSERT INTO LaunchpadDatabaseRevision VALUES (2210, 12, 0);

