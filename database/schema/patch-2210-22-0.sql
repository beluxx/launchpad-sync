-- Copyright 2020 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- This patch can be applied "cold", in a "fast-downtime" way. It basically
-- adds the new OCI database columns, and rename current indexes so they can be
-- removed and replaced with new ones that includes the new columns.

ALTER TABLE BugTask
    ADD COLUMN ociproject integer REFERENCES ociproject,
    ADD COLUMN ociprojectseries integer REFERENCES ociprojectseries,
    DROP CONSTRAINT bugtask_assignment_checks,
    ADD CONSTRAINT bugtask_assignment_checks CHECK (
        CASE
            WHEN product IS NOT NULL THEN productseries IS NULL AND distribution IS NULL AND distroseries IS NULL AND sourcepackagename IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN productseries IS NOT NULL THEN distribution IS NULL AND distroseries IS NULL AND sourcepackagename IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN distribution IS NOT NULL THEN distroseries IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN distroseries IS NOT NULL THEN ociproject IS NULL AND ociprojectseries IS NULL
            WHEN ociproject IS NOT NULL THEN ociprojectseries IS NULL
            WHEN ociprojectseries IS NOT NULL THEN true
            ELSE false
        END);

ALTER INDEX bugtask_distinct_sourcepackage_assignment
    RENAME TO old__bugtask_distinct_sourcepackage_assignment;

ALTER TABLE BugTaskFlat
    ADD COLUMN ociproject integer,
    ADD COLUMN ociprojectseries integer;

ALTER TABLE BugSummary
    ADD COLUMN ociproject integer REFERENCES ociproject,
    ADD COLUMN ociprojectseries integer REFERENCES ociprojectseries,
    DROP CONSTRAINT bugtask_assignment_checks,
    ADD CONSTRAINT bugtask_assignment_checks CHECK (
        CASE
            WHEN product IS NOT NULL THEN productseries IS NULL AND distribution IS NULL AND distroseries IS NULL AND sourcepackagename IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN productseries IS NOT NULL THEN distribution IS NULL AND distroseries IS NULL AND sourcepackagename IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN distribution IS NOT NULL THEN distroseries IS NULL AND ociproject IS NULL AND ociprojectseries IS NULL
            WHEN distroseries IS NOT NULL THEN ociproject IS NULL AND ociprojectseries IS NULL
            WHEN ociproject IS NOT NULL THEN ociprojectseries IS NULL
            WHEN ociprojectseries IS NOT NULL THEN true
            ELSE false
        END);

ALTER INDEX bugsummary__unique
    RENAME TO old__bugsummary__unique;

ALTER TABLE BugSummaryJournal
    ADD COLUMN ociproject integer,
    ADD COLUMN ociprojectseries integer;

-- Functions

CREATE OR REPLACE FUNCTION bugtask_flatten(task_id integer, check_only boolean)
    RETURNS boolean
    LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
    AS $$
DECLARE
    bug_row Bug%ROWTYPE;
    task_row BugTask%ROWTYPE;
    old_flat_row BugTaskFlat%ROWTYPE;
    new_flat_row BugTaskFlat%ROWTYPE;
    _product_active boolean;
    _access_policies integer[];
    _access_grants integer[];
