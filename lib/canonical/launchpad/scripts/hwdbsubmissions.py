# Copyright 2007, 2008 Canonical Ltd.  All rights reserved.

"""Parse Hardware Database submissions.

Base classes, intended to be used both for the commercial certification
data and for the community test submissions.
"""


__all__ = [
           'SubmissionParser',
           'process_pending_submissions',
          ]


import bz2
from cStringIO import StringIO
from datetime import datetime, timedelta
from logging import getLogger
import os
import re
import sys
import cElementTree as etree

import pytz

from zope.component import getUtility
from zope.interface import implements

from canonical.lazr.xml import RelaxNGValidator

from canonical.config import config
from canonical.launchpad.interfaces.hwdb import (
    HWBus, HWSubmissionProcessingStatus, IHWDeviceDriverLinkSet, IHWDeviceSet,
    IHWDriverSet, IHWSubmissionDeviceSet, IHWSubmissionSet, IHWVendorIDSet,
    IHWVendorNameSet)
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import LoopTuner
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)

_relax_ng_files = {
    '1.0': 'hardware-1_0.rng', }

_time_regex = re.compile(r"""
    ^(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)
    T(?P<hour>\d\d):(?P<minute>\d\d):(?P<second>\d\d)
    (?:\.(?P<second_fraction>\d{0,6}))?
    (?P<tz>
        (?:(?P<tz_sign>[-+])(?P<tz_hour>\d\d):(?P<tz_minute>\d\d))
        | Z)?$
    """,
    re.VERBOSE)

ROOT_UDI = '/org/freedesktop/Hal/devices/computer'

# See include/linux/pci_ids.h in the Linux kernel sources for a complete
# list of PCI class and subclass codes.
PCI_CLASS_STORAGE = 1
PCI_SUBCLASS_STORAGE_SATA = 6

PCI_CLASS_BRIDGE = 6
PCI_SUBCLASS_BRIDGE_PCI = 4
PCI_SUBCLASS_BRIDGE_CARDBUS = 7

PCI_CLASS_SERIALBUS_CONTROLLER = 12
PCI_SUBCLASS_SERIALBUS_USB = 3

WARNING_NO_HAL_KERNEL_VERSION = 1
WARNING_NO_KERNEL_PACKAGE_DATA = 2

DB_FORMAT_FOR_VENDOR_ID = {
    'pci': '0x%04x',
    'usb_device': '0x%04x',
    'scsi': '%-8s',
    }

DB_FORMAT_FOR_PRODUCT_ID = {
    'pci': '0x%04x',
    'usb_device': '0x%04x',
    'scsi': '%-16s',
    }

