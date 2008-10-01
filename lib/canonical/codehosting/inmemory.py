# Copyright 2008 Canonical Ltd.  All rights reserved.

"""In-memory doubles of core codehosting objects."""

__metaclass__ = type
__all__ = [
    'FakeLaunchpadFrontend',
    ]

from xmlrpclib import Fault

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces.branch import BranchType
from canonical.launchpad.interfaces.codehosting import NOT_FOUND_FAULT_CODE
from canonical.launchpad.testing import ObjectFactory
from canonical.launchpad.xmlrpc.codehosting import datetime_from_tuple
from canonical.launchpad.xmlrpc import faults


class FakeStore:
    """Fake store that implements find well enough to pass tests."""

    def __init__(self, object_set):
        self._object_set = object_set

    def find(self, cls, **kwargs):
        branch_id = kwargs.pop('id')
        assert len(kwargs) == 1, (
            'Expected only id and one other. Got %r' % kwargs)
        attribute = kwargs.keys()[0]
        expected_value = kwargs[attribute]
        branch = self._object_set.get(branch_id)
        if branch is None:
            return None
        if expected_value is getattr(branch, attribute):
            return branch
        return None


class FakeDatabaseObject:
    """Base class for fake database objects."""

    def _set_object_set(self, object_set):
        self.__storm_object_info__ = {'store': FakeStore(object_set)}


class ObjectSet:
    """Generic set of database objects."""

    def __init__(self):
        self._objects = []

    def _add(self, db_object):
        self._objects.append(db_object)
        db_object.id = len(self._objects) - 1
        db_object._set_object_set(self)
        return db_object

    def __iter__(self):
        return iter(self._objects)

    def get(self, id):
        try:
            return self._objects[id]
        except IndexError:
            return None

    def getByName(self, name):
        for obj in self:
            if obj.name == name:
                return obj


class FakeBranch(FakeDatabaseObject):

    def __init__(self, branch_type, name, owner, url=None, product=None,
                 stacked_on=None, private=False):
        self.branch_type = branch_type
        self.last_mirror_attempt = None
        self.last_mirrored = None
        self.last_mirrored_id = None
        self.next_mirror_time = None
        self.url = url
        self.mirror_failures = 0
        self.name = name
        self.owner = owner
        self.stacked_on = None
        self.mirror_status_message = None
        self.stacked_on = stacked_on
        self.private = private
        self.product = product

    @property
    def unique_name(self):
        if self.product is None:
            product = '+junk'
        else:
            product = self.product.name
        return '~%s/%s/%s' % (self.owner.name, product, self.name)

    def getPullURL(self):
        pass

    def requestMirror(self):
        self.next_mirror_time = UTC_NOW


class FakePerson(FakeDatabaseObject):

    def __init__(self, name):
        self.name = self.displayname = name


class FakeProduct(FakeDatabaseObject):

    def __init__(self, name):
        self.name = name
        self.development_focus = FakeProductSeries()


class FakeProductSeries(FakeDatabaseObject):

    user_branch = None


class FakeScriptActivity(FakeDatabaseObject):

    def __init__(self, name, hostname, date_started, date_completed):
        self.id = self.name = name
        self.hostname = hostname
        self.date_started = datetime_from_tuple(date_started)
        self.date_completed = datetime_from_tuple(date_completed)


class FakeObjectFactory(ObjectFactory):

    def __init__(self, branch_set, person_set, product_set):
        super(FakeObjectFactory, self).__init__()
        self._branch_set = branch_set
        self._person_set = person_set
        self._product_set = product_set

    def makeBranch(self, branch_type=None, stacked_on=None, private=False,
                   product=None, owner=None):
        if branch_type == BranchType.MIRRORED:
            url = self.getUniqueURL()
        else:
            url = None
        if owner is None:
            owner = self.makePerson()
        branch = FakeBranch(
            branch_type, name=self.getUniqueString(), owner=owner, url=url,
            stacked_on=stacked_on, product=product, private=private)
        self._branch_set._add(branch)
        return branch

    def makePerson(self):
        person = FakePerson(name=self.getUniqueString())
        self._person_set._add(person)
        return person

    def makeProduct(self):
        product = FakeProduct(self.getUniqueString())
        self._product_set._add(product)
        return product


