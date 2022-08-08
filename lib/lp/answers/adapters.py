# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters used in the Answer Tracker."""

from typing import List

from lp.answers.interfaces.faqtarget import IFAQTarget

__all__ = []  # type: List[str]


def question_to_questiontarget(question):
    """Adapts an IQuestion to its IQuestionTarget."""
    return question.target


def series_to_questiontarget(series):
    """Adapts an IDistroSeries or IProductSeries into an IQuestionTarget."""
    return series.parent


def sourcepackage_to_questiontarget(sourcepackage):
    """Adapts an ISourcePackage into an IQuestionTarget."""
    return sourcepackage.distribution_sourcepackage


def question_to_faqtarget(question):
    """Adapt an IQuestion into an IFAQTarget.

    It adapts the question's target to IFAQTarget.
    """
    return IFAQTarget(question.target)


def distrosourcepackage_to_faqtarget(distrosourcepackage):
    """Adapts an `IDistributionSourcePackage` into an `IFAQTarget`."""
    return distrosourcepackage.distribution


def sourcepackage_to_faqtarget(sourcepackage):
    """Adapts an `ISourcePackage` into an `IFAQTarget`."""
    return sourcepackage.distribution


def faq_to_faqtarget(faq):
    """Adapts an `IFAQ` into an `IFAQTarget`."""
    return faq.target
