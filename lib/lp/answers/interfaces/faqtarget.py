# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for things that can host IFAQ."""

__all__ = [
    "IFAQTarget",
]


from lazr.restful.declarations import exported_as_webservice_entry

from lp.answers.interfaces.faqcollection import IFAQCollection


@exported_as_webservice_entry("faq_target", as_of="beta")
class IFAQTarget(IFAQCollection):
    """An object that can contain a FAQ document."""

    def newFAQ(owner, title, content, keywords=None, date_created=None):
        """Create a new FAQ hosted in this target.

        :param owner: The `IPerson` creating the FAQ document.
        :param title: The document's title.
        :param content: The document's content.
        :param keywords: The document's keywords.
        :param date_created: The creation time of the document.
            Defaults to now.
        """

    def findSimilarFAQs(summary):
        """Return FAQs contained in this target similar to summary.

        Return a list of FAQs similar to the summary provided. These
        FAQs should be found using a fuzzy search. The list should be
        ordered from the most similar FAQ to the least similar FAQ

        :param summary: A summary phrase.
        """
