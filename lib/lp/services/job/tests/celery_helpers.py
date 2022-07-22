# Copyright 2012-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ["noop", "pop_notifications"]

from celery.task import task

# Force the correct celeryconfig to be used.
import lp.services.job.celeryjob

# Quiet lint unused import warning.
lp.services.job.celeryjob


@task
def pop_notifications():
    from lp.testing.mail_helpers import pop_notifications

    return [message.as_string() for message in pop_notifications()]


@task
def noop():
    """Task that does nothing.

    Used to ensure that other tasks have completed.
    """
