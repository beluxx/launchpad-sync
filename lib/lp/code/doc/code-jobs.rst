Code Jobs
=========

The addition of the Job table provides a generic way to have server side jobs
processing events generated from the web UI.

Branch Jobs
-----------

This type of job processes events that have been generated for branches.

 BranchJobType:
   REVISION - sending revision/diff email from scanner
   ATTRIBUTE - attribute changes from web ui / api
   IMPORT - code import email

If there were no subscribers at the time the event was generated, no job is
created.

The BranchJob table has a json_data field to hold details specific
to the particular type of subscription job.

BranchJobType.REVISION
......................

The json data would hold:
  from_revno - the first revision number to process
  from_revid - the revision id of the from revno
  to_revno - the last revision number to process
  to_revid - the revision id of the to revno

BranchJobType.ATTRIBUTE
.......................

The json data would hold the from and to values of the change, and for values
where we only show the new values, it would hold those too.

BranchJobType.IMPORT
....................

The json data here would effectively store the text of the message.  Used
primarily in the status changes on the import job itself.  Perhaps this should
be combined with the attribute type email and have a general preamble for the
generated email.

Branch Merge Proposal Jobs
--------------------------

Jobs for merge proposals are slightly different from individual branch
subscription based emails as merge proposal jobs end up sending emails to
subscribers of both the source and target branches.

  BranchMergeProposalJobType:
    NEW - A new merge proposal has been created
    COMMENT - A new comment has been made on the proposal
    NEW_REVIEWER - A review has been requested for a person or team
    DIFF_GENERATION - A new dynamic diff needs to be generated

Each job also has some optional json data.

BranchMergeProposalJobType.NEW
..............................

The json data includes the identity of the initial comment if one was made,
and the initial reviewer if one was requested.


BranchMergeProposalJobType.COMMENT
..................................

The json data here refers to the identity of the commit message.

BranchMergeProposalJobType.NEW_REVIEWER
.......................................

The json data here refers to the new reviewer and the type of review
requested.

BranchMergeProposalJobType.DIFF_GENERATION
..........................................

The dynamic moving diff has been determined to be out of date, and a new diff
needs to be generated.  This is processed by the merge analysis daemon.

