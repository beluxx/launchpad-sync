# (c) Canonical Ltd. 2004
# arch-tag: db407517-732d-47e3-a4c1-c1f8f9dece3a

__metaclass__ = type

import re, os, popen2
from math import ceil
import smtplib
import sys
from xml.sax.saxutils import escape as xml_escape

from zope.component import getUtility
from zope.i18n.interfaces import IUserPreferredLanguages

from canonical.lp.placelessauth.encryption import SSHADigestEncryptor
from canonical.launchpad.interfaces import ILanguages, IPerson
from canonical.launchpad.interfaces import IProjectSet
from canonical.launchpad.database import RosettaLanguage, Person

from canonical.rosetta.poexport import POExport
from canonical.rosetta.pofile import POHeader

charactersPerLine = 50

def count_lines(text):
    count = 0

    for line in text.split('\n'):
        count += int(ceil(float(len(line)) / charactersPerLine))

    return count

def fake_person():
    # XXX: Temporary hack, to be removed as soon as we have the login template
    # working.
    return Person.selectBy(displayname='Foo Bar')[0]

def canonicalise_code(code):
    '''Convert a language code to a standard xx_YY form.'''

    if '-' in code:
        language, country = code.split('-', 1)

        return "%s_%s" % (language, country.upper())
    else:
        return code

def codes_to_languages(codes):
    '''Convert a list of ISO language codes to language objects.'''

    languages = []
    all_languages = getUtility(ILanguages)

    for code in codes:
        try:
            languages.append(all_languages[canonicalise_code(code)])
        except KeyError:
            pass

    return languages

def request_languages(request):
    '''Turn a request into a list of languages to show.'''

    person = IPerson(request.principal, None)

    # If the user is authenticated, try seeing if they have any languages set.

    if person is not None:
        languages = list(person.languages())

        if languages:
            return languages

    # If the user is not authenticated, or they are authenticated but have no
    # languages set, try looking at the HTTP headers for clues.

    codes = IUserPreferredLanguages(request).getPreferredLanguages()

    return codes_to_languages(codes)

def parse_cformat_string(s):
    '''Parse a printf()-style format string into a sequence of interpolations
    and non-interpolations.'''
    if s == '':
        return ()

    match = re.match('(%%|[^%])+', s)

    if match:
        t = match.group(0)
        return (('string', t),) + parse_cformat_string(s[len(t):])

    match = re.match('%[^diouxXeEfFgGcspn]*[diouxXeEfFgGcspn]', s)

    if match:
        t = match.group(0)
        return (('interpolation', t),) + parse_cformat_string(s[len(t):])

    raise ValueError(s)


class ViewProjects:
    def newProjectSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                projects = getUtility(IProjectSet)
                projects.new(
                    name=self.request.form['name'],
                    displayname=self.request.form['displayname'],
                    title=self.request.form['title'],
                    url=self.request.form.get('url', None),
                    description=self.request.form['description'],
                    owner=1
                    )
            else:
                raise RuntimeError("This form must be posted!")

            self.submitted = True
            return "Thank you for submitting the form."
        else:
            self.submitted = False
            return ""

    def requestProjectSubmit(self):
        self.error = None

        if not "SUBMIT" in self.request.form:
            return False

        if not self.request.method == "POST":
            return False

        from_email = 'Rosetta <launchpad@canonical.com>'
        to_email = 'Dafydd Harries <daf@muse.19inch.net>'

        try:
            smtp = smtplib.SMTP('localhost')
            smtp.sendmail(from_email, to_email,
                "From: %s\n"
                "To: %s\n"
                "Subject: Rosetta project request: %s\n"
                "\n"
                "Name: %s\n\n"
                "Homepage: %s\n\n"
                "Download page: %s\n\n"
                "Description\n"
                "-----------\n\n"
                "%s\n\n"
                "Revision Control Information\n"
                "----------------------------\n\n"
                "%s\n"
                % (
                    from_email,
                    to_email,
                    self.request.form['name'],
                    self.request.form['name'],
                    self.request.form['homepage'],
                    self.request.form['download-page'],
                    self.request.form['revision-control-info'],
                    self.request.form['description']))
        except smtplib.SMTPException, e:
            self.error = e
        else:
            smtp.quit()

        return True


