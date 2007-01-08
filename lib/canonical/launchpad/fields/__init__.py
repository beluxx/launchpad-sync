# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

from StringIO import StringIO
from textwrap import dedent

from zope.app.content_types import guess_content_type
from zope.component import getUtility
from zope.schema import (
    Bytes, Choice, Field, Int, Text, TextLine, Password, Tuple)
from zope.schema.interfaces import (
    IBytes, IField, IInt, IPassword, IText, ITextLine)
from zope.interface import implements

from canonical.database.sqlbase import cursor
from canonical.launchpad import _
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.name import valid_name
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


# Marker object to tell BaseImageUpload to keep the existing image.
KEEP_SAME_IMAGE = object()


# Field Interfaces
class IStrippedTextLine(ITextLine):
    """A field with leading and trailing whitespaces stripped."""

class ITitle(IStrippedTextLine):
    """A Field that implements a launchpad Title"""

class ISummary(IText):
    """A Field that implements a Summary"""

class IDescription(IText):
    """A Field that implements a Description"""

class IWhiteboard(IText):
    """A Field that implements a Whiteboard"""

class ITimeInterval(ITextLine):
    """A field that captures a time interval in days, hours, minutes."""

class IBugField(IField):
    """A Field that allows entry of a Bug number or nickname"""

class IPasswordField(IPassword):
    """A field that ensures we only use http basic authentication safe
    ascii characters."""

