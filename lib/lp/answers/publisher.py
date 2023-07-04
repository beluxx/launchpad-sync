# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Answers's custom publication."""

__all__ = [
    "AnswersBrowserRequest",
    "AnswersFacet",
    "AnswersLayer",
    "answers_request_publication_factory",
]


from zope.interface import implementer
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from lp.services.webapp.interfaces import IFacet
from lp.services.webapp.publication import LaunchpadBrowserPublication
from lp.services.webapp.servers import (
    LaunchpadBrowserRequest,
    VHostWebServiceRequestPublicationFactory,
)


@implementer(IFacet)
class AnswersFacet:
    name = "answers"
    rootsite = "answers"
    text = "Questions"
    default_view = "+questions"


class AnswersLayer(IDefaultBrowserLayer):
    """The Answers layer."""


@implementer(AnswersLayer)
class AnswersBrowserRequest(LaunchpadBrowserRequest):
    """Instances of AnswersBrowserRequest provide `AnswersLayer`."""

    def __init__(self, body_instream, environ, response=None):
        super().__init__(body_instream, environ, response)
        # Many of the responses from Answers vary based on language.
        self.response.setHeader(
            "Vary", "Cookie, Authorization, Accept-Language"
        )


def answers_request_publication_factory():
    return VHostWebServiceRequestPublicationFactory(
        "answers", AnswersBrowserRequest, LaunchpadBrowserPublication
    )
