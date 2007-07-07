"""Unicode support for CSV files.

Taken from the Python documentation:
http://docs.python.org/lib/csv-examples.html

Adapted to work for Python 2.4.
"""

__metaclass__ = type
__all__ = ['UnicodeReader',
           'UnicodeWriter',
           'UnicodeDictReader',
           'UnicodeDictWriter']


import csv
import codecs
import cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8.
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getencoder(encoding)

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        (data,len_encoded) = self.encoder(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class UnicodeDictReader(csv.DictReader):
    def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                 dialect="excel", encoding="utf-8", *args, **kwds):
        csv.DictReader.__init__(self, f, fieldnames, restkey, restval,
                                dialect, *args, **kwds)
        # overwrite the reader with a UnicodeReader
        self.reader = UnicodeReader(f, dialect, encoding, *args, **kwds)

class UnicodeDictWriter(csv.DictWriter):
    def __init__(self, f, fieldnames, restval="", extrasaction="raise",
                 dialect="excel", encoding="utf-8",
                 *args, **kwds):
        csv.DictWriter.__init__(self, f, fieldnames, restval,
                                extrasaction, dialect, *args, **kwds)
        # overwrite the writer with a UnicodeWriter
        self.writer = UnicodeWriter(f, dialect, encoding, *args, **kwds)