class IShipItRecipientDisplayname(ITextLine):
    """A field used for the recipientdisplayname attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItOrganization(ITextLine):
    """A field used for the organization attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItCity(ITextLine):
    """A field used for the city attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItProvince(ITextLine):
    """A field used for the province attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItAddressline1(ITextLine):
    """A field used for the addressline1 attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItAddressline2(ITextLine):
    """A field used for the addressline2 attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItPhone(ITextLine):
    """A field used for the phone attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItReason(ITextLine):
    """A field used for the reason attribute on shipit forms.

    This is used so we can register a special widget with width constraints to
    this field. The size constraints are a requirement of the shipping company.
    """

class IShipItQuantity(IInt):
    """A field used for the quantity of CDs on shipit forms."""


class ITag(ITextLine):
    """A tag.

    A text line which can be used as a simple text tag.
    """


class IBaseImageUpload(IBytes):
    """Marker interface for ImageUpload fields."""

    max_dimensions = Tuple(
        title=_('Maximun dimensions'),
        description=_('A two-tuple with the maximun width and height (in '
                      'pixels) of this image.'))
    max_size = Int(
        title=_('Maximun size'),
        description=_('The maximun size (in bytes) of this image.'))

    default_image_resource = TextLine(
        title=_('The default image'),
        description=_(
            'The URL of the zope3 resource of the default image that should '
            'be used. Something of the form /@@/nyet-mugshot'))

    def getCurrentImage():
        """Return the value of the field for the object bound to it.

        Raise FieldNotBoundError if the field is not bound to any object.
        """


class StrippedTextLine(TextLine):
    implements(IStrippedTextLine)


# Title
# A field to capture a launchpad object title
class Title(StrippedTextLine):
    implements(ITitle)


# Summary
# A field capture a Launchpad object summary
class Summary(Text):
    implements(ISummary)


# Description
# A field capture a Launchpad object description
class Description(Text):
    implements(IDescription)


# Whiteboard
# A field capture a Launchpad object whiteboard
class Whiteboard(Text):
    implements(IWhiteboard)


# TimeInterval
# A field to capture an interval in time, such as X days, Y hours, Z
# minutes.
class TimeInterval(TextLine):
    implements(ITimeInterval)

    def _validate(self, value):
        if 'mon' in value:
            return 0
        return 1


class BugField(Field):
    implements(IBugField)


class Tag(TextLine):

    implements(ITag)

    def constraint(self, value):
        """Make sure that the value is a valid name."""
        super_constraint = TextLine.constraint(self, value)
        return super_constraint and valid_name(value)


class PasswordField(Password):
    implements(IPasswordField)

    def _validate(self, value):
        # Local import to avoid circular imports
        from canonical.launchpad.interfaces.validation import valid_password
        if not valid_password(value):
            raise LaunchpadValidationError(_(
                "The password provided contains non-ASCII characters."))


class UniqueField(TextLine):
    """Base class for fields that are used for unique attributes."""

    errormessage = _("%s is already taken")
    attribute = None

    @property
    def _content_iface(self):
        """Return the content interface. 

        Override this in subclasses.
        """
        return None

    def _getByAttribute(self, input):
        """Return the content object with the given attribute.

        Override this in subclasses.
        """
        raise NotImplementedError

    def _validate(self, input):
        """Raise a LaunchpadValidationError if the attribute is not available.

        A attribute is not available if it's already in use by another object 
        of this same context. The 'input' should be valid as per TextLine.
        """
        TextLine._validate(self, input)
        assert self._content_iface is not None
        _marker = object()
        if (self._content_iface.providedBy(self.context) and 
            input == getattr(self.context, self.attribute, _marker)):
            # The attribute wasn't changed.
            return

        contentobj = self._getByAttribute(input)
        if contentobj is not None:
            raise LaunchpadValidationError(self.errormessage % input)


class ContentNameField(UniqueField):
    """Base class for fields that are used by unique 'name' attributes."""

    attribute = 'name'

    def _getByAttribute(self, name):
        """Return the content object with the given name."""
        return self._getByName(name)


class BlacklistableContentNameField(ContentNameField):
    """ContentNameField that also need to check against the NameBlacklist
       table in case the name has been blacklisted.
    """
    def _validate(self, input):
        """As per UniqueField._validate, except a LaunchpadValidationError
           is also raised if the name has been blacklisted.
        """
        super(BlacklistableContentNameField, self)._validate(input)

        _marker = object()
        if (self._content_iface.providedBy(self.context) and 
            input == getattr(self.context, self.attribute, _marker)):
            # The attribute wasn't changed.
            return

        name = input.encode('UTF-8')
        cur = cursor()
        cur.execute("SELECT is_blacklisted_name(%(name)s)", vars())
        blacklisted = cur.fetchone()[0]
        if blacklisted:
            raise LaunchpadValidationError(
                    "The name '%(input)s' has been blocked by the "
                    "Launchpad administrators" % vars()
                    )


class ShipItRecipientDisplayname(TextLine):
    implements(IShipItRecipientDisplayname)


class ShipItOrganization(TextLine):
    implements(IShipItOrganization)


class ShipItCity(TextLine):
    implements(IShipItCity)


class ShipItProvince(TextLine):
    implements(IShipItProvince)


class ShipItAddressline1(TextLine):
    implements(IShipItAddressline1)


class ShipItAddressline2(TextLine):
    implements(IShipItAddressline2)


class ShipItPhone(TextLine):
    implements(IShipItPhone)


class ShipItReason(Text):
    implements(IShipItReason)


class ShipItQuantity(Int):
    implements(IShipItQuantity)


class ProductBugTracker(Choice):
    """A bug tracker used by a Product.

    It accepts all the values in the vocabulary, as well as a special
    marker object, which represents the Malone bug tracker.
    This field uses two attributes to model its state, 'official_malone'
    and 'bugtracker'
    """
    malone_marker = object()

    def get(self, ob):
        if ob.official_malone:
            return self.malone_marker
        else:
            return ob.bugtracker

    def set(self, ob, value):
        if self.readonly:
            raise TypeError("Can't set values on read-only fields.")
        if value is self.malone_marker:
            ob.official_malone = True
            ob.bugtracker = None
        else:
            ob.official_malone = False
            ob.bugtracker = value


class FieldNotBoundError(Exception):
    """The field is not bound to any object."""


class BaseImageUpload(Bytes):
    """Base class for ImageUpload fields.

    Any subclass of this one must be used in conjunction with
    ImageUploadWidget and must define the following attributes:
    - max_dimensions: the maximun dimension of the image; a tuple of the
      form (width, height).
    - max_size: the maximun size of the image, in bytes.
    - default_image_resource: the zope3 resource of the image that should be
      used when the user hasn't yet provided one; should be a string of the
      form /@@/<resource-name>
    """

    implements(IBaseImageUpload)

    max_dimensions = ()
    max_size = 0
    default_image_resource = '/@@/nyet-mugshot'

    def getCurrentImage(self):
        if self.context is None:
            raise FieldNotBoundError("This field must be bound to an object.")
        else:
            return getattr(self.context, self.__name__)

    def _valid_image(self, image):
        """Check that the given image is under the given constraints."""
        # No global import to avoid hard dependency on PIL being installed
        import PIL.Image
        if len(image) > self.max_size:
            raise LaunchpadValidationError(_(dedent("""
                This image exceeds the maximum allowed size in bytes.""")))
        try:
            image = PIL.Image.open(StringIO(image))
        except IOError:
            raise LaunchpadValidationError(_(dedent("""
                The file uploaded was not recognized as an image; please
                check it and retry.""")))
        width, height = image.size
        max_width, max_height = self.max_dimensions
        if width > max_width or height > max_height:
            raise LaunchpadValidationError(_(dedent("""
                This image exceeds the maximum allowed width or height in
                pixels.""")))
        return True

    def validate(self, value):
        value.seek(0)
        content = value.read()
        Bytes.validate(self, content)
        self._valid_image(content)

    def set(self, object, value):
        if value is not KEEP_SAME_IMAGE and value is not None:
            value.seek(0)
            content = value.read()
            filename = value.filename
            type, dummy = guess_content_type(name=filename, body=content)
            img = getUtility(ILibraryFileAliasSet).create(
                name=filename, size=len(content), file=StringIO(content),
                contentType=type)
            Bytes.set(self, object, img)
        elif value is None:
            Bytes.set(self, object, None)
        else:
            # Nothing to do; user wants to keep the existing image.
            pass


class LargeImageUpload(BaseImageUpload):

    # The max dimensions here is actually a bit bigger than the advertised
    # one --it's nice to be a bit permissive with user-entered data where we
    # can.
    max_dimensions = (200, 200)
    max_size = 100*1024
    default_image_resource = '/@@/nyet-mugshot'


class SmallImageUpload(BaseImageUpload):

    max_dimensions = (64, 64)
    max_size = 25*1024
    default_image_resource = '/@@/nyet-mini'