class ViewProject:
    def thereAreProducts(self):
        return len(list(self.context.products)) > 0

    def products(self):
        person = IPerson(self.request.principal, None)
        if person is None:
            person = fake_person()

        for product in self.context.rosettaProducts():
            total = 0
            currentCount = 0
            rosettaCount = 0
            updatesCount = 0
            for language in request_languages(self.request):
                total += product.messageCount()
                currentCount += product.currentCount(language.code)
                rosettaCount += product.rosettaCount(language.code)
                updatesCount += product.updatesCount(language.code)

            nonUpdatesCount = currentCount - updatesCount
            translated = currentCount  + rosettaCount
            untranslated = total - translated
            try:
                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100
            except ZeroDivisionError:
                # XXX: I think we will see only this case when we don't have
                # anything to translate.
                currentPercent = 0
                rosettaPercent = 0
                updatesPercent = 0
                nonUpdatesPercent = 0
                translatedPercent = 0
                untranslatedPercent = 100

            # NOTE: To get a 100% value:
            # 1.- currentPercent + rosettaPercent + untranslatedPercent
            # 2.- translatedPercent + untranslatedPercent
            # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
            # untranslatedPercent
            retdict = {
                'name': product.name,
                'title': product.title,
                'poLen': total,
                'poCurrentCount': currentCount,
                'poRosettaCount': rosettaCount,
                'poUpdatesCount' : updatesCount,
                'poNonUpdatesCount' : nonUpdatesCount,
                'poTranslated': translated,
                'poUntranslated': untranslated,
                'poCurrentPercent': currentPercent,
                'poRosettaPercent': rosettaPercent,
                'poUpdatesPercent' : updatesPercent,
                'poNonUpdatesPercent' : nonUpdatesPercent,
                'poTranslatedPercent': translatedPercent,
                'poUntranslatedPercent': untranslatedPercent,
            }

            yield retdict


class ViewProduct:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.languages = request_languages(self.request)

    def thereAreTemplates(self):
        return len(list(self.context.poTemplates())) > 0

    def languageTemplates(self):
        if self.languages:
            for language in self.languages:
                yield LanguageTemplates(language, self.context.poTemplates())
        else:
            raise RuntimeError(
                "Can't generate LanguageTemplates without languages.")


class LanguageTemplates:
    def __init__(self, language, templates):
        self.language = language
        self._templates = templates

    def templates(self):
        for template in self._templates:
            retdict = {
                'name': template.name,
                'title': template.title,
                'poLen': len(template),
                'poCurrentCount': 0,
                'poRosettaCount': 0,
                'poUpdatesCount' : 0,
                'poNonUpdatesCount' : 0,
                'poTranslated': 0,
                'poUntranslated': len(template),
                'poCurrentPercent': 0,
                'poRosettaPercent': 0,
                'poUpdatesPercent' : 0,
                'poNonUpdatesPercent' : 0,
                'poTranslatedPercent': 0,
                'poUntranslatedPercent': 100,
            }

            try:
                poFile = template.poFile(self.language.code)
            except KeyError:
                pass
            else:
                total = len(template)
                currentCount = poFile.currentCount
                rosettaCount = poFile.rosettaCount
                updatesCount = poFile.updatesCount
                nonUpdatesCount = currentCount - updatesCount
                translated = currentCount  + rosettaCount
                untranslated = total - translated

                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100

                # NOTE: To get a 100% value:
                # 1.- currentPercent + rosettaPercent + untranslatedPercent
                # 2.- translatedPercent + untranslatedPercent
                # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
                # untranslatedPercent
                retdict.update({
                    'poLen': total,
                    'poCurrentCount': currentCount,
                    'poRosettaCount': rosettaCount,
                    'poUpdatesCount' : updatesCount,
                    'poNonUpdatesCount' : nonUpdatesCount,
                    'poTranslated': translated,
                    'poUntranslated': untranslated,
                    'poCurrentPercent': currentPercent,
                    'poRosettaPercent': rosettaPercent,
                    'poUpdatesPercent' : updatesPercent,
                    'poNonUpdatesPercent' : nonUpdatesPercent,
                    'poTranslatedPercent': translatedPercent,
                    'poUntranslatedPercent': untranslatedPercent,
                })

            yield retdict