class SubmissionParser(object):
    """A Parser for the submissions to the hardware database."""

    def __init__(self, logger=None):
        if logger is None:
            logger = getLogger()
        self.logger = logger
        self.doc_parser = etree.XMLParser()
        self._logged_warnings = set()

        self.validator = {}
        directory = os.path.join(config.root, 'lib', 'canonical',
                                 'launchpad', 'scripts')
        for version, relax_ng_filename in _relax_ng_files.items():
            path = os.path.join(directory, relax_ng_filename)
            self.validator[version] = RelaxNGValidator(path)
        self._setMainSectionParsers()
        self._setHardwareSectionParsers()
        self._setSoftwareSectionParsers()

    def _logError(self, message, submission_key):
        """Log `message` for an error in submission submission_key`."""
        self.logger.error(
            'Parsing submission %s: %s' % (submission_key, message))

    def _logWarning(self, message, warning_id=None):
        """Log `message` for a warning in submission submission_key`."""
        if warning_id is None:
            issue_warning = True
        elif warning_id not in self._logged_warnings:
            issue_warning = True
            self._logged_warnings.add(warning_id)
        else:
            issue_warning = False
        if issue_warning:
            self.logger.warning(
                'Parsing submission %s: %s' % (self.submission_key, message))

    def _getValidatedEtree(self, submission, submission_key):
        """Create an etree doc from the XML string submission and validate it.

        :return: an `lxml.etree` instance representation of a valid
            submission or None for invalid submissions.
        """
        try:
            tree = etree.parse(StringIO(submission), parser=self.doc_parser)
        except SyntaxError, error_value:
            self._logError(error_value, submission_key)
            return None

        submission_doc = tree.getroot()
        if submission_doc.tag != 'system':
            self._logError("root node is not '<system>'", submission_key)
            return None
        version = submission_doc.attrib.get('version', None)
        if not version in self.validator.keys():
            self._logError(
                'invalid submission format version: %s' % repr(version),
                submission_key)
            return None
        self.submission_format_version = version

        validator = self.validator[version]
        if not validator.validate(submission):
            self._logError(
                'Relax NG validation failed.\n%s' % validator.error_log,
                submission_key)
            return None
        return submission_doc

    def _getValueAttributeAsBoolean(self, node):
        """Return the value of the attribute "value" as a boolean."""
        value = node.attrib['value']
        # Paranoia check: The Relax NG validation already ensures that the
        # attribute value is either 'True' or 'False'.
        assert value in ('True', 'False'), (
            'Parsing submission %s: Boolean value for attribute "value" '
            'expected in tag <%s>' % (self.submission_key, node.tag))
        return value == 'True'

    def _getValueAttributeAsString(self, node):
        """Return the value of the attribute "value"."""
        # The Relax NG validation ensures that the attribute exists.
        return node.attrib['value']

    def _getValueAttributeAsDateTime(self, time_node):
        """Convert a "value" attribute into a datetime object."""
        time_text = time_node.get('value')

        # we cannot use time.strptime: this function accepts neither fractions
        # of a second nor a time zone given e.g. as '+02:30'.
        mo = _time_regex.search(time_text)

        # The Relax NG schema allows a leading minus sign and year numbers
        # with more than four digits, which are not "covered" by _time_regex.
        if mo is None:
            raise ValueError(
                'Timestamp with unreasonable value: %s' % time_text)

        time_parts = mo.groupdict()

        year = int(time_parts['year'])
        month = int(time_parts['month'])
        day = int(time_parts['day'])
        hour = int(time_parts['hour'])
        minute = int(time_parts['minute'])
        second = int(time_parts['second'])
        second_fraction = time_parts['second_fraction']
        if second_fraction is not None:
            milliseconds = second_fraction + '0' * (6 - len(second_fraction))
            milliseconds = int(milliseconds)
        else:
            milliseconds = 0

        # The Relax NG validator accepts leap seconds, but the datetime
        # constructor rejects them. The time values submitted by the HWDB
        # client are not necessarily very precise, hence we can round down
        # to 59.999999 seconds without losing any real precision.
        if second > 59:
            second = 59
            milliseconds = 999999

        timestamp = datetime(year, month, day, hour, minute, second,
                             milliseconds, tzinfo=pytz.timezone('utc'))

        tz_sign = time_parts['tz_sign']
        tz_hour = time_parts['tz_hour']
        tz_minute = time_parts['tz_minute']
        if tz_sign in ('-', '+'):
            delta = timedelta(hours=int(tz_hour), minutes=int(tz_minute))
            if tz_sign == '-':
                timestamp = timestamp + delta
            else:
                timestamp = timestamp - delta
        return timestamp

    def _getClientData(self, client_node):
        """Parse the <client> node in the <summary> section.

        :return: A dictionary with keys 'name', 'version', 'plugins'.
                 Name and version describe the the client program that
                 produced the submission. Pugins is a list with one
                 entry per client plugin; each entry is dictionary with
                 the keys 'name' and 'version'.
        """
        result = {'name': client_node.get('name'),
                  'version': client_node.get('version')}
        plugins = result['plugins'] = []
        for node in client_node.getchildren():
            # Ensured by the Relax NG validation: The only allowed sub-tag
            # of <client> is <plugin>, which has the attributes 'name' and
            # 'version'.
            plugins.append({'name': node.get('name'),
                            'version': node.get('version')})
        return result

    _parse_summary_section = {
        'live_cd': _getValueAttributeAsBoolean,
        'system_id': _getValueAttributeAsString,
        'distribution': _getValueAttributeAsString,
        'distroseries': _getValueAttributeAsString,
        'architecture': _getValueAttributeAsString,
        'private': _getValueAttributeAsBoolean,
        'contactable': _getValueAttributeAsBoolean,
        'date_created': _getValueAttributeAsDateTime,
        'client': _getClientData,
        }

    def _parseSummary(self, summary_node):
        """Parse the <summary> part of a submission.

        :return: A dictionary with the keys 'live_cd', 'system_id',
                 'distribution', 'distroseries', 'architecture',
                 'private', 'contactable', 'date_created', 'client'.
                 See the sample XML file tests/hardwaretest.xml for
                 detailed description of the values.
        """
        summary = {}
        # The Relax NG validation ensures that we have exactly those
        # sub-nodes that are listed in _parse_summary_section.
        for node in summary_node.getchildren():
            parser = self._parse_summary_section[node.tag]
            summary[node.tag] = parser(self, node)
        return summary

    def _getValueAndType(self, node):
        """Return (value, type) of a <property> or <value> node."""
        type_ = node.get('type')
        if type_ in ('dbus.Boolean', 'bool'):
            value = node.text.strip()
            # Pure paranoia: The Relax NG validation ensures that <property>
            # and <value> tags have only the allowed values.
            assert value in ('True', 'False'), (
                'Parsing submission %s: Invalid bool value for <property> or '
                    '<value>: %s' % (self.submission_key, repr(value)))
            return (value == 'True', type_)
        elif type_ in ('str', 'dbus.String', 'dbus.UTF8String'):
            return (node.text.strip(), type_)
        elif type_ in ('dbus.Byte', 'dbus.Int16', 'dbus.Int32', 'dbus.Int64',
                       'dbus.UInt16', 'dbus.UInt32', 'dbus.UInt64', 'int',
                       'long'):
            value = node.text.strip()
            return (int(value), type_)
        elif type_ in ('dbus.Double', 'float'):
            value = node.text.strip()
            return (float(value), type_)
        elif type_ in ('dbus.Array', 'list'):
            value = []
            for sub_node in node.getchildren():
                value.append(self._getValueAndType(sub_node))
            return (value, type_)
        elif type_ in ('dbus.Dictionary', 'dict'):
            value = {}
            for sub_node in node.getchildren():
                value[sub_node.get('name')] = self._getValueAndType(sub_node)
            return (value, type_)
        else:
            # This should not happen: The Relax NG validation ensures
            # that we have only those values for type_ that appear in
            # the if/elif expressions above.
            raise AssertionError(
                'Parsing submission %s: Unexpected <property> or <value> '
                    'type: %s' % (self.submission_key, type_))

    def _parseProperty(self, property_node):
        """Parse a <property> node.

        :return: (name, (value, type)) of a property.
        """
        property_name = property_node.get('name')
        return (property_node.get('name'),
                self._getValueAndType(property_node))

    def _parseProperties(self, properties_node):
        """Parse <property> sub-nodes of properties_node.

        :return: A dictionary, where each key is the name of a property;
                 the values are the tuples (value, type) of a property.
        """
        properties = {}
        for property_node in properties_node.getchildren():
            # Paranoia check: The Relax NG schema ensures that a node
            # with <property> sub-nodes has no other sub-nodes
            assert property_node.tag == 'property', (
            'Parsing submission %s: Found <%s> node, expected <property>'
                % (self.submission_key, property_node.tag))
            property_name, property_value = self._parseProperty(property_node)
            if property_name in properties.keys():
                raise ValueError(
                    '<property name="%s"> found more than once in <%s>'
                    % (property_name, properties_node.tag))
            properties[property_name] = property_value
        return properties

    def _parseDevice(self, device_node):
        """Parse a HAL <device> node.

        :return: A dictionary d with the keys 'id', 'udi', 'parent',
                 'properties'. d['id'] is an ID of the device d['udi']
                 is the HAL UDI of the device; d['properties'] is a
                 dictionary with the properties of the device (see
                 _parseProperties for details).
        """
        # The Relax NG validation ensures that the attributes "id" and
        # "udi" exist; it also ensures that "id" contains an integer.
        device_data = {'id': int(device_node.get('id')),
                       'udi': device_node.get('udi')}
        parent = device_node.get('parent', None)
        if parent is not None:
            parent = int(parent.strip())
        device_data['parent'] = parent
        device_data['properties'] = self._parseProperties(device_node)
        return device_data

    def _parseHAL(self, hal_node):
        """Parse the <hal> section of a submission.

        :return: A list, where each entry is the result of a _parseDevice
                 call.
        """
        # The Relax NG validation ensures that <hal> has the attribute
        # "version"
        hal_data = {'version': hal_node.get('version')}
        hal_data['devices'] = devices = []
        for device_node in hal_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <device> tags within <hal>
            assert device_node.tag == 'device', (
                'Parsing submission %s: Unexpected tag <%s> in <hal>'
                % (self.submission_key, device_node.tag))
            devices.append(self._parseDevice(device_node))
        return hal_data

    def _parseProcessors(self, processors_node):
        """Parse the <processors> node.

        :return: A list of dictionaries, where each dictionary d contains
                 the data of a <processor> node. The dictionary keys are
                 'id', 'name', 'properties'. d['id'] is an ID of a
                 <processor> node, d['name'] its name, and d['properties']
                 contains the properties of a processor (see
                 _parseProperties for details).
        """
        result = []
        for processor_node in processors_node.getchildren():
            # Pure paranoia: The Relax NG valiation ensures already
            # the we have only <processor> as sub-tags of <processors>.
            assert processor_node.tag == 'processor', (
                'Parsing submission %s: Unexpected tag <%s> in <processors>'
                   % (self.submission_key, processors_node.tag))
            processor = {}
            # The RelaxNG validation ensures that the attribute "id" exists
            # and that it contains an integer.
            processor['id'] = int(processor_node.get('id'))
            processor['name'] = processor_node.get('name')
            processor['properties'] = self._parseProperties(processor_node)
            result.append(processor)
        return result

    def _parseAliases(self, aliases_node):
        """Parse the <aliases> node.

        :return: A list of dictionaries, where each dictionary d has the
                 keys 'id', 'vendor', 'model'. d['id'] is the ID of a
                 HAL device; d['vendor'] is an alternative vendor name of
                 the device; d['model'] is an alternative model name.

                 See tests/hardwaretest.xml more more details.
        """
        aliases = []
        for alias_node in aliases_node.getchildren():
            # Pure paranoia: The Relax NG valiation ensures already
            # the we have only <alias> tags within <aliases>
            assert alias_node.tag == 'alias', (
                'Parsing submission %s: Unexpected tag <%s> in <aliases>'
                    % (self.submission_key, alias_node.tag))
            # The RelaxNG validation ensures that the attribute "target"
            # exists and that it contains an integer.
            alias = {'target': int(alias_node.get('target'))}
            for sub_node in alias_node.getchildren():
                # The Relax NG svalidation ensures that we have exactly
                # two subnodes: <vendor> and <model>
                alias[sub_node.tag] = sub_node.text.strip()
            aliases.append(alias)
        return aliases

    _parse_hardware_section = {
        'hal': _parseHAL,
        'processors': _parseProcessors,
        'aliases': _parseAliases}

    def _setHardwareSectionParsers(self):
        self._parse_hardware_section = {
            'hal': self._parseHAL,
            'processors': self._parseProcessors,
            'aliases': self._parseAliases}

    def _parseHardware(self, hardware_node):
        """Parse the <hardware> part of a submission.

        :return: A dictionary with the keys 'hal', 'processors', 'aliases',
                 where the values are the parsing results of _parseHAL,
                 _parseProcessors, _parseAliases.
        """
        hardware_data = {}
        for node in hardware_node.getchildren():
            parser = self._parse_hardware_section[node.tag]
            result = parser(node)
            hardware_data[node.tag] = result
        return hardware_data

    def _parseLSBRelease(self, lsb_node):
        """Parse the <lsb_release> part of a submission.

        :return: A dictionary with the content of the <properta> nodes
                 within the <lsb> node. See tests/hardwaretest.xml for
                 details.
        """
        return self._parseProperties(lsb_node)

    def _parsePackages(self, packages_node):
        """Parse the <packages> part of a submission.

        :return: A dictionary with one entry per <package> sub-node.
                 The key is the package name, the value a dictionary
                 containing the content of the <property> nodes within
                 <package>. See tests/hardwaretest.xml for more details.
        """
        packages = {}
        for package_node in packages_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <package> tags within <packages>.
            assert package_node.tag == 'package', (
                'Parsing submission %s: Unexpected tag <%s> in <packages>'
                % (self.submission_key, package_node.tag))
            package_name = package_node.get('name')
            if package_name in packages.keys():
                raise ValueError(
                    '<package name="%s"> appears more than once in <packages>'
                    % package_name)
            # The RelaxNG validation ensures that the attribute "id" exists
            # and that it contains an integer.
            package_data = {'id': int(package_node.get('id'))}
            package_data['properties'] = self._parseProperties(package_node)
            packages[package_name] = package_data
        return packages

    def _parseXOrg(self, xorg_node):
        """Parse the <xorg> part of a submission.

        :return: A dictionary with the keys 'version' and 'drivers'.
                 d['version'] is the xorg version; d['drivers'] is
                 a dictionary with one entry for each <driver> sub-node,
                 where the key is the driver name, the value is a dictionary
                 containing the attributes of the <driver> node. See
                 tests/hardwaretest.xml for more details.
        """
        xorg_data = {'version': xorg_node.get('version')}
        xorg_data['drivers'] = xorg_drivers = {}
        for driver_node in xorg_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <driver> tags within <xorg>.
            assert driver_node.tag == 'driver', (
                'Parsing submission %s: Unexpected tag <%s> in <xorg>'
                    % (self.submission_key, driver_node.tag))
            driver_info = dict(driver_node.attrib)
            if 'device' in driver_info:
                # The Relax NG validation ensures that driver_info['device']
                # consists of only digits, if present.
                driver_info['device'] = int(driver_info['device'])
            driver_name = driver_info['name']
            if driver_name in xorg_drivers.keys():
                raise ValueError(
                    '<driver name="%s"> appears more than once in <xorg>'
                    % driver_name)
            xorg_drivers[driver_name] = driver_info
        return xorg_data

    _parse_software_section = {
        'lsbrelease': _parseLSBRelease,
        'packages': _parsePackages,
        'xorg': _parseXOrg}

    def _setSoftwareSectionParsers(self):
        self._parse_software_section = {
            'lsbrelease': self._parseLSBRelease,
            'packages': self._parsePackages,
            'xorg': self._parseXOrg}

    def _parseSoftware(self, software_node):
        """Parse the <software> section of a submission.

        :return: A dictionary with the keys 'lsbrelease', 'packages',
                 'xorg', containing the parsing results of the respective
                 sub-nodes. The key 'lsbrelease' exists always; 'xorg'
                 and 'packages' are optional. See _parseLSBRelease,
                 _parsePackages, _parseXOrg for more details.
        """
        software_data = {}
        for node in software_node.getchildren():
            parser = self._parse_software_section[node.tag]
            result = parser(node)
            software_data[node.tag] = result
        # The nodes <packages> and <xorg> are optional. Ensure that
        # we have dummy entries in software_data for these nodes, if
        # the nodes do not appear in a submission in order to avoid
        # KeyErrors elsewhere in this module.
        for node_name in ('packages', 'xorg'):
            if node_name not in software_data:
                software_data[node_name] = {}
        return software_data

    def _parseQuestions(self, questions_node):
        """Parse the <questions> part of a submission.

        :return: A list, where each entry is a dictionary containing
                 the parsing result of the <question> sub-nodes.

                 Content of a list entry d (see tests/hardwaretest.xml
                 for a more detailed description):
                 d['name']:
                        The name of a question. (Always present)
                 d['plugin']:
                        The name of the client plugin which is
                        "responsible" for the question. (Optional)
                 d['targets']:
                        A list, where each entry is a dicitionary
                        describing a target device for this question.
                        This list is always present, but may be empty.

                        The contents of each list entry t is:

                        t['id']:
                                The ID of a HAL <device> node of a
                                target device.
                        t['drivers']:
                                A list of driver names, possibly empty.
                 d['answer']:
                        The answer to this question. The value is a
                        dictionary a:
                        a['value']:
                                The value of the answer. (Always present)

                                For questions of type muliple_choice,
                                the value should match one of the
                                entries of the answer_choices list,

                                For questions of type measurement, the
                                value is a numerical value.
                        a['type']:
                                This is either 'multiple_choice' or
                                'measurement'. (Always present)
                        a['unit']:
                                The unit of a measurement value.
                                (Optional)
                 d['answer_choices']:
                        A list of choices from which the user can select
                        an answer. This list is always present, but should
                        be empty for questions of type measurement.
                 d['command']:
                        The command line of a test script which was
                        run for this question. (Optional)
                 d['comment']:
                        A comment the user has typed when running the
                        client. (Optional)

                 A consistency check of the content of d is done in
                 method _checkSubmissionConsistency.
        """
        questions = []
        for question_node in questions_node.getchildren():
            # Pure paranoia: The Relax NG validation ensures already
            # that we have only <driver> tags within <xorg>
            assert question_node.tag == 'question', (
                'Parsing submission %s: Unexpected tag <%s> in <questions>'
                % (self.submission_key, question_node.tag))
            question = {'name': question_node.get('name')}
            plugin = question_node.get('plugin', None)
            if plugin is not None:
                question['plugin'] = plugin
            question['targets'] = targets = []
            answer_choices = []

            for sub_node in question_node.getchildren():
                sub_tag = sub_node.tag
                if sub_tag == 'answer':
                    question['answer'] = answer = {}
                    answer['type'] = sub_node.get('type')
                    if answer['type'] == 'multiple_choice':
                        question['answer_choices'] = answer_choices
                    unit = sub_node.get('unit', None)
                    if unit is not None:
                        answer['unit'] = unit
                    answer['value'] = sub_node.text.strip()
                elif sub_tag == 'answer_choices':
                    for value_node in sub_node.getchildren():
                        answer_choices.append(
                            self._getValueAndType(value_node))
                elif sub_tag == 'target':
                    # The Relax NG schema ensures that the attribute
                    # id exists and that it is an integer
                    target = {'id': int(sub_node.get('id'))}
                    target['drivers'] = drivers = []
                    for driver_node in sub_node.getchildren():
                        drivers.append(driver_node.text.strip())
                    targets.append(target)
                elif sub_tag in('comment', 'command'):
                    data = sub_node.text
                    if data is not None:
                        question[sub_tag] = data.strip()
                else:
                    # This should not happen: The Relax NG validation
                    # ensures that we have only those tags which appear
                    # in the if/elif expressions.
                    raise AssertionError(
                        'Parsing submission %s: Unexpected node <%s> in '
                        '<question>' % (self.submission_key, sub_tag))
            questions.append(question)
        return questions

    def _setMainSectionParsers(self):
        self._parse_system = {
            'summary': self._parseSummary,
            'hardware': self._parseHardware,
            'software': self._parseSoftware,
            'questions': self._parseQuestions}

    def parseMainSections(self, submission_doc):
        # The RelaxNG validation ensures that submission_doc has exactly
        # four sub-nodes and that the names of the sub-nodes appear in the
        # keys of self._parse_system.
        submission_data = {}
        try:
            for node in submission_doc.getchildren():
                parser = self._parse_system[node.tag]
                submission_data[node.tag] = parser(node)
        except ValueError, value:
            self._logError(value, self.submission_key)
            return None
        return submission_data

    def parseSubmission(self, submission, submission_key):
        """Parse the data of a HWDB submission.

        :return: A dictionary with the keys 'summary', 'hardware',
                 'software', 'questions'. See _parseSummary,
                 _parseHardware, _parseSoftware, _parseQuestions for
                 the content.
        """
        self.submission_key = submission_key
        submission_doc  = self._getValidatedEtree(submission, submission_key)
        if submission_doc is None:
            return None

        return self.parseMainSections(submission_doc)

    def _findDuplicates(self, all_ids, test_ids):
        """Search for duplicate elements in test_ids.

        :return: A set of those elements in the sequence test_ids that
        are elements of the set all_ids or that appear more than once
        in test_ids.

        all_ids is updated with test_ids.
        """
        duplicates = set()
        # Note that test_ids itself may contain an ID more than once.
        for test_id in test_ids:
            if test_id in all_ids:
                duplicates.add(test_id)
            else:
                all_ids.add(test_id)
        return duplicates

    def findDuplicateIDs(self, parsed_data):
        """Return the set of duplicate IDs.

        The IDs of devices, processors and software packages should be
        unique; this method returns a list of duplicate IDs found in a
        submission.
        """
        all_ids = set()
        duplicates = self._findDuplicates(
            all_ids,
            [device['id']
             for device in parsed_data['hardware']['hal']['devices']])
        duplicates.update(self._findDuplicates(
            all_ids,
            [processor['id']
             for processor in parsed_data['hardware']['processors']]))
        duplicates.update(self._findDuplicates(
            all_ids,
            [package['id']
             for package in parsed_data['software']['packages'].values()]))
        return duplicates

    def _getIDMap(self, parsed_data):
        """Return a dictionary ID -> devices, processors and packages."""
        id_map = {}
        hal_devices = parsed_data['hardware']['hal']['devices']
        for device in hal_devices:
            id_map[device['id']] = device

        for processor in parsed_data['hardware']['processors']:
            id_map[processor['id']] = processor

        for package in parsed_data['software']['packages'].values():
            id_map[package['id']] = package

        return id_map

    def findInvalidIDReferences(self, parsed_data):
        """Return the set of invalid references to IDs.

        The sub-tag <target> of <question> references a device, processor
        of package node by its ID; the submission must contain a <device>,
        <processor> or <software> tag with this ID. This method returns a
        set of those IDs mentioned in <target> nodes that have no
        corresponding device or processor node.
        """
        id_device_map = self._getIDMap(parsed_data)
        known_ids = set(id_device_map.keys())
        questions = parsed_data['questions']
        target_lists = [question['targets'] for question in questions]
        all_targets = []
        for target_list in target_lists:
            all_targets.extend(target_list)
        all_target_ids = set(target['id'] for target in all_targets)
        return all_target_ids.difference(known_ids)

    def getUDIDeviceMap(self, devices):
        """Return a dictionary which maps UDIs to HAL devices.

        If a UDI is used more than once, a ValueError is raised.
        """
        udi_device_map = {}
        for device in devices:
            if device['udi'] in udi_device_map:
                raise ValueError('Duplicate UDI: %s' % device['udi'])
            else:
                udi_device_map[device['udi']] = device
        return udi_device_map

    def _getIDUDIMaps(self, devices):
        """Return two mappings describing the relation between IDs and UDIs.

        :return: two dictionaries id_to_udi and udi_to_id, where
                 id_2_udi has IDs as keys and UDI as values, and where
                 udi_to_id has UDIs as keys and IDs as values.
        """
        id_to_udi = {}
        udi_to_id = {}
        for device in devices:
            id = device['id']
            udi = device['udi']
            id_to_udi[id] = udi
            udi_to_id[udi] = id
        return id_to_udi, udi_to_id

    def getUDIChildren(self, udi_device_map):
        """Build lists of all children of a UDI.

        :return: A dictionary that maps UDIs to lists of children.

        If any info.parent property points to a non-existing existing
        device, a ValueError is raised.
        """
        # Each HAL device references its parent device (HAL attribute
        # info.parent), except for the "root node", which has no parent.
        children = {}
        known_udis = set(udi_device_map.keys())
        for device in udi_device_map.values():
            parent_property = device['properties'].get('info.parent', None)
            if parent_property is not None:
                parent = parent_property[0]
                if not parent in known_udis:
                    raise ValueError(
                        'Unknown parent UDI %s in <device id="%s">'
                        % (parent, device['id']))
                if parent in children:
                    children[parent].append(device)
                else:
                    children[parent] = [device]
            else:
                # A node without a parent is a root node. Only one root node
                # is allowed, which must have the UDI
                # "/org/freedesktop/Hal/devices/computer".
                # Other nodes without a parent UDI indicate an error, as well
                # as a non-existing root node.
                if device['udi'] != ROOT_UDI:
                    raise ValueError(
                        'root device node found with unexpected UDI: '
                        '<device id="%s" udi="%s">' % (device['id'],
                                                       device['udi']))

        if not ROOT_UDI in children:
            raise ValueError('No root device found')
        return children

    def _removeChildren(self, udi, udi_test):
        """Remove recursively all children of the device named udi."""
        if udi in udi_test:
            children = udi_test[udi]
            for child in children:
                self._removeChildren(child['udi'], udi_test)
            del udi_test[udi]

    def checkHALDevicesParentChildConsistency(self, udi_children):
        """Ensure that HAL devices are represented in exactly one tree.

        :return: A list of those UDIs that are not "connected" to the root
                 node /org/freedesktop/Hal/devices/computer

        HAL devices "know" their parent device; each device has a parent,
        except the root element. This means that it is possible to traverse
        all existing devices, beginning at the root node.

        Several inconsistencies are possible:

        (a) we may have more than one root device (i.e., one without a
            parent)
        (b) we may have no root element
        (c) circular parent/child references may exist.

        (a) and (b) are already checked in _getUDIChildren; this method
        implements (c),
        """
        # If we build a copy of udi_children and if we remove, starting at
        # the root UDI, recursively all children from this copy, we should
        # get a dictionary, where all values are empty lists. Any remaining
        # nodes must have circular parent references.

        udi_test = {}
        for udi, children in udi_children.items():
            udi_test[udi] = children[:]
        self._removeChildren(ROOT_UDI, udi_test)
        return udi_test.keys()

    def checkConsistency(self, parsed_data):
        """Run consistency checks on the submitted data.

        :return: True, if the data looks consistent, otherwise False.
        :param: parsed_data: parsed submission data, as returned by
                             parseSubmission
        """
        duplicate_ids = self.findDuplicateIDs(parsed_data)
        if duplicate_ids:
            self._logError('Duplicate IDs found: %s' % duplicate_ids,
                           self.submission_key)
            return False

        invalid_id_references = self.findInvalidIDReferences(parsed_data)
        if invalid_id_references:
            self._logError(
                'Invalid ID references found: %s' % invalid_id_references,
                self.submission_key)
            return False

        try:
            udi_device_map = self.getUDIDeviceMap(
                parsed_data['hardware']['hal']['devices'])
            udi_children = self.getUDIChildren(udi_device_map)
        except ValueError, value:
            self._logError(value, self.submission_key)
            return False

        circular = self.checkHALDevicesParentChildConsistency(udi_children)
        if circular:
            self._logError('Found HAL devices with circular parent/child '
                           'relationship: %s' % circular,
                           self.submission_key)
            return False

        return True

    def buildDeviceList(self, parsed_data):
        """Create a list of devices from a submission."""
        self.hal_devices = hal_devices = {}
        for hal_data in parsed_data['hardware']['hal']['devices']:
            udi = hal_data['udi']
            hal_devices[udi] = HALDevice(hal_data['id'], udi,
                                         hal_data['properties'], self)
        for device in hal_devices.values():
            parent_udi = device.parent_udi
            if parent_udi is not None:
                hal_devices[parent_udi].addChild(device)

    def getKernelPackageName(self):
        """Return the kernel package name of the submission,"""
        root_hal_device = self.hal_devices[ROOT_UDI]
        kernel_version = root_hal_device.getProperty('system.kernel.version')
        if kernel_version is None:
            self._logWarning(
                'Submission does not provide property system.kernel.version '
                'for /org/freedesktop/Hal/devices/computer.',
                WARNING_NO_HAL_KERNEL_VERSION)
            return None
        kernel_package_name = 'linux-image-' + kernel_version
        packages = self.parsed_data['software']['packages']
        # The submission is not required to provide any package data...
        if packages and kernel_package_name not in packages:
            # ...but if we have it, we want it to be consistent with
            # the HAL root node property.
            self._logWarning(
                'Inconsistent kernel version data: According to HAL the '
                'kernel is %s, but the submission does not know about a '
                'kernel package %s'
                % (kernel_version, kernel_package_name),
                WARNING_NO_HAL_KERNEL_VERSION)
            return None
        return kernel_package_name

    def processSubmission(self, submission):
        """Process a submisson.

        :return: True, if the submission could be sucessfully processed,
            otherwise False.
        :param submission: An IHWSubmission instance.
        """
        raw_submission = submission.raw_submission
        raw_submission.open()
        submission_data = raw_submission.read()
        raw_submission.close()
        # We assume that the data has been sent bzip2-compressed,
        # but this is not checked when the data is submitted.
        expanded_data = None
        try:
            expanded_data = bz2.decompress(submission_data)
        except IOError:
            # An IOError is raised, if the data is not BZip2-compressed.
            # We assume in this case that valid uncompressed data has been
            # submitted. If this assumption is wrong, parseSubmission()
            # or checkConsistency() will complain, hence we don't check
            # anything else here.
            pass
        if expanded_data is not None:
            submission_data = expanded_data

        parsed_data = self.parseSubmission(
            submission_data, submission.submission_key)
        if parsed_data is None:
            return False
        self.parsed_data = parsed_data
        if not self.checkConsistency(parsed_data):
            return False
        self.buildDeviceList(parsed_data)
        root_device = self.hal_devices[ROOT_UDI]
        root_device.createDBData(submission, None)
        return True