BEGIN
    -- This is the master function to update BugTaskFlat, but there are
    -- maintenance triggers and jobs on the involved tables that update
    -- it directly. Any changes here probably require a corresponding
    -- change in other trigger functions.

    SELECT * INTO task_row FROM BugTask WHERE id = task_id;
    SELECT * INTO old_flat_row FROM BugTaskFlat WHERE bugtask = task_id;

    -- If the task doesn't exist, ensure that there's no flat row.
    IF task_row.id IS NULL THEN
        IF old_flat_row.bugtask IS NOT NULL THEN
            IF NOT check_only THEN
                DELETE FROM BugTaskFlat WHERE bugtask = task_id;
            END IF;
            RETURN FALSE;
        ELSE
            RETURN TRUE;
        END IF;
    END IF;

    SELECT * FROM bug INTO bug_row WHERE id = task_row.bug;

    -- If it's a product(series) task, we must consult the active flag.
    IF task_row.product IS NOT NULL THEN
        SELECT product.active INTO _product_active
            FROM product WHERE product.id = task_row.product LIMIT 1;
    ELSIF task_row.productseries IS NOT NULL THEN
        SELECT product.active INTO _product_active
            FROM
                product
                JOIN productseries ON productseries.product = product.id
            WHERE productseries.id = task_row.productseries LIMIT 1;
    END IF;

    SELECT policies, grants
        INTO _access_policies, _access_grants
        FROM bug_build_access_cache(bug_row.id, bug_row.information_type)
            AS (policies integer[], grants integer[]);

    -- Compile the new flat row.
    SELECT task_row.id, bug_row.id, task_row.datecreated,
           bug_row.duplicateof, bug_row.owner, bug_row.fti,
           bug_row.information_type, bug_row.date_last_updated,
           bug_row.heat, task_row.product, task_row.productseries,
           task_row.distribution, task_row.distroseries,
           task_row.sourcepackagename, task_row.status,
           task_row.importance, task_row.assignee,
           task_row.milestone, task_row.owner,
           COALESCE(_product_active, TRUE),
           _access_policies,
           _access_grants,
           bug_row.latest_patch_uploaded, task_row.date_closed,
           task_row.ociproject, task_row.ociprojectseries
           INTO new_flat_row;

    -- Calculate the necessary updates.
    IF old_flat_row.bugtask IS NULL THEN
        IF NOT check_only THEN
            INSERT INTO BugTaskFlat VALUES (new_flat_row.*);
        END IF;
        RETURN FALSE;
    ELSIF new_flat_row != old_flat_row THEN
        IF NOT check_only THEN
            UPDATE BugTaskFlat SET
                bug = new_flat_row.bug,
                datecreated = new_flat_row.datecreated,
                duplicateof = new_flat_row.duplicateof,
                bug_owner = new_flat_row.bug_owner,
                fti = new_flat_row.fti,
                information_type = new_flat_row.information_type,
                date_last_updated = new_flat_row.date_last_updated,
                heat = new_flat_row.heat,
                product = new_flat_row.product,
                productseries = new_flat_row.productseries,
                distribution = new_flat_row.distribution,
                distroseries = new_flat_row.distroseries,
                sourcepackagename = new_flat_row.sourcepackagename,
                status = new_flat_row.status,
                importance = new_flat_row.importance,
                assignee = new_flat_row.assignee,
                milestone = new_flat_row.milestone,
                owner = new_flat_row.owner,
                active = new_flat_row.active,
                access_policies = new_flat_row.access_policies,
                access_grants = new_flat_row.access_grants,
                date_closed = new_flat_row.date_closed,
                latest_patch_uploaded = new_flat_row.latest_patch_uploaded,
                ociproject = new_flat_row.ociproject,
                ociprojectseries = new_flat_row.ociprojectseries
                WHERE bugtask = new_flat_row.bugtask;
        END IF;
        RETURN FALSE;
    ELSE
        RETURN TRUE;
    END IF;
END;
$$;


CREATE OR REPLACE FUNCTION bug_summary_inc(d bugsummary) RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    -- Shameless adaption from postgresql manual
    LOOP
        -- first try to update the row
        UPDATE BugSummary SET count = count + d.count
        WHERE
            ((product IS NULL AND $1.product IS NULL)
                OR product = $1.product)
            AND ((productseries IS NULL AND $1.productseries IS NULL)
                OR productseries = $1.productseries)
            AND ((distribution IS NULL AND $1.distribution IS NULL)
                OR distribution = $1.distribution)
            AND ((distroseries IS NULL AND $1.distroseries IS NULL)
                OR distroseries = $1.distroseries)
            AND ((sourcepackagename IS NULL AND $1.sourcepackagename IS NULL)
                OR sourcepackagename = $1.sourcepackagename)
            AND ((ociproject IS NULL AND $1.ociproject IS NULL)
                OR ociproject = $1.ociproject)
            AND ((ociprojectseries IS NULL AND $1.ociprojectseries IS NULL)
                OR ociprojectseries = $1.ociprojectseries)
            AND ((viewed_by IS NULL AND $1.viewed_by IS NULL)
                OR viewed_by = $1.viewed_by)
            AND ((tag IS NULL AND $1.tag IS NULL)
                OR tag = $1.tag)
            AND status = $1.status
            AND ((milestone IS NULL AND $1.milestone IS NULL)
                OR milestone = $1.milestone)
            AND importance = $1.importance
            AND has_patch = $1.has_patch
            AND access_policy IS NOT DISTINCT FROM $1.access_policy;
        IF found THEN
            RETURN;
        END IF;
        -- not there, so try to insert the key
        -- if someone else inserts the same key concurrently,
        -- we could get a unique-key failure
        BEGIN
            INSERT INTO BugSummary(
                count, product, productseries, distribution,
                distroseries, sourcepackagename,
                ociproject, ociprojectseries,
                viewed_by, tag,
                status, milestone, importance, has_patch, access_policy)
            VALUES (
                d.count, d.product, d.productseries, d.distribution,
                d.distroseries, d.sourcepackagename,
                d.ociproject, d.ociprojectseries,
                d.viewed_by, d.tag,
                d.status, d.milestone, d.importance, d.has_patch,
                d.access_policy);
            RETURN;
        EXCEPTION WHEN unique_violation THEN
            -- do nothing, and loop to try the UPDATE again
        END;
    END LOOP;
END;

$$;