class FakeBranchPuller:

    def __init__(self, branch_set, script_activity_set):
        self._branch_set = branch_set
        self._script_activity_set = script_activity_set

    def _getBranchPullInfo(self, branch):
        default_branch = ''
        if branch.product is not None:
            series = branch.product.development_focus
            user_branch = series.user_branch
            if user_branch is not None:
                default_branch = '/' + user_branch.unique_name
        return (
            branch.id, branch.getPullURL(), branch.unique_name,
            default_branch)

    def getBranchPullQueue(self, branch_type):
        queue = []
        branch_type = BranchType.items[branch_type]
        for branch in self._branch_set:
            if (branch.branch_type == branch_type
                and branch.next_mirror_time < UTC_NOW):
                queue.append(self._getBranchPullInfo(branch))
        return queue

    def startMirroring(self, branch_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirror_attempt = UTC_NOW
        branch.next_mirror_time = None
        return True

    def mirrorComplete(self, branch_id, last_revision_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirrored_id = last_revision_id
        branch.last_mirrored = UTC_NOW
        branch.mirror_failures = 0
        for stacked_branch in self._branch_set:
            if stacked_branch.stacked_on is branch:
                stacked_branch.requestMirror()
        return True

    def mirrorFailed(self, branch_id, reason):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.mirror_failures += 1
        branch.mirror_status_message = reason
        return True

    def recordSuccess(self, name, hostname, date_started, date_completed):
        self._script_activity_set._add(
            FakeScriptActivity(name, hostname, date_started, date_completed))
        return True

    def setStackedOn(self, branch_id, stacked_on_location):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        stacked_on_location = stacked_on_location.rstrip('/')
        for stacked_on_branch in self._branch_set:
            if stacked_on_location == stacked_on_branch.url:
                branch.stacked_on = stacked_on_branch
                break
            if stacked_on_location == '/' + stacked_on_branch.unique_name:
                branch.stacked_on = stacked_on_branch
                break
        else:
            return faults.NoSuchBranch(stacked_on_location)
        return True


class FakeBranchFilesystem:

    def __init__(self, branch_set, product_set):
        self._branch_set = branch_set
        self._product_set = product_set

    def createBranch(self, *args):
        pass

    def requestMirror(self, requester_id, branch_id):
        self._branch_set.get(branch_id).requestMirror()

    def getBranchInformation(self, *args):
        pass

    def getDefaultStackedOnBranch(self, requester_id, product_name):
        if product_name == '+junk':
            return ''
        product = self._product_set.getByName(product_name)
        if product is None:
            return Fault(
                NOT_FOUND_FAULT_CODE,
                'Project %r does not exist.' % (product_name,))
        branch = product.development_focus.user_branch
        if branch is None:
            return ''
        # XXX: This is a terrible replacement for the privacy check, but it
        # makes the tests pass.
        if branch.private and branch.owner.id != requester_id:
            return ''
        return '/' + product.development_focus.user_branch.unique_name


class FakeLaunchpadFrontend:

    def __init__(self):
        self._branch_set = ObjectSet()
        self._script_activity_set = ObjectSet()
        self._person_set = ObjectSet()
        self._product_set = ObjectSet()
        self._puller = FakeBranchPuller(
            self._branch_set, self._script_activity_set)
        self._branchfs = FakeBranchFilesystem(
            self._branch_set, self._product_set)
        self._factory = FakeObjectFactory(
            self._branch_set, self._person_set, self._product_set)

    def getFilesystemEndpoint(self):
        return self._branchfs

    def getPullerEndpoint(self):
        return self._puller

    def getLaunchpadObjectFactory(self):
        return self._factory

    def getBranchSet(self):
        return self._branch_set

    def getLastActivity(self, activity_name):
        return self._script_activity_set.getByName(activity_name)
