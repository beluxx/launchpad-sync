-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

ALTER TABLE SourcePackagePublishingHistory ADD COLUMN sourcepackagename INTEGER;
ALTER TABLE BinaryPackagePublishingHistory ADD COLUMN binarypackagename INTEGER;

-- INDICES?

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

