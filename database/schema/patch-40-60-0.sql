set client_min_messages=ERROR;

-- Creates a field to know the distrorelease that we should be translating as the main target.
ALTER TABLE Distribution ADD COLUMN translation_target integer REFERENCES DistroRelease(id);
UPDATE Distribution
SET translation_target = (
    SELECT id
    FROM DistroRelease
    WHERE DistroRelease.distribution = Distribution.id AND
          DistroRelease.datereleased IS NOT NULL
    ORDER BY DistroRelease.datereleased DESC LIMIT 1)
WHERE name = 'ubuntu';

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 60, 0);