class ViewPOTemplate:
    def num_messages(self):
        N = len(self.context)
        if N == 0:
            return "no messages at all"
        elif N == 1:
            return "1 message"
        else:
            return "%s messages" % N

    # XXX: hardcoded value
    def isPlural(self):
        if len(self.context.sighting('23').pluralText) > 0:
            return True
        else:
            return False

    def languages(self):
        languages = list(self.context.languages())
        languages.sort(lambda a, b: cmp(a.englishName, b.englishName))
        return languages


def traverseIPOTemplate(potemplate, request, name):
    try:
        return potemplate.poFile(name)
    except KeyError:
        pass


class ViewPOFile:
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.header = POHeader(msgstr=context.header)
        self.header.finish()

    def pluralFormExpression(self):
        plural = self.header['Plural-Forms']
        return plural.split(';', 1)[1].split('=',1)[1].split(';', 1)[0].strip();

    def completeness(self):
        return "%.2f%%" % (
            float(self.context.translatedCount()) / len(self.context.poTemplate) * 100)

    def untranslated(self):
        return len(self.context.poTemplate) - len(self.context)

    def editSubmit(self):
        if "SUBMIT" in self.request.form:
            if self.request.method == "POST":
                self.header['Plural-Forms'] = 'nplurals=%s; plural=%s;' % (
                    self.request.form['pluralforms'],
                    self.request.form['expression'])
                self.context.header = self.header.msgstr.encode('utf-8')
                self.context.pluralForms = int(self.request.form['pluralforms'])
            else:
                raise RuntimeError("This form must be posted!")

            self.submitted = True
            return "Thank you for submitting the form."
        else:
            self.submitted = False
            return ""


class TranslatorDashboard:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

    def projects(self):
        return getUtility(IProjectSet)


class ViewPreferences:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

    def languages(self):
        return getUtility(ILanguages)

    def selectedLanguages(self):
        return list(self.person.languages())

    def submit(self):
        person = self.person
        self.submitted_personal = False
        self.error_msg = None

        if "SAVE-LANGS" in self.request.form:
            if self.request.method == "POST":
                oldInterest = list(person.languages())

                if 'selectedlanguages' in self.request.form:
                    if isinstance(self.request.form['selectedlanguages'], list):
                        newInterest = self.request.form['selectedlanguages']
                    else:
                        newInterest = [ self.request.form['selectedlanguages'] ]
                else:
                    newInterest = []

                # XXX: We should fix this, instead of get englishName list, we
                # should get language's code
                for englishName in newInterest:
                    for language in self.languages():
                        if language.englishName == englishName:
                            if language not in oldInterest:
                                person.addLanguage(language)
                for language in oldInterest:
                    if language.englishName not in newInterest:
                        person.removeLanguage(language)
            else:
                raise RuntimeError("This form must be posted!")
        elif "SAVE-PERSONAL" in self.request.form:
            if self.request.method == "POST":
                # First thing to do, check the password if it's wrong we stop.
                currentPassword = self.request.form['currentPassword']
                ssha = SSHADigestEncryptor()
                if currentPassword and ssha.validate(currentPassword, person.password):
                    # The password is valid
                    password1 = self.request.form['newPassword1']
                    password2 = self.request.form['newPassword2']
                    if password1 and password1 == password2:
                        try:
                            person.password = ssha.encrypt(password1)
                        except UnicodeEncodeError:
                            self.error_msg = \
                                "The password can only have ascii characters."
                    elif password1:
                        #The passwords are differents.
                        self.error_msg = \
                            "The two passwords you entered did not match."

                    given = self.request.form['given']
                    if given and person.givenname != given:
                        person.givenname = given
                    family = self.request.form['family']
                    if family and person.familyname != family:
                        person.familyname = family
                    display = self.request.form['display']
                    if display and person.displayname != display:
                        person.displayname = display
                else:
                    self.error_msg = "The username or password you entered is not valid."
            else:
                raise RuntimeError("This form must be posted!")

            self.submitted_personal = True