CREATE OR REPLACE FUNCTION bugtask_maintain_bugtaskflat_trig()
    RETURNS trigger
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'public'
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM bugtask_flatten(NEW.id, FALSE);
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.bug != OLD.bug THEN
            RAISE EXCEPTION 'cannot move bugtask to a different bug';
        ELSIF (NEW.product IS DISTINCT FROM OLD.product
            OR NEW.productseries IS DISTINCT FROM OLD.productseries) THEN
            -- product.active may differ. Do a full update.
            PERFORM bugtask_flatten(NEW.id, FALSE);
        ELSIF (
            NEW.datecreated IS DISTINCT FROM OLD.datecreated
            OR NEW.product IS DISTINCT FROM OLD.product
            OR NEW.productseries IS DISTINCT FROM OLD.productseries
            OR NEW.distribution IS DISTINCT FROM OLD.distribution
            OR NEW.distroseries IS DISTINCT FROM OLD.distroseries
            OR NEW.sourcepackagename IS DISTINCT FROM OLD.sourcepackagename
            OR NEW.ociproject IS DISTINCT FROM OLD.ociproject
            OR NEW.ociprojectseries IS DISTINCT FROM OLD.ociprojectseries
            OR NEW.status IS DISTINCT FROM OLD.status
            OR NEW.importance IS DISTINCT FROM OLD.importance
            OR NEW.assignee IS DISTINCT FROM OLD.assignee
            OR NEW.milestone IS DISTINCT FROM OLD.milestone
            OR NEW.owner IS DISTINCT FROM OLD.owner
            OR NEW.date_closed IS DISTINCT FROM OLD.date_closed) THEN
            -- Otherwise just update the columns from bugtask.
            -- Access policies and grants may have changed due to target
            -- transitions, but an earlier trigger will already have
            -- mirrored them to all relevant flat tasks.
            UPDATE BugTaskFlat SET
                datecreated = NEW.datecreated,
                product = NEW.product,
                productseries = NEW.productseries,
                distribution = NEW.distribution,
                distroseries = NEW.distroseries,
                sourcepackagename = NEW.sourcepackagename,
                ociproject = NEW.ociproject,
                ociprojectseries = NEW.ociprojectseries,
                status = NEW.status,
                importance = NEW.importance,
                assignee = NEW.assignee,
                milestone = NEW.milestone,
                owner = NEW.owner,
                date_closed = NEW.date_closed
                WHERE bugtask = NEW.id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        PERFORM bugtask_flatten(OLD.id, FALSE);
    END IF;
    RETURN NULL;
END;
$$;

DROP FUNCTION bugsummary_targets;
CREATE OR REPLACE FUNCTION bugsummary_targets(btf_row public.bugtaskflat)
    RETURNS TABLE(
        product integer,
        productseries integer,
        distribution integer,
        distroseries integer,
        sourcepackagename integer,
        ociproject integer,
        ociprojectseries integer
    )
    LANGUAGE sql IMMUTABLE
    AS $_$
    -- Include a sourcepackagename-free task if this one has a
    -- sourcepackagename, so package tasks are also counted in their
    -- distro/series.
    -- XXX what about pillar for ociprojects?
    SELECT
        $1.product, $1.productseries, $1.distribution,
        $1.distroseries, $1.sourcepackagename,
        $1.ociproject, $1.ociprojectseries
    UNION -- Implicit DISTINCT
    SELECT
        $1.product, $1.productseries, $1.distribution,
        $1.distroseries, NULL,
        $1.ociproject, $1.ociprojectseries;
$_$;

CREATE OR REPLACE FUNCTION bugsummary_locations(
        btf_row bugtaskflat, tags text[])
    RETURNS SETOF bugsummaryjournal
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF btf_row.duplicateof IS NOT NULL THEN
        RETURN;
    END IF;
    RETURN QUERY
        SELECT
            CAST(NULL AS integer) AS id,
            CAST(1 AS integer) AS count,
            bug_targets.product, bug_targets.productseries,
            bug_targets.distribution, bug_targets.distroseries,
            bug_targets.sourcepackagename,
            bug_viewers.viewed_by, bug_tags.tag, btf_row.status,
            btf_row.milestone, btf_row.importance,
            btf_row.latest_patch_uploaded IS NOT NULL AS has_patch,
            bug_viewers.access_policy,
            bug_targets.ociproject, bug_targets.ociprojectseries
        FROM
            bugsummary_targets(btf_row) AS bug_targets,
            unnest(tags) AS bug_tags (tag),
            bugsummary_viewers(btf_row) AS bug_viewers;
END;
$$;

CREATE OR REPLACE FUNCTION bugsummary_insert_journals(
        journals bugsummaryjournal[])
    RETURNS void
    LANGUAGE sql
    AS $$
    -- We sum the rows here to minimise the number of inserts into the
    -- journal, as in the case of UPDATE statement we may have -1s and +1s
    -- cancelling each other out.
    INSERT INTO BugSummaryJournal(
            count, product, productseries, distribution,
            distroseries, sourcepackagename, ociproject, ociprojectseries,
            viewed_by, tag, status, milestone, importance, has_patch,
            access_policy)
        SELECT
            SUM(count), product, productseries, distribution,
            distroseries, sourcepackagename, ociproject, ociprojectseries,
            viewed_by, tag, status, milestone, importance, has_patch,
            access_policy
        FROM unnest(journals)
        GROUP BY
            product, productseries, distribution,
            distroseries, sourcepackagename, ociproject, ociprojectseries,
            viewed_by, tag, status, milestone, importance, has_patch,
            access_policy
        HAVING SUM(count) != 0;
$$;

INSERT INTO LaunchpadDatabaseRevision VALUES (2210, 22, 0);
