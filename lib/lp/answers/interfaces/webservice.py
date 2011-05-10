# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="lp.answers.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

__all__ = [
    'IQuestion',
    'IQuestionSet',
    ]

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED

from canonical.launchpad.components.apihelpers import patch_entry_return_type
from lp.answers.interfaces.question import IQuestion
from lp.answers.interfaces.questioncollection import IQuestionSet


IQuestionSet.queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['collection_entry_schema'] = IQuestion
patch_entry_return_type(IQuestionSet, 'get', IQuestion)