class ViewSearchResults:
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.projects = getUtility(IProjectSet)
        self.queryProvided = 'q' in request.form and \
            request.form.get('q')
        self.query = request.form.get('q')

        if self.queryProvided:
            self.results = self.projects.search(self.query)
            self.resultCount = self.results.count()
        else:
            self.results = []
            self.resultCount = 0


class ViewPOExport:
    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.poTemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        self.request.response.setHeader('Content-Type', 'application/x-po')
        self.request.response.setHeader('Content-Length', len(exportedFile))
        self.request.response.setHeader('Content-disposition',
                'attachment; filename="%s.po"' % languageCode)
        return exportedFile


class ViewMOExport:

    def __call__(self):
        pofile = self.context
        poExport = POExport(pofile.poTemplate)
        languageCode = pofile.language.code
        exportedFile = poExport.export(languageCode)

        # XXX: It's ok to hardcode the msgfmt path?
        msgfmt = popen2.Popen3('/usr/bin/msgfmt -o - -', True)

        # We feed the command with our .po file from the stdin
        msgfmt.tochild.write(exportedFile)
        msgfmt.tochild.close()

        # Now we wait until the command ends
        status = msgfmt.wait()

        if os.WIFEXITED(status):
            if os.WEXITSTATUS(status) == 0:
                # The command worked
                output = msgfmt.fromchild.read()

                self.request.response.setHeader('Content-Type',
                    'application/x-gmo')
                self.request.response.setHeader('Content-Length',
                    len(output))
                self.request.response.setHeader('Content-disposition',
                    'attachment; filename="%s.mo"' % languageCode)
                return output
            else:
                # XXX: Perhaps we should be more "polite" if it fails
                return msgfmt.childerr.read()
        else:
            # XXX: Perhaps we should be more "polite" if it fails
            return "ERROR exporting the .mo!!"


