import re
from pyPgSQL import PgSQL

from nickname import generate_nick

class SQLThing:
    def __init__(self, dbname):
        self.dbname = dbname
        self.db = PgSQL.connect(database=self.dbname)

    def commit(self):
        return self.db.commit()
    
    def close(self):
        return self.db.close()

    def ensure_string_format(self, name):
        try:
            # check that this is unicode data
            name.decode("utf-8").encode("utf-8")
            return name
        except UnicodeError:
            # check that this is latin-1 data
            s = name.decode("latin-1").encode("utf-8")
            s.decode("utf-8")
            return s

    def _get_dicts(self, cursor):
        names = [x[0] for x in cursor.description]
        ret = []
        for item in cursor.fetchall():
            res = {}
            for i in range(len(names)):
                res[names[i]] = item[i]
            ret.append(res)
        return ret

    def _query_to_dict(self, query, args=None):
        cursor = self._exec(query, args)
        return self._get_dicts(cursor)
        
    def _query(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        results = cursor.fetchall()
        return results
    
    def _query_single(self, query, args=None):
        q = self._query(query, args)
        if len(q) == 1:
            return q[0]
        elif not q:
            return None
        else:
            raise AssertionError, "%s killed us on %s %s" \
                % (len(q), query, args)

    def _exec(self, query, args=None):
        #print repr(query), repr(args)
        cursor = self.db.cursor()
        cursor.execute(query, args or [])
        return cursor

    def _insert(self, table, data):
        keys = data.keys()
        query = "INSERT INTO %s (%s) VALUES (%s)" \
                 % (table, ",".join(keys), ",".join(["%s"] * len(keys)))
        try:
            self._exec(query, data.values())
        except:
            print "Bad things happened, data was %s" % data
            raise

class Katie(SQLThing):
    def getSourcePackageRelease(self, name, version):  
        return self._query_to_dict("""SELECT * FROM source, fingerprint
                                      WHERE  source = %s 
                                      AND    source.sig_fpr = fingerprint.id
                                      AND    version = %s""", (name, version))
    
    def getBinaryPackageRelease(self, name, version, arch):  
        return self._query_to_dict("""SELECT * FROM binaries, architecture, 
                                                    fingerprint
                                      WHERE  package = %s 
                                      AND    version = %s
                                      AND    binaries.sig_fpr = fingerprint.id
                                      AND    binaries.architecture =
                                                architecture.id
                                      AND    arch_string = %s""",
                                        (name, version, arch))

class Launchpad(SQLThing):
    #
    # SourcePackageName
    #
    def ensureSourcePackageName(self, name):
        if self.getSourcePackageName(name):
            return
        name = self.ensure_string_format(name)
        self._insert("sourcepackagename", {"name": name})

    def getSourcePackageName(self, name):
        return self._query_single("""SELECT id FROM sourcepackagename
                                     WHERE name = %s;""", (name,))

    #
    # SourcePackage
    #
    def ensureSourcePackage(self, src):
        if self.getSourcePackage(src.package):
            return

        self.ensureSourcePackageName(src.package)
        name = self.getSourcePackageName(src.package)

        people = self.getPeople(*src.maintainer)[0]
    
        description = self.ensure_string_format(src.description)
        short_desc = description.split("\n")[0]

        data = {
            "maintainer":           people,
            "shortdesc" :           short_desc,
            "distro":               1, # XXX
            "description":          description,
            "sourcepackagename":    name[0]
        }
        self._insert("sourcepackage", data)

    def getSourcePackage(self, name_name):
        self.ensureSourcePackageName(name_name)
        name = self.getSourcePackageName(name_name)
        # FIXME: SELECT * is crap !!!
        return self._query_single("""SELECT * FROM sourcepackage 
                                     WHERE sourcepackagename=%s;""",
                                  (name[0],))
        
    #
    # SourcePackageRelease
    #
    def getSourcePackageRelease(self, name, version):
        src_id = self.getSourcePackage(name)
        if not src_id:
            return None
        #FIXME: SELECT * is crap !!!
        return self._query("""SELECT * FROM sourcepackagerelease
                              WHERE sourcepackage = %s 
                              AND version = %s;""", (src_id[0] , version))

    def createSourcePackageRelease(self, src):
        self.ensureSourcePackage(src)

        srcpkgid = self.getSourcePackage(src.package)[0]
        maintid = self.getPeople(*src.maintainer)[0]
        if src.dsc_signing_key_owner:
            key = self.getGPGKey(src.dsc_signing_key, 
                                 *src.dsc_signing_key_owner)[0]
        else:
            key = None

        dsc = self.ensure_string_format(src.dsc)
        changelog = self.ensure_string_format(src.changelog)
        component = self.getComponentByName(src.component)[0]
        data = {
            "sourcepackage":           srcpkgid,
            "version":                 src.version,
            "dateuploaded":            src.date_uploaded,
            "builddepends":            src.build_depends,
            "builddependsindep":       src.build_depends_indep,
            "architecturehintlist":    src.architecture,
            "component":               component,
            "srcpackageformat":        1,
            "creator":                 maintid,
            "urgency":                 1,
            "changelog":               changelog,
            "dsc":                     dsc,
            "dscsigningkey":           key,
        }                                                          
        self._insert("sourcepackagerelease", data)

        release = self.getSourcePackageRelease(src.package, src.version)[0]
        # 1 - PROPOSED
        # 2 - NEW
        # 3 - ACCEPTED
        # 4 - PUBLISHED
        # 5 - REJECTED
        # 6 - SUPERSEDED
        # 7 - REMOVED
        data = {
            "distrorelease":           1,
            "sourcepackagerelease":    release[0],
            "uploadstatus":            4,
        }
        self._insert("sourcepackagepublishing", data)

    #
    # Build
    #
    #FIXME: DOn't use until we have the DB modification
    def getBuild(self, name, version):
        build_id = self.getBinaryPackage(name, version)
        #FIXME: SELECT * is crap !!!
        return self._query("""SELECT * FROM build 
                              WHERE  id = %s;""", (build_id[0],))

    def createBuild(self, bin):
        srcpkg = self.getSourcePackageRelease(bin.source, bin.source_version)
        if not srcpkg:
            # try handling crap like lamont's world-famous
            # debian-installer 20040801ubuntu16.0.20040928
            bin.source_version = re.sub("\.\d+\.\d+$", "", bin.source_version)
            
            srcpkg = self.getSourcePackageRelease(bin.source,
                                                  bin.source_version)
            if not srcpkg:
                print "\t** FMO courtesy of TROUP & TROUT inc. on %s (%s)" \
                    % (bin.source, bin.source_version)
                return

        if bin.gpg_signing_key_owner:
            key = self.getGPGKey(bin.gpg_signing_key, 
                                 *bin.gpg_signing_key_owner)[0]
        else:
            key = None
    
        data = {
            "processor":            1,
            "distroarchrelease":    1,
            "buildstate":           1,
            "gpgsigningkey":        key,
            "sourcepackagerelease": srcpkg[0][0],
        }
        self._insert("build", data)

        ##FIXME: for god sake !!!!
        return self._query("""SELECT currval('build_id_seq');""")[0]

    #
    # BinaryPackageName
    #
    def getBinaryPackageName(self, name):
        return self._query("""SELECT * FROM binarypackagename 
                              WHERE  name = %s;""", (name,))

    def createBinaryPackageName(self, name):
        name = self.ensure_string_format(name)
        self._insert("binarypackagename", {"name": name})
        
    #
    # BinaryPackage
    #
    def getBinaryPackage(self, name, version):
        bin_id = self.getBinaryPackageName(name)
        if not bin_id:
            return None
        return self._query_single("""SELECT * from binarypackage
                                     WHERE  binarypackagename = %s AND 
                                            version = %s;""", 
                                  (bin_id[0][0], version))

    def createBinaryPackage(self, bin):
        if not self.getBinaryPackageName(bin.package):
            self.createBinaryPackageName(bin.package)
        
        build = self.createBuild(bin)
        if not build:
            # LA VARZEA
            return

        name = self.getBinaryPackageName(bin.package)
        if not name:
            self.createBinaryPackageName(bin.package)
            name = self.getBinaryPackageName(bin.package)

               
        description = self.ensure_string_format(bin.description)
        short_desc = description.split("\n")[0]
        licence = self.ensure_string_format(bin.licence)
        component = self.getComponentByName(bin.component)[0]

        data = {
            "binarypackagename":    name[0][0],
            "component":            component,
            "version":              bin.version,
            "shortdesc":            short_desc,
            "description":          description,
            "build":                build[0],
            "binpackageformat":     1, # XXX
            "section":              1, # XXX
            "priority":             1, # XXX
            "shlibdeps":            bin.shlibs,
            "depends":              bin.depends,
            "suggests":             bin.suggests,
            "recommends":           bin.recommends,
            "conflicts":            bin.conflicts,
            "replaces":             bin.replaces,
            "provides":             bin.provides,
            "essential":            False,
            "installedsize":        bin.installed_size,
            "licence":              licence
        }
        self._insert("binarypackage", data)

        ## Just publish the binary as Warty DistroRelease
        bin_id = self.getBinaryPackage(bin.package, bin.version)
       
        data = {
           "binarypackage":     bin_id[0], 
           "component":         component, 
           "section":           1, # XXX
           "priority":          1, # XXX
           "distroarchrelease": 1, # XXX distroarchrelease
        }
        self._insert("packagepublishing", data)

    #
    # People
    #
    def getPeople(self, name, email):        
        name = self.ensure_string_format(name)
        email = self.ensure_string_format(email)
        self.ensurePerson(name, email)
        return self.getPersonByEmail(email)

    def getPersonByEmail(self, email):
        return self._query_single("""SELECT Person.id FROM Person,emailaddress 
                                     WHERE email = %s AND 
                                           Person.id = emailaddress.person;""",
                                  (email,))
    
    def getPersonByName(self, name):
        return self._query_single("""SELECT Person.id FROM Person
                                     WHERE name = %s""", (name,))
    
    def getPersonByDisplayName(self, displayname):
        return self._query_single("""SELECT Person.id FROM Person 
                                     WHERE displayname = %s""", (displayname,))

    def createPeople(self, name, email):
        print "\tCreating Person %s <%s>" % (name, email)
        name = self.ensure_string_format(name)

        items = name.split()
        if len(items) == 1:
            givenname = name
            familyname = ""
        else:
            givenname = items[0]
            familyname = " ".join(items[1:])

        data = {
            "displayname":  name,
            "givenname":    givenname,
            "familyname":   familyname,
            "name":         generate_nick(email, self.getPersonByName),
        }
        self._insert("person", data)
        pid = self._query_single("SELECT CURRVAL('person_id_seq')")[0]
        self.createEmail(pid, email)
        
    def createEmail(self, pid, email):
        data = {
            "email":    email,
            "person":   pid,
            "status":   1, # XXX
        }
        self._insert("emailaddress", data)

    def ensurePerson(self, name, email):
        people = self.getPersonByEmail(email)
        if people:
            return people
        # XXX this check isn't exactly right -- if there are name
        # collisions, we just add addresses because there is no way to
        # validate them. Bad bad kiko.
        people = self.getPersonByDisplayName(name)
        if people:
            print "\tAdding address <%s> for %s" % (email, name)
            self.createEmail(people[0], email)
            return people
        self.createPeople(name, email)
    
    def getGPGKey(self, key, name, email, id, armor, is_revoked,
                  algorithm, keysize):
        self.ensurePerson(name, email)
        person = self.getPersonByEmail(email)[0]
        ret = self._query_single("""SELECT id FROM gpgkey
                                    WHERE  keyid = %s""", (id,))
        if not ret:
            ret = self.createGPGKey(person, key, id, armor, is_revoked,
                                    algorithm, keysize)
        return ret

    def createGPGKey(self, person, key, id, armor, is_revoked, algorithm,
                     keysize):
        # person      | integer | not null
        # keyid       | text    | not null
        # fingerprint | text    | not null
        # pubkey      | text    | not null
        # revoked     | boolean | not null
        # algorith    | integer | not null
        # keysize     | integer | not null
        data = {
            "person":       person,
            "keyid":        id,
            "fingerprint":  key,
            "pubkey":       armor,
            "revoked":      is_revoked and "True" or "False",
            "algorithm":    algorithm,
            "keysize":      keysize,
        }
        self._insert("gpgkey", data)
        return self._query_single("""SELECT id FROM gpgkey
                                     WHERE id = CURRVAL('gpgkey_id_seq')""")

    #
    # Distro/Release
    #
    def getDistro(self, distro):
        # XXX
        pass

    def getRelease(self, distro, release):
        # XXX
        pass

    def getComponentByName(self, component):
        ret = self._query_single("""SELECT id FROM component 
                                    WHERE  name = %s""", component)
        if not ret:
            raise ValueError, "Component %s not found" % component
        return ret