class HALDevice:
    """The representation of a HAL device node."""

    def __init__(self, id, udi, properties, parser):
        """HALDevice constructor.

        :param id: The ID of the HAL device in the submission data as
            specified in <device id=...>.
        :type id: int
        :param udi: The UDI of the HAL device.
        :type udi: string
        :param properties: The HAL properties of the device.
        :type properties: dict
        :param parser: The parser processing a submission.
        :type parser: SubmissionParser
        """
        self.id = id
        self.udi = udi
        self.properties = properties
        self.children = []
        self.parser = parser
        self.parent = None

    def addChild(self, child):
        """Add a child device and set the child's parent."""
        assert type(child) == type(self)
        self.children.append(child)
        child.parent = self

    def getProperty(self, property_name):
        """Return the property property_name.

        Note that there is no check of the property type.
        """
        if property_name not in self.properties:
            return None
        name, type_ = self.properties[property_name]
        return name

    @property
    def parent_udi(self):
        """The UDI of the parent device."""
        return self.getProperty('info.parent')

    # Translation of the HAL info.bus/info.subsystem property to HWBus
    # enumerated buses.
    hal_bus_hwbus = {
        'pcmcia': HWBus.PCMCIA,
        'usb_device': HWBus.USB,
        'ide': HWBus.IDE,
        'serio': HWBus.SERIAL,
        }

    # Translation of subclasses of the PCI class storage to HWBus
    # enumerated buses. The Linux kernel accesses IDE and SATA disks
    # and CDROM drives via the SCSI system; we want to know the real bus
    # of the drive. See for example the file include/linux/pci_ids.h
    # in the Linux kernel sources for a list of PCI device classes and
    # subclasses. Note that the subclass 4 (RAID) is missing. While it
    # may make sense to declare a RAID storage class for PCI devices,
    # "RAID" does not tell us anything about the bus of the storage
    # devices.
    pci_storage_subclass_hwbus = {
        0: HWBus.SCSI,
        1: HWBus.IDE,
        2: HWBus.FLOPPY,
        3: HWBus.IPI, # Intelligent Peripheral Interface
        5: HWBus.ATA,
        6: HWBus.SATA,
        7: HWBus.SAS,
        }

    def translateScsiBus(self):
        """Return the real bus of a device where raw_bus=='scsi'.

        The kernel uses the SCSI layer to access storage devices
        connected via the USB, IDE, SATA buses. See `is_real_device`
        for more details. This method determines the real bus
        of a device accessed via the kernel's SCSI subsystem.
        """
        # While SCSI devices from valid submissions should have a
        # parent and a grandparent, we can't be sure for bogus or
        # broken submissions.
        parent = self.parent
        if parent is None:
            self.parser._logWarning(
                'Found SCSI device without a parent: %s.' % self.udi)
            return None
        grandparent = parent.parent
        if grandparent is None:
            self.parser._logWarning(
                'Found SCSI device without a grandparent: %s.' % self.udi)
            return None

        grandparent_bus = grandparent.raw_bus
        if grandparent_bus == 'pci':
            if (grandparent.getProperty('pci.device_class')
                != PCI_CLASS_STORAGE):
                # This is not a storage class PCI device? This
                # indicates a bug somewhere in HAL or in the hwdb
                # client, or a fake submission.
                device_class = grandparent.getProperty('pci.device_class')
                self.parser._logWarning(
                    'A (possibly fake) SCSI device %s is connected to '
                    'PCI device %s that has the PCI device class %s; '
                    'expected class 1 (storage).'
                    % (self.udi, grandparent.udi, device_class))
                return None
            pci_subclass = grandparent.getProperty('pci.device_subclass')
            return self.pci_storage_subclass_hwbus.get(pci_subclass)
        elif grandparent_bus == 'usb':
            # USB storage devices have the following HAL device hierarchy:
            # - HAL node for the USB device. info.bus == 'usb_device',
            #   device class == 0, device subclass == 0
            # - HAL node for the USB storage interface. info.bus == 'usb',
            #   interface class 8, interface subclass 6
            #   (see http://www.usb.org/developers/devclass_docs
            #   /usb_msc_overview_1.2.pdf)
            # - HAL node for the (fake) SCSI host. raw_bus is None
            # - HAL node for the (fake) SCSI device. raw_bus == 'scsi'
            # - HAL node for the mass storage device
            #
            # Physically, the storage device can be:
            # (1) a genuine USB device, like a memory stick
            # (2) a IDE/SATA hard disk, connected to a USB -> SATA/IDE
            #     bridge
            # (3) a card reader
            # There is no formal way to distinguish cases (1) and (2):
            # The device and interface classes are in both cases
            # identical; the only way to figure out, if we have a USB
            # hard disk enclosure or a USB memory stick would be to
            # look at the vendor or product names, or to look up some
            # external data sources. Of course, we can also ask the
            # submitter in the future.
            #
            # The cases (1) and (2) differ from (3) in the property
            # the property storage.removable. For (1) and (2), this
            # property is False, for (3) it is True. Since we do not
            # store at present any device characteristics in the HWDB,
            # so there is no point to distinguish between (1), (2) on
            # one side and (3) on the other side. Distinguishing
            # between (1) and (2) might be more interesting, because
            # a hard disk is clearly a separate device, but as written,
            # it is hard to distinguish between (1) and (2)
            #
            # To sum up: we cannot get any interesting and reliable
            # information about the details of USB storage device,
            # so we'll treat those devices as "black boxes".
            return None
        else:
            return HWBus.SCSI

    def translatePciBus(self):
        # Cardbus (aka PCCard, sometimes also incorrectly called
        # PCMCIA) devices are treated as PCI devices by the kernel.
        # We can detect PCCards by checking that the parent device
        # is a PCI bridge (device class 6) for the Cardbus (device
        # subclass 7).
        # XXX Abel Deuring 2005-05-14 How can we detect ExpressCards?
        # I do not have any such card at present...
        parent_class = self.parent.getProperty('pci.device_class')
        parent_subclass = self.parent.getProperty('pci.device_subclass')
        if (parent_class == PCI_CLASS_BRIDGE
            and parent_subclass == PCI_SUBCLASS_BRIDGE_CARDBUS):
            return HWBus.PCCARD
        else:
            return HWBus.PCI

    translate_bus_name = {
        'pci': translatePciBus,
        'scsi': translateScsiBus,
        }

    @property
    def raw_bus(self):
        """Return the device bus as specified by HAL.

        Older versions of HAL stored this value in the property
        info.bus; newer versions store it in info.subsystem.
        """
        # Note that info.bus is gone for all devices except the
        # USB bus. For USB devices, the property info.bus returns more
        # detailed data: info.subsystem has the value 'usb' for all
        # HAL nodes belonging to USB devices, while info.bus has the
        # value 'usb_device' for the root node of a USB device, and the
        # value 'usb' for sub-nodes of a USB device. We use these
        # different value to to find the root USB device node, hence
        # try to read info.bus first.
        result = self.getProperty('info.bus')
        if result is not None:
            return result
        return self.getProperty('info.subsystem')

    @property
    def real_bus(self):
        """Return the bus this device connects to on the host side.

        :return: A bus as enumerated in HWBus or None, if the bus
            cannot be determined.
        """
        device_bus = self.raw_bus
        result = self.hal_bus_hwbus.get(device_bus)
        if result is not None:
            return result

        if device_bus == 'scsi':
            return self.translateScsiBus()
        elif device_bus == 'pci':
            return self.translatePciBus()
        elif self.udi == ROOT_UDI:
            # The computer itself. In Hardy, HAL provides no info.bus
            # for the machine itself; older versions set info.bus to
            # 'unknown', hence it is better to use the machine's
            # UDI.
            return HWBus.SYSTEM
        else:
            self.parser._logWarning(
                'Unknown bus %r for device %s' % (device_bus, self.udi))
            return None

    @property
    def is_real_device(self):
        """True, if the HAL device correspends to a real device.

        In many cases HAL has more than one device entry for the
        same physical device. We are only interested in real, physical,
        devices but not in the fine details, how HAL represents different
        aspects of them.

        For example, the HAL device node hiearchy for a SATA disk and
        its host controller looks like this:

        HAL device node of the host controller
            udi: .../pci_8086_27c5
            HAL properties:
                info.bus: pci
                pci.device_class: 1 (storage)
                pci.device_subclass: 6 (SATA)
                info.linux.driver: ahci

        HAL device node of the "output aspect" of the host controller
            udi: .../pci_8086_27c5_scsi_host
            HAL properties:
                info.bus: n/a
                info.driver: n/a
                info.parent: .../pci_8086_27c5

        HAL device node of a hard disk.
            udi: .../pci_8086_27c5_scsi_host_scsi_device_lun0
            HAL properties:
                info.bus: scsi
                info.driver: sd
                info.parent: .../pci_8086_27c5_scsi_host

        HAL device node of the "storage aspect" of the hard disk
            udi: .../storage_serial_1ATA_Hitachi_HTS541616J9SA00_SB...
            HAL properties
                info.driver: n/a
                info.parent: .../pci_8086_27c5_scsi_host_scsi_device_lun0

        HAL device node of a disk partition:
            udi: .../volume_uuid_0ee803cf_...
            HAL properties
                info.driver: n/a
                info.parent: .../storage_serial_1ATA_Hitachi_HTS541616J...

        (optionally more nodes for more partitions)

        HAL device node of the "generic SCSI aspect" of the hard disk:
            udi: .../pci_8086_27c5_scsi_host_scsi_device_lun0_scsi_generic
                info.driver: n/a
                info.parent: .../pci_8086_27c5_scsi_host_scsi_device_lun0

        This disk is _not_ a SCSI disk, but a SATA disk. In other words,
        the SCSI details are in this case just an artifact of the Linux
        kernel, which uses its SCSI subsystem as a "central hub" to access
        IDE, SATA, USB, IEEE1394 storage devices. The only interesting
        detail for us is that the sd driver is involved in accesses to the
        disk.

        Heuristics:

        - Most real devices have the property info.bus; we consider only
          those devices to be real which have this property set.

        - As written above, the SCSI bus often appears as an artifact;
          for PCI host controllers, their properties pci.device_class
          and pci.device_subclass tell us if we have a real SCSI host
          controller: pci.device_class == 1 means a storage controller,
          pci.device_subclass == 0 means a SCSI controller. This works
          too for PCCard controllers, which use the PCI device class
          numbers too.

        - The value "usb_device" of the HAL property info.bus identifies
          USB devices, with one exception: The USB host controller, which
          itself has an info.bus property with the value "pci", has a
          sub-device with info.bus='usb_device' for its "output aspect".
          These sub-devices can be identified by the device class their
          parent and by their USB vendor/product IDs, which are 0:0.
        """
        bus = self.raw_bus
        if bus in (None, 'usb', 'ssb', 'scsi_host'):
            # bus is None for a number of "virtual components", like
            # /org/freedesktop/Hal/devices/computer_alsa_timer or
            # /org/freedesktop/Hal/devices/computer_oss_sequencer, so
            # we ignore them. (The real sound devices appear with
            # other UDIs in HAL.)
            #
            # XXX Abel Deuring 20080425: This ignores a few components
            # like laptop batteries or the CPU, where info.bus is None.
            # Since these components are not the most important ones
            # for the HWDB, we'll ignore them for now. Bug 237038.
            #
            # info.bus == 'usb' is used for end points of USB devices;
            # the root node of a USB device has info.bus == 'usb_device'.
            #
            # info.bus == 'ssb' is used for "aspects" of Broadcom
            # Ethernet and WLAN devices, but like 'usb', they do not
            # represent separate devices.
            #
            # info.bus == 'scsi_host' is used by the HAL version in
            # Intrepid to real and "fake" SCSI host controllers.
            # (ON Hardy, these nodes have no info.bus property)
            # HAL nodes with this bus value are sub-nodes for the
            # "SCSI aspect" of another HAL node which represents the
            # real device.
            #
            # The computer itself is the only HAL device without the
            # info.bus property that we treat as a real device.
            return self.udi == ROOT_UDI
        elif bus == 'usb_device':
            vendor_id = self.getProperty('usb_device.vendor_id')
            product_id = self.getProperty('usb_device.product_id')
            if vendor_id == 0 and product_id == 0:
                # double-check: The parent device should be a PCI host
                # controller, identifiable by its device class and subclass.
                # XXX Abel Deuring 2008-04-28 Bug=237039: This ignores other
                # possible bridges, like ISA->USB..
                parent = self.parent
                parent_bus = parent.raw_bus
                parent_class = parent.getProperty('pci.device_class')
                parent_subclass = parent.getProperty('pci.device_subclass')
                if (parent_bus == 'pci'
                    and parent_class == PCI_CLASS_SERIALBUS_CONTROLLER
                    and parent_subclass == PCI_SUBCLASS_SERIALBUS_USB):
                    return False
                else:
                    self.parser._logWarning(
                        'USB device found with vendor ID==0, product ID==0, '
                        'where the parent device does not look like a USB '
                        'host controller: %s' % self.udi)
                    return False
            return True
        elif bus == 'scsi':
            # Ensure consistency with HALDevice.real_bus
            return self.real_bus is not None
        else:
            return True

    def getRealChildren(self):
        """Return the list of real child devices of this devices.

        The list of real child devices consists of the direct child
        devices of this device where child.is_real_device == True, and
        of the (recursively collected) list of real sub-devices of
        those child devices where child.is_real_device == False.
        """
        result = []
        for sub_device in self.children:
            if sub_device.is_real_device:
                # XXX Abel Deuring 2008-05-06: IEEE1394 devices are a bit
                # nasty: The standard does not define any specification
                # for product IDs or product names, hence HAL often
                # uses the value 0 for the property ieee1394.product_id
                # and a value like "Unknown (0x00d04b)" for
                # ieee.product, where 0x00d04b is the vendor ID. I have
                # currently no idea how to find or generate something
                # that could be used as the product ID, so IEEE1394
                # devices are at present simply dropped from the list of
                # devices. Otherwise, we'd pollute the HWDB with
                # unreliable data. Bug 237044.
                if sub_device.raw_bus != 'ieee1394':
                    result.append(sub_device)
            else:
                result.extend(sub_device.getRealChildren())
        return result

    @property
    def has_reliable_data(self):
        """Can this device be stored in the HWDB?

        Devices are identifed by (bus, vendor_id, product_id).
        At present we cannot generate reliable vendor and/or product
        IDs for devices where
        info.bus in ('pnp', 'platform', 'ieee1394', 'pcmcia', 'mmc').

        info.bus == 'platform' is used for devices like the i8042
        which controls keyboard and mouse; HAL has no vendor
        information for these devices, so there is no point to
        treat them as real devices.

        info.bus == 'pnp' is used for components like the ancient
        AT DMA controller or the keyboard. Like for the bus
        'platform', HAL does not provide any vendor data.

        info.bus == 'mmc' is used for SD/MMC cards. We do not not
        have at present enough background information to properly
        extract a vendor and product ID from these cards.

        info.bus == 'misc' and info.bus == 'unknown' are obviously
        not very useful, except for the computer itself, which has
        the bus 'unknown'.

        XXX Abel Deuring 2008-05-06: IEEE1394 devices are a bit
        nasty: The standard does not define any specification
        for product IDs or product names, hence HAL often uses
        the value 0 for the property ieee1394.product_id and a
        value like "Unknown (0x00d04b)" for ieee.product, where
        0x00d04b is the vendor ID. I have currently no idea how
        to find or generate something that could be used as the
        product ID, so IEEE1394 devices are at present simply
        not stored in the HWDB. Otherwise, we'd pollute the HWDB
        with unreliable data. Bug #237044.

        While PCMCIA devices have a manufacturer ID, at least its
        value as provided by HAL in pcmcia.manf_id it is not very
        reliable. The HAL property pcmcia.prod_id1 is too not
        reliable. Sometimes it contains a useful vendor name like
        "O2Micro" or "ATMEL", but sometimes useless values like
        "IEEE 802.11b". See for example
        drivers/net/wireless/atmel_cs.c in the Linux kernel sources.

        Provided that a device is not excluded by the above criteria,
        ensure that we have vendor ID, product ID and product name.
        """
        bus = self.raw_bus
        if bus == 'unknown' and self.udi != ROOT_UDI:
            # The root node is course a real device; storing data
            # about other devices with the bus "unkown" is pointless.
            return False
        if bus in ('pnp', 'platform', 'ieee1394', 'pcmcia', 'mmc', 'misc'):
            return False

        # We identify devices by bus, vendor ID and product ID;
        # additionally, we need a product name. If any of these
        # are not available, we can't store information for this
        # device.
        if (self.real_bus is None or self.vendor_id is None
            or self.product_id is None or self.product is None):
            # Many IDE devices don't provide useful vendor and product
            # data. We don't want to clutter the log with warnings
            # about this problem -- there is nothing we can do to fix
            # it.
            if self.real_bus != HWBus.IDE:
                self.parser._logWarning(
                    'A HALDevice that is supposed to be a real device does '
                    'not provide bus, vendor ID, product ID or product name: '
                    '%r %r %r %r %s'
                    % (self.real_bus, self.vendor_id, self.product_id,
                       self.product, self.udi),
                    self.parser.submission_key)
            return False
        return True

    def getScsiVendorAndModelName(self):
        """Separate vendor and model name of SCSI decvices.

        SCSI devcies are identified by an 8 charcter vendor name
        and an 16 character model name. The Linux kernel use the
        the SCSI command set to access block devices connected
        via USB, IEEE1394 and ATA buses too.

        For ATA disks, the Linux kernel sets the vendor name to "ATA"
        and prepends the model name with the real vendor name, but only
        if the combined length if not larger than 16. Otherwise the
        real vendor name is omitted.

        This method provides a safe way to retrieve the  the SCSI vendor
        and model name.

        If the vendor name is 'ATA', and if the model name contains
        at least one ' ' character, the string before the first ' ' is
        returned as the vendor name, and the the string after the first
        ' ' is returned as the model name.

        In all other cases, vendor and model name are returned unmodified.
        """
        vendor = self.getProperty('scsi.vendor')
        if vendor == 'ATA':
            # The assumption below that the vendor name does not
            # contain any spaces is not necessarily correct, but
            # it is hard to find a better heuristic to separate
            # the vendor name from the product name.
            splitted_name = self.getProperty('scsi.model').split(' ', 1)
            if len(splitted_name) < 2:
                return 'ATA', splitted_name[0]
            return splitted_name
        return (vendor, self.getProperty('scsi.model'))

    def getVendorOrProduct(self, type_):
        """Return the vendor or product of this device.

        :return: The vendor or product data for this device.
        :param type_: 'vendor' or 'product'
        """
        # HAL does not store vendor data very consistently. Try to find
        # the data in several places.
        assert type_ in ('vendor', 'product'), (
            'Unexpected value of type_: %r' % type_)

        bus = self.raw_bus
        if self.udi == ROOT_UDI:
            # HAL sets info.product to "Computer", provides no property
            # info.vendor and raw_bus is "unknown", hence the logic
            # below does not work properly.
            return self.getProperty('system.hardware.' + type_)
        elif bus == 'scsi':
            vendor, product = self.getScsiVendorAndModelName()
            if type_ == 'vendor':
                return vendor
            else:
                return product
        else:
            result = self.getProperty('info.' + type_)
            if result is None:
                if bus is None:
                    return None
                else:
                    return self.getProperty('%s.%s' % (bus, type_))
            else:
                return result

    @property
    def vendor(self):
        """The vendor of this device."""
        return self.getVendorOrProduct('vendor')


    @property
    def product(self):
        """The vendor of this device."""
        return self.getVendorOrProduct('product')


    def getVendorOrProductID(self, type_):
        """Return the vendor or product ID for this device.

        :return: The vendor or product ID for this device.
        :param type_: 'vendor' or 'product'
        """
        assert type_ in ('vendor', 'product'), (
            'Unexpected value of type_: %r' % type_)
        bus = self.raw_bus
        if self.udi == ROOT_UDI:
            # HAL does not provide IDs for a system itself, we use the
            # vendor resp. product name instead.
            return self.getVendorOrProduct(type_)
        elif bus is None:
            return None
        elif bus == 'scsi' or self.udi == ROOT_UDI:
            # The SCSI specification does not distinguish between a
            # vendor/model ID and vendor/model name: the SCSI INQUIRY
            # command returns an 8 byte string as the vendor name and
            # a 16 byte string as the model name. We use these strings
            # as the vendor/product name as well as the vendor/product
            # ID.
            #
            # Similary, HAL does not provide a vendor or product ID
            # for the host system itself, so we use the vendor resp.
            # product name as the vendor/product ID for systems too.
            return self.getVendorOrProduct(type_)
        else:
            return self.getProperty('%s.%s_id' % (bus, type_))

    @property
    def vendor_id(self):
        """The vendor ID of this device."""
        return self.getVendorOrProductID('vendor')

    @property
    def product_id(self):
        """The product ID of this device."""
        return self.getVendorOrProductID('product')

    @property
    def vendor_id_for_db(self):
        """The vendor ID in the representation needed for the HWDB tables.

        USB and PCI IDs are represented in the database in hexadecimal,
        while the IDs provided by HAL are integers.

        The SCSI vendor name is right-padded with spaces to 8 bytes.
        """
        bus = self.raw_bus
        format = DB_FORMAT_FOR_VENDOR_ID.get(bus)
        if format is None:
            return self.vendor_id
        else:
            return format % self.vendor_id

    @property
    def product_id_for_db(self):
        """The product ID in the representation needed for the HWDB tables.

        USB and PCI IDs are represented in the database in hexadecimal,
        while the IDs provided by HAL are integers.

        The SCSI product name is right-padded with spaces to 16 bytes.
        """
        bus = self.raw_bus
        format = DB_FORMAT_FOR_PRODUCT_ID.get(bus)
        if format is None:
            return self.product_id
        else:
            return format % self.product_id

    def getDriver(self):
        """Return the HWDriver instance associated with this device.

        Create a HWDriver record, if it does not already exist.
        """
        # HAL and the HWDB client know at present only about kernel
        # drivers, so there is currently no need to search for
        # for user space printer drivers, for example.
        driver_name = self.getProperty('info.linux.driver')
        if driver_name is not None:
            kernel_package_name = self.parser.getKernelPackageName()
            db_driver_set = getUtility(IHWDriverSet)
            return db_driver_set.getOrCreate(kernel_package_name, driver_name)
        else:
            return None

    def ensureVendorIDVendorNameExists(self):
        """Ensure that a useful HWVendorID record for self.vendor_id exists.

        A vendor ID is associated with a vendor name. For many devices
        we rely on the information from the submission to create this
        association in the HWVendorID table.

        We do _not_ use the submitted vendor name for USB, PCI and
        PCCard devices, because we can get them from independent
        sources. See l/c/l/doc/hwdb-device-tables.txt.
        """
        bus = self.real_bus
        if (self.vendor is not None and
            bus not in (HWBus.PCI, HWBus.PCCARD, HWBus.USB)):
            hw_vendor_id_set = getUtility(IHWVendorIDSet)
            hw_vendor_id = hw_vendor_id_set.getByBusAndVendorID(
                bus, self.vendor_id_for_db)
            if hw_vendor_id is None:
                hw_vendor_name_set = getUtility(IHWVendorNameSet)
                hw_vendor_name = hw_vendor_name_set.getByName(self.vendor)
                if hw_vendor_name is None:
                    hw_vendor_name = hw_vendor_name_set.create(self.vendor)
                hw_vendor_id_set.create(
                    self.real_bus, self.vendor_id_for_db, hw_vendor_name)

    def createDBData(self, submission, parent_submission_device):
        """Create HWDB records for this HAL device and its children.

        A HWDevice record for (bus, vendor ID, product ID) of this
        device and a HWDeviceDriverLink record (device, None) are
        created, if they do not already exist.

        A HWSubmissionDevice record is created for (HWDeviceDriverLink,
        submission).

        HWSubmissionDevice records and missing HWDeviceDriverLink
        records for known drivers of this device are created.

        createDBData is called recursively for all real child devices.

        This method may only be called, if self.real_device == True.
        """
        assert self.is_real_device, ('HALDevice.createDBData must be called '
                                     'for real devices only.')
        if not self.has_reliable_data:
            return
        bus = self.real_bus
        vendor_id = self.vendor_id_for_db
        product_id = self.product_id_for_db
        product_name = self.product

        self.ensureVendorIDVendorNameExists()

        db_device = getUtility(IHWDeviceSet).getOrCreate(
            bus, vendor_id, product_id, product_name)
        # Create a HWDeviceDriverLink record without an associated driver
        # for each real device. This will allow us to relate tests and
        # bugs to a device in general as well as to a specific
        # combination of a device and a driver.
        device_driver_link = getUtility(IHWDeviceDriverLinkSet).getOrCreate(
            db_device, None)
        submission_device = getUtility(IHWSubmissionDeviceSet).create(
            device_driver_link, submission, parent_submission_device,
            self.id)
        self.createDBDriverData(submission, db_device, submission_device)

    def createDBDriverData(self, submission, db_device, submission_device):
        """Create HWDB records for drivers of this device and its children.

        This method creates HWDeviceDriverLink and HWSubmissionDevice
        records for this device and its children.
        """
        driver = self.getDriver()
        if driver is not None:
            device_driver_link_set = getUtility(IHWDeviceDriverLinkSet)
            device_driver_link = device_driver_link_set.getOrCreate(
                db_device, driver)
            submission_device = getUtility(IHWSubmissionDeviceSet).create(
                device_driver_link, submission, submission_device, self.id)
        for sub_device in self.children:
            if sub_device.is_real_device:
                sub_device.createDBData(submission, submission_device)
            else:
                sub_device.createDBDriverData(submission, db_device,
                                              submission_device)