class TranslatePOTemplate:
    DEFAULT_COUNT = 5

    def __init__(self, context, request):
        # This sets up the following instance variables:
        #
        #  context:
        #    The context PO template object.
        #  request:
        #    The request from the browser.
        #  codes:
        #    A list of codes for the langauges to translate into.
        #  languages:
        #    A list of languages to translate into.
        #  pluralForms:
        #    A dictionary by language code of plural form counts.
        #  badLanguages:
        #    A list of languages for which no plural form information is
        #    available.
        #  offset:
        #    The offset into the template of the first message being
        #    translated.
        #  count:
        #    The number of messages being translated.
        #  error:
        #    A flag indicating whether an error ocurred during initialisation.
        #
        # No initialisation if performed if the request's principal is not
        # authenticated.

        self.person = IPerson(request.principal, None)

        if self.person is None:
            return

        self.context = context
        self.request = request

        self.error = False

        self.codes = request.form.get('languages')

        # Turn language codes into language objects.

        if self.codes:
            self.languages = codes_to_languages(self.codes.split(','))
        else:
            self.languages = request_languages(request)

        # Get plural form and completeness information.

        self.completeness = {}
        self.pluralForms = {}
        self.pluralFormsError = False

        all_languages = getUtility(ILanguages)

        for language in self.languages:
            try:
                pofile = context.poFile(language.code)
            except KeyError:
                if all_languages[language.code].pluralForms is not None:
                    self.pluralForms[language.code] = \
                        all_languages[language.code].pluralForms
                else:
                    # We don't have a default plural form for this Language
                    self.pluralForms[language.code] = None
                    self.error = True
                # As we don't have teh pofile, the completeness is 0
                self.completeness[language.code] = 0
            else:
                self.pluralForms[language.code] = pofile.pluralForms
                self.completeness[language.code] = \
                    float(pofile.translatedCount()) / len(pofile.poTemplate) * 100

        self.badLanguages = [ all_languages[x] for x in self.pluralForms
            if self.pluralForms[x] is None ]

        # Get pagination information.

        if 'offset' in request.form:
            self.offset = int(request.form.get('offset'))
        else:
            self.offset = 0

        if 'count' in request.form:
            self.count = int(request.form.get('count'))
        else:
            self.count = self.DEFAULT_COUNT

    def atBeginning(self):
        return self.offset == 0

    def atEnd(self):
        return self.offset + self.count >= len(self.context)

    def _makeURL(self, **kw):
        parameters = {}

        # Parameters to copy from kwargs or form.
        for name in ('languages', 'count'):
            if name in kw:
                parameters[name] = kw[name]
            elif name in self.request.form:
                parameters[name] = self.request.form.get(name)

        # Parameters to copy from kwargs only.
        for name in ('offset',):
            if name in kw:
                parameters[name] = kw[name]

        if parameters:
            #return str(self.request.URL) + '?' + '&'.join(map(
                #lambda x: x + '=' + str(parameters[x]), parameters))
            keys = parameters.keys()
            keys.sort()
            return str(self.request.URL) + '?' + '&'.join(
                [ x + '=' + str(parameters[x]) for x in keys ])
        else:
            return str(self.request.URL)

    def beginningURL(self):
        return self._makeURL()

    def endURL(self):
        # The largest offset less than the length of the template x that is a
        # multiple of self.count.

        length = len(self.context)

        if length % self.count == 0:
            offset = length - self.count
        else:
            offset = length - (length % self.count)

        if offset == 0:
            return self._makeURL()
        else:
            return self._makeURL(offset = offset)

    def previousURL(self):
        if self.offset - self.count <= 0:
            return self._makeURL()
        else:
            return self._makeURL(offset = self.offset - self.count)

    def nextURL(self):
        if self.offset + self.count >= len(self.context):
            raise ValueError
        else:
            return self._makeURL(offset = self.offset + self.count)

    def _mungeMessageID(self, text, flags):
        # Convert leading and trailing spaces on each line to open boxes.

        lines = []

        for line in xml_escape(text).split('\n'):
            match = re.match('^( *)((?: *[^ ]+)*)( *)$', line)

            if match:
                lines.append(
                    u'\u2423' * len(match.group(1)) +
                    match.group(2) +
                    u'\u2423' * len(match.group(3)))
            else:
                raise AssertionError(
                    "Regular expression that should always match didn't.")

        for i in range(len(lines)):
            if 'c-format' in flags:
                line = ''

                for segment in parse_cformat_string(lines[i]):
                    type, content = segment

                    if type == 'interpolation':
                        line += ('<span class="interpolation">%s</span>'
                            % content)
                    elif type == 'string':
                        line += content

                lines[i] = line

        # Insert arrows and HTML line breaks at newlines.

        return '\n'.join(lines).replace('\n', u'\u21b5<br/>\n')

    def _messageID(self, messageID, flags):
        lines = count_lines(messageID.msgid)

        return {
            'lines' : lines,
            'isMultiline' : lines > 1,
            'text' : messageID.msgid,
            'displayText' : self._mungeMessageID(messageID.msgid, flags)
        }

    def _messageSet(self, set):
        messageIDs = set.messageIDs()
        isPlural = len(list(messageIDs)) > 1
        messageID = self._messageID(messageIDs[0], set.flags())
        translations = {}

        for language in self.languages:
            # XXX: missing exception handling
            translations[language] = \
                set.translationsForLanguage(language.code)

        if isPlural:
            messageIDPlural = self._messageID(messageIDs[1], set.flags())
        else:
            messageIDPlural = None

        return {
            'id' : set.id,
            'isPlural' : isPlural,
            'messageID' : messageID,
            'messageIDPlural' : messageIDPlural,
            'sequence' : set.sequence,
            'fileReferences': set.fileReferences,
            'commentText' : set.commentText,
            'sourceComment' : set.sourceComment,
            'translations' : translations,
        }

    def messageSets(self):
        # XXX: The call to __getitem__() should be replaced with a [] when the
        # implicit __getslice__ problem has been fixed.
        for set in self.context.__getitem__(slice(self.offset, self.offset+self.count)):
            yield self._messageSet(set)

    def submitTranslations(self):
        self.submitted = False

        if not "SUBMIT" in self.request.form:
            return None

        sets = {}

        # Extract msgids from form.

        for key in self.request.form:
            match = re.match('set_(\d+)_msgid$', key)

            if match:
                id = int(match.group(1))
                sets[id] = {}
                sets[id]['msgid'] = self.request.form[key].replace('\r', '')
                sets[id]['translations'] = {}

        # Extract translations from form.

        for key in self.request.form:
            match = re.match(r'set_(\d+)_translation_([a-z]+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)

                sets[id]['translations'][code] = {}
                sets[id]['translations'][code][0] = (
                    self.request.form[key].replace('\r', ''))

                continue

            match = re.match(r'set_(\d+)_translation_([a-z]+)_(\d+)$', key)

            if match:
                id = int(match.group(1))
                code = match.group(2)
                pluralform = int(match.group(3))

                if not code in sets[id]['translations']:
                    sets[id]['translations'][code] = {}

                sets[id]['translations'][code][pluralform] = self.request.form[key]

        # Get/create a PO file for each language.
        # XXX: This should probably be done more lazily.

        pofiles = {}

        for language in self.languages:
            try:
                pofiles[language.code] = self.context.poFile(language.code)
            except KeyError:
                pofiles[language.code] = self.context.newPOFile(
                    self.person, language.code)

        # Put the translations in the database.

        for set in sets.values():
            # XXX: Handle the case where the set is not already in the PO
            # file.

            msgid_text = set['msgid']

            for code in set['translations'].keys():
                new_translations = set['translations'][code]

                # Skip if there are no non-empty translations.

                if not [ x for x in new_translations if x != '' ]:
                    continue

                # Check that this is a translation for a message set that's
                # actually in the template.

                try:
                    pot_set = self.context[msgid_text]
                except KeyError:
                    raise RuntimeError(
                        "Got translation for msgid %s which is not in "
                        "the template." % repr(msgid_text))

                # Get hold of an appropriate message set in the PO file,
                # creating it if necessary.
                # XXX: Message set creation should probably be lazier also.

                try:
                    po_set = pofiles[code][msgid_text]
                except KeyError:
                    po_set = pofiles[code].createMessageSetFromText(msgid_text)

                # Get a hold of a list of existing translations for the
                # message set.

                old_translations = po_set.translations()

                for index in new_translations:
                    # For each translation, add it to the database if it is
                    # non-null and different to the old one.
                    if (new_translations[index] is not None and
                            new_translations[index] != '' and
                            new_translations[index] !=
                            old_translations[index]):
                        po_set.makeTranslationSighting(
                            person = self.person,
                            text = new_translations[index],
                            pluralForm = index,
                            update = True,
                            fromPOFile = False)

        self.submitted = True

        # XXX: Should return the number of new translations or something
        # useful like that.

# XXX: Implement class ViewTranslationEfforts: to create new Efforts

class ViewTranslationEffort:
    def thereAreTranslationEffortCategories(self):
        return len(list(self.context.categories())) > 0

    def languageTranslationEffortCategories(self):
        person = IPerson(self.request.principal, None)
        if person is not None:
            # XXX: Use request_languages().
            for language in person.languages():
                yield LanguageTranslationEffortCategories(language,
                    self.context.categories())
        else:
            # XXX
            person = fake_person()
            # XXX: Use request_languages().
            for language in person.languages():
                yield LanguageTranslationEffortCategories(language,
                    self.context.categories())


class LanguageTranslationEffortCategories:
    def __init__(self, language, translationEffortCategories):
        self.language = language
        self._categories = translationEffortCategories

    # XXX: We should create a common method so we reuse code with
    # LanguageProducts.products()
    def translationEffortCategories(self):
        for category in self._categories:
            total = category.messageCount()
            currentCount = category.currentCount(self.language.code)
            rosettaCount = category.rosettaCount(self.language.code)
            updatesCount = category.updatesCount(self.language.code)
            nonUpdatesCount = currentCount - updatesCount
            translated = currentCount  + rosettaCount
            untranslated = total - translated

            try:
                currentPercent = float(currentCount) / total * 100
                rosettaPercent = float(rosettaCount) / total * 100
                updatesPercent = float(updatesCount) / total * 100
                nonUpdatesPercent = float (nonUpdatesCount) / total * 100
                translatedPercent = float(translated) / total * 100
                untranslatedPercent = float(untranslated) / total * 100
            except ZeroDivisionError:
                # XXX: I think we will see only this case when we don't have
                # anything to translate.
                currentPercent = 0
                rosettaPercent = 0
                updatesPercent = 0
                nonUpdatesPercent = 0
                translatedPercent = 0
                untranslatedPercent = 100

            # NOTE: To get a 100% value:
            # 1.- currentPercent + rosettaPercent + untranslatedPercent
            # 2.- translatedPercent + untranslatedPercent
            # 3.- rosettaPercent + updatesPercent + nonUpdatesPercent +
            # untranslatedPercent
            retdict = {
                'name': category.name,
                'title': category.title,
                'poLen': total,
                'poCurrentCount': currentCount,
                'poRosettaCount': rosettaCount,
                'poUpdatesCount' : updatesCount,
                'poNonUpdatesCount' : nonUpdatesCount,
                'poTranslated': translated,
                'poUntranslated': untranslated,
                'poCurrentPercent': currentPercent,
                'poRosettaPercent': rosettaPercent,
                'poUpdatesPercent' : updatesPercent,
                'poNonUpdatesPercent' : nonUpdatesPercent,
                'poTranslatedPercent': translatedPercent,
                'poUntranslatedPercent': untranslatedPercent,
            }

            yield retdict


# XXX: Is there any way to reuse ViewProduct, we have exactly the same code
# here.
class ViewTranslationEffortCategory:
    def thereAreTemplates(self):
        return len(list(self.context.poTemplates())) > 0

    def languageTemplates(self):
        person = IPerson(self.request.principal, None)
        if person is not None:
            # XXX: Use request_languages().
            for language in person.languages():
                yield LanguageTemplates(language, self.context.poTemplates())
        else:
            # XXX
            person = fake_person()
            # XXX: Use request_languages().
            for language in person.languages():
                yield LanguageTemplates(language, self.context.poTemplates())

#
# XXX Mark Shuttleworth 02/10/04 I've copied this into Doap, maybe Login
#     needs to be common code in some way?
#
class LogIn:

    def isSameHost(self, url):
        """Returns True if the url appears to be from the same host as
        we are."""
        return url.startswith(self.request.getApplicationURL())

    def login(self):
        referer = self.request.getHeader('referer')  # Traditional w3c speling
        if referer and self.isSameHost(referer):
            self.request.response.redirect(referer)
        else:
            self.request.response.redirect(self.request.getURL(1))
        return ''

