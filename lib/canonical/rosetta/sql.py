# arch-tag: da5d31ba-6994-4893-b252-83f4f66f0aba

from canonical.arch.sqlbase import SQLBase, quote
from canonical.rosetta.interfaces import IProjects, IProject, IProduct, \
    IPOTemplate, IPOFile, IPOMessageSet, IPOMessageIDSighting, IPOMessageID, \
    IPOTranslationSighting, IPOTranslation, ILanguage, ILanguages, IPerson
from sqlobject import ForeignKey, MultipleJoin, IntCol, BoolCol, StringCol, \
    DateTimeCol
from zope.interface import implements
from canonical.rosetta import pofile
from types import NoneType

__metaclass__ = type

class RosettaProjects:
    implements(IProjects)

    def __iter__(self):
        return iter(RosettaProject.select())

    def __getitem__(self, name):
        # XXX: encoding should not be necessary
        ret = RosettaProject.selectBy(name=name.encode('ascii'))

        if ret.count() == 0:
            raise KeyError, name
        else:
            return ret[0]


    def new(self, name, title, url, description, owner):
        if type(url) != NoneType:
            url = url.encode('ascii')
        return RosettaProject(name=name.encode('ascii'),
            title=title.encode('ascii'), url=url,
            description=description.encode('ascii'),
            owner=owner, datecreated='now')


class RosettaProject(SQLBase):
    implements(IProject)

    _table = 'Project'

    _columns = [
        ForeignKey(name='owner', foreignKey='RosettaPerson', dbName='owner',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('url', dbName='homepageurl')
    ]

    productsIter = MultipleJoin('RosettaProduct', joinColumn='project')

    def products(self):
        return iter(self.productsIter)

    def poTemplates(self):
        for p in self.products():
            for t in p.poTemplates():
                yield t

    def poTemplate(self, name):
        '''SELECT POTemplate.* FROM POTemplate, Product WHERE
            POTemplate.product = Product.id AND
            Product.project = id AND
            POTemplate.name = name;'''
        #raise NotImplementedError
        #import pdb; pdb.set_trace()
        results = RosettaPOTemplate.select('''
            POTemplate.product = Product.id AND
            Product.project = %d AND
            POTemplate.name = %s''' %
            # XXX: encoding should not be necessary
            (self.id, quote(name.encode('ascii'))),
            clauseTables=('Product',))

        if results.count() == 0:
            raise KeyError, name
        else:
            return results[0]


class RosettaProduct(SQLBase):
    implements(IProduct)

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='RosettaProject', dbName='project',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
    ]

    poTemplatesIter = MultipleJoin('RosettaPOTemplate', joinColumn='product')

    def poTemplates(self):
        return iter(self.poTemplatesIter)

    def newPOTemplate(self, name, title):
        return RosettaPOTemplate(name=name, title=title, product=self)