class ProcessingLoop(object):
    """An `ITunableLoop` for processing HWDB submissions."""

    implements(ITunableLoop)

    def __init__(self, transaction, logger, max_submissions):
        self.transaction = transaction
        self.logger = logger
        self.max_submissions = max_submissions
        self.valid_submissions = 0
        self.invalid_submissions = 0
        self.finished = False
        self.janitor = getUtility(ILaunchpadCelebrities).janitor

    def _validateSubmission(self, submission):
        submission.status = HWSubmissionProcessingStatus.PROCESSED
        self.valid_submissions += 1

    def _invalidateSubmission(self, submission):
        submission.status = HWSubmissionProcessingStatus.INVALID
        self.invalid_submissions += 1

    def isDone(self):
        """See `ITunableLoop`."""
        return self.finished

    def __call__(self, chunk_size):
        """Process a batch of yet unprocessed HWDB submissions."""
        # chunk_size is a float; we compare it below with an int value,
        # which can lead to unexpected results. Since it is also used as
        # a limit for an SQL query, convert it into an integer.
        chunk_size = int(chunk_size)
        submissions = getUtility(IHWSubmissionSet).getByStatus(
            HWSubmissionProcessingStatus.SUBMITTED,
            user=self.janitor
            )[:chunk_size]
        # Listify the submissions, since we'll have to loop over each
        # one anyway. This saves a COUNT query for getting the number of
        # submissions
        submissions = list(submissions)
        if len(submissions) < chunk_size:
            self.finished = True
        for submission in submissions:
            try:
                parser = SubmissionParser(self.logger)
                success = parser.processSubmission(submission)
                if success:
                    self._validateSubmission(submission)
                else:
                    self._invalidateSubmission(submission)
            except (KeyboardInterrupt, SystemExit):
                # We should never catch these exceptions.
                raise
            except Exception, error:
                info = sys.exc_info()
                message = (
                    'Exception while processing HWDB submission %s'
                    % submission.submission_key)
                properties = [('error-explanation', message)]
                request = ScriptRequest(properties)
                error_utility = ErrorReportingUtility()
                error_utility.raising(info, request)
                self.logger.error('%s (%s)' % (message, request.oopsid))

                self.transaction.abort()
                self._invalidateSubmission(submission)
                # Ensure that this submission is marked as bad, even if
                # further submissions in this batch raise an exception.
                self.transaction.commit()

            if self.max_submissions is not None:
                if self.max_submissions <= (
                    self.valid_submissions + self.invalid_submissions):
                    self.finished = True
                    break
        self.transaction.commit()

def process_pending_submissions(transaction, logger, max_submissions=None):
    """Process pending submissions.

    Parse pending submissions, store extracted data in HWDB tables and
    mark them as either PROCESSED or INVALID.
    """
    loop = ProcessingLoop(transaction, logger, max_submissions)
    # It is hard to predict how long it will take to parse a submission.
    # we don't want to last a DB transaction too long but we also
    # don't want to commit more often than necessary. The LoopTuner
    # handles this for us. The loop's run time will be approximated to
    # 2 seconds, but will never handle more than 50 submissions.
    loop_tuner = LoopTuner(
                loop, 2, minimum_chunk_size=1, maximum_chunk_size=50)
    loop_tuner.run()
    logger.info(
        'Processed %i valid and %i invalid HWDB submissions'
        % (loop.valid_submissions, loop.invalid_submissions))