class RosettaPOTemplate(SQLBase):
    implements(IPOTemplate)

    _table = 'POTemplate'

    _columns = [
        ForeignKey(name='product', foreignKey='RosettaProduct', dbName='product',
            notNull=True),
        StringCol('name', dbName='name', notNull=True, unique=True),
        StringCol('title', dbName='title', notNull=True, unique=True),
    ]

    poFilesIter = MultipleJoin('RosettaPOFile', joinColumn='potemplate')

    def poFiles(self):
        return iter(self.poFilesIter)

    def languages(self):
        '''SELECT Language.* FROM POFile, Language WHERE
            POFile.language = Language.id AND
            POFile.potemplate = self.id;'''
        return RosettaLanguage.select('''
            POFile.language = Language.id AND POFile.potemplate = %d
            ''' % self.id, clauseTables=('POFile', 'Language'))

    def poFile(self, code):
        '''SELECT POFile.* FROM POTemplate, POFile, Language WHERE
            POFile.template = POTemplate.id AND
            POFile.language = Language.id AND
            Language.code = code;'''
        ret = RosettaPOFile.select("""
            POFile.potemplate = %d AND
            POFile.language = Language.id AND
            Language.code = %s
            """ % (self.id, quote(code).encode('ascii')),
            clauseTables=('Language',))

        if ret.count() == 0:
            raise KeyError, code
        else:
            return ret[0]

    def __iter__(self):
        '''
        POMsgSet.potemplate = %d AND
        POMsgSet.pofile IS NULL
        '''
        '''
        SELECT POMsgSet.* FROM POMsgSet WHERE
        POMsgSet.potfile = self.id AND
        POMsgSet.iscurrent = true;
        '''
        #return iter(RosettaPOMessageSet.selectBy(poTemplateID = self.id, poFileID = None))
        return iter(RosettaPOMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL
            '''
            % self.id))

    def __getitem__(self, msgid):
        if type(msgid) is unicode:
            msgid = msgid.encode('utf-8')
        msgid_obj = RosettaPOMessageID.selectBy(text=msgid)
        if msgid_obj.count() == 0:
            raise KeyError, msgid
        msgid_obj = msgid_obj[0]
        # XXX: AND sequence != 0
        sets = RosettaPOMessageSet.selectBy(poTemplate=self,
                                            poFile=None,
                                            primeMessageID_=msgid_obj)
        if sets.count() == 0:
            raise KeyError, msgid
        else:
            return sets[0]

    def __len__(self):
        '''Same query as __iter__, but with COUNT.'''
        #raise NotImplementedError
        return RosettaPOMessageSet.select(
            '''
            POMsgSet.potemplate = %d AND
            POMsgSet.pofile IS NULL
            '''
            % self.id).count()


class RosettaPOFile(SQLBase):
    implements(IPOFile)

    _table = 'POFile'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate',
            dbName='potemplate', notNull=True),
        ForeignKey(name='language', foreignKey='RosettaLanguage', dbName='language',
            notNull=True),
        StringCol(name='topComment', dbName='topcomment', notNull=True),
        StringCol(name='header', dbName='header', notNull=True),
        BoolCol(name='headerFuzzy', dbName='fuzzyheader', notNull=True)
        # XXX: missing fields
    ]

    # XXX: ???
    messageSetsIter = MultipleJoin('RosettaPOMessageSet', joinColumn='pofile')

    def messageSet(self):
        return iter(self.messageSetsIter)

    def __iter__(self):
        return iter(self.messageSets)

    # XXX: not implemented
    def __len__(self):
        '''Count of __iter__.'''
        return 26

    def __getitem__(self, messageSet):
        '''
        SELECT POMessageSet.* FROM
            POMsgSet poSet,
            POMsgSet potSet,
            POTemplate self,
            POFile pofile,
            POMsgID pomsgid
        WHERE
            pofile.potemplate = {self.id} AND
            poSet.pofile = pofile.id AND
            poSet.primemsgid = pomsgid.id AND
            potSet.potemplate = {self.poTemplate.id} AND
            potSet.primemsgid = pomsgid.id;
        '''
        res = RosettaPOMessageSet.select('''
            pofile.potemplate = %d AND
            poSet.id = %d AND
            poSet.primemsgid = pomsgid.id AND
            potSet.potemplate = %d AND
            potSet.primemsgid = pomsgid.id''' % \
            (self.id, messageSet.id, self.poTemplate.id),
            clauseTables = [
                'POMsgSet poSet',
                'POMsgSet potSet',
                'POTemplate template',
                'POFile pofile',
                'POMsgID pomsgid',
                ])
        if res.count() == 0:
            raise KeyError, messageSet.id
        return res[0]

    def translated(self):
        '''
        SELECT POMsgSet.* FROM
            POMsgSet,
            POTranslationSighting
        WHERE
            POMsgSet.pofile = self.id AND
            POTranslationSighting.pomsgset = POMsgSet.id;
        '''
        raise NotImplementedError


    # XXX: not implemented
    def translated_count(self):
        '''Same as translated(), but with COUNT.'''
        return 14

    def untranslated(self):
        '''XXX'''
        raise NotImplementedError

    # XXX: not implemented
    def untranslated_count(self):
        '''Same as untranslated(), but with COUNT.'''
        return 9


class RosettaPOMessageSet(SQLBase):
    implements(IPOMessageSet)

    _table = 'POMsgSet'

    _columns = [
        ForeignKey(name='poTemplate', foreignKey='RosettaPOTemplate', dbName='potemplate', notNull=True),
        ForeignKey(name='poFile', foreignKey='RosettaPOFile', dbName='pofile', notNull=False),
        ForeignKey(name='primeMessageID_', foreignKey='RosettaPOMessageID', dbName='primemsgid', notNull=True),
        IntCol(name='sequence', dbName='sequence', notNull=True),
        BoolCol(name='isComplete', dbName='iscomplete', notNull=True),
        BoolCol(name='fuzzy', dbName='fuzzy', notNull=True),
        BoolCol(name='obsolete', dbName='obsolete', notNull=True),
        StringCol(name='commentText', dbName='commenttext', notNull=False),
        StringCol(name='fileReferences', dbName='filereferences', notNull=False),
        StringCol(name='sourceComment', dbName='sourcecomment', notNull=False),
        StringCol(name='flagsComment', dbName='flagscomment', notNull=False),
    ]

    def messageIDs(self):
        return RosettaPOMessageID.select('''
            POMsgIDSighting.pomsgset = %d AND
            POMsgIDSighting.pomsgid = POMsgID.id
            ''' % self.id, clauseTables=('POMsgIDSighting',))

    def getMessageIDSighting(self, plural_form):
        """Return the message ID sighting that is current and has the
        plural form provided."""
        ret = RosettaPOMessageIdSighting.selectBy(poMessageSet=self,
                                                   pluralForm=plural_form)
        if ret.count() == 0:
            raise KeyError, plural_form
        else:
            return ret[0]


    def translations(self):
        return RosettaPOTranslation.select('''
            POTranslationSighting.pomsgset = %d AND
            POTranslationSighting.potranslation = POTranslation.id
            ''' % self.id, clauseTables=('POTranslationSighting',))

    def getTranslationsForThatPOMessageSetOverThere(self):
        '''
        SELECT DISTINCT ON (sighting.pluralform) sighting.* FROM
            POMsgSet potset,
            POMsgSet poset,
            POFile pofile,
            POTranslation translation,
            POTranslationSighting sighting
            WHERE
            potset.id = 5 AND
            potset.pofile IS NULL AND
            potset.potemplate = pofile.potemplate AND
            pofile.id = poset.pofile AND
            potset.primemsgid = poset.primemsgid AND
            poset.id = sighting.pomsgset AND
            sighting.potranslation = translation.id
            ORDER BY sighting.pluralform, sighting.lasttouched
        '''

    def getTranslationSighting(self, plural_form):
        """Return the translation sighting that is current and has the
        plural form provided."""


class RosettaEditPOMessageSet(RosettaPOMessageSet):
    """Interface for editing a MessageSet."""

    def makeMessageIDSighting(self, text, plural_form):
        """Return a new message ID sighting that points back to us."""
        messageIDs = RosettaPOMessageID.selectBy(text=text)
        if messageIDs.count() == 0:
            messageID = RosettaPOMessageID(text=text)
        else:
            messageID = messageIDs[0]
        existing = RosettaPOMessageIDSighting.selectBy(
            poMessageSet=self,
            poMessageID=messageID,
            pluralForm=plural_form)
        if existing.count():
            existing = existing[0]
            existing.touch()
            return existing
        return RosettaPOMessageIDSighting(
            poMessageSet=self,
            poMessageID=messageID,
            firstSeen="NOW",
            lastSeen="NOW",
            isCurrent=True,
            pluralForm=plural_form)

    def makeTranslationSighting(self, text, plural_form):
        """Return a new translation sighting that points back to us."""
        translations = RosettaPOTranslation.selectBy(text=text)
        if translations.count() == 0:
            translation = RosettaPOTranslation(text=text)
        else:
            translation = translations[0]
        existing = RosettaPOTranslationSighting.selectBy(
            poMessageSet=self,
            poTranslation=translation,
            pluralForm=plural_form,
            person='XXX FIXME')
        if existing.count():
            existing = existing[0]
            existing.touch()
            return existing
        return RosettaPOTranslationSighting(
            poMessageSet=self,
            poTranslation=translation,
            firstSeen="NOW",
            lastTouched="NOW",
            isCurrent=True,
            pluralForm=plural_form,
            deprecated=False,
            person='XXX FIXME')


class RosettaPOMessageIDSighting(SQLBase):
    implements(IPOMessageIDSighting)

    _table = 'POMsgIDSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMsgSet', dbName='pomsgset', notNull=True),
        ForeignKey(name='poMessageID', foreignKey='RosettaPOMsgID', dbName='pomsgid', notNull=True),
        DateTimeCol(name='firstSeen', dbName='firstseen', notNull=True),
        DateTimeCol(name='lastSeen', dbName='lastseen', notNull=True),
        BoolCol(name='inPOFile', dbName='inpofile', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
    ]


class RosettaPOMessageID(SQLBase):
    implements(IPOMessageID)

    _table = 'POMsgID'

    _columns = [
        StringCol(name='text', dbName='msgid', notNull=True, unique=True)
    ]

class RosettaPOTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

    _table = 'POTranslationSighting'

    _columns = [
        ForeignKey(name='poMessageSet', foreignKey='RosettaPOMessageSet',
            dbName='pomsgset', notNull=True),
        ForeignKey(name='poTranslation', foreignKey='RosettPOTranslation',
            dbName='potranslation', notNull=True),
        ForeignKey(name='person', foreignKey='RosettaPerson',
            dbName='person', notNull=True),
        # license
        DateTimeCol(name='firstSeen', dbName='firstseen', notNull=True),
        DateTimeCol(name='lastTouched', dbName='lasttouched', notNull=True),
        BoolCol(name='inPOFile', dbName='inpofile', notNull=True),
        IntCol(name='pluralForm', dbName='pluralform', notNull=True),
        BoolCol(name='deprecated', dbName='deprecated', notNull=True),
    ]


class RosettaPOTranslation(SQLBase):
    implements(IPOTranslation)

    _table = 'POTranslation'

    _columns = [
        StringCol(name='text', dbName='translation', notNull=True, unique=True)
    ]

class RosettaLanguages:
    implements(ILanguages)

    def __getitem__(self, code):
        return RosettaLanguage.selectBy(code=code)

    def keys(self):
        code = RosettaLanguage.select()
        for code in iter(RosettaLanguage.select()):
            yield code

class RosettaLanguage(SQLBase):
    implements(ILanguage)

    _table = 'Language'

    _columns = [
        StringCol(name='code', dbName='code', notNull=True, unique=True),
        StringCol(name='nativeName', dbName='nativename'),
        StringCol(name='englishName', dbName='englishname')
    ]

class RosettaPerson(SQLBase):
    implements(IPerson)

    _table = 'Person'

    _columns = [
        StringCol(name='presentationName', dbName='presentationname')
    ]

#    isMaintainer
#    isTranslator
#    isContributor

    # Invariant: isMaintainer implies isContributor

    # XXX: not implemented
    def maintainedProjects(self):
        '''SELECT Project.* FROM Project
            WHERE Project.owner = self.id
            '''

    # XXX: not implemented
    def translatedProjects(self):
        '''SELECT Project.* FROM Project, Product, POTemplate, POFile
            WHERE
                POFile.owner = self.id AND
                POFile.template = POTemplate.id AND
                POTemplate.product = Product.id AND
                Product.project = Project.id
            ORDER BY ???
            '''

    # XXX: not fully implemented
    def languages(self):
        for code in ('cy', 'es'):
            yield RosettaLanguage.selectBy(code=code)[0]

# XXX: Should we use principal instead of hard code Joe Example?
def personFromPrincipal(principal):
    ret = RosettaPerson.selectBy(presentationName = 'Joe Example')
    if ret.count() == 0:
        raise KeyError, principal
    else:
        return ret[0]
